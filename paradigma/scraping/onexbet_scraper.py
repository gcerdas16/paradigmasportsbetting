"""
Scraper de 1xBet para fútbol.

Intercepta la API interna de 1xBet (cr.1xbet.com/service-api/LineFeed/)
usando Playwright. No requiere cuenta de 1xBet para pre-match odds.

Endpoints principales:
    - /service-api/LineFeed/Get1x2_VZip        → odds 1X2 (comprimidas)
    - /service-api/LineFeed/GetSportsShortZip   → lista deportes/ligas
    - /service-api/main-line-feed/v1/expressDay  → feed del día

Uso:
    from paradigma.scraping.onexbet_scraper import OneXBetScraper
    scraper = OneXBetScraper()
    soft_odds, events_info = scraper.scrape_football_odds()
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Endpoints de la API (comunes a todas las casas del mismo platform)
API_ENDPOINTS = {
    "1x2": "/service-api/LineFeed/Get1x2_VZip",
    "sports": "/service-api/LineFeed/GetSportsShortZip",
    "express": "/service-api/main-line-feed/v1/expressDay",
    "events": "/service-api/LineFeed/GetEventsZip",
    "champs": "/service-api/LineFeed/GetChampsZip",
    "sports_v2": "/service-api/LineFeed/GetSportsWithCountZip",
}

# Configuración por casa de apuestas (todas usan el mismo backend BetB2B)
BOOK_CONFIGS = {
    "1xbet": {
        "name": "1xBet",
        "domain_filter": "1xbet",  # para filtrar requests interceptados
        "football_url": "https://1xbet.com/en/line/football",
        "league_urls": [
            "https://1xbet.com/en/line/football/88637-england-premier-league",
            "https://1xbet.com/en/line/football/127733-spain-laliga",
            "https://1xbet.com/en/line/football/96463-germany-bundesliga",
            "https://1xbet.com/en/line/football/110163-italy-serie-a",
            "https://1xbet.com/en/line/football/12821-france-ligue-1",
            "https://1xbet.com/en/line/football/118587-uefa-champions-league",
            "https://1xbet.com/en/line/football/118593-uefa-europa-league",
        ],
    },
    "melbet": {
        "name": "MelBet",
        "domain_filter": "melbet",
        "football_url": "https://melbet.com/en/line/football",
        "league_urls": [
            "https://melbet.com/en/line/football/88637-england-premier-league",
            "https://melbet.com/en/line/football/127733-spain-laliga",
            "https://melbet.com/en/line/football/96463-germany-bundesliga",
            "https://melbet.com/en/line/football/110163-italy-serie-a",
            "https://melbet.com/en/line/football/12821-france-ligue-1",
            "https://melbet.com/en/line/football/118587-uefa-champions-league",
            "https://melbet.com/en/line/football/118593-uefa-europa-league",
        ],
    },
    "20bet": {
        "name": "20Bet",
        "domain_filter": "20bet",
        "football_url": "https://20bet.com/en/line/football",
        "league_urls": [
            "https://20bet.com/en/line/football/88637-england-premier-league",
            "https://20bet.com/en/line/football/127733-spain-laliga",
            "https://20bet.com/en/line/football/96463-germany-bundesliga",
            "https://20bet.com/en/line/football/110163-italy-serie-a",
            "https://20bet.com/en/line/football/12821-france-ligue-1",
            "https://20bet.com/en/line/football/118587-uefa-champions-league",
            "https://20bet.com/en/line/football/118593-uefa-europa-league",
        ],
    },
}

# Directorio de debug output
DEBUG_DIR = Path("scraping_debug")

# Sport ID para fútbol en 1xBet
FOOTBALL_SPORT_ID = 1


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

class OneXBetScraper:
    """Scrapea odds de casas BetB2B (1xBet, MelBet, 20Bet) interceptando su API interna."""

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000,
                 book_key: str = "1xbet"):
        self.headless = headless
        self.timeout_ms = timeout_ms
        if book_key not in BOOK_CONFIGS:
            raise ValueError(f"book_key '{book_key}' no válido. Opciones: {list(BOOK_CONFIGS.keys())}")
        self.book_key = book_key
        self.book_config = BOOK_CONFIGS[book_key]

    def scrape_football_odds(self) -> tuple[dict, list[dict]]:
        """
        Scrapea odds de fútbol de 1xBet.

        Returns:
            soft_odds: dict compatible con ev_calculator.py
                {event_id: {market: {(outcome_name, point): odds}}}
            events_info: lista con info de cada evento
                [{"event_id", "home_team", "away_team", "league",
                  "commence_time", "sport_key", "sport_title"}]
        """
        from playwright.sync_api import sync_playwright, Response

        # Contenedores para datos interceptados
        all_responses: list[dict] = []
        all_events: list[dict] = []
        raw_api_data: dict[str, list] = {}

        def on_response(response: Response):
            """Callback para interceptar respuestas de la API de 1xBet."""
            url = response.url
            parsed = urlparse(url)
            domain = parsed.netloc
            path = parsed.path

            # Solo interceptar requests de esta casa
            if self.book_config["domain_filter"] not in domain:
                return

            # Capturar respuestas JSON de la API
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type and "javascript" not in content_type:
                return

            try:
                body = response.json()
            except Exception:
                return

            # Identificar el tipo de endpoint
            endpoint_key = None
            for key, ep_path in API_ENDPOINTS.items():
                if ep_path in path:
                    endpoint_key = key
                    break

            if endpoint_key:
                logger.info(
                    f"  API interceptada: {endpoint_key} "
                    f"({type(body).__name__}, size={len(str(body))})"
                )
                if endpoint_key not in raw_api_data:
                    raw_api_data[endpoint_key] = []
                raw_api_data[endpoint_key].append(body)

            # Capturar cualquier respuesta que parezca contener eventos
            if isinstance(body, dict):
                # 1xBet empaqueta datos de varias formas
                self._extract_events_from_body(body, path, all_events)
            elif isinstance(body, list):
                for item in body:
                    if isinstance(item, dict):
                        self._extract_events_from_body(item, path, all_events)

        book_name = self.book_config["name"]
        logger.info(f"Iniciando scraping de {book_name} fútbol...")

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

            # Navegar a la página de fútbol pre-match
            football_url = self.book_config["football_url"]
            logger.info(f"Navegando a {football_url}")
            try:
                page.goto(
                    football_url,
                    wait_until="networkidle",
                    timeout=self.timeout_ms,
                )
                page.wait_for_timeout(5_000)
            except Exception as e:
                logger.warning(f"Timeout en carga inicial (esperado): {e}")

            # Scroll para cargar más eventos
            logger.info("Scrolling para cargar más eventos...")
            for i in range(8):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2_000)

            # Intentar navegar a ligas específicas populares
            league_urls = self.book_config["league_urls"]

            for league_url in league_urls:
                logger.info(f"Navegando a {league_url.split('/')[-1]}")
                try:
                    page.goto(
                        league_url,
                        wait_until="networkidle",
                        timeout=30_000,
                    )
                    page.wait_for_timeout(3_000)
                    # Scroll
                    for _ in range(3):
                        page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight)"
                        )
                        page.wait_for_timeout(1_500)
                except Exception as e:
                    logger.warning(f"Error en liga: {e}")
                    continue

            browser.close()

        logger.info(
            f"Scraping completado. "
            f"API responses: {sum(len(v) for v in raw_api_data.values())}, "
            f"Eventos detectados: {len(all_events)}"
        )

        # Guardar debug
        self._save_debug(raw_api_data, all_events)

        # Convertir a formato Paradigma
        soft_odds, events_info = self._to_paradigma_format(all_events, raw_api_data)

        logger.info(f"Datos formateados: {len(soft_odds)} eventos con odds")
        return soft_odds, events_info

    # ---------------------------------------------------------------------------
    # Extracción de eventos de la API
    # ---------------------------------------------------------------------------

    def _extract_events_from_body(
        self, body: dict, path: str, all_events: list[dict]
    ):
        """Extrae eventos de fútbol de la respuesta de la API de 1xBet.

        Formato confirmado (Get1x2_VZip):
            {"Value": [{O1, O2, I, LI, LE, E, AE, ...}, ...]}
        """
        events_to_process = []

        for key in ("Value", "Result", "Events", "data"):
            if key in body and isinstance(body[key], list):
                events_to_process.extend(body[key])

        if not events_to_process and "O1" in body and "O2" in body:
            events_to_process.append(body)

        for event in events_to_process:
            if not isinstance(event, dict):
                continue
            # Filtrar solo fútbol (SI = Sport ID, 1 = football)
            sport_id = event.get("SI")
            if sport_id is not None and int(sport_id) != FOOTBALL_SPORT_ID:
                continue
            # Debe tener equipos
            if event.get("O1") and event.get("O2"):
                all_events.append(event)

    # ---------------------------------------------------------------------------
    # Conversión a formato Paradigma (compatible con ev_calculator.py)
    # ---------------------------------------------------------------------------

    def _to_paradigma_format(
        self,
        events: list[dict],
        raw_api_data: dict[str, list],
    ) -> tuple[dict, list[dict]]:
        """
        Convierte los datos de 1xBet al formato Paradigma.

        soft_odds: {event_id: {market: {(outcome_name, point): odds}}}
        events_info: [{event_id, home_team, away_team, ...}]
        """
        soft_odds = {}
        events_info = []
        seen_ids = set()

        # Procesar todos los eventos capturados (tanto de raw_api_data como individuales)
        all_to_parse = list(events)

        # También extraer de raw_api_data
        for api_key, responses in raw_api_data.items():
            for response_data in responses:
                if isinstance(response_data, dict):
                    items = response_data.get("Value", [])
                    if isinstance(items, list):
                        all_to_parse.extend(items)

        for event in all_to_parse:
            parsed = self._parse_single_event(event)
            if not parsed:
                continue
            eid = parsed["event_id"]
            if eid in seen_ids:
                continue
            seen_ids.add(eid)
            if parsed["markets"]:
                soft_odds[eid] = parsed["markets"]
            events_info.append({
                "event_id": eid,
                "home_team": parsed["home"],
                "away_team": parsed["away"],
                "league": parsed["league"],
                "league_id": parsed.get("league_id", ""),
                "commence_time": parsed["start_time"],
                "sport_key": "soccer",
                "sport_title": f"Soccer - {parsed['league']}",
                "book_key": self.book_key,
                "book_name": self.book_config["name"],
            })

        return soft_odds, events_info

    def _parse_single_event(self, event: dict) -> Optional[dict]:
        """Parsea un evento individual de 1xBet.

        Estructura confirmada (Get1x2_VZip → Value[]):
            I   = Event ID (ej: 711873450)
            O1  = Home team (ej: "Manchester United")
            O2  = Away team
            L   = Liga (idioma local)
            LE  = Liga (inglés, ej: "England. Premier League")
            LI  = League ID (ej: 88637)
            CE  = País (ej: "England")
            S   = Start time (timestamp)
            SI  = Sport ID (1 = fútbol)
            E   = Lista de odds: [{C, CV, G, T, P?}, ...]
                  G=1 → moneyline: T=1 home, T=2 draw, T=3 away
                  G=1 → totals:    T=9 over, T=10 under (P = points)
                  G=1 → handicap:  T=7 home, T=8 away (P = points)
            AE  = Additional events (mercados extra):
                  [{G: 2, ME: [{C, CE, CV, G, T, P?}, ...]}, ...]
        """
        if not isinstance(event, dict):
            return None

        home = event.get("O1", "")
        away = event.get("O2", "")
        if not home or not away:
            return None

        event_id = event.get("I")
        if not event_id:
            return None
        event_id = str(event_id)

        # Preferir nombre en inglés (LE) sobre local (L)
        league = event.get("LE") or event.get("L") or ""
        start_time = event.get("S") or ""

        # Filtrar solo fútbol
        sport_id = event.get("SI")
        if sport_id is not None and int(sport_id) != FOOTBALL_SPORT_ID:
            return None

        markets = {}
        h2h_odds = {}
        totals_odds = {}
        spreads_odds = {}

        # --- E: Lista principal de odds ---
        e_list = event.get("E", [])
        if isinstance(e_list, list):
            self._parse_odds_entries(e_list, home, away,
                                    h2h_odds, totals_odds, spreads_odds)

        # --- AE: Mercados adicionales (handicaps, totals extra) ---
        ae_list = event.get("AE", [])
        if isinstance(ae_list, list):
            for ae_group in ae_list:
                if not isinstance(ae_group, dict):
                    continue
                me_list = ae_group.get("ME", [])
                if isinstance(me_list, list):
                    self._parse_odds_entries(me_list, home, away,
                                            h2h_odds, totals_odds, spreads_odds)

        if h2h_odds:
            markets["h2h"] = h2h_odds
        if totals_odds:
            markets["totals"] = totals_odds
        if spreads_odds:
            markets["spreads"] = spreads_odds

        league_id = event.get("LI", "")

        return {
            "event_id": event_id,
            "home": home,
            "away": away,
            "league": league,
            "league_id": league_id,
            "start_time": start_time,
            "markets": markets,
        }

    @staticmethod
    def _parse_odds_entries(
        entries: list[dict],
        home: str,
        away: str,
        h2h_odds: dict,
        totals_odds: dict,
        spreads_odds: dict,
    ):
        """Parsea una lista de odds entries de 1xBet.

        Cada entry tiene:
            C  = coeficiente decimal (ej: 2.007)
            CV = formato americano (ej: "+101")
            G  = grupo (1 = principal, 2 = alternativo)
            T  = tipo de mercado:
                 1 = Home win, 2 = Draw, 3 = Away win
                 7 = Handicap Home, 8 = Handicap Away
                 9 = Over, 10 = Under
            P  = points (para totals/handicaps)
        """
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            t = entry.get("T")
            c = entry.get("C")
            if t is None or c is None:
                continue

            try:
                odds = float(c)
            except (ValueError, TypeError):
                continue
            if odds <= 1.0:
                continue

            p = entry.get("P")  # Points para totals/handicaps

            # 1X2 (moneyline)
            if t == 1:
                h2h_odds[(home, None)] = odds
            elif t == 2:
                h2h_odds[("Draw", None)] = odds
            elif t == 3:
                h2h_odds[(away, None)] = odds
            # Totals
            elif t == 9 and p is not None:
                totals_odds[("Over", float(p))] = odds
            elif t == 10 and p is not None:
                totals_odds[("Under", float(p))] = odds
            # Handicaps
            elif t == 7 and p is not None:
                spreads_odds[(home, float(p))] = odds
            elif t == 8 and p is not None:
                spreads_odds[(away, float(p))] = odds

    # ---------------------------------------------------------------------------
    # Debug
    # ---------------------------------------------------------------------------

    @staticmethod
    def _save_debug(raw_api_data: dict, events: list[dict]):
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Guardar raw API data
        api_path = DEBUG_DIR / f"1xbet_api_{ts}.json"
        serializable = {}
        for key, responses in raw_api_data.items():
            serializable[key] = []
            for r in responses:
                try:
                    json.dumps(r)
                    serializable[key].append(r)
                except (TypeError, ValueError):
                    serializable[key].append(str(r)[:1000])
        api_path.write_text(json.dumps(serializable, indent=2, default=str))

        # Guardar eventos extraídos
        evt_path = DEBUG_DIR / f"1xbet_events_{ts}.json"
        try:
            evt_path.write_text(json.dumps(events[:200], indent=2, default=str))
        except Exception:
            evt_path.write_text("[]")

        logger.info(f"Debug guardado: {api_path}, {evt_path}")


# ---------------------------------------------------------------------------
# CLI para prueba independiente
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scraper = OneXBetScraper(headless=True)
    soft_odds, events_info = scraper.scrape_football_odds()

    print(f"\n{'='*60}")
    print(f"1xBet — Eventos con odds: {len(soft_odds)}")
    print(f"{'='*60}")

    for info in events_info[:30]:
        eid = info["event_id"]
        if eid in soft_odds:
            markets = soft_odds[eid]
            market_names = list(markets.keys())
            print(f"\n  {info['home_team']} vs {info['away_team']}")
            print(f"    Liga: {info['league']}")
            print(f"    Mercados: {market_names}")
            for mkt_name, outcomes in markets.items():
                print(f"    {mkt_name}:")
                for (name, point), odds in outcomes.items():
                    pt_str = f" {point}" if point is not None else ""
                    print(f"      {name}{pt_str}: {odds:.4f}")
