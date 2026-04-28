"""
Scraper de Bet365 para fútbol.

Usa Playwright para interceptar la API interna de Bet365.
Bet365 usa un formato propietario (pipe-delimited, XOR-encrypted)
además de endpoints JSON modernos.

Este scraper intenta ambos métodos:
1. Interceptar respuestas JSON (API moderna)
2. Parsear formato pipe-delimited + XOR (API legacy)

Uso:
    from paradigma.scraping.bet365_scraper import Bet365Scraper
    scraper = Bet365Scraper()
    soft_odds, events_info = scraper.scrape_football_odds()
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Bet365 redirige según región. Probar varios TLDs.
BET365_URLS = {
    "football": [
        "https://www.bet365.com/#/AS/B1/",          # Internacional
        "https://www.bet365.cr/#/AS/B1/",            # Costa Rica
        "https://www.bet365.com.au/#/AS/B1/",        # Australia
    ],
    "soccer_prematch": [
        "https://www.bet365.com/#/AC/B1/C1/D7/E40/F4/",
    ],
}

# Dominios de API internos conocidos de Bet365
BET365_API_DOMAINS = [
    "bet365.com",
    "bet365.cr",
    "bet365.com.au",
    "365-api",
    "sportsbook",
    "stableui",
]

# Directorio de debug
DEBUG_DIR = Path("scraping_debug")


# ---------------------------------------------------------------------------
# XOR Decoder (para formato legacy de Bet365)
# ---------------------------------------------------------------------------

def xor_decode(msg: str, key: int) -> str:
    """Aplica XOR a un mensaje para decodificarlo."""
    return "".join(chr(ord(c) ^ key) for c in msg)


def parse_pipe_odds(data: str) -> list[dict]:
    """
    Parsea el formato pipe-delimited de Bet365.
    
    Formato: campos separados por | y ;
    Valores clave: NA=nombre, OD=odds(XOR), BC=datetime, FD=equipos,
                   HD=handicap, PA=participante
    """
    events = []
    
    if not data or "|" not in data:
        return events
    
    try:
        # Extraer la clave XOR del campo TK
        tk_match = re.search(r';TK=([^;|]+)', data)
        if not tk_match:
            return events
        tk = tk_match.group(1)
        xor_key = ord(tk[0]) ^ ord(tk[1])
        
        # Dividir en bloques de mercado (MG;)
        blocks = data.split("MG;")
        if len(blocks) < 3:
            return events
        
        for block in blocks[2:]:
            event = _parse_pipe_block(block, xor_key)
            if event:
                events.append(event)
    except Exception as e:
        logger.debug(f"Error parsing pipe format: {e}")
    
    return events


def _parse_pipe_block(block: str, xor_key: int) -> Optional[dict]:
    """Parsea un bloque individual del formato pipe-delimited."""
    try:
        fields = {}
        for row in block.split("|"):
            for field in row.split(";"):
                if "=" in field:
                    key, value = field.split("=", 1)
                    if key not in fields:
                        fields[key] = value
        
        # Extraer equipos
        teams_raw = fields.get("FD", "")
        if " v " not in teams_raw:
            return None
        home, away = teams_raw.split(" v ", 1)
        
        # Extraer datetime
        bc = fields.get("BC", "")
        if len(bc) >= 14:
            start_time = f"{bc[:4]}-{bc[4:6]}-{bc[6:8]}T{bc[8:10]}:{bc[10:12]}:{bc[12:14]}Z"
        else:
            start_time = ""
        
        # Extraer odds (XOR encoded)
        odds_raw = []
        for row in block.split("|"):
            if row.startswith("PA"):
                for field in row.split(";"):
                    if field.startswith("OD=") and len(field) > 3:
                        od_value = field[3:]
                        if od_value:
                            try:
                                decoded = xor_decode(od_value, xor_key)
                                if "/" in decoded:
                                    n, d = decoded.split("/")
                                    decimal = int((int(n) / int(d) + 1) * 100) * 10
                                    odds_raw.append(decimal / ODDS_DIVISOR)
                                else:
                                    odds_raw.append(None)
                            except Exception:
                                odds_raw.append(None)
        
        if not odds_raw or not home or not away:
            return None
        
        return {
            "home": home.strip(),
            "away": away.strip(),
            "start_time": start_time,
            "odds_raw": odds_raw,
        }
    except Exception:
        return None


ODDS_DIVISOR = 1000.0


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

class Bet365Scraper:
    """Scrapea odds de Bet365 interceptando su API interna via Playwright."""

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    def scrape_football_odds(self) -> tuple[dict, list[dict]]:
        """
        Scrapea odds de fútbol de Bet365.

        Returns:
            soft_odds: {event_id: {market: {(outcome_name, point): odds}}}
            events_info: [{event_id, home_team, away_team, ...}]
        """
        from playwright.sync_api import sync_playwright, Response

        # Contenedores para datos interceptados
        json_responses: list[dict] = []
        pipe_responses: list[str] = []
        all_urls_captured: list[str] = []

        def on_response(response: Response):
            """Intercepta respuestas de la API de Bet365."""
            url = response.url
            
            # Filtrar: solo respuestas del dominio de Bet365
            is_bet365 = any(d in url for d in BET365_API_DOMAINS)
            if not is_bet365:
                return

            content_type = response.headers.get("content-type", "")
            
            try:
                status = response.status
                if status != 200:
                    return

                body_text = response.text()
                all_urls_captured.append(url)

                # Intentar parsear como JSON
                if "json" in content_type or "javascript" in content_type:
                    try:
                        body_json = json.loads(body_text)
                        json_responses.append({
                            "url": url,
                            "data": body_json,
                        })
                        logger.info(f"  JSON interceptado: {url[:80]}...")
                        return
                    except json.JSONDecodeError:
                        pass

                # Detectar formato pipe-delimited (legacy)
                if "|" in body_text and ";" in body_text:
                    if "PA" in body_text or "MG" in body_text or "OD=" in body_text:
                        pipe_responses.append(body_text)
                        logger.info(
                            f"  Pipe-format interceptado: {url[:80]}... "
                            f"(size={len(body_text)})"
                        )

            except Exception as e:
                logger.debug(f"  Error procesando response: {e}")

        logger.info("Iniciando scraping de Bet365 fútbol...")

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

            # Intentar múltiples URLs de Bet365
            loaded = False
            for url_list in [BET365_URLS["football"], BET365_URLS["soccer_prematch"]]:
                if loaded:
                    break
                for url in url_list:
                    logger.info(f"  Navegando a {url}")
                    try:
                        page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
                        page.wait_for_timeout(5_000)
                        
                        # Verificar que cargó (no redirect a captcha o geoblock)
                        current_url = page.url
                        title = page.title()
                        logger.info(f"  Página cargada: {title} ({current_url[:60]})")
                        
                        if "bet365" in current_url.lower():
                            loaded = True
                            break
                    except Exception as e:
                        logger.warning(f"  Error en {url}: {e}")
                        continue

            if loaded:
                # Scroll para cargar más datos
                logger.info("  Scrolling para cargar más eventos...")
                for _ in range(5):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2_000)

                # Intentar navegar a secciones específicas de fútbol
                # Bet365 usa navegación por hash, intentar clics
                try:
                    # Buscar links a ligas populares
                    football_links = page.query_selector_all(
                        'a[href*="soccer"], a[href*="football"], '
                        'div[class*="soccer"], div[class*="football"]'
                    )
                    logger.info(f"  Links de fútbol encontrados: {len(football_links)}")
                    
                    for link in football_links[:5]:
                        try:
                            link.click()
                            page.wait_for_timeout(3_000)
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"  Error buscando links: {e}")

                # Esperar un poco más para capturar respuestas
                page.wait_for_timeout(5_000)

                # Screenshot para debug
                self._save_screenshot(page)
            else:
                logger.error("  No se pudo cargar ninguna URL de Bet365")
                self._save_screenshot(page)

            browser.close()

        logger.info(
            f"  Captura completada: "
            f"{len(json_responses)} JSON, {len(pipe_responses)} pipe, "
            f"{len(all_urls_captured)} URLs total"
        )

        # Guardar debug
        self._save_debug(json_responses, pipe_responses, all_urls_captured)

        # Intentar parsear datos
        soft_odds, events_info = self._parse_all_data(
            json_responses, pipe_responses
        )

        logger.info(f"  Datos formateados: {len(soft_odds)} eventos con odds")
        return soft_odds, events_info

    # ---------------------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------------------

    def _parse_all_data(
        self,
        json_responses: list[dict],
        pipe_responses: list[str],
    ) -> tuple[dict, list[dict]]:
        """Intenta extraer odds de todas las respuestas capturadas."""
        soft_odds = {}
        events_info = []
        seen_ids = set()

        # 1. Parsear respuestas JSON (API moderna)
        for resp in json_responses:
            data = resp["data"]
            events = self._extract_json_events(data)
            for event in events:
                eid = event["event_id"]
                if eid in seen_ids:
                    continue
                seen_ids.add(eid)
                if event["markets"]:
                    soft_odds[eid] = event["markets"]
                events_info.append({
                    "event_id": eid,
                    "home_team": event["home"],
                    "away_team": event["away"],
                    "league": event.get("league", ""),
                    "commence_time": event.get("start_time", ""),
                    "sport_key": "soccer",
                    "sport_title": f"Soccer - {event.get('league', '')}",
                    "book_key": "bet365",
                    "book_name": "Bet365",
                })

        # 2. Parsear respuestas pipe-delimited (legacy)
        if not soft_odds:
            logger.info("  No se encontraron datos JSON. Intentando formato pipe...")
            for pipe_data in pipe_responses:
                pipe_events = parse_pipe_odds(pipe_data)
                for i, event in enumerate(pipe_events):
                    eid = f"b365_{i}_{event['home'][:3]}_{event['away'][:3]}"
                    if eid in seen_ids:
                        continue
                    seen_ids.add(eid)
                    
                    # Las pipe odds vienen en orden: 1, X, 2
                    h2h_odds = {}
                    odds_raw = event.get("odds_raw", [])
                    if len(odds_raw) >= 3:
                        if odds_raw[0]:
                            h2h_odds[(event["home"], None)] = odds_raw[0]
                        if odds_raw[1]:
                            h2h_odds[("Draw", None)] = odds_raw[1]
                        if odds_raw[2]:
                            h2h_odds[(event["away"], None)] = odds_raw[2]
                    
                    markets = {}
                    if h2h_odds:
                        markets["h2h"] = h2h_odds
                    
                    if markets:
                        soft_odds[eid] = markets
                    events_info.append({
                        "event_id": eid,
                        "home_team": event["home"],
                        "away_team": event["away"],
                        "league": "",
                        "commence_time": event.get("start_time", ""),
                        "sport_key": "soccer",
                        "sport_title": "Soccer",
                        "book_key": "bet365",
                        "book_name": "Bet365",
                    })

        return soft_odds, events_info

    def _extract_json_events(self, data) -> list[dict]:
        """Extrae eventos de una respuesta JSON de Bet365."""
        events = []
        
        if isinstance(data, dict):
            # Buscar arrays de eventos en cualquier nivel
            for key in ("events", "data", "results", "matches", "fixtures",
                       "EventList", "Events", "Matches"):
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        event = self._parse_json_event(item)
                        if event:
                            events.append(event)
            
            # Buscar recursivamente en sub-objetos
            if not events:
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        sub_events = self._extract_json_events(value)
                        events.extend(sub_events)
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # ¿Es un evento directamente?
                    event = self._parse_json_event(item)
                    if event:
                        events.append(event)
                    else:
                        sub_events = self._extract_json_events(item)
                        events.extend(sub_events)
        
        return events

    @staticmethod
    def _parse_json_event(item: dict) -> Optional[dict]:
        """Intenta parsear un dict como evento con odds."""
        if not isinstance(item, dict):
            return None
        
        # Buscar nombres de equipo en varios formatos comunes
        home = (item.get("home") or item.get("homeName") or 
                item.get("home_team") or item.get("HomeTeam") or
                item.get("T1", ""))
        away = (item.get("away") or item.get("awayName") or
                item.get("away_team") or item.get("AwayTeam") or
                item.get("T2", ""))
        
        if not home or not away:
            # Intentar extraer de un campo combinado
            name = item.get("name", "") or item.get("Name", "")
            if " v " in name:
                home, away = name.split(" v ", 1)
            elif " vs " in name:
                home, away = name.split(" vs ", 1)
            elif " - " in name and len(name.split(" - ")) == 2:
                home, away = name.split(" - ", 1)
        
        if not home or not away:
            return None
        
        event_id = str(
            item.get("id") or item.get("eventId") or item.get("ID") or
            item.get("FI") or f"b365_{home[:3]}_{away[:3]}"
        )
        
        league = (item.get("league") or item.get("competition") or
                  item.get("League") or item.get("CT") or "")
        start_time = (item.get("startTime") or item.get("start") or
                     item.get("StartTime") or item.get("BC") or "")
        
        # Buscar odds
        markets = {}
        
        # Formato 1: odds directas en el evento
        h2h_odds = {}
        for home_key in ("odds_home", "home_odds", "OddsHome", "HA"):
            if home_key in item:
                try:
                    h2h_odds[(home.strip(), None)] = float(item[home_key])
                except (ValueError, TypeError):
                    pass
        for draw_key in ("odds_draw", "draw_odds", "OddsDraw", "HD"):
            if draw_key in item:
                try:
                    h2h_odds[("Draw", None)] = float(item[draw_key])
                except (ValueError, TypeError):
                    pass
        for away_key in ("odds_away", "away_odds", "OddsAway", "AA"):
            if away_key in item:
                try:
                    h2h_odds[(away.strip(), None)] = float(item[away_key])
                except (ValueError, TypeError):
                    pass
        
        if h2h_odds:
            markets["h2h"] = h2h_odds
        
        # Formato 2: odds en sub-array
        for offers_key in ("betOffers", "odds", "markets", "Odds", "Prices"):
            offers = item.get(offers_key, [])
            if isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict):
                        _parse_json_offer(offer, home.strip(), away.strip(), markets)
        
        return {
            "event_id": event_id,
            "home": home.strip(),
            "away": away.strip(),
            "league": str(league),
            "start_time": str(start_time),
            "markets": markets,
        }

    # ---------------------------------------------------------------------------
    # Debug
    # ---------------------------------------------------------------------------

    def _save_screenshot(self, page):
        """Guarda screenshot de la página para debug."""
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        try:
            page.screenshot(
                path=str(DEBUG_DIR / f"bet365_screenshot_{ts}.png"),
                full_page=False,
            )
        except Exception:
            pass

    @staticmethod
    def _save_debug(json_responses, pipe_responses, urls):
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # URLs capturadas
        urls_path = DEBUG_DIR / f"bet365_urls_{ts}.json"
        urls_path.write_text(json.dumps(urls, indent=2))

        # JSON responses
        json_path = DEBUG_DIR / f"bet365_json_{ts}.json"
        serializable = []
        for resp in json_responses:
            try:
                json.dumps(resp)
                serializable.append(resp)
            except (TypeError, ValueError):
                serializable.append({"url": resp.get("url", ""), "error": "not serializable"})
        json_path.write_text(json.dumps(serializable, indent=2, default=str))

        # Pipe responses (primeros 5000 chars de cada uno)
        if pipe_responses:
            pipe_path = DEBUG_DIR / f"bet365_pipe_{ts}.txt"
            content = "\n\n--- SEPARATOR ---\n\n".join(
                r[:5000] for r in pipe_responses
            )
            pipe_path.write_text(content, encoding="utf-8", errors="replace")

        logger.info(
            f"  Debug guardado: {json_path}"
            f"{f', {pipe_path}' if pipe_responses else ''}"
        )


def _parse_json_offer(
    offer: dict, home: str, away: str, markets: dict
):
    """Parsea un bet offer individual de formato JSON."""
    outcomes = offer.get("outcomes") or offer.get("selections") or []
    offer_type = str(offer.get("type", "") or offer.get("name", "")).lower()

    for outcome in outcomes:
        if not isinstance(outcome, dict):
            continue
        odds = outcome.get("odds") or outcome.get("price") or outcome.get("decimal")
        if odds is None:
            continue
        try:
            odds = float(odds)
            # Kambi-style milliodds
            if odds > 100:
                odds = odds / 1000.0
        except (ValueError, TypeError):
            continue
        if odds <= 1.0:
            continue

        label = str(outcome.get("label", "") or outcome.get("name", ""))
        otype = str(outcome.get("type", ""))
        line = outcome.get("line") or outcome.get("handicap") or outcome.get("points")

        # Determinar mercado
        if "total" in offer_type or "over" in offer_type:
            if line is not None:
                line = float(line)
                if line > 100:
                    line = line / 1000.0
                if "totals" not in markets:
                    markets["totals"] = {}
                if "over" in label.lower() or otype == "OT_OVER":
                    markets["totals"][("Over", line)] = odds
                elif "under" in label.lower() or otype == "OT_UNDER":
                    markets["totals"][("Under", line)] = odds

        elif "handicap" in offer_type or "spread" in offer_type:
            if line is not None:
                line = float(line)
                if abs(line) > 100:
                    line = line / 1000.0
                if "spreads" not in markets:
                    markets["spreads"] = {}
                if label == home or "home" in otype.lower():
                    markets["spreads"][(home, line)] = odds
                elif label == away or "away" in otype.lower():
                    markets["spreads"][(away, -line)] = odds

        else:
            # Default: h2h
            if "h2h" not in markets:
                markets["h2h"] = {}
            if label == home or "home" in otype.lower() or otype == "OT_ONE":
                markets["h2h"][(home, None)] = odds
            elif label.lower() == "draw" or otype == "OT_CROSS":
                markets["h2h"][("Draw", None)] = odds
            elif label == away or "away" in otype.lower() or otype == "OT_TWO":
                markets["h2h"][(away, None)] = odds


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import argparse
    parser = argparse.ArgumentParser(description="Bet365 scraper")
    parser.add_argument("--no-headless", action="store_true",
                       help="Mostrar browser (útil para debug/captcha)")
    args = parser.parse_args()

    scraper = Bet365Scraper(headless=not args.no_headless)
    soft_odds, events_info = scraper.scrape_football_odds()

    print(f"\n{'='*60}")
    print(f"Bet365 — Eventos con odds: {len(soft_odds)}")
    print(f"{'='*60}")

    for info in events_info[:30]:
        eid = info["event_id"]
        if eid in soft_odds:
            markets = soft_odds[eid]
            print(f"\n  {info['home_team']} vs {info['away_team']}")
            print(f"    Liga: {info['league']}")
            for mkt_name, outcomes in markets.items():
                print(f"    {mkt_name}:")
                for (name, point), odds in outcomes.items():
                    pt_str = f" {point}" if point is not None else ""
                    print(f"      {name}{pt_str}: {odds:.4f}")
