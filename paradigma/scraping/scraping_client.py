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

logger = logging.getLogger(__name__)


class ScrapingClient:
    """
    Cliente unificado de scraping.

    Fase 1: Solo Pinnacle (para validar que el scraper funciona).
    Fase 2: + 1xBet scraper (soft book).
    Fase 3: + 888sport, Betway, etc.

    En Fase 1, produce pinnacle_data para comparar con The Odds API y
    validar que los datos son correctos.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.pinnacle = PinnacleScraper(headless=headless)

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

    def _get_soft_book_odds(self, events_info: list[dict]) -> list[dict]:
        """
        Obtiene odds de casas blandas.

        TODO Fase 2: Integrar scrapers de:
        - 1xBet (basado en repos/sports-arbitrage-1xbet)
        - 888sport
        - Betway
        - etc.

        Por ahora retorna lista vacía. El sistema actual con The Odds API
        sigue funcionando en paralelo para soft books.
        """
        logger.warning(
            "Soft book scraping no implementado aún. "
            "Usar The Odds API para soft books mientras tanto."
        )
        return []


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
