"""
Script de verificación: compara odds scrapeadas vs sitios reales.

Genera links directos a Pinnacle y 1xBet para cada partido emparejado,
mostrando las odds capturadas para verificación manual.

Uso:
    cd paradigma
    python -m scraping.verify_odds
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraping.pinnacle_scraper import PinnacleScraper
from scraping.onexbet_scraper import OneXBetScraper
from scraping.event_matcher import match_events

logger = logging.getLogger(__name__)


def build_1xbet_link(event_id: str, league_id: str = "") -> str:
    """Construye link directo al evento en 1xBet."""
    if league_id:
        return f"https://1xbet.com/en/line/football/{league_id}/{event_id}"
    return f"https://1xbet.com/en/line/football?eventId={event_id}"


def build_pinnacle_link(event_id: str) -> str:
    """Construye link directo al evento en Pinnacle."""
    return f"https://www.pinnacle.com/en/soccer/matchup/{event_id}"


def verify():
    print("\n" + "=" * 80)
    print("🔍 VERIFICACIÓN DE ODDS — Pinnacle vs 1xBet")
    print("=" * 80)
    print("  Scrapeando ambos sitios...\n")

    # Scrape
    pin_scraper = PinnacleScraper(headless=True)
    pinnacle_data, pin_events = pin_scraper.scrape_all_football()

    xbet_scraper = OneXBetScraper(headless=True)
    onexbet_data, xbet_events = xbet_scraper.scrape_football_odds()

    # Solo eventos con odds
    pin_with_odds = [e for e in pin_events if e["event_id"] in pinnacle_data]
    xbet_with_odds = [e for e in xbet_events if e["event_id"] in onexbet_data]

    # Match
    matched = match_events(pin_with_odds, xbet_with_odds)

    # Index 1xBet events by event_id for league_id lookup
    xbet_by_id = {e["event_id"]: e for e in xbet_events}

    print(f"\n{'=' * 80}")
    print(f"📋 PARTIDOS EMPAREJADOS: {len(matched)}")
    print(f"{'=' * 80}")
    print(f"  Abra los links en su navegador para verificar que las odds coincidan.\n")

    for i, (p_evt, s_evt) in enumerate(matched, 1):
        p_eid = p_evt["event_id"]
        s_eid = s_evt["event_id"]

        home = p_evt["home_team"]
        away = p_evt["away_team"]
        league = p_evt.get("league", "")

        # Links
        pin_link = build_pinnacle_link(p_eid)
        s_info = xbet_by_id.get(s_eid, {})
        xbet_link = build_1xbet_link(s_eid, str(s_info.get("league_id", "")))

        print(f"  {'─' * 76}")
        print(f"  #{i} {home} vs {away}")
        print(f"     Liga: {league}")
        print(f"     🟢 Pinnacle: {pin_link}")
        print(f"     🔵 1xBet:    {xbet_link}")

        # Mostrar odds h2h
        pin_market = pinnacle_data.get(p_eid, {}).get("h2h", {})
        xbet_market = onexbet_data.get(s_eid, {}).get("h2h", {})

        if pin_market or xbet_market:
            print(f"     ┌─────────────┬──────────┬──────────┐")
            print(f"     │   Mercado    │ Pinnacle │  1xBet   │")
            print(f"     ├─────────────┼──────────┼──────────┤")

            # Collect all outcome names
            all_outcomes = set()
            for k in pin_market:
                all_outcomes.add(k[0])
            for k in xbet_market:
                all_outcomes.add(k[0])

            for outcome in sorted(all_outcomes):
                pin_odds = pin_market.get((outcome, None))
                xbet_odds = xbet_market.get((outcome, None))
                pin_str = f"{pin_odds:.3f}" if pin_odds else "  —   "
                xbet_str = f"{xbet_odds:.3f}" if xbet_odds else "  —   "
                label = outcome[:11].ljust(11)
                print(f"     │ {label} │ {pin_str:>8} │ {xbet_str:>8} │")

            print(f"     └─────────────┴──────────┴──────────┘")

        # Mostrar totals (main line only)
        pin_totals = pinnacle_data.get(p_eid, {}).get("totals", {})
        xbet_totals = onexbet_data.get(s_eid, {}).get("totals", {})

        if pin_totals and xbet_totals:
            # Find common points
            pin_points = {k[1] for k in pin_totals if k[0] == "Over"}
            xbet_points = {k[1] for k in xbet_totals if k[0] == "Over"}
            common = sorted(pin_points & xbet_points)

            if common:
                # Show first common line
                pt = common[len(common) // 2]  # Middle line
                p_over = pin_totals.get(("Over", pt))
                p_under = pin_totals.get(("Under", pt))
                x_over = xbet_totals.get(("Over", pt))
                x_under = xbet_totals.get(("Under", pt))

                if p_over and x_over:
                    print(f"     Totals {pt}:")
                    print(f"       Over:  Pinnacle {p_over:.3f}  |  1xBet {x_over:.3f}")
                    if p_under and x_under:
                        print(f"       Under: Pinnacle {p_under:.3f}  |  1xBet {x_under:.3f}")

        # Mostrar spreads (main line)
        pin_spreads = pinnacle_data.get(p_eid, {}).get("spreads", {})
        xbet_spreads = onexbet_data.get(s_eid, {}).get("spreads", {})

        if pin_spreads and xbet_spreads:
            pin_sp_points = {abs(k[1]) for k in pin_spreads}
            xbet_sp_points = {abs(k[1]) for k in xbet_spreads}
            common_sp = sorted(pin_sp_points & xbet_sp_points)

            if common_sp:
                pt = common_sp[0]
                # Find home spread
                p_home_sp = pin_spreads.get((home, -pt)) or pin_spreads.get((home, pt))
                x_home_sp = xbet_spreads.get((home, -pt)) or xbet_spreads.get((home, pt))
                if p_home_sp and x_home_sp:
                    print(f"     Spread ±{pt}:")
                    print(f"       {home}: Pinnacle {p_home_sp:.3f}  |  1xBet {x_home_sp:.3f}")

        print()

        # Solo mostrar los primeros 20
        if i >= 20:
            remaining = len(matched) - 20
            if remaining > 0:
                print(f"  ... y {remaining} partidos más")
            break

    print(f"\n{'=' * 80}")
    print(f"  Para verificar: abra los links de Pinnacle y 1xBet en su navegador")
    print(f"  y compare las odds mostradas arriba con las del sitio real.")
    print(f"  Si coinciden (±0.01), el scraper está funcionando correctamente.")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    verify()
