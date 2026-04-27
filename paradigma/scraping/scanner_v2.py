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


def format_match_time(commence_time) -> str:
    """Convierte commence_time (ISO string o Unix timestamp) a texto legible."""
    if not commence_time:
        return ""
    try:
        t = commence_time
        if isinstance(t, (int, float)):
            dt = datetime.fromtimestamp(float(t), tz=timezone.utc)
        elif isinstance(t, str) and t.isdigit():
            dt = datetime.fromtimestamp(float(t), tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        return f"{days[dt.weekday()]} {dt.day:02d} {months[dt.month-1]} — {dt.hour:02d}:{dt.minute:02d} UTC"
    except Exception:
        return str(commence_time)

# Agregar el directorio padre al path para importar módulos de paradigma
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from ev_calculator import find_value_bets
from scraping.pinnacle_scraper import PinnacleScraper
from scraping.onexbet_scraper import OneXBetScraper, BOOK_CONFIGS
from scraping.event_matcher import match_events, names_match

logger = logging.getLogger(__name__)


def scan_once(headless: bool = True, book_keys: list = None) -> list:
    """
    Ejecuta un ciclo completo de escaneo usando scraping.

    1. Scrape Pinnacle (referencia)
    2. Scrape soft books (1xBet, MelBet, 20Bet, etc.)
    3. Emparejar eventos
    4. Convertir a formato ev_calculator
    5. Calcular value bets

    Args:
        headless: ejecutar browsers sin ventana visible
        book_keys: lista de casas a scrapear (default: solo 1xbet)

    Returns:
        Lista de ValueBets encontradas.
    """
    if book_keys is None:
        book_keys = ["1xbet"]

    logger.info("=" * 60)
    logger.info(f"Scanner v2 (Scraping) — {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"  Casas: {', '.join(BOOK_CONFIGS[k]['name'] for k in book_keys)}")
    logger.info("=" * 60)

    # ── 1. Scrape Pinnacle ──────────────────────────────────────
    total_steps = 2 + len(book_keys)
    logger.info(f"\n📊 Paso 1/{total_steps}: Scraping Pinnacle...")
    pinnacle_scraper = PinnacleScraper(headless=headless)
    pinnacle_data, pinnacle_events = pinnacle_scraper.scrape_all_football()
    logger.info(f"   Pinnacle: {len(pinnacle_data)} eventos con odds")

    if not pinnacle_data:
        logger.error("No se obtuvieron datos de Pinnacle. Abortando.")
        return []

    pin_events_with_odds = [
        evt for evt in pinnacle_events if evt["event_id"] in pinnacle_data
    ]

    # ── 2. Scrape soft books ──────────────────────────────────────
    unified_pinnacle = {}
    soft_book_rows = []
    total_matched = 0

    for step_i, book_key in enumerate(book_keys, start=2):
        book_name = BOOK_CONFIGS[book_key]["name"]
        logger.info(f"\n🎰 Paso {step_i}/{total_steps}: Scraping {book_name}...")

        try:
            scraper = OneXBetScraper(headless=headless, book_key=book_key)
            soft_data, soft_events = scraper.scrape_football_odds()
        except Exception as e:
            logger.error(f"   Error scraping {book_name}: {e}")
            continue

        logger.info(f"   {book_name}: {len(soft_data)} eventos con odds")

        if not soft_data:
            logger.warning(f"   {book_name}: sin datos, saltando.")
            continue

        # Emparejar con Pinnacle
        soft_with_odds = [
            evt for evt in soft_events if evt["event_id"] in soft_data
        ]
        logger.info(
            f"   Con odds: {len(pin_events_with_odds)} Pinnacle, "
            f"{len(soft_with_odds)} {book_name}"
        )

        matched = match_events(pin_events_with_odds, soft_with_odds)
        logger.info(f"   Emparejados: {len(matched)} partidos")
        total_matched += len(matched)

        if not matched:
            logger.warning(f"   {book_name}: 0 partidos emparejados.")
            continue

        # Convertir a filas
        for p_evt, s_evt in matched:
            p_eid = p_evt["event_id"]
            s_eid = s_evt["event_id"]
            unified_id = p_eid

            if p_eid in pinnacle_data:
                unified_pinnacle[unified_id] = pinnacle_data[p_eid]

            if s_eid in soft_data:
                p_home = p_evt["home_team"]
                p_away = p_evt["away_team"]

                for market_key, outcomes in soft_data[s_eid].items():
                    for (outcome_name, outcome_point), odds in outcomes.items():
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
                            "book_key": book_key,
                            "book_title": book_name,
                            "market": market_key,
                            "outcome_name": final_name,
                            "outcome_point": outcome_point,
                            "odds": odds,
                            "book_link": None,
                            "market_link": None,
                            "outcome_link": None,
                        })

    if not soft_book_rows:
        logger.error("No se obtuvieron odds de ninguna casa blanda. Abortando.")
        return []

    # ── Paso final: Calcular EV ────────────────────────────────────
    logger.info(f"\n📐 Paso {total_steps}/{total_steps}: Calculando EV...")
    books_summary = {}
    for row in soft_book_rows:
        books_summary[row["book_title"]] = books_summary.get(row["book_title"], 0) + 1
    logger.info(
        f"   Pinnacle: {len(unified_pinnacle)} eventos"
        f"   | Soft books: {sum(books_summary.values())} odds "
        f"({', '.join(f'{k}: {v}' for k, v in books_summary.items())})"
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
    logger.info(f"   Por mercado (soft books → matched en Pinnacle):")
    for mk in sorted(market_counts.keys()):
        logger.info(f"     {mk}: {market_counts[mk]} odds, {market_matched.get(mk, 0)} matched")

    # Diagnóstico detallado: mostrar keys que NO matchean para totals/spreads
    for debug_market in ("totals", "spreads"):
        shown = 0
        for row in soft_book_rows:
            if row["market"] != debug_market or shown >= 3:
                continue
            eid = row["event_id"]
            ok = (row["outcome_name"], row["outcome_point"])
            if eid in unified_pinnacle and debug_market in unified_pinnacle[eid]:
                pin_keys = list(unified_pinnacle[eid][debug_market].keys())
                if ok not in unified_pinnacle[eid][debug_market]:
                    logger.info(
                        f"   🔍 {debug_market} MISMATCH [{row['home_team']} vs {row['away_team']}]:"
                        f"\n        1xBet key:    {ok!r}  (type: {type(ok[0]).__name__}, {type(ok[1]).__name__})"
                        f"\n        Pinnacle keys: {pin_keys[:6]}"
                        f"\n        Pinnacle types: {[(type(k[0]).__name__, type(k[1]).__name__) for k in pin_keys[:3]]}"
                    )
                    shown += 1

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
            match_time = format_match_time(vb.commence_time)
            if match_time:
                print(f"     📅 {match_time}")
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
        print(f"    Fuente: Pinnacle (scraping) vs soft books (scraping)")
        print(f"    Costo: $0")

    # Near-misses: diagnóstico de oportunidades cercanas
    if near_misses:
        print(f"\n{'='*70}")
        print(f"🔍 NEAR MISSES (EV 1-{config.MIN_EV_PERCENT}%): {len(near_misses)}")
        print(f"{'='*70}")
        for vb in near_misses[:15]:
            pt_str = f" {vb.outcome_point}" if vb.outcome_point is not None else ""
            pin_str = f" (Pin: {vb.pinnacle_odds:.2f})" if vb.pinnacle_odds else ""
            time_str = format_match_time(vb.commence_time)
            time_part = f" [{time_str}]" if time_str else ""
            print(
                f"  [{vb.market:>7}] {vb.home_team} vs {vb.away_team}{time_part} | "
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

    # Parsear argumentos: --books 1xbet,melbet,20bet
    import argparse
    parser = argparse.ArgumentParser(description="Scanner v2 — Scraping multi-book")
    parser.add_argument(
        "--books", type=str, default="1xbet",
        help=f"Casas a scrapear separadas por coma. Disponibles: {', '.join(BOOK_CONFIGS.keys())}"
    )
    parser.add_argument("--no-headless", action="store_true", help="Mostrar browsers")
    args = parser.parse_args()

    book_keys = [k.strip() for k in args.books.split(",")]
    book_names = [BOOK_CONFIGS[k]["name"] for k in book_keys if k in BOOK_CONFIGS]

    print(f"\n🚀 Scanner v2 — Scraping Mode (Pinnacle + {' + '.join(book_names)})")
    print(f"   Umbral EV: >{config.MIN_EV_PERCENT}%")
    print(f"   Kelly: ÷{int(1/config.KELLY_FRACTION)}, cap {config.MAX_KELLY_PERCENT}%")
    print(f"   Modo: {'PAPER' if config.PAPER_TRADING else 'REAL'}")

    value_bets, near_misses = scan_once(
        headless=not args.no_headless,
        book_keys=book_keys,
    )
    print_results(value_bets, near_misses)
