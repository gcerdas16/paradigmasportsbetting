"""
Scrapers para 888sport y BetSafe.

Descubrimiento via API sniffer (2026-04-27):
    - 888sport migró de Kambi a plataforma "Spectate" propia
      API: spectate-web.888sport.es
    - BetSafe (grupo Betsson) usa su propia API proxy
      API: www.betsafe.com/api/sb/v1/
    - El CDN público de Kambi (eu-offering.kambicdn.org) está bloqueado/inaccesible

Ambos requieren Playwright para interceptar las respuestas JSON.

Uso:
    from paradigma.scraping.kambi_scraper import Sport888Scraper, BetSafeScraper
    scraper = Sport888Scraper()
    soft_odds, events_info = scraper.scrape_football_odds()
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEBUG_DIR = Path("scraping_debug")

# Registro de casas para scanner_v2
BOOK_CONFIGS = {
    "888sport": {
        "name": "888sport",
        "scraper_class": "Sport888Scraper",
    },
    "betsafe": {
        "name": "BetSafe",
        "scraper_class": "BetSafeScraper",
    },
}


# ---------------------------------------------------------------------------
# 888sport — Plataforma Spectate
# ---------------------------------------------------------------------------

class Sport888Scraper:
    """
    Scrapea 888sport via interceptación de su API Spectate.

    API descubierta:
        spectate-web.888sport.es/spectate/sportsbook-req/getUpcomingEvents/football/today
        → keys: selection_pointers, events, event_order, match_request_limit
    """

    FOOTBALL_URL = "https://www.888sport.es/futbol/"
    API_DOMAIN = "spectate-web.888sport.es"

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    def scrape_football_odds(self) -> tuple[dict, list[dict]]:
        from playwright.sync_api import sync_playwright, Response

        api_responses: list[dict] = []

        def on_response(response: Response):
            url = response.url
            if self.API_DOMAIN not in url:
                return
            if response.status != 200:
                return
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type and "javascript" not in content_type:
                return
            try:
                body = response.json()
                api_responses.append({"url": url, "data": body})
                logger.info(f"  888sport API: {url[:80]}...")
            except Exception:
                pass

        logger.info("Iniciando scraping de 888sport (Spectate)...")

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

            try:
                logger.info(f"  Navegando a {self.FOOTBALL_URL}")
                page.goto(self.FOOTBALL_URL, wait_until="networkidle",
                         timeout=self.timeout_ms)
                page.wait_for_timeout(5_000)
            except Exception as e:
                logger.warning(f"  Timeout en carga: {e}")

            # Scroll para cargar más eventos
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2_000)

            # Intentar clics en ligas populares
            try:
                league_links = page.query_selector_all(
                    'a[href*="premier"], a[href*="liga"], a[href*="bundesliga"], '
                    'a[href*="serie-a"], a[href*="ligue"]'
                )
                for link in league_links[:5]:
                    try:
                        link.click()
                        page.wait_for_timeout(3_000)
                    except Exception:
                        continue
            except Exception:
                pass

            page.wait_for_timeout(3_000)
            browser.close()

        logger.info(f"  888sport: {len(api_responses)} API responses capturadas")

        # Guardar debug
        self._save_debug(api_responses)

        # Parsear
        soft_odds, events_info = self._parse_spectate(api_responses)
        logger.info(f"  888sport: {len(soft_odds)} eventos con odds")
        return soft_odds, events_info

    def _parse_spectate(self, responses: list[dict]) -> tuple[dict, list[dict]]:
        """Parsea respuestas de la API Spectate de 888sport."""
        soft_odds = {}
        events_info = []
        seen = set()

        for resp in responses:
            data = resp["data"]
            if not isinstance(data, dict):
                continue

            events = data.get("events", {})
            if not events:
                # Buscar recursivamente
                for key, val in data.items():
                    if isinstance(val, dict) and "events" in val:
                        events = val["events"]
                        break

            if not isinstance(events, dict):
                if isinstance(events, list):
                    for evt in events:
                        self._parse_888_event(evt, soft_odds, events_info, seen)
                continue

            for evt_id, evt_data in events.items():
                self._parse_888_event(evt_data, soft_odds, events_info, seen,
                                     fallback_id=evt_id)

        return soft_odds, events_info

    def _parse_888_event(self, evt: dict, soft_odds: dict,
                         events_info: list, seen: set,
                         fallback_id: str = ""):
        """Parsea un evento individual de la API Spectate."""
        if not isinstance(evt, dict):
            return

        # Buscar nombres de equipo
        home = (evt.get("home_name") or evt.get("homeName") or
                evt.get("home") or evt.get("homeTeam") or "")
        away = (evt.get("away_name") or evt.get("awayName") or
                evt.get("away") or evt.get("awayTeam") or "")

        # Intentar extraer de nombre combinado
        if not home or not away:
            name = evt.get("name", "") or evt.get("event_name", "")
            for sep in [" v ", " vs ", " - ", " – "]:
                if sep in name:
                    parts = name.split(sep, 1)
                    home, away = parts[0].strip(), parts[1].strip()
                    break

        if not home or not away:
            return

        event_id = str(evt.get("id") or evt.get("event_id") or
                       evt.get("eventId") or fallback_id)
        if not event_id or event_id in seen:
            return
        seen.add(event_id)

        league = (evt.get("competition") or evt.get("league") or
                  evt.get("competitionName") or "")
        start_time = (evt.get("start_time") or evt.get("startTime") or
                      evt.get("start") or "")

        # Buscar odds en la estructura del evento
        markets = self._extract_888_markets(evt, home, away)

        if markets:
            soft_odds[event_id] = markets

        events_info.append({
            "event_id": event_id,
            "home_team": home,
            "away_team": away,
            "league": str(league),
            "commence_time": str(start_time),
            "sport_key": "soccer",
            "sport_title": f"Soccer - {league}",
            "book_key": "888sport",
            "book_name": "888sport",
        })

    @staticmethod
    def _extract_888_markets(evt: dict, home: str, away: str) -> dict:
        """Extrae mercados/odds de un evento Spectate."""
        markets = {}

        # Buscar en sub-objetos que contengan odds/selections/markets
        for key in ("selections", "markets", "odds", "betOffers",
                    "match_markets", "prices"):
            container = evt.get(key)
            if not container:
                continue

            if isinstance(container, list):
                for item in container:
                    _parse_generic_selection(item, home, away, markets)
            elif isinstance(container, dict):
                for mk, mv in container.items():
                    if isinstance(mv, list):
                        for item in mv:
                            _parse_generic_selection(item, home, away, markets)
                    elif isinstance(mv, dict):
                        _parse_generic_selection(mv, home, away, markets)

        # Buscar odds directamente en el evento (flat)
        h2h = {}
        for hk in ("odds_home", "home_odds", "1"):
            if hk in evt:
                try:
                    h2h[(home, None)] = float(evt[hk])
                except (ValueError, TypeError):
                    pass
        for dk in ("odds_draw", "draw_odds", "X"):
            if dk in evt:
                try:
                    h2h[("Draw", None)] = float(evt[dk])
                except (ValueError, TypeError):
                    pass
        for ak in ("odds_away", "away_odds", "2"):
            if ak in evt:
                try:
                    h2h[(away, None)] = float(evt[ak])
                except (ValueError, TypeError):
                    pass
        if h2h:
            markets.setdefault("h2h", {}).update(h2h)

        return markets

    def _save_debug(self, responses: list[dict]):
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = DEBUG_DIR / f"888sport_spectate_{ts}.json"
        serializable = []
        for r in responses:
            try:
                json.dumps(r)
                serializable.append(r)
            except (TypeError, ValueError):
                serializable.append({"url": r.get("url", ""), "error": "not serializable"})
        path.write_text(json.dumps(serializable, indent=2, default=str))
        logger.info(f"  Debug: {path}")


# ---------------------------------------------------------------------------
# BetSafe — Betsson Group API
# ---------------------------------------------------------------------------

class BetSafeScraper:
    """
    Scrapea BetSafe via interceptación de su API Betsson.

    API descubierta:
        www.betsafe.com/api/sb/v1/widgets/event-market/v1
        → data.events, data.markets, data.marketSelections, data.scoreboards
    """

    FOOTBALL_URL = "https://www.betsafe.com/es/apuestas-deportivas/futbol?tab=liveAndUpcoming"
    API_PATH_PREFIX = "/api/sb/v1/"

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    def scrape_football_odds(self) -> tuple[dict, list[dict]]:
        from playwright.sync_api import sync_playwright, Response

        api_responses: list[dict] = []

        def on_response(response: Response):
            url = response.url
            if self.API_PATH_PREFIX not in url:
                return
            if response.status != 200:
                return
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                return
            try:
                body = response.json()
                size_kb = len(response.text()) / 1024
                api_responses.append({"url": url, "data": body, "size_kb": size_kb})
                logger.info(f"  BetSafe API: {url[:80]}... ({size_kb:.0f}KB)")
            except Exception:
                pass

        logger.info("Iniciando scraping de BetSafe (Betsson API)...")

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

            try:
                logger.info(f"  Navegando a {self.FOOTBALL_URL}")
                page.goto(self.FOOTBALL_URL, wait_until="networkidle",
                         timeout=self.timeout_ms)
                page.wait_for_timeout(5_000)
            except Exception as e:
                logger.warning(f"  Timeout en carga: {e}")

            # Scroll para cargar más
            for _ in range(8):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2_000)

            page.wait_for_timeout(3_000)
            browser.close()

        logger.info(f"  BetSafe: {len(api_responses)} API responses capturadas")

        # Guardar debug
        self._save_debug(api_responses)

        # Parsear
        soft_odds, events_info = self._parse_betsson(api_responses)
        logger.info(f"  BetSafe: {len(soft_odds)} eventos con odds")
        return soft_odds, events_info

    def _parse_betsson(self, responses: list[dict]) -> tuple[dict, list[dict]]:
        """Parsea respuestas de la API Betsson de BetSafe."""
        soft_odds = {}
        events_info = []
        seen = set()

        for resp in responses:
            url = resp["url"]
            data = resp["data"]

            # El endpoint principal es event-market/v1
            if "event-market" not in url and "view" not in url:
                continue

            if not isinstance(data, dict):
                continue

            inner = data.get("data", data)
            if not isinstance(inner, dict):
                continue

            events_map = inner.get("events", {})
            markets_map = inner.get("markets", {})
            selections_map = inner.get("marketSelections", {})

            if not events_map:
                continue

            # events_map puede ser dict o list
            if isinstance(events_map, list):
                for evt in events_map:
                    self._parse_betsafe_event(
                        evt, markets_map, selections_map,
                        soft_odds, events_info, seen
                    )
            elif isinstance(events_map, dict):
                for evt_id, evt in events_map.items():
                    self._parse_betsafe_event(
                        evt, markets_map, selections_map,
                        soft_odds, events_info, seen,
                        fallback_id=str(evt_id)
                    )

        return soft_odds, events_info

    def _parse_betsafe_event(self, evt: dict, markets_map, selections_map,
                              soft_odds: dict, events_info: list,
                              seen: set, fallback_id: str = ""):
        """Parsea un evento de BetSafe."""
        if not isinstance(evt, dict):
            return

        # Nombres de equipo
        home = (evt.get("homeName") or evt.get("home") or
                evt.get("homeTeamName") or "")
        away = (evt.get("awayName") or evt.get("away") or
                evt.get("awayTeamName") or "")

        # Intentar extraer de nombre combinado
        if not home or not away:
            name = evt.get("name", "") or evt.get("eventName", "")
            for sep in [" v ", " vs ", " - ", " – ", " @ "]:
                if sep in name:
                    parts = name.split(sep, 1)
                    home, away = parts[0].strip(), parts[1].strip()
                    break

        # Intentar desde participantes/competitors
        if not home or not away:
            participants = evt.get("participants") or evt.get("competitors") or []
            if isinstance(participants, list) and len(participants) >= 2:
                home = participants[0].get("name", "") if isinstance(participants[0], dict) else str(participants[0])
                away = participants[1].get("name", "") if isinstance(participants[1], dict) else str(participants[1])

        if not home or not away:
            return

        event_id = str(evt.get("id") or evt.get("eventId") or fallback_id)
        if not event_id or event_id in seen:
            return
        seen.add(event_id)

        league = (evt.get("competition") or evt.get("league") or
                  evt.get("categoryName") or evt.get("groupName") or "")
        start_time = (evt.get("startTime") or evt.get("start") or
                      evt.get("startDate") or "")

        # Buscar mercados asociados a este evento
        markets = {}

        # Método 1: market IDs en el evento
        market_ids = evt.get("marketIds") or evt.get("markets") or []
        if isinstance(market_ids, list):
            for mid in market_ids:
                mid_str = str(mid)
                if isinstance(markets_map, dict) and mid_str in markets_map:
                    mkt = markets_map[mid_str]
                    self._parse_betsafe_market(
                        mkt, mid_str, selections_map, home, away, markets
                    )

        # Método 2: buscar por event_id en markets_map
        if not markets and isinstance(markets_map, dict):
            for mid, mkt in markets_map.items():
                if isinstance(mkt, dict):
                    mkt_event_id = str(mkt.get("eventId") or mkt.get("event_id") or "")
                    if mkt_event_id == event_id:
                        self._parse_betsafe_market(
                            mkt, str(mid), selections_map, home, away, markets
                        )

        # Método 3: odds directamente en el evento
        if not markets:
            markets = Sport888Scraper._extract_888_markets(evt, home, away)

        if markets:
            soft_odds[event_id] = markets

        events_info.append({
            "event_id": event_id,
            "home_team": home,
            "away_team": away,
            "league": str(league),
            "commence_time": str(start_time),
            "sport_key": "soccer",
            "sport_title": f"Soccer - {league}",
            "book_key": "betsafe",
            "book_name": "BetSafe",
        })

    @staticmethod
    def _parse_betsafe_market(mkt: dict, mkt_id: str, selections_map,
                               home: str, away: str, markets: dict):
        """Parsea un mercado de BetSafe y extrae odds."""
        if not isinstance(mkt, dict):
            return

        mkt_name = str(mkt.get("name") or mkt.get("marketName") or
                       mkt.get("type") or mkt_id).lower()

        # Obtener selections (odds) de este mercado
        selection_ids = mkt.get("selectionIds") or mkt.get("selections") or []
        selections = []

        if isinstance(selection_ids, list) and isinstance(selections_map, dict):
            for sid in selection_ids:
                sid_str = str(sid)
                if sid_str in selections_map:
                    selections.append(selections_map[sid_str])
        elif isinstance(selection_ids, list):
            # selections_map podría estar inlined
            selections = [s for s in selection_ids if isinstance(s, dict)]

        # También buscar selections directamente en el mercado
        if not selections:
            for key in ("outcomes", "selections", "odds"):
                val = mkt.get(key)
                if isinstance(val, list):
                    selections = val
                    break

        if not selections:
            return

        # Clasificar mercado
        is_h2h = any(k in mkt_name for k in ["1x2", "match winner", "fulltime",
                                               "full time", "match result",
                                               "moneyline", "winner"])
        is_total = any(k in mkt_name for k in ["over", "under", "total",
                                                 "goals"])
        is_spread = any(k in mkt_name for k in ["handicap", "spread", "asian",
                                                  "hcap"])

        for sel in selections:
            if not isinstance(sel, dict):
                continue

            odds = sel.get("odds") or sel.get("price") or sel.get("decimal")
            if odds is None:
                continue
            try:
                odds = float(odds)
                if odds > 100:
                    odds = odds / 1000.0
            except (ValueError, TypeError):
                continue
            if odds <= 1.0:
                continue

            label = str(sel.get("name") or sel.get("label") or
                       sel.get("selectionName") or "")
            line = sel.get("line") or sel.get("handicap") or sel.get("points")

            if is_total and line is not None:
                try:
                    line = float(line)
                    if line > 100:
                        line = line / 1000.0
                except (ValueError, TypeError):
                    continue
                if "totals" not in markets:
                    markets["totals"] = {}
                if "over" in label.lower():
                    markets["totals"][("Over", line)] = odds
                elif "under" in label.lower():
                    markets["totals"][("Under", line)] = odds

            elif is_spread and line is not None:
                try:
                    line = float(line)
                    if abs(line) > 100:
                        line = line / 1000.0
                except (ValueError, TypeError):
                    continue
                if "spreads" not in markets:
                    markets["spreads"] = {}
                if label == home or "1" == label or "home" in label.lower():
                    markets["spreads"][(home, line)] = odds
                elif label == away or "2" == label or "away" in label.lower():
                    markets["spreads"][(away, -line)] = odds

            elif is_h2h or (not is_total and not is_spread):
                if "h2h" not in markets:
                    markets["h2h"] = {}
                if label == home or "1" == label or "home" in label.lower():
                    markets["h2h"][(home, None)] = odds
                elif label.lower() in ("draw", "x", "empate"):
                    markets["h2h"][("Draw", None)] = odds
                elif label == away or "2" == label or "away" in label.lower():
                    markets["h2h"][(away, None)] = odds

    def _save_debug(self, responses: list[dict]):
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = DEBUG_DIR / f"betsafe_betsson_{ts}.json"
        serializable = []
        for r in responses:
            try:
                json.dumps(r)
                serializable.append(r)
            except (TypeError, ValueError):
                serializable.append({"url": r.get("url", ""), "error": "not serializable"})
        path.write_text(json.dumps(serializable, indent=2, default=str))
        logger.info(f"  Debug: {path}")


# ---------------------------------------------------------------------------
# Helper compartido
# ---------------------------------------------------------------------------

def _parse_generic_selection(item: dict, home: str, away: str, markets: dict):
    """Parsea una selección/outcome genérica e intenta clasificarla."""
    if not isinstance(item, dict):
        return

    odds = item.get("odds") or item.get("price") or item.get("decimal")
    if odds is None:
        return
    try:
        odds = float(odds)
        if odds > 100:
            odds = odds / 1000.0
    except (ValueError, TypeError):
        return
    if odds <= 1.0:
        return

    label = str(item.get("name") or item.get("label") or
                item.get("selection_name") or "")
    mkt_type = str(item.get("market_type") or item.get("type") or
                   item.get("marketName") or "").lower()

    line = item.get("line") or item.get("handicap") or item.get("points")

    if "total" in mkt_type or "over" in mkt_type:
        if line is not None:
            try:
                line = float(line)
            except (ValueError, TypeError):
                return
            if "totals" not in markets:
                markets["totals"] = {}
            if "over" in label.lower():
                markets["totals"][("Over", line)] = odds
            elif "under" in label.lower():
                markets["totals"][("Under", line)] = odds
    elif "handicap" in mkt_type or "spread" in mkt_type:
        if line is not None:
            try:
                line = float(line)
            except (ValueError, TypeError):
                return
            if "spreads" not in markets:
                markets["spreads"] = {}
            if label == home or "home" in label.lower():
                markets["spreads"][(home, line)] = odds
            elif label == away or "away" in label.lower():
                markets["spreads"][(away, -line)] = odds
    else:
        if "h2h" not in markets:
            markets["h2h"] = {}
        if label == home or label == "1" or "home" in label.lower():
            markets["h2h"][(home, None)] = odds
        elif label.lower() in ("draw", "x", "empate"):
            markets["h2h"][("Draw", None)] = odds
        elif label == away or label == "2" or "away" in label.lower():
            markets["h2h"][(away, None)] = odds


# ---------------------------------------------------------------------------
# Factory para scanner_v2
# ---------------------------------------------------------------------------

def create_scraper(book_key: str, headless: bool = True):
    """Crea el scraper correcto según book_key."""
    if book_key == "888sport":
        return Sport888Scraper(headless=headless)
    elif book_key == "betsafe":
        return BetSafeScraper(headless=headless)
    else:
        raise ValueError(f"book_key '{book_key}' no válido. Opciones: {list(BOOK_CONFIGS.keys())}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="888sport / BetSafe scraper")
    parser.add_argument(
        "--book", type=str, default="888sport",
        choices=list(BOOK_CONFIGS.keys()),
        help="Casa a scrapear",
    )
    parser.add_argument("--no-headless", action="store_true",
                       help="Mostrar browser")
    args = parser.parse_args()

    scraper = create_scraper(args.book, headless=not args.no_headless)
    soft_odds, events_info = scraper.scrape_football_odds()

    book_name = BOOK_CONFIGS[args.book]["name"]
    print(f"\n{'='*60}")
    print(f"{book_name} — Eventos con odds: {len(soft_odds)}")
    print(f"{'='*60}")

    for info in events_info[:30]:
        eid = info["event_id"]
        if eid in soft_odds:
            markets = soft_odds[eid]
            print(f"\n  {info['home_team']} vs {info['away_team']}")
            print(f"    Liga: {info['league']}")
            for mkt_name, outcomes in markets.items():
                print(f"    {mkt_name}:")
                for (name, point), odds_val in outcomes.items():
                    pt_str = f" {point}" if point is not None else ""
                    print(f"      {name}{pt_str}: {odds_val:.4f}")
