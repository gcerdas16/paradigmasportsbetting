"""
Scanner principal: busca value bets periódicamente.
Orquesta odds_client -> ev_calculator -> tracker -> telegram.
Incluye: scouting gratuito, tracking de frescura, auto-liquidación.
"""

import logging
import time
from datetime import datetime, timezone

import config
from odds_client import OddsClient
from ev_calculator import find_value_bets
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
        self._seen_bets: set[str] = set()  # Evitar duplicados

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

        # Verificar stop-loss
        if self.tracker.check_stop_loss():
            self.notifier.send_stop_loss(self.tracker.bankroll)
            return []

        # Verificar exposición diaria ANTES de gastar API calls
        if self.tracker.is_daily_limit_reached():
            logger.info("Límite de exposición diaria alcanzado. Saltando escaneo de odds (ahorrando API calls).")
            # Aún intentar liquidar apuestas pendientes
            try:
                settle_result = self.settler.settle_pending()
                if settle_result.get("settled", 0) > 0:
                    logger.info(f"Auto-liquidación: {settle_result}")
            except Exception as e:
                logger.warning(f"Error en auto-liquidación: {e}")
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

        # 3b. Deduplicar: solo la mejor odd por evento+mercado+outcome
        best_per_outcome: dict[str, object] = {}
        for vb in value_bets:
            outcome_key = f"{vb.event_id}|{vb.market}|{vb.outcome_name}|{vb.outcome_point}"
            if outcome_key not in best_per_outcome or vb.odds > best_per_outcome[outcome_key].odds:
                best_per_outcome[outcome_key] = vb
        value_bets = list(best_per_outcome.values())
        value_bets.sort(key=lambda x: x.ev_percent, reverse=True)

        logger.info(f"Value bets únicas (mejor odd por outcome): {len(value_bets)}")

        # 4. Procesar cada value bet
        new_bets = []
        for vb in value_bets:
            # Deduplicar entre escaneos
            bet_key = f"{vb.event_id}|{vb.market}|{vb.outcome_name}|{vb.outcome_point}"
            if bet_key in self._seen_bets:
                continue
            self._seen_bets.add(bet_key)

            # Registrar apuesta
            bet = self.tracker.place_bet(vb)
            if bet is None:
                continue  # Exposición diaria excedida

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

        # 5. Auto-liquidar apuestas completadas
        try:
            settle_result = self.settler.settle_pending()
            if settle_result.get("settled", 0) > 0:
                logger.info(f"Auto-liquidación: {settle_result}")
        except Exception as e:
            logger.warning(f"Error en auto-liquidación: {e}")

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
