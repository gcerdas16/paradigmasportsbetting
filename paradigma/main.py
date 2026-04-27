"""
Paradigma — Value Betting System (Fase 1)

Usa Pinnacle como referencia de precio justo (vía The Odds API)
para detectar value bets en casas blandas.

Modos de uso:
    python main.py              # Escaneo único
    python main.py --loop       # Escaneo continuo cada N minutos
    python main.py --stats      # Ver estadísticas actuales
    python main.py --test       # Test rápido de conexión a la API
"""

import argparse
import logging
import sys

import config
from scanner import ValueScanner
from tracker import Tracker
from odds_client import OddsClient


def setup_logging():
    """Configura logging para consola y archivo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("paradigma.log", encoding="utf-8"),
        ],
    )


def cmd_scan(args):
    """Ejecuta un escaneo único o en loop."""
    scanner = ValueScanner()
    if args.loop:
        scanner.run_loop()
    else:
        bets = scanner.scan_once()
        if bets:
            print(f"\n✅ {len(bets)} value bets encontradas.")
        else:
            print("\n— No se encontraron value bets en este momento.")

        stats = scanner.tracker.get_stats()
        print(f"\n📊 Bankroll: ${stats['bankroll']:.2f} | "
              f"Apuestas: {stats['total_bets']} | "
              f"P&L: ${stats['total_pnl']:+.2f}")


def cmd_stats(args):
    """Muestra estadísticas del tracker."""
    tracker = Tracker()
    stats = tracker.get_stats()

    mode = "PAPER" if stats["is_paper"] else "REAL"
    print(f"\n📊 Estadísticas ({mode} TRADING)")
    print("=" * 40)
    print(f"  Bankroll:     ${stats['bankroll']:.2f} (inicio: ${stats['initial_bankroll']:.2f})")
    print(f"  P&L:          ${stats['total_pnl']:+.2f}")
    print(f"  ROI:          {stats['roi_percent']:+.1f}%")
    print(f"  Apuestas:     {stats['total_bets']} ({stats['settled']} cerradas, {stats['pending']} pendientes)")
    print(f"  Wins/Losses:  {stats['wins']}/{stats['losses']}")
    print(f"  Win Rate:     {stats['win_rate']:.1f}%")
    print(f"  EV promedio:  {stats['avg_ev']:.1f}%")
    clv_str = f"{stats['avg_clv']:+.2f}%" if stats['avg_clv'] is not None else "N/A"
    print(f"  CLV promedio: {clv_str}")
    print(f"  Faltan:       {stats['bets_to_validate']} apuestas para validar")


def cmd_test(args):
    """Test de conexión a The Odds API."""
    print("🔌 Probando conexión a The Odds API...")

    client = OddsClient()
    sports = client.get_active_sports()

    if sports:
        print(f"✅ Conexión exitosa. {len(sports)} deportes activos:")
        for s in sports[:10]:
            print(f"   • {s['title']} ({s['key']})")
        if len(sports) > 10:
            print(f"   ... y {len(sports) - 10} más")
        print(f"\n📊 API requests restantes: {client.remaining_requests}")
    else:
        print("❌ No se pudo conectar. Verificar ODDS_API_KEY en .env")


def main():
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Paradigma — Value Betting System"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Scan
    scan_parser = subparsers.add_parser("scan", help="Escanear value bets")
    scan_parser.add_argument("--loop", action="store_true", help="Modo continuo")

    # Stats
    subparsers.add_parser("stats", help="Ver estadísticas")

    # Test
    subparsers.add_parser("test", help="Probar conexión API")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        # Default: escaneo único
        args.loop = False
        cmd_scan(args)


if __name__ == "__main__":
    main()
