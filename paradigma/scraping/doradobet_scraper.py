"""
Scraper de DoradoBet — plataforma Altenar.

DoradoBet usa Altenar como backend (sb2frontend-altenar2.biahosted.com).
La API devuelve eventos y odds en JSON limpio via endpoints:
  - /api/widget/GetUpcoming  → pre-match
  - /api/widget/GetLivenow   → live (no nos interesa por ahora)

Interceptamos la respuesta de GetUpcoming para extraer odds de fútbol.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# URL de fútbol en DoradoBet (sport ID 66 = fútbol)
DORADOBET_FOOTBALL_URL = "https://doradobet.com/deportes/66"

# Dominio de la API Altenar
ALTENAR_DOMAIN = "sb2frontend-altenar2.biahosted.com"

# Directorio de debug
DEBUG_DIR = Path("scraping_debug")


class DoradoBetScraper:
    """Scrapea odds de DoradoBet interceptando la API de Altenar."""

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    def scrape_football_odds(self) -> tuple[dict, list[dict]]:
        """
        Scrapea odds de fútbol de DoradoBet.

        Returns:
            soft_odds: dict compatible con ev_calculator.py
                {event_id: {market: {(outcome_name, point): odds}}}
            events_info: lista con info de cada evento
        """
        from playwright.sync_api import sync_playwright, Response

        api_responses: list[dict] = []

        def on_response(response: Response):
            """Captura respuestas de la API de Altenar."""
            url = response.url
            parsed = urlparse(url)
            domain = parsed.netloc

            if ALTENAR_DOMAIN not in domain:
                return

            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                return

            try:
                body = response.json()
            except Exception:
                return

            path = parsed.path.lower()
            size_kb = len(response.text()) / 1024

            logger.info(f"  📡 Altenar: {parsed.path} ({size_kb:.1f}KB)")

            api_responses.append({
                "path": parsed.path,
                "body": body,
                "size_kb": size_kb,
            })

        logger.info("Iniciando scraping de DoradoBet (Altenar)...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--ignore-certificate-errors"],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                ignore_https_errors=True,
            )
            page = ctx.new_page()
            page.on("response", on_response)

            logger.info(f"Navegando a {DORADOBET_FOOTBALL_URL}")
            try:
                page.goto(
                    DORADOBET_FOOTBALL_URL,
                    wait_until="networkidle",
                    timeout=self.timeout_ms,
                )
                page.wait_for_timeout(5_000)
            except Exception as e:
                logger.warning(f"Timeout en carga inicial: {e}")

            # Scroll para cargar más eventos
            logger.info("Scrolling para cargar más eventos...")
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2_000)

            browser.close()

        logger.info(f"Capturadas {len(api_responses)} respuestas de Altenar")

        # Guardar respuestas raw para debug
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        debug_file = DEBUG_DIR / f"doradobet_raw_{ts}.json"

        # Solo guardar estructura (no todo el body para no ser enorme)
        debug_data = []
        for r in api_responses:
            entry = {"path": r["path"], "size_kb": r["size_kb"]}
            body = r["body"]
            if isinstance(body, dict):
                entry["keys"] = list(body.keys())
                # Para cada key, mostrar tipo y tamaño
                for k, v in body.items():
                    if isinstance(v, list):
                        entry[f"_{k}_len"] = len(v)
                        if v and isinstance(v[0], dict):
                            entry[f"_{k}_first_keys"] = list(v[0].keys())
                            entry[f"_{k}_first_sample"] = json.dumps(v[0], default=str)[:2000]
                    elif isinstance(v, dict):
                        entry[f"_{k}_keys"] = list(v.keys())[:20]
            debug_data.append(entry)

        debug_file.write_text(json.dumps(debug_data, indent=2, default=str, ensure_ascii=False))
        logger.info(f"Debug guardado en {debug_file}")

        # Buscar la respuesta de GetUpcoming (la más grande con odds)
        upcoming_data = None
        for r in api_responses:
            path_lower = r["path"].lower()
            if "getupcoming" in path_lower or "upcoming" in path_lower:
                upcoming_data = r["body"]
                logger.info(f"  → Usando GetUpcoming ({r['size_kb']:.1f}KB)")
                break

        if upcoming_data is None:
            # Fallback: buscar la respuesta JSON más grande que tenga 'events'
            for r in sorted(api_responses, key=lambda x: -x["size_kb"]):
                if isinstance(r["body"], dict) and "events" in r["body"]:
                    upcoming_data = r["body"]
                    logger.info(f"  → Usando fallback: {r['path']} ({r['size_kb']:.1f}KB)")
                    break

        if upcoming_data is None:
            logger.error("No se encontró respuesta con datos de eventos")
            logger.info(f"Respuestas capturadas:")
            for r in api_responses:
                keys = list(r["body"].keys()) if isinstance(r["body"], dict) else "N/A"
                logger.info(f"  {r['path']} ({r['size_kb']:.1f}KB) keys={keys}")
            return {}, []

        # Parsear la respuesta de Altenar
        return self._parse_altenar_response(upcoming_data)

    def _parse_altenar_response(self, data: dict) -> tuple[dict, list[dict]]:
        """
        Parsea la respuesta de la API de Altenar.

        Estructura real de Altenar:
        {
            "events": [{"id", "name": "Home vs. Away", "marketIds": [...], "competitorIds": [...], "startDate"}],
            "markets": [{"id", "name": "1x2", "typeId", "oddIds": [...]}],
            "odds": [{"id", "price", "name", "competitorId", "typeId"}],
        }

        Las relaciones son por arrays de IDs:
          event.marketIds → market.id
          market.oddIds   → odd.id
        """
        events_raw = data.get("events", [])
        markets_raw = data.get("markets", [])
        odds_raw = data.get("odds", [])

        logger.info(
            f"Altenar data: {len(events_raw)} events, "
            f"{len(markets_raw)} markets, {len(odds_raw)} odds"
        )

        if not events_raw:
            logger.warning("No se encontraron eventos en la respuesta")
            logger.info(f"Keys en data: {list(data.keys())}")
            for k, v in data.items():
                if isinstance(v, list):
                    logger.info(f"  {k}: list[{len(v)}]")
                    if v and isinstance(v[0], dict):
                        logger.info(f"    first item keys: {list(v[0].keys())[:15]}")
                elif isinstance(v, dict):
                    logger.info(f"  {k}: dict keys={list(v.keys())[:10]}")
                else:
                    logger.info(f"  {k}: {type(v).__name__} = {str(v)[:100]}")
            return {}, []

        # Indexar markets por su ID
        markets_by_id: dict[int, dict] = {}
        for mkt in markets_raw:
            mid = mkt.get("id")
            if mid is not None:
                markets_by_id[mid] = mkt

        # Indexar odds por su ID
        odds_by_id: dict[int, dict] = {}
        for odd in odds_raw:
            oid = odd.get("id")
            if oid is not None:
                odds_by_id[oid] = odd

        # Log muestra para debug
        if events_raw:
            sample = events_raw[0]
            logger.info(f"  Sample event keys: {list(sample.keys())[:15]}")
        if markets_raw:
            sample = markets_raw[0]
            logger.info(f"  Sample market keys: {list(sample.keys())[:15]}")
        if odds_raw:
            sample = odds_raw[0]
            logger.info(f"  Sample odd keys: {list(sample.keys())[:15]}")

        # Construir output
        soft_odds = {}
        events_info = []
        parsed_count = 0

        for evt in events_raw:
            eid = evt.get("id")
            if eid is None:
                continue
            eid_str = str(eid)

            # Resolver markets de este evento via marketIds
            event_market_ids = evt.get("marketIds", [])
            event_markets = [markets_by_id[mid] for mid in event_market_ids if mid in markets_by_id]

            # Para cada market, resolver sus odds via oddIds
            markets_with_odds = []
            for mkt in event_markets:
                odd_ids = mkt.get("oddIds", [])
                mkt_odds = [odds_by_id[oid] for oid in odd_ids if oid in odds_by_id]
                markets_with_odds.append((mkt, mkt_odds))

            parsed = self._parse_event(evt, markets_with_odds)
            if parsed is None:
                continue

            parsed_count += 1
            if parsed["markets"]:
                soft_odds[eid_str] = parsed["markets"]

            events_info.append({
                "event_id": eid_str,
                "home_team": parsed["home"],
                "away_team": parsed["away"],
                "league": parsed["league"],
                "commence_time": parsed["start_time"],
                "sport_key": "soccer",
                "sport_title": f"Soccer - {parsed['league']}",
                "book_key": "doradobet",
                "book_name": "DoradoBet",
            })

        logger.info(
            f"DoradoBet: {parsed_count} eventos parseados, "
            f"{len(soft_odds)} con odds"
        )

        return soft_odds, events_info

    def _parse_event(self, evt: dict, markets_with_odds: list[tuple[dict, list[dict]]]) -> Optional[dict]:
        """Parsea un evento individual de Altenar.

        Args:
            evt: evento raw con keys: id, name, competitorIds, startDate, marketIds, etc.
            markets_with_odds: lista de (market_dict, [odd_dict, ...]) ya resueltos por ID.
        """
        # Nombre viene como "Home vs. Away" o "Home - Away"
        name = evt.get("name") or ""
        home, away = "", ""
        for sep in (" vs. ", " vs ", " - "):
            if sep in name:
                parts = name.split(sep, 1)
                home, away = parts[0].strip(), parts[1].strip()
                break

        if not home or not away:
            return None

        league = (evt.get("leagueName") or evt.get("categoryName")
                  or evt.get("champName") or evt.get("competitionName") or "")
        start_time = evt.get("startDate") or evt.get("date") or ""

        # Parsear odds de cada mercado
        h2h_odds = {}
        totals_odds = {}
        spreads_odds = {}

        for mkt, mkt_odds in markets_with_odds:
            mkt_type = mkt.get("typeId") or mkt.get("type") or 0
            mkt_name = (mkt.get("name") or "").lower()

            # Identificar tipo de mercado por typeId o nombre
            is_h2h = (mkt_type == 1 or "1x2" in mkt_name or "match result" in mkt_name
                      or "full time result" in mkt_name)
            is_totals = (mkt_type in (17, 18, 21, 28) or "over/under" in mkt_name
                         or "total" in mkt_name)
            is_spreads = (mkt_type in (3, 4, 14, 15) or "handicap" in mkt_name
                          or "spread" in mkt_name or "asian handicap" in mkt_name)

            for odd in mkt_odds:
                price = odd.get("price")
                if price is None:
                    continue
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    continue
                if price <= 1.0:
                    continue

                outcome_name = odd.get("name") or ""
                # Altenar usa specialValue, handicap, o line para puntos
                point = (odd.get("specialValue") or odd.get("points")
                         or odd.get("handicap") or odd.get("line"))

                if is_h2h:
                    name_lower = outcome_name.lower().strip()
                    # Altenar h2h names: equipo nombre, "1", "X", "2", o "Draw"
                    if name_lower in ("1",) or name_lower == home.lower():
                        h2h_odds[("Home", None)] = price
                    elif name_lower in ("x", "draw", "tie"):
                        h2h_odds[("Draw", None)] = price
                    elif name_lower in ("2",) or name_lower == away.lower():
                        h2h_odds[("Away", None)] = price
                    elif home.lower() in name_lower:
                        h2h_odds[("Home", None)] = price
                    elif away.lower() in name_lower:
                        h2h_odds[("Away", None)] = price

                elif is_totals and point is not None:
                    try:
                        pt = float(point)
                    except (ValueError, TypeError):
                        continue
                    name_lower = outcome_name.lower()
                    if "over" in name_lower or name_lower == "o":
                        totals_odds[("Over", pt)] = price
                    elif "under" in name_lower or name_lower == "u":
                        totals_odds[("Under", pt)] = price

                elif is_spreads and point is not None:
                    try:
                        pt = float(point)
                    except (ValueError, TypeError):
                        continue
                    name_lower = outcome_name.lower()
                    if name_lower in ("1", "home") or home.lower() in name_lower:
                        spreads_odds[(home, pt)] = price
                    elif name_lower in ("2", "away") or away.lower() in name_lower:
                        spreads_odds[(away, pt)] = price

        result_markets = {}
        if h2h_odds:
            result_markets["h2h"] = h2h_odds
        if totals_odds:
            result_markets["totals"] = totals_odds
        if spreads_odds:
            result_markets["spreads"] = spreads_odds

        return {
            "home": home,
            "away": away,
            "league": league,
            "start_time": start_time,
            "markets": result_markets,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scraper = DoradoBetScraper(headless=False)
    soft_odds, events_info = scraper.scrape_football_odds()

    print(f"\n{'='*60}")
    print(f"DoradoBet: {len(events_info)} eventos, {len(soft_odds)} con odds")
    print(f"{'='*60}")

    for evt in events_info[:10]:
        eid = evt["event_id"]
        markets = soft_odds.get(eid, {})
        market_str = ", ".join(f"{k}({len(v)})" for k, v in markets.items())
        print(f"  {evt['home_team']} vs {evt['away_team']} [{evt['league']}] → {market_str}")
