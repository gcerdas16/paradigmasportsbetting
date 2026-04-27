"""
Scanner v2: Usa scraping directo en vez de The Odds API.

Flujo:
    1. Scrape Pinnacle → odds de referencia (sharp)
    2. Scrape 1xBet → odds de casa blanda (soft)
    3. Emparejar eventos por nombre de equipo
    4. Calcular EV con ev_calculator.find_value_bets()
    5. Mostrar/registrar value bets encontradas

Costo: $0 (vs $60/mes de The Odds API)

Uso:
    python -m scraping.scanner_v2
"""

import logging
import sys
import os
from datetime import datetime, timezone

# Agregar el directorio padre al path para importar módulos de paradigma
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from ev_calculator import find_value_bets
from scraping.pinnacle_scraper import PinnacleScraper
from scraping.onexbet_scraper import OneXBetScraper
from scraping.event_matcher import match_events, names_match

logger = logging.getLogger(__name__)


def scan_once(headless: bool = True) -> list:
    """
    Ejecuta un ciclo completo de escaneo usando scraping.

    1. Scrape Pinnacle (referencia)
    2. Scrape 1xBet (soft book)
    3. Emparejar eventos
    4. Convertir a formato ev_calculator
    5. Calcular value bets

    Returns:
        Lista de ValueBets encontradas.
    """
    logger.info("=" * 60)
    logger.info(f"Scanner v2 (Scraping) — {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    # ── 1. Scrape Pinnacle ──────────────────────────────────────
    logger.info("\n📊 Paso 1/4: Scraping Pinnacle...")
    pinnacle_scraper = PinnacleScraper(headless=headless)
    pinnacle_data, pinnacle_events = pinnacle_scraper.scrape_all_football()
    logger.info(f"   Pinnacle: {len(pinnacle_data)} eventos con odds")

    if not pinnacle_data:
        logger.error("No se obtuvieron datos de Pinnacle. Abortando.")
        return []

    # ── 2. Scrape 1xBet ────────────────────────────────────────
    logger.info("\n🎰 Paso 2/4: Scraping 1xBet...")
    onexbet_scraper = OneXBetScraper(headless=headless)
    onexbet_data, onexbet_events = onexbet_scraper.scrape_football_odds()
    logger.info(f"   1xBet: {len(onexbet_data)} eventos con odds")

    if not onexbet_data:
        logger.error("No se obtuvieron datos de 1xBet. Abortando.")
        return []

    # ── 3. Emparejar eventos ────────────────────────────────────
    logger.info("\n🔗 Paso 3/4: Emparejando eventos Pinnacle ↔ 1xBet...")

    # CRÍTICO: Solo emparejar eventos que TIENEN odds.
    # events_info incluye todos los matchups; pinnacle_data/onexbet_data
    # solo tienen los que tienen odds reales.
    pin_events_with_odds = [
        evt for evt in pinnacle_events if evt["event_id"] in pinnacle_data
    ]
    xbet_events_with_odds = [
        evt for evt in onexbet_events if evt["event_id"] in onexbet_data
    ]
    logger.info(
        f"   Con odds: {len(pin_events_with_odds)} Pinnacle, "
        f"{len(xbet_events_with_odds)} 1xBet"
    )

    matched = match_events(pin_events_with_odds, xbet_events_with_odds)
    logger.info(f"   Emparejados: {len(matched)} partidos")

    if not matched:
        logger.warning("No se emparejó ningún evento. Verificar nombres.")
        logger.info("Ejemplos Pinnacle:")
        for evt in pin_events_with_odds[:5]:
            logger.info(f"   {evt['home_team']} vs {evt['away_team']}")
        logger.info("Ejemplos 1xBet:")
        for evt in xbet_events_with_odds[:5]:
            logger.info(f"   {evt['home_team']} vs {evt['away_team']}")
        return []

    # ── 4. Convertir a formato ev_calculator ────────────────────
    logger.info("\n📐 Paso 4/4: Calculando EV...")

    # Construir pinnacle_data con event_ids unificados
    # y soft_book_odds en formato de filas individuales
    unified_pinnacle = {}
    soft_book_rows = []

    for p_evt, s_evt in matched:
        p_eid = p_evt["event_id"]
        s_eid = s_evt["event_id"]

        # Usar el ID de Pinnacle como ID unificado
        unified_id = p_eid

        # Copiar odds de Pinnacle
        if p_eid in pinnacle_data:
            unified_pinnacle[unified_id] = pinnacle_data[p_eid]

        # Convertir odds de 1xBet a filas individuales
        if s_eid in onexbet_data:
            # Para spreads: mapear nombres de equipo 1xBet → Pinnacle
            s_home = s_evt["home_team"]
            s_away = s_evt["away_team"]
            p_home = p_evt["home_team"]
            p_away = p_evt["away_team"]

            for market_key, outcomes in onexbet_data[s_eid].items():
                for (outcome_name, outcome_point), odds in outcomes.items():
                    # Spreads usan nombres de equipo como outcome_name.
                    # 1xBet puede decir "Man Utd" pero Pinnacle dice
                    # "Manchester United". Traducimos al nombre de Pinnacle.
                    final_name = outcome_name
                    if market_key == "spreads":
                        if names_match(outcome_name, p_home):
                            final_name = p_home
                        elif names_match(outcome_name, p_away):
                            final_name = p_away

                    soft_book_rows.append({
                        "event_id": unified_id,
                        "sport_key": "soccer",
                        "sport_title": f"Soccer - {p_evt.get('league', '')}",
                        "commence_time": p_evt.get("commence_time", ""),
                        "home_team": p_evt["home_team"],
                        "away_team": p_evt["away_team"],
                        "book_key": "onexbet",
                        "book_title": "1xBet",
                        "market": market_key,
                        "outcome_name": final_name,
                        "outcome_point": outcome_point,
                        "odds": odds,
                        "book_link": None,
                        "market_link": None,
                        "outcome_link": None,
                    })

    logger.info(
        f"   Pinnacle: {len(unified_pinnacle)} eventos"
        f"   | 1xBet: {len(soft_book_rows)} odds individuales"
    )

    # Diagnóstico: cuántas odds por mercado y cuántas matchean con Pinnacle
    market_counts = {}
    market_matched = {}
    for row in soft_book_rows:
        mk = row["market"]
        market_counts[mk] = market_counts.get(mk, 0) + 1
        eid = row["event_id"]
        ok = (row["outcome_name"], row["outcome_point"])
        if eid in unified_pinnacle and mk in unified_pinnacle[eid] and ok in unified_pinnacle[eid][mk]:
            market_matched[mk] = market_matched.get(mk, 0) + 1
    logger.info(f"   Por mercado (1xBet → matched en Pinnacle):")
    for mk in sorted(market_counts.keys()):
        logger.info(f"     {mk}: {market_counts[mk]} odds, {market_matched.get(mk, 0)} matched")

    # Calcular value bets con umbral bajo para capturar near-misses
    real_threshold = config.MIN_EV_PERCENT
    original = config.MIN_EV_PERCENT
    config.MIN_EV_PERCENT = 1.0  # Capturar todo con EV > 1%
    all_bets = find_value_bets(soft_book_rows, unified_pinnacle)
    config.MIN_EV_PERCENT = original  # Restaurar

    # Filtro de seguridad: EV > 30% es casi seguro un error de emparejamiento
    MAX_SANE_EV = 30.0
    suspicious = [vb for vb in all_bets if vb.ev_percent > MAX_SANE_EV]
    if suspicious:
        logger.warning(
            f"   ⚠️ {len(suspicious)} bets con EV > {MAX_SANE_EV}% descartadas "
            f"(probable error de emparejamiento):"
        )
        for vb in suspicious:
            logger.warning(
                f"     {vb.home_team} vs {vb.away_team} | "
                f"{vb.outcome_name} @ {vb.odds:.2f} | EV: {vb.ev_percent:.1f}%"
            )
    all_bets = [vb for vb in all_bets if vb.ev_percent <= MAX_SANE_EV]

    # Separar: value bets reales vs near-misses
    value_bets = [vb for vb in all_bets if vb.ev_percent >= real_threshold]
    near_misses = [vb for vb in all_bets if vb.ev_percent < real_threshold]

    # Deduplicar value bets
    best_per_outcome: dict[str, object] = {}
    for vb in value_bets:
        key = f"{vb.event_id}|{vb.market}|{vb.outcome_name}|{vb.outcome_point}"
        if key not in best_per_outcome or vb.odds > best_per_outcome[key].odds:
            best_per_outcome[key] = vb
    value_bets = sorted(best_per_outcome.values(), key=lambda x: x.ev_percent, reverse=True)

    # Deduplicar near-misses
    best_nm: dict[str, object] = {}
    for vb in near_misses:
        key = f"{vb.event_id}|{vb.market}|{vb.outcome_name}|{vb.outcome_point}"
        if key not in best_nm or vb.odds > best_nm[key].odds:
            best_nm[key] = vb
    near_misses = sorted(best_nm.values(), key=lambda x: x.ev_percent, reverse=True)[:15]

    return value_bets, near_misses


def print_results(value_bets: list, near_misses: list = None):
    """Imprime los resultados de forma legible."""
    print(f"\n{'='*70}")
    print(f"🎯 VALUE BETS ENCONTRADAS: {len(value_bets)}")
    print(f"{'='*70}")

    if not value_bets:
        print("  (ninguna — las odds actuales no superan el umbral de EV)")
        print(f"  Umbral configurado: EV > {config.MIN_EV_PERCENT}%")
    else:
        for i, vb in enumerate(value_bets, 1):
            pt_str = f" {vb.outcome_point}" if vb.outcome_point is not None else ""
            pin_str = f" (Pinnacle: {vb.pinnacle_odds:.2f})" if vb.pinnacle_odds else ""

            print(f"\n  #{i} [{vb.market}] {vb.home_team} vs {vb.away_team}")
            print(f"     Liga: {vb.sport_title}")
            print(f"     Apuesta: {vb.outcome_name}{pt_str} @ {vb.odds:.3f} ({vb.book_title}){pin_str}")
            print(f"     EV: {vb.ev_percent:+.2f}%  |  Kelly: {vb.kelly_stake_percent:.2f}%")
            print(f"     Fair prob: {vb.fair_prob:.4f}")

        avg_ev = sum(vb.ev_percent for vb in value_bets) / len(value_bets)
        avg_kelly = sum(vb.kelly_stake_percent for vb in value_bets) / len(value_bets)
        markets = {}
        for vb in value_bets:
            markets[vb.market] = markets.get(vb.market, 0) + 1

        print(f"\n{'─'*70}")
        print(f"  Resumen:")
        print(f"    Total: {len(value_bets)} value bets")
        print(f"    EV promedio: {avg_ev:+.2f}%")
        print(f"    Kelly promedio: {avg_kelly:.2f}%")
        print(f"    Por mercado: {markets}")
        print(f"    Fuente: Pinnacle (scraping) vs 1xBet (scraping)")
        print(f"    Costo: $0")

    # Near-misses: diagnóstico de oportunidades cercanas
    if near_misses:
        print(f"\n{'='*70}")
        print(f"🔍 NEAR MISSES (EV 1-{config.MIN_EV_PERCENT}%): {len(near_misses)}")
        print(f"{'='*70}")
        for vb in near_misses[:15]:
            pt_str = f" {vb.outcome_point}" if vb.outcome_point is not None else ""
            pin_str = f" (Pin: {vb.pinnacle_odds:.2f})" if vb.pinnacle_odds else ""
            print(
                f"  [{vb.market:>7}] {vb.home_team} vs {vb.away_team} | "
                f"{vb.outcome_name}{pt_str} @ {vb.odds:.3f}{pin_str} | "
                f"EV: {vb.ev_percent:+.2f}%"
            )
        nm_markets = {}
        for vb in near_misses:
            nm_markets[vb.market] = nm_markets.get(vb.market, 0) + 1
        print(f"  Por mercado: {nm_markets}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("\n🚀 Scanner v2 — Scraping Mode (Pinnacle + 1xBet)")
    print(f"   Umbral EV: >{config.MIN_EV_PERCENT}%")
    print(f"   Kelly: ÷{int(1/config.KELLY_FRACTION)}, cap {config.MAX_KELLY_PERCENT}%")
    print(f"   Modo: {'PAPER' if config.PAPER_TRADING else 'REAL'}")

    value_bets, near_misses = scan_once(headless=True)
    print_results(value_bets, near_misses)
