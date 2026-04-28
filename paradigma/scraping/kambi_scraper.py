"""
Scraper para casas Kambi (888sport, Unibet, etc.)

La plataforma Kambi expone una API REST pública en eu-offering.kambicdn.org
que NO requiere Playwright ni autenticación. Solo HTTP requests simples.

Casas confirmadas sobre Kambi:
    888sport  →  operador "888"
    Unibet    →  operador "ub"

Uso:
    from paradigma.scraping.kambi_scraper import KambiScraper
    scraper = KambiScraper(book_key="888sport")
    soft_odds, events_info = scraper.scrape_football_odds()
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

KAMBI_BASE_URL = "https://eu-offering.kambicdn.org/offering/v2018"

# Configuración por casa de apuestas
# Nota: 888sport podría haber migrado fuera de Kambi (verificar con test).
# BetSafe es del grupo Betsson → cubre la casa prioritaria "Betsson".
BOOK_CONFIGS = {
    "888sport": {
        "name": "888sport",
        "operator": "888",
    },
    "unibet": {
        "name": "Unibet",
        "operator": "ub",
    },
    "betsafe": {
        "name": "BetSafe",
        "operator": "betsafe",
    },
}

# Categorías de mercado Kambi
# Cada category ID mapea a un tipo de apuesta
MARKET_CATEGORIES = {
    "h2h": 12579,       # Full Time Result (1X2)
    "totals": 12580,     # Total Goals (Over/Under)
    "spreads": 12218,    # Handicap / Asian Handicap
}

# Competiciones objetivo (termKey path)
# Se descubren automáticamente del group.json, pero estas son las principales
TARGET_COMPETITIONS = [
    "england/premier_league",
    "spain/la_liga",
    "germany/bundesliga",
    "italy/serie_a",
    "france/ligue_1",
    "champions_league",
    "europa_league",
    "usa/mls",
]

# Directorio de debug output
DEBUG_DIR = Path("scraping_debug")

# Kambi devuelve odds en milésimas (1950 = 1.95 decimal)
ODDS_DIVISOR = 1000.0


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

class KambiScraper:
    """Scrapea odds de casas Kambi (888sport, Unibet) vía API REST pública."""

    def __init__(self, book_key: str = "888sport", timeout: int = 15):
        if book_key not in BOOK_CONFIGS:
            raise ValueError(
                f"book_key '{book_key}' no válido. "
                f"Opciones: {list(BOOK_CONFIGS.keys())}"
            )
        self.book_key = book_key
        self.book_config = BOOK_CONFIGS[book_key]
        self.operator = self.book_config["operator"]
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        })

    def scrape_football_odds(self) -> tuple[dict, list[dict]]:
        """
        Scrapea odds de fútbol de la casa Kambi configurada.

        Returns:
            soft_odds: dict compatible con ev_calculator.py
                {event_id: {market: {(outcome_name, point): odds}}}
            events_info: lista con info de cada evento
                [{"event_id", "home_team", "away_team", "league",
                  "commence_time", "sport_key", "sport_title",
                  "book_key", "book_name"}]
        """
        book_name = self.book_config["name"]
        logger.info(f"Iniciando scraping de {book_name} fútbol (Kambi API)...")

        # 1. Descubrir competiciones disponibles
        competitions = self._discover_competitions()
        if not competitions:
            logger.warning("No se encontraron competiciones. Usando lista fija.")
            competitions = TARGET_COMPETITIONS

        logger.info(f"  Competiciones a scrapear: {len(competitions)}")

        # 2. Para cada competición, obtener odds de cada mercado
        all_events_raw: dict[str, dict] = {}  # event_id -> event_data
        all_odds: dict[str, dict] = {}        # event_id -> {market -> outcomes}

        for comp in competitions:
            for market_key, category_id in MARKET_CATEGORIES.items():
                try:
                    data = self._fetch_competition_odds(comp, category_id)
                    if not data or "events" not in data:
                        continue
                    self._parse_events(
                        data["events"], market_key, all_events_raw, all_odds
                    )
                except Exception as e:
                    logger.debug(f"  Error en {comp}/{market_key}: {e}")
                    continue

            # Rate limiting cortés
            time.sleep(0.3)

        logger.info(
            f"  Scraping completado: {len(all_events_raw)} eventos, "
            f"{len(all_odds)} con odds"
        )

        # 3. Guardar debug
        self._save_debug(all_events_raw, all_odds)

        # 4. Convertir a formato Paradigma
        soft_odds, events_info = self._to_paradigma_format(
            all_events_raw, all_odds
        )

        logger.info(f"  Datos formateados: {len(soft_odds)} eventos con odds")
        return soft_odds, events_info

    # ---------------------------------------------------------------------------
    # API Kambi
    # ---------------------------------------------------------------------------

    def _discover_competitions(self) -> list[str]:
        """Descubre competiciones de fútbol disponibles desde group.json."""
        url = f"{KAMBI_BASE_URL}/{self.operator}/group.json"
        params = {"lang": "en_US", "market": "ZZ"}

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"  No se pudo obtener group.json: {e}")
            return []

        competitions = []
        try:
            for sport_group in data.get("group", {}).get("groups", []):
                if sport_group.get("termKey") != "football":
                    continue

                # Iterar países
                for country in sport_group.get("groups", []):
                    country_key = country.get("termKey", "")

                    if "groups" in country:
                        # País con sub-ligas
                        for league in country["groups"]:
                            league_key = league.get("termKey", "")
                            comp_path = f"{country_key}/{league_key}"

                            # Filtrar: solo incluir competiciones que nos interesan
                            if self._is_target_competition(comp_path, league.get("name", "")):
                                competitions.append(comp_path)
                    else:
                        # País sin sub-ligas (ej: competiciones internacionales)
                        if self._is_target_competition(country_key, country.get("name", "")):
                            competitions.append(country_key)
        except Exception as e:
            logger.warning(f"  Error parseando group.json: {e}")

        logger.info(f"  Competiciones descubiertas: {len(competitions)}")
        for comp in competitions:
            logger.debug(f"    {comp}")

        return competitions

    @staticmethod
    def _is_target_competition(comp_path: str, comp_name: str) -> bool:
        """Verifica si una competición está en nuestra lista de interés."""
        path_lower = comp_path.lower()
        name_lower = comp_name.lower()

        targets = [
            "premier_league", "la_liga", "bundesliga", "serie_a",
            "ligue_1", "champions_league", "europa_league", "mls",
            "primera_division",  # Costa Rica
            "eredivisie", "primeira_liga",  # Extra: Holanda, Portugal
        ]

        for target in targets:
            if target in path_lower or target in name_lower:
                return True
        return False

    def _fetch_competition_odds(
        self, competition: str, category: int
    ) -> Optional[dict]:
        """Obtiene odds de una competición para un tipo de mercado."""
        url = (
            f"{KAMBI_BASE_URL}/{self.operator}"
            f"/listView/football/{competition}.json"
        )
        params = {
            "lang": "en_US",
            "market": "ZZ",
            "category": category,
            "includeParticipants": "true",
        }

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if "404" in str(e):
                return None
            logger.debug(f"  HTTP error para {competition}: {e}")
            return None
        except Exception as e:
            logger.debug(f"  Error fetching {competition}: {e}")
            return None

    # ---------------------------------------------------------------------------
    # Parsing
    # ---------------------------------------------------------------------------

    def _parse_events(
        self,
        events: list[dict],
        market_key: str,
        all_events_raw: dict,
        all_odds: dict,
    ):
        """Parsea eventos de una respuesta Kambi y acumula odds."""
        for event_wrapper in events:
            event = event_wrapper.get("event", {})

            # Filtrar eventos ya iniciados
            state = event.get("state", "")
            if state == "STARTED":
                continue

            event_id = str(event.get("id", ""))
            if not event_id:
                continue

            home_name = event.get("homeName", "")
            away_name = event.get("awayName", "")
            if not home_name or not away_name:
                continue

            # Guardar info del evento
            if event_id not in all_events_raw:
                all_events_raw[event_id] = {
                    "id": event_id,
                    "home": home_name,
                    "away": away_name,
                    "league": event.get("group", ""),
                    "start_time": event.get("start", ""),
                    "sport": event.get("sport", "FOOTBALL"),
                }

            # Parsear betOffers
            bet_offers = event_wrapper.get("betOffers", [])
            if not bet_offers:
                continue

            if event_id not in all_odds:
                all_odds[event_id] = {}

            for offer in bet_offers:
                outcomes = offer.get("outcomes", [])
                if not outcomes:
                    continue

                parsed = self._parse_bet_offer(
                    offer, outcomes, market_key, home_name, away_name
                )
                if parsed:
                    if market_key not in all_odds[event_id]:
                        all_odds[event_id][market_key] = {}
                    all_odds[event_id][market_key].update(parsed)

    def _parse_bet_offer(
        self,
        offer: dict,
        outcomes: list[dict],
        market_key: str,
        home: str,
        away: str,
    ) -> Optional[dict]:
        """Parsea un betOffer individual a nuestro formato."""
        result = {}

        for outcome in outcomes:
            odds_milli = outcome.get("odds")
            if odds_milli is None or odds_milli <= ODDS_DIVISOR:
                continue

            odds_decimal = odds_milli / ODDS_DIVISOR
            label = outcome.get("label", "")
            otype = outcome.get("type", "")

            # Línea para totals/spreads (Kambi la da en milésimas)
            line_milli = outcome.get("line")
            line = line_milli / ODDS_DIVISOR if line_milli is not None else None

            if market_key == "h2h":
                # 1X2: mapear por tipo de outcome
                if otype == "OT_ONE" or label == home:
                    result[(home, None)] = odds_decimal
                elif otype == "OT_CROSS" or label.lower() == "draw":
                    result[("Draw", None)] = odds_decimal
                elif otype == "OT_TWO" or label == away:
                    result[(away, None)] = odds_decimal

            elif market_key == "totals":
                if line is None:
                    continue
                if otype == "OT_OVER" or "over" in label.lower():
                    result[("Over", line)] = odds_decimal
                elif otype == "OT_UNDER" or "under" in label.lower():
                    result[("Under", line)] = odds_decimal

            elif market_key == "spreads":
                if line is None:
                    continue
                # Kambi: handicap line puede estar en offer o outcome
                handicap_line = line
                if otype == "OT_ONE" or label == home:
                    result[(home, handicap_line)] = odds_decimal
                elif otype == "OT_TWO" or label == away:
                    # Away handicap es el opuesto
                    result[(away, -handicap_line)] = odds_decimal

        return result if result else None

    # ---------------------------------------------------------------------------
    # Formato Paradigma
    # ---------------------------------------------------------------------------

    def _to_paradigma_format(
        self,
        all_events_raw: dict,
        all_odds: dict,
    ) -> tuple[dict, list[dict]]:
        """Convierte a formato compatible con ev_calculator.py."""
        soft_odds = {}
        events_info = []

        for event_id, event_data in all_events_raw.items():
            if event_id not in all_odds:
                continue
            markets = all_odds[event_id]
            if not markets:
                continue

            # Solo incluir mercados con datos
            clean_markets = {k: v for k, v in markets.items() if v}
            if not clean_markets:
                continue

            soft_odds[event_id] = clean_markets
            events_info.append({
                "event_id": event_id,
                "home_team": event_data["home"],
                "away_team": event_data["away"],
                "league": event_data["league"],
                "commence_time": event_data["start_time"],
                "sport_key": "soccer",
                "sport_title": f"Soccer - {event_data['league']}",
                "book_key": self.book_key,
                "book_name": self.book_config["name"],
            })

        return soft_odds, events_info

    # ---------------------------------------------------------------------------
    # Debug
    # ---------------------------------------------------------------------------

    def _save_debug(self, all_events_raw: dict, all_odds: dict):
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        book = self.book_key

        # Guardar eventos
        evt_path = DEBUG_DIR / f"kambi_{book}_events_{ts}.json"
        evt_path.write_text(
            json.dumps(all_events_raw, indent=2, default=str)
        )

        # Guardar odds (serializar tuple keys)
        odds_serializable = {}
        for eid, markets in all_odds.items():
            odds_serializable[eid] = {}
            for mkt, outcomes in markets.items():
                odds_serializable[eid][mkt] = {
                    f"{name}|{point}": odds
                    for (name, point), odds in outcomes.items()
                }

        odds_path = DEBUG_DIR / f"kambi_{book}_odds_{ts}.json"
        odds_path.write_text(
            json.dumps(odds_serializable, indent=2, default=str)
        )

        logger.info(f"  Debug guardado: {evt_path}, {odds_path}")


# ---------------------------------------------------------------------------
# CLI para prueba independiente
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Kambi scraper (888sport/Unibet)")
    parser.add_argument(
        "--book", type=str, default="888sport",
        choices=list(BOOK_CONFIGS.keys()),
        help="Casa a scrapear",
    )
    args = parser.parse_args()

    scraper = KambiScraper(book_key=args.book)
    soft_odds, events_info = scraper.scrape_football_odds()

    print(f"\n{'='*60}")
    print(f"{BOOK_CONFIGS[args.book]['name']} (Kambi) — Eventos con odds: {len(soft_odds)}")
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
