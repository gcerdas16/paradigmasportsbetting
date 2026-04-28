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

    # Ligas europeas para capturar más eventos (overlap con Pinnacle)
    LEAGUE_URLS = [
        "https://www.888sport.es/futbol/champions-league/",
        "https://www.888sport.es/futbol/europa-league/",
        "https://www.888sport.es/futbol/premier-league/",
        "https://www.888sport.es/futbol/la-liga/",
        "https://www.888sport.es/futbol/bundesliga/",
        "https://www.888sport.es/futbol/serie-a/",
        "https://www.888sport.es/futbol/ligue-1/",
    ]

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
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2_000)

            # Navegar a ligas europeas para capturar más eventos
            for league_url in self.LEAGUE_URLS:
                try:
                    logger.info(f"  888sport liga: {league_url.split('/')[-2]}")
                    page.goto(league_url, wait_until="networkidle",
                             timeout=self.timeout_ms)
                    page.wait_for_timeout(3_000)
                    for _ in range(2):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1_500)
                except Exception as e:
                    logger.warning(f"  Error en liga 888: {e}")
                    continue

            page.wait_for_timeout(2_000)
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

        # Estructura 888sport Spectate confirmada:
        # evt["markets"][mkt_id]["selections"][sel_id]["decimal_price"] = "5.500"
        # evt["markets"][mkt_id]["selections"][sel_id]["type"] = "1"/"X"/"2"
        # evt["markets"][mkt_id]["name"] = "Ganador del partido"

        for key in ("markets", "selections", "odds", "betOffers",
                    "match_markets", "prices"):
            container = evt.get(key)
            if not container:
                continue

            if isinstance(container, list):
                for item in container:
                    _parse_generic_selection(item, home, away, markets)
            elif isinstance(container, dict):
                for mk, mv in container.items():
                    if not isinstance(mv, dict):
                        continue
                    # Spectate: market dict con sub-dict "selections"
                    sels = mv.get("selections")
                    if isinstance(sels, dict):
                        mkt_name = str(mv.get("name", "")).lower()
                        for sel_id, sel in sels.items():
                            if isinstance(sel, dict):
                                # Inyectar market_name para clasificación
                                sel_copy = dict(sel)
                                sel_copy["_market_name"] = mkt_name
                                _parse_generic_selection(sel_copy, home, away, markets)
                    elif isinstance(mv, list):
                        for item in mv:
                            _parse_generic_selection(item, home, away, markets)
                    else:
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

    # Ligas individuales para capturar 1X2 (no aparece en liveAndUpcoming)
    LEAGUE_URLS = [
        "https://www.betsafe.com/es/apuestas-deportivas/futbol/champions-league",
        "https://www.betsafe.com/es/apuestas-deportivas/futbol/europa-league",
        "https://www.betsafe.com/es/apuestas-deportivas/futbol/premier-league",
        "https://www.betsafe.com/es/apuestas-deportivas/futbol/la-liga",
        "https://www.betsafe.com/es/apuestas-deportivas/futbol/bundesliga",
        "https://www.betsafe.com/es/apuestas-deportivas/futbol/serie-a",
        "https://www.betsafe.com/es/apuestas-deportivas/futbol/ligue-1",
    ]

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

            # Cargar página principal primero
            try:
                logger.info(f"  Navegando a {self.FOOTBALL_URL}")
                page.goto(self.FOOTBALL_URL, wait_until="networkidle",
                         timeout=self.timeout_ms)
                page.wait_for_timeout(5_000)
            except Exception as e:
                logger.warning(f"  Timeout en carga inicial: {e}")

            # Scroll en la página principal
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2_000)

            # Navegar a cada liga para capturar 1X2 y otros mercados
            for league_url in self.LEAGUE_URLS:
                try:
                    logger.info(f"  Navegando a liga: {league_url.split('/')[-1]}")
                    page.goto(league_url, wait_until="networkidle",
                             timeout=self.timeout_ms)
                    page.wait_for_timeout(3_000)
                    # Scroll en liga
                    for _ in range(3):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1_500)
                except Exception as e:
                    logger.warning(f"  Error en liga: {e}")
                    continue

            page.wait_for_timeout(2_000)

            # ── Paso clave: fetch explícito de MW3W (1X2) ──
            # BetSafe no carga odds 1X2 automáticamente — hay que pedirlas
            mw3w_ids = self._collect_mw3w_market_ids(api_responses)
            if mw3w_ids:
                logger.info(f"  Fetching {len(mw3w_ids)} mercados MW3W explícitamente...")
                # Hacer en batches de 20 para no sobrecargar
                for i in range(0, len(mw3w_ids), 20):
                    batch = mw3w_ids[i:i+20]
                    ids_param = ",".join(batch)
                    fetch_url = f"/api/sb/v1/widgets/event-market/v1?includescoreboards=true&marketids={ids_param}"
                    try:
                        result = page.evaluate(f"""
                            fetch('{fetch_url}')
                                .then(r => r.json())
                                .catch(e => ({{ error: e.message }}))
                        """)
                        if isinstance(result, dict) and "error" not in result:
                            api_responses.append({
                                "url": f"https://www.betsafe.com{fetch_url}",
                                "data": result,
                                "size_kb": 0,
                            })
                            logger.info(f"  MW3W batch {i//20+1}: OK")
                        else:
                            logger.warning(f"  MW3W batch {i//20+1}: {result}")
                    except Exception as e:
                        logger.warning(f"  MW3W fetch error: {e}")
            else:
                logger.info("  No se encontraron market IDs MW3W para fetch")

            browser.close()

        logger.info(f"  BetSafe: {len(api_responses)} API responses capturadas")

        # Guardar debug
        self._save_debug(api_responses)

        # Parsear
        soft_odds, events_info = self._parse_betsson(api_responses)
        logger.info(f"  BetSafe: {len(soft_odds)} eventos con odds")
        return soft_odds, events_info

    @staticmethod
    def _collect_mw3w_market_ids(responses: list[dict]) -> list[str]:
        """
        Busca en responses interceptadas los event IDs que tienen MW3W
        y construye los market IDs para fetch explícito.
        """
        mw3w_ids = set()

        for resp in responses:
            data = resp.get("data", {})
            if not isinstance(data, dict):
                continue
            inner = data.get("data", data)
            if not isinstance(inner, dict):
                continue

            # Buscar en markets (lista) los que tengan marketTemplateId MW3W
            markets = inner.get("markets", [])
            if isinstance(markets, list):
                for mkt in markets:
                    if isinstance(mkt, dict):
                        tmpl = str(mkt.get("marketTemplateId", "")).upper()
                        if tmpl == "MW3W":
                            mid = mkt.get("id", "")
                            if mid:
                                mw3w_ids.add(str(mid))

            # Buscar en events que tengan marketTemplateIds incluyendo MW3W
            events = inner.get("events", [])
            if isinstance(events, list):
                for evt in events:
                    if not isinstance(evt, dict):
                        continue
                    templates = evt.get("marketTemplateIds", [])
                    if isinstance(templates, list) and "MW3W" in templates:
                        eid = evt.get("id", "")
                        if eid:
                            # Construir market ID: m-{eventId}-MW3W
                            mw3w_ids.add(f"m-{eid}-MW3W")
            elif isinstance(events, dict):
                for eid, evt in events.items():
                    if not isinstance(evt, dict):
                        continue
                    templates = evt.get("marketTemplateIds", [])
                    if isinstance(templates, list) and "MW3W" in templates:
                        mw3w_ids.add(f"m-{eid}-MW3W")

        return list(mw3w_ids)

    def _parse_betsson(self, responses: list[dict]) -> tuple[dict, list[dict]]:
        """Parsea respuestas de la API Betsson de BetSafe."""
        soft_odds = {}
        events_info = []
        seen = set()

        for resp in responses:
            url = resp["url"]
            data = resp["data"]

            # Endpoints relevantes: event-market, view, popular-bets
            if not any(x in url for x in ["event-market", "view", "popular-bets"]):
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

    def _parse_betsafe_event(self, evt: dict, markets_list: list,
                              selections_list: list,
                              soft_odds: dict, events_info: list,
                              seen: set, fallback_id: str = ""):
        """Parsea un evento de BetSafe (estructura real confirmada)."""
        if not isinstance(evt, dict):
            return

        # Estructura real: participants[i]["label"], participants[i]["side"]
        home = ""
        away = ""
        participants = evt.get("participants") or evt.get("competitors") or []
        if isinstance(participants, list) and len(participants) >= 2:
            # Ordenar por side: 1=home, 2=away
            sorted_parts = sorted(participants,
                                  key=lambda p: p.get("side", 0) if isinstance(p, dict) else 0)
            for part in sorted_parts:
                if not isinstance(part, dict):
                    continue
                name = part.get("label") or part.get("name") or ""
                side = part.get("side", 0)
                if side == 1 or (not home and side != 2):
                    home = name
                elif side == 2 or (not away):
                    away = name

        # Fallback: extraer de label combinado
        if not home or not away:
            label = evt.get("label") or evt.get("name") or evt.get("eventName") or ""
            for sep in [" v ", " vs ", " - ", " \u2013 ", " @ "]:
                if sep in label:
                    parts = label.split(sep, 1)
                    home, away = parts[0].strip(), parts[1].strip()
                    break

        if not home or not away:
            return

        event_id = str(evt.get("id") or evt.get("eventId") or fallback_id)
        if not event_id or event_id in seen:
            return
        seen.add(event_id)

        league = (evt.get("competitionName") or evt.get("competition") or
                  evt.get("categoryName") or evt.get("groupName") or "")
        start_time = (evt.get("startDate") or evt.get("startTime") or
                      evt.get("start") or "")

        # Buscar mercados del evento en la lista de markets
        markets = {}

        # markets_list es una LISTA de dicts con "eventId" y "marketTemplateId"
        evt_markets = []
        if isinstance(markets_list, list):
            for mkt in markets_list:
                if isinstance(mkt, dict) and str(mkt.get("eventId", "")) == event_id:
                    evt_markets.append(mkt)

        for mkt in evt_markets:
            mkt_id = str(mkt.get("id", ""))
            template = str(mkt.get("marketTemplateId", "")).upper()

            # Encontrar selections de este mercado
            mkt_sels = []
            if isinstance(selections_list, list):
                for sel in selections_list:
                    if isinstance(sel, dict) and str(sel.get("marketId", "")) == mkt_id:
                        mkt_sels.append(sel)

            if not mkt_sels:
                continue

            self._classify_and_store(
                template, mkt, mkt_sels, home, away, markets
            )

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
    def _classify_and_store(template: str, mkt: dict, mkt_sels: list,
                            home: str, away: str, markets: dict):
        """
        Clasifica mercado por marketTemplateId y almacena odds.

        Templates BetSafe confirmados:
            MHDA  = Match Winner / 1X2
            MWOU  = Over/Under totals
            AGSNAB = Asian Handicap / Spread
            BTTS  = Both Teams to Score (ignorar)
            DC    = Double Chance (ignorar)
        """
        mkt_name = str(mkt.get("name") or mkt.get("marketName") or "").lower()

        # Clasificar por template ID
        is_h2h = template in ("MW3W", "MHDA", "FT1X2", "1X2")
        is_total = template in ("MWOU", "OU", "FTOU")
        is_spread = template in ("AGSNAB", "AH", "FTAH", "HC")

        # Fallback: clasificar por nombre
        if not is_h2h and not is_total and not is_spread:
            if any(k in mkt_name for k in ["1x2", "match winner", "full time result",
                                            "ganador", "winner"]):
                is_h2h = True
            elif any(k in mkt_name for k in ["over", "under", "total", "goles"]):
                is_total = True
            elif any(k in mkt_name for k in ["handicap", "spread", "hándicap"]):
                is_spread = True
            else:
                return  # Skip unknown markets

        for sel in mkt_sels:
            if not isinstance(sel, dict):
                continue

            odds = sel.get("odds") or sel.get("price")
            if odds is None:
                continue
            try:
                odds = float(odds)
            except (ValueError, TypeError):
                continue
            if odds <= 1.0:
                continue

            label = str(sel.get("label") or sel.get("name") or "").strip()
            line = sel.get("line") or sel.get("handicap") or sel.get("points")

            if is_h2h:
                if "h2h" not in markets:
                    markets["h2h"] = {}
                if label == home:
                    markets["h2h"][(home, None)] = odds
                elif label.lower() in ("draw", "x", "empate"):
                    markets["h2h"][("Draw", None)] = odds
                elif label == away:
                    markets["h2h"][(away, None)] = odds

            elif is_total and line is not None:
                try:
                    line = float(line)
                except (ValueError, TypeError):
                    continue
                if "totals" not in markets:
                    markets["totals"] = {}
                if "over" in label.lower() or "m\u00e1s" in label.lower():
                    markets["totals"][("Over", line)] = odds
                elif "under" in label.lower() or "menos" in label.lower():
                    markets["totals"][("Under", line)] = odds

            elif is_spread and line is not None:
                try:
                    line = float(line)
                except (ValueError, TypeError):
                    continue
                if "spreads" not in markets:
                    markets["spreads"] = {}
                if label == home:
                    markets["spreads"][(home, line)] = odds
                elif label == away:
                    markets["spreads"][(away, -line)] = odds

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

    # 888sport usa "decimal_price" (string), BetSafe usa "odds" (float)
    odds = (item.get("decimal_price") or item.get("odds") or
            item.get("price") or item.get("decimal"))
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
    # 888sport Spectate: "type" = "1"/"X"/"2" para 1X2
    sel_type = str(item.get("type", ""))
    mkt_name = str(item.get("_market_name") or item.get("market_type") or
                   item.get("marketName") or "").lower()

    line = item.get("line") or item.get("handicap") or item.get("points")

    if "total" in mkt_name or "over" in mkt_name or "under" in mkt_name:
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
    elif "handicap" in mkt_name or "spread" in mkt_name:
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
        # 1X2 / Match Winner — usar type si disponible
        if "h2h" not in markets:
            markets["h2h"] = {}
        if label == home or sel_type == "1" or "home" in label.lower():
            markets["h2h"][(home, None)] = odds
        elif label.lower() in ("draw", "x", "empate") or sel_type.upper() == "X":
            markets["h2h"][("Draw", None)] = odds
        elif label == away or sel_type == "2" or "away" in label.lower():
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
