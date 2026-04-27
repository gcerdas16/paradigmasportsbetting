"""
Cliente de datos vía scraping — reemplazo directo de OddsClient.

Produce exactamente el mismo formato de datos que OddsClient para que
ev_calculator.py funcione sin cambios.

Uso:
    from paradigma.scraping.scraping_client import ScrapingClient
    client = ScrapingClient()
    pinnacle_data, soft_odds, events_info = client.get_all_odds()

    # Estos datos van directo a find_value_bets():
    from ev_calculator import find_value_bets
    value_bets = find_value_bets(soft_odds, pinnacle_data)
"""

import logging
from typing import Optional

from scraping.pinnacle_scraper import PinnacleScraper
from scraping.onexbet_scraper import OneXBetScraper

logger = logging.getLogger(__name__)


class ScrapingClient:
    """
    Cliente unificado de scraping.

    Fase 1: Pinnacle (referencia sharp) + 1xBet (soft book).
    Fase 2: + 888sport, bet365, etc.

    Produce pinnacle_data + soft_book_odds en formato compatible
    con ev_calculator.py sin necesidad de The Odds API.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.pinnacle = PinnacleScraper(headless=headless)
        self.onexbet = OneXBetScraper(headless=headless)

    def get_pinnacle_odds(
        self,
        league_filter: Optional[list[str]] = None,
    ) -> tuple[dict, list[dict]]:
        """
        Scrapea Pinnacle y retorna datos en formato Paradigma.

        Returns:
            pinnacle_data: dict event_id -> {market -> {(name, point) -> odds}}
            events_info: lista de info de eventos
        """
        return self.pinnacle.scrape_all_football(league_filter=league_filter)

    def get_all_odds(
        self,
        league_filter: Optional[list[str]] = None,
    ) -> tuple[dict, list[dict], list[dict]]:
        """
        Obtiene odds de Pinnacle + soft books.

        Returns:
            pinnacle_data: dict para ev_calculator
            soft_book_odds: lista de rows para ev_calculator
            events_info: info de eventos
        """
        # Paso 1: Pinnacle
        pinnacle_data, events_info = self.get_pinnacle_odds(league_filter)

        # Paso 2: Soft books (TODO: agregar scrapers de 1xBet, 888sport, etc.)
        soft_book_odds = self._get_soft_book_odds(events_info)

        logger.info(
            f"ScrapingClient: {len(pinnacle_data)} eventos Pinnacle, "
            f"{len(soft_book_odds)} odds de soft books"
        )

        return pinnacle_data, soft_book_odds, events_info

    def get_onexbet_odds(self) -> tuple[dict, list[dict]]:
        """
        Scrapea 1xBet y retorna datos en formato Paradigma.

        Returns:
            soft_odds: dict event_id -> {market -> {(name, point) -> odds}}
            events_info: lista de info de eventos
        """
        return self.onexbet.scrape_football_odds()

    def _get_soft_book_odds(self, events_info: list[dict]) -> list[dict]:
        """
        Obtiene odds de casas blandas (1xBet + futuras).

        Retorna lista de dicts en formato compatible con ev_calculator.
        Cada dict tiene: event_id, book_key, book_title, markets.
        """
        soft_book_odds = []

        # --- 1xBet ---
        try:
            onexbet_data, onexbet_events = self.get_onexbet_odds()
            logger.info(f"1xBet: {len(onexbet_data)} eventos con odds")
            for eid, markets in onexbet_data.items():
                soft_book_odds.append({
                    "event_id": eid,
                    "book_key": "onexbet",
                    "book_title": "1xBet",
                    "markets": markets,
                })
        except Exception as e:
            logger.error(f"Error scraping 1xBet: {e}")

        # TODO Fase 2: Agregar más scrapers
        # - bet365 (accesible desde CR)
        # - 888sport (accesible desde CR)

        return soft_book_odds


# ---------------------------------------------------------------------------
# CLI para prueba independiente
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    client = ScrapingClient(headless=True)
    pinnacle_data, soft_odds, events_info = client.get_all_odds()

    print(f"\n{'='*60}")
    print(f"RESUMEN SCRAPING CLIENT")
    print(f"{'='*60}")
    print(f"  Eventos Pinnacle: {len(pinnacle_data)}")
    print(f"  Soft book odds:   {len(soft_odds)}")
    print(f"  Eventos info:     {len(events_info)}")

    # Mostrar mercados disponibles por evento
    for info in events_info[:5]:  # Solo primeros 5
        eid = info["event_id"]
        if eid in pinnacle_data:
            mkts = pinnacle_data[eid]
            print(f"\n  {info['home_team']} vs {info['away_team']} ({info['league']})")
            for mkt_name, outcomes in mkts.items():
                print(f"    {mkt_name}: {len(outcomes)} outcomes")
