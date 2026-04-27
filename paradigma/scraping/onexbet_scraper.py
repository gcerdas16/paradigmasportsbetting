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

# Dominio de la API interna (redirige a la versión Costa Rica)
ONEXBET_API_DOMAIN = "cr.1xbet.com"

# URL de fútbol pre-match
ONEXBET_FOOTBALL_URL = "https://1xbet.com/en/line/football"

# Endpoints de la API que queremos interceptar
API_ENDPOINTS = {
    "1x2": "/service-api/LineFeed/Get1x2_VZip",
    "sports": "/service-api/LineFeed/GetSportsShortZip",
    "express": "/service-api/main-line-feed/v1/expressDay",
    # Estos endpoints adicionales pueden aparecer al navegar
    "events": "/service-api/LineFeed/GetEventsZip",
    "champs": "/service-api/LineFeed/GetChampsZip",
    "sports_v2": "/service-api/LineFeed/GetSportsWithCountZip",
}

# Directorio de debug output
DEBUG_DIR = Path("scraping_debug")

# Sport ID para fútbol en 1xBet
FOOTBALL_SPORT_ID = 1


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

class OneXBetScraper:
    """Scrapea odds de 1xBet interceptando la API interna cr.1xbet.com."""

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000):
        self.headless = headless
        self.timeout_ms = timeout_ms

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

            # Solo interceptar requests de 1xBet
            if "1xbet" not in domain:
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

        logger.info("Iniciando scraping de 1xBet fútbol...")

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
            logger.info(f"Navegando a {ONEXBET_FOOTBALL_URL}")
            try:
                page.goto(
                    ONEXBET_FOOTBALL_URL,
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
            league_urls = [
                "https://1xbet.com/en/line/football/88637-england-premier-league",
                "https://1xbet.com/en/line/football/127733-spain-laliga",
                "https://1xbet.com/en/line/football/96463-germany-bundesliga",
                "https://1xbet.com/en/line/football/110163-italy-serie-a",
                "https://1xbet.com/en/line/football/12821-france-ligue-1",
                "https://1xbet.com/en/line/football/118587-uefa-champions-league",
                "https://1xbet.com/en/line/football/118593-uefa-europa-league",
            ]

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

        1xBet puede devolver datos en varios formatos. Los principales son:
        - Value: lista de eventos directos
        - Result: objeto con eventos
        - El body mismo puede ser un evento individual
        """
        events_to_process = []

        # Formato 1: {"Value": [...]} o {"Result": [...]}
        for key in ("Value", "Result", "Events", "Games", "data"):
            if key in body and isinstance(body[key], list):
                events_to_process.extend(body[key])

        # Formato 2: El body contiene campos de evento directamente
        if not events_to_process and self._looks_like_event(body):
            events_to_process.append(body)

        for event in events_to_process:
            if not isinstance(event, dict):
                continue
            # Filtrar solo fútbol
            sport_id = event.get("SI") or event.get("SportId") or event.get("sport_id")
            if sport_id is not None and int(sport_id) != FOOTBALL_SPORT_ID:
                continue

            # Verificar que tiene equipos y odds
            if self._has_teams_and_odds(event):
                all_events.append(event)

    @staticmethod
    def _looks_like_event(body: dict) -> bool:
        """Heurística: ¿el dict parece un evento deportivo?"""
        event_keys = {"CI", "LI", "O1", "O2", "AE", "ME"}
        alt_keys = {"ChampionshipId", "LeagueId", "Opp1", "Opp2"}
        return bool(event_keys & body.keys()) or bool(alt_keys & body.keys())

    @staticmethod
    def _has_teams_and_odds(event: dict) -> bool:
        """¿El evento tiene equipos y alguna cuota?"""
        # 1xBet usa formato comprimido con keys cortas
        has_teams = bool(
            (event.get("O1") or event.get("Opp1") or event.get("home"))
            and (event.get("O2") or event.get("Opp2") or event.get("away"))
        )
        # Odds pueden estar en varios lugares
        has_odds = bool(
            event.get("E")  # Events/odds array
            or event.get("ME")  # Market Events
            or event.get("AE")  # All Events
            or event.get("Odds")
            or event.get("odds")
            or event.get("CoefHome")
        )
        return has_teams or has_odds  # Ser permisivo para capturar más

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

        # Primero procesar datos del endpoint 1x2 (más completo)
        for api_key, responses in raw_api_data.items():
            for response_data in responses:
                parsed = self._parse_1xbet_response(response_data)
                for evt in parsed:
                    eid = evt.get("event_id")
                    if eid and eid not in seen_ids:
                        seen_ids.add(eid)
                        if evt.get("markets"):
                            soft_odds[eid] = evt["markets"]
                        events_info.append({
                            "event_id": eid,
                            "home_team": evt.get("home", ""),
                            "away_team": evt.get("away", ""),
                            "league": evt.get("league", ""),
                            "commence_time": evt.get("start_time", ""),
                            "sport_key": "soccer",
                            "sport_title": f"Soccer - {evt.get('league', '')}",
                        })

        # Luego procesar eventos individuales capturados
        for event in events:
            parsed = self._parse_single_event(event)
            if parsed:
                eid = parsed.get("event_id")
                if eid and eid not in seen_ids:
                    seen_ids.add(eid)
                    if parsed.get("markets"):
                        soft_odds[eid] = parsed["markets"]
                    events_info.append({
                        "event_id": eid,
                        "home_team": parsed.get("home", ""),
                        "away_team": parsed.get("away", ""),
                        "league": parsed.get("league", ""),
                        "commence_time": parsed.get("start_time", ""),
                        "sport_key": "soccer",
                        "sport_title": f"Soccer - {parsed.get('league', '')}",
                    })

        return soft_odds, events_info

    def _parse_1xbet_response(self, data) -> list[dict]:
        """Parsea una respuesta completa de la API de 1xBet."""
        results = []

        if isinstance(data, dict):
            # {"Value": [...]} es el formato más común
            items = (
                data.get("Value")
                or data.get("Result")
                or data.get("Events")
                or data.get("data")
                or []
            )
            if isinstance(items, list):
                for item in items:
                    parsed = self._parse_single_event(item)
                    if parsed:
                        results.append(parsed)
            else:
                parsed = self._parse_single_event(data)
                if parsed:
                    results.append(parsed)
        elif isinstance(data, list):
            for item in data:
                parsed = self._parse_single_event(item)
                if parsed:
                    results.append(parsed)

        return results

    def _parse_single_event(self, event: dict) -> Optional[dict]:
        """Parsea un evento individual de 1xBet.

        1xBet usa un formato comprimido con keys cortas:
            CI/ChampionshipId = League ID
            LI/LeagueId = League ID
            O1/Opp1 = Home team
            O2/Opp2 = Away team
            I/Id = Event ID
            S/Start = Start time
            E = List of odds entries
            AE = Additional events
            ME = Market events
        """
        if not isinstance(event, dict):
            return None

        # Extraer info del evento
        home = (
            event.get("O1")
            or event.get("Opp1")
            or event.get("home")
            or event.get("Home")
            or ""
        )
        away = (
            event.get("O2")
            or event.get("Opp2")
            or event.get("away")
            or event.get("Away")
            or ""
        )
        if not home or not away:
            return None

        event_id = str(
            event.get("I")
            or event.get("Id")
            or event.get("id")
            or event.get("CI", "")
        )
        if not event_id:
            return None

        league = (
            event.get("L")
            or event.get("League")
            or event.get("league")
            or event.get("ChampionshipName")
            or ""
        )
        start_time = (
            event.get("S")
            or event.get("Start")
            or event.get("start_time")
            or event.get("StartDate")
            or ""
        )

        # Filtrar solo fútbol (sport_id = 1)
        sport_id = event.get("SI") or event.get("SportId") or event.get("sport_id")
        if sport_id is not None and int(sport_id) != FOOTBALL_SPORT_ID:
            return None

        # Parsear odds
        markets = {}

        # --- Odds de los campos E (Events) ---
        odds_list = event.get("E", []) or event.get("AE", []) or event.get("ME", [])
        if isinstance(odds_list, list):
            h2h_odds = {}
            totals_odds = {}
            spreads_odds = {}

            for entry in odds_list:
                if not isinstance(entry, dict):
                    continue

                # 1xBet usa T (Type) y C (Coefficient/Odds)
                t = entry.get("T")
                c = entry.get("C")
                p = entry.get("P")  # Points (para totals/handicaps)

                if t is None or c is None:
                    continue

                try:
                    odds = float(c)
                except (ValueError, TypeError):
                    continue

                if odds <= 1.0:
                    continue

                # Mapeo de tipos de 1xBet
                # T=1: Home win, T=2: Away win, T=3: Draw
                # T=9: Over, T=10: Under
                # T=7: Handicap Home, T=8: Handicap Away
                if t == 1:
                    h2h_odds[(home, None)] = odds
                elif t == 2:
                    h2h_odds[(away, None)] = odds
                elif t == 3:
                    h2h_odds[("Draw", None)] = odds
                elif t == 9 and p is not None:
                    totals_odds[("Over", float(p))] = odds
                elif t == 10 and p is not None:
                    totals_odds[("Under", float(p))] = odds
                elif t == 7 and p is not None:
                    spreads_odds[(home, float(p))] = odds
                elif t == 8 and p is not None:
                    spreads_odds[(away, float(p))] = odds

            if h2h_odds:
                markets["h2h"] = h2h_odds
            if totals_odds:
                markets["totals"] = totals_odds
            if spreads_odds:
                markets["spreads"] = spreads_odds

        # --- Odds de campos directos (formato alternativo) ---
        if not markets:
            h2h_odds = {}
            for key, name in [("CoefHome", home), ("CoefDraw", "Draw"), ("CoefAway", away)]:
                val = event.get(key)
                if val:
                    try:
                        h2h_odds[(name, None)] = float(val)
                    except (ValueError, TypeError):
                        pass
            if h2h_odds:
                markets["h2h"] = h2h_odds

        return {
            "event_id": event_id,
            "home": home,
            "away": away,
            "league": league,
            "start_time": start_time,
            "markets": markets,
        }

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
