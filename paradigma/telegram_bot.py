"""
Alertas via Telegram.
Envía notificaciones cuando se detecta una value bet.
"""

import logging
import requests
from typing import Optional

import config
from ev_calculator import ValueBet

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envía alertas a Telegram."""

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.token = token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

        if not self.enabled:
            logger.warning(
                "Telegram no configurado. Las alertas se mostrarán solo en consola."
            )

    def send_value_bet(self, vb: ValueBet, stake: float, bankroll: float):
        """Envía alerta de value bet detectada."""
        mode = "PAPER" if config.PAPER_TRADING else "REAL"
        point_str = f" {vb.outcome_point}" if vb.outcome_point is not None else ""

        pinnacle_str = f" (Pinnacle: {vb.pinnacle_odds:.2f})" if vb.pinnacle_odds else ""
        link_str = f"🔗 [Apostar aqui]({vb.best_link})\n" if vb.best_link else ""

        msg = (
            f"{'📝' if config.PAPER_TRADING else '💰'} *{mode} BET*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚽ *{vb.home_team}* vs *{vb.away_team}*\n"
            f"🏷️ {vb.sport_title}\n"
            f"📅 {vb.commence_time[:16]}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *{vb.outcome_name}{point_str}* ({vb.market})\n"
            f"📊 Odds: *{vb.odds:.2f}* @ {vb.book_title}{pinnacle_str}\n"
            f"📈 EV: *+{vb.ev_percent:.1f}%*\n"
            f"🎰 Fair Prob: {vb.fair_prob:.1%}\n"
            f"💵 Stake: ${stake:.2f} ({vb.kelly_stake_percent:.2f}%)\n"
            f"🏦 Bankroll: ${bankroll:.2f}\n"
            f"{link_str}"
        )

        self._send(msg)

    def send_stats(self, stats: dict):
        """Envía resumen de estadísticas."""
        mode = "PAPER" if stats["is_paper"] else "REAL"
        clv_str = (
            f"📊 CLV promedio: {stats['avg_clv']:+.2f}%\n"
            if stats["avg_clv"] is not None
            else "📊 CLV: sin datos aún\n"
        )

        msg = (
            f"📊 *RESUMEN {mode}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Bankroll: ${stats['bankroll']:.2f} "
            f"(inicio: ${stats['initial_bankroll']:.2f})\n"
            f"📈 P&L: ${stats['total_pnl']:+.2f}\n"
            f"💹 ROI: {stats['roi_percent']:+.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎲 Apuestas: {stats['total_bets']} "
            f"({stats['settled']} cerradas, {stats['pending']} pendientes)\n"
            f"✅ Wins: {stats['wins']} | ❌ Losses: {stats['losses']}\n"
            f"🎯 Win Rate: {stats['win_rate']:.1f}%\n"
            f"📈 EV promedio: {stats['avg_ev']:.1f}%\n"
            f"{clv_str}"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Faltan {stats['bets_to_validate']} apuestas para validar\n"
        )

        self._send(msg)

    def send_stop_loss(self, bankroll: float):
        """Envía alerta de stop-loss."""
        msg = (
            f"🚨 *STOP-LOSS ACTIVADO*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Bankroll: ${bankroll:.2f}\n"
            f"📉 Pérdida semanal > {config.STOP_LOSS_WEEKLY_PERCENT}%\n"
            f"⏸️ Operaciones PAUSADAS\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Revisar estrategia antes de continuar."
        )
        self._send(msg)

    def send_message(self, text: str):
        """Envía un mensaje de texto genérico."""
        self._send(text)

    def _send(self, text: str):
        """Envía mensaje via Telegram API."""
        # Siempre mostrar en consola
        print(text.replace("*", "").replace("━", "-"))

        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                logger.error(
                    f"Telegram error {resp.status_code}: {resp.text}"
                )
        except requests.RequestException as e:
            logger.error(f"Telegram send failed: {e}")
