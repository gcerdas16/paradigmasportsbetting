"""
Scanner principal: busca value bets y arbitraje periódicamente.
Orquesta odds_client -> ev_calculator -> arb_finder -> tracker -> telegram.
Incluye: scouting gratuito, tracking de frescura, auto-liquidación.
"""

import logging
import time
from datetime import datetime, timezone

import config
from odds_client import OddsClient
from ev_calculator import find_value_bets
from arb_finder import find_arb_opportunities
from tracker import Tracker
from telegram_bot import TelegramNotifier
from odds_history import OddsHistory
from result_settler import ResultSettler

logger = logging.getLogger(__name__)


class ValueScanner:
    """Orquestador principal del sistema Paradigma."""

    def __init__(self):
        self.client = OddsClient()
        self.tracker = Tracker()
        self.notifier = TelegramNotifier()
        self.history = OddsHistory(max_snapshots=10)
        self.settler = ResultSettler(self.client, self.tracker)

    def scan_once(self) -> list:
        """
        Ejecuta un ciclo de escaneo completo.

        1. Obtener odds de The Odds API
        2. Extraer Pinnacle + casas blandas
        3. Calcular EV y encontrar value bets
        4. Registrar apuestas y enviar alertas

        Returns:
            Lista de ValueBets encontradas.
        """
        logger.info("=" * 60)
        logger.info(f"Escaneo iniciado: {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 60)

        # 0. SIEMPRE intentar liquidar apuestas pendientes primero
        try:
            settle_result = self.settler.settle_pending()
            if settle_result.get("settled", 0) > 0:
                logger.info(f"Auto-liquidación: {settle_result}")
        except Exception as e:
            logger.warning(f"Error en auto-liquidación: {e}")

        # Verificar stop-loss (después de liquidar para tener bankroll real)
        if self.tracker.check_stop_loss():
            self.notifier.send_stop_loss(self.tracker.bankroll)
            return []

        # Verificar límites ANTES de gastar API calls
        daily_full = self.tracker.is_daily_limit_reached()
        total_full = self.tracker.is_total_limit_reached()

        if daily_full or total_full:
            reason = "diario" if daily_full else "total"
            logger.info(f"Límite {reason} alcanzado. Saltando escaneo de odds (ahorrando API calls).")
            return []

        # 0. Scouting gratuito (no gasta quota)
        total_events_available = 0
        for sport in config.SPORTS:
            try:
                sport_events = self.client.get_events(sport)
                total_events_available += len(sport_events)
            except Exception:
                pass
        logger.info(f"Scouting: {total_events_available} eventos disponibles (gratis)")

        if total_events_available == 0:
            logger.warning("No hay eventos disponibles en ningún deporte.")
            return []

        # 1. Obtener odds (con bookmakers param = 4x más barato)
        events = self.client.get_all_odds()
        if not events:
            logger.warning("No se obtuvieron eventos. Verificar API key y conexión.")
            return []

        # 1b. Registrar snapshot de precios (freshness tracking)
        snap_stats = self.history.record_snapshot(events)
        movement = self.history.get_movement_stats()
        if "error" not in movement:
            logger.info(
                f"Movimiento de precios: {movement['changed']}/{movement['compared']} "
                f"cambiaron ({movement['change_percent']}%)"
            )

        # 2. Extraer Pinnacle y casas blandas (excluye exchanges automáticamente)
        pinnacle_data = self.client.extract_pinnacle_odds(events)
        soft_odds = self.client.extract_soft_book_odds(events)

        if not pinnacle_data:
            logger.warning(
                "No hay odds de Pinnacle. Verificar que 'pinnacle' esté en TARGET_BOOKMAKERS."
            )
            return []

        # 3. Encontrar value bets
        value_bets = find_value_bets(soft_odds, pinnacle_data)

        # 3b. Deduplicar: solo la mejor EV por EVENTO (1 apuesta por partido)
        best_per_event: dict[str, object] = {}
        for vb in value_bets:
            eid = vb.event_id
            if eid not in best_per_event or vb.ev_percent > best_per_event[eid].ev_percent:
                best_per_event[eid] = vb
        value_bets = list(best_per_event.values())
        value_bets.sort(key=lambda x: x.ev_percent, reverse=True)

        logger.info(f"Value bets únicas (mejor EV por evento): {len(value_bets)}")

        # 4. Procesar cada value bet
        new_bets = []
        for vb in value_bets:
            # Deduplicar contra DB (persistente entre reinicios)
            if self.tracker.has_pending_bet_for_event(vb.event_id):
                logger.info(f"SKIP (ya existe en DB): {vb.display_name}")
                continue

            # Registrar apuesta
            bet = self.tracker.place_bet(vb)
            if bet is None:
                continue  # Exposición excedida

            new_bets.append(vb)

            # Enviar alerta
            self.notifier.send_value_bet(
                vb,
                stake=bet.stake,
                bankroll=self.tracker.bankroll,
            )

        # Resumen del escaneo
        logger.info(
            f"Escaneo completado: {len(events)} eventos | "
            f"{len(pinnacle_data)} con Pinnacle | "
            f"{len(value_bets)} value bets | "
            f"{len(new_bets)} nuevas registradas"
        )

        if self.client.remaining_requests is not None:
            logger.info(f"API requests restantes: {self.client.remaining_requests}")

        # 5. Buscar arbitraje (usa los mismos eventos, no gasta API extra)
        arb_opps = find_arb_opportunities(events)
        new_arbs = []
        for arb in arb_opps:
            # Deduplicar contra DB
            if self.tracker.has_pending_bet_for_event(arb.event_id):
                logger.info(f"ARB SKIP (ya existe en DB): {arb.display_name}")
                continue

            # Stake: 2% del bankroll por arb (fijo, no Kelly)
            arb_stake = self.tracker.bankroll * 0.02
            bets = self.tracker.place_arb(arb, arb_stake)
            if bets:
                new_arbs.append(arb)
                self.notifier.send_message(
                    f"💰 *ARBITRAJE DETECTADO*\n"
                    f"{arb.display_name}\n"
                    f"Mercado: {arb.market}\n"
                    f"Ganancia: +{arb.profit_percent:.2f}%\n"
                    f"{arb.display_arb}\n"
                    f"Stake total: ${arb_stake:.2f}"
                )

        logger.info(
            f"Arbitraje: {len(arb_opps)} oportunidades | "
            f"{len(new_arbs)} nuevas registradas"
        )

        return value_bets

    def run_loop(self):
        """
        Ejecuta el scanner en un loop periódico.
        Ctrl+C para detener.
        """
        mode = "PAPER TRADING" if config.PAPER_TRADING else "REAL TRADING"
        interval = config.SCAN_INTERVAL_MINUTES

        cost_mode = "bookmakers (optimizado)" if config.USE_BOOKMAKERS_PARAM else "regions"
        self.notifier.send_message(
            f"🚀 *Paradigma iniciado*\n"
            f"Modo: {mode}\n"
            f"Bankroll: ${self.tracker.bankroll:.2f}\n"
            f"Intervalo: {interval} min\n"
            f"Deportes: {len(config.SPORTS)}\n"
            f"Umbral EV: >{config.MIN_EV_PERCENT}%\n"
            f"Kelly: ÷{int(1/config.KELLY_FRACTION)}, cap {config.MAX_KELLY_PERCENT}%\n"
            f"API: {cost_mode}"
        )

        scan_count = 0

        try:
            while True:
                scan_count += 1
                logger.info(f"\n--- Escaneo #{scan_count} ---")

                try:
                    self.scan_once()
                except Exception as e:
                    logger.error(f"Error en escaneo #{scan_count}: {e}", exc_info=True)

                # Enviar stats cada 10 escaneos
                if scan_count % 10 == 0:
                    stats = self.tracker.get_stats()
                    self.notifier.send_stats(stats)

                logger.info(f"Próximo escaneo en {interval} minutos...")
                time.sleep(interval * 60)

        except KeyboardInterrupt:
            logger.info("\nScanner detenido por el usuario.")
            stats = self.tracker.get_stats()
            self.notifier.send_stats(stats)
            print("\n--- Estadísticas finales ---")
            for k, v in stats.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    scanner = ValueScanner()
    scanner.run_loop()
