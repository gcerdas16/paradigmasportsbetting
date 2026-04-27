"""
Auto-liquidación de apuestas usando el endpoint /scores de The Odds API.

Verifica partidos completados y liquida apuestas pendientes automáticamente.
Calcula CLV comparando odds registradas vs Pinnacle al cierre.
"""

import logging
from datetime import datetime, timezone

import config
from odds_client import OddsClient
from tracker import Tracker, Bet

logger = logging.getLogger(__name__)


class ResultSettler:
    """Liquida apuestas pendientes consultando resultados reales."""

    def __init__(self, client: OddsClient, tracker: Tracker):
        self.client = client
        self.tracker = tracker

    def settle_pending(self) -> dict:
        """
        Verifica apuestas pendientes contra resultados reales.

        Returns:
            Dict con conteo de apuestas liquidadas por resultado.
        """
        pending = self.tracker.get_pending_bets()
        if not pending:
            logger.info("No hay apuestas pendientes por liquidar.")
            return {"settled": 0}

        # Agrupar pendientes por deporte
        sports_needed = set()
        for bet in pending:
            if bet.sport_key:
                sports_needed.add(bet.sport_key)

        # Obtener scores de cada deporte
        all_scores = {}
        for sport in sports_needed:
            scores = self.client.get_scores(sport, days_from=3)
            for game in scores:
                if game.get("completed"):
                    all_scores[game["id"]] = game

        logger.info(
            f"Scores obtenidos: {len(all_scores)} partidos completados "
            f"de {len(sports_needed)} deportes"
        )

        # Intentar liquidar cada apuesta pendiente
        results = {"win": 0, "loss": 0, "push": 0, "not_found": 0}

        for bet in pending:
            if bet.event_id not in all_scores:
                results["not_found"] += 1
                continue

            game = all_scores[bet.event_id]
            result = self._determine_result(bet, game)

            if result is None:
                results["not_found"] += 1
                continue

            self.tracker.settle_bet(
                bet_id=bet.id,
                result=result,
                odds_at_close=None,  # TODO: obtener odds de cierre via historical
            )
            results[result] = results.get(result, 0) + 1

        total_settled = results["win"] + results["loss"] + results["push"]
        logger.info(
            f"Liquidación: {total_settled} apuestas resueltas "
            f"({results['win']}W / {results['loss']}L / {results['push']}P), "
            f"{results['not_found']} sin resultado aún"
        )

        return {"settled": total_settled, **results}

    def _determine_result(self, bet: Bet, game: dict) -> str | None:
        """
        Determina si una apuesta ganó, perdió o empató.

        Args:
            bet: La apuesta registrada.
            game: El resultado del partido (de /scores API).

        Returns:
            "win", "loss", "push" o None si no se puede determinar.
        """
        scores = game.get("scores")
        if not scores or len(scores) < 2:
            return None

        # Extraer scores
        score_map = {}
        for s in scores:
            try:
                score_map[s["name"]] = int(s["score"])
            except (ValueError, KeyError):
                return None

        home = game.get("home_team")
        away = game.get("away_team")

        if home not in score_map or away not in score_map:
            return None

        home_score = score_map[home]
        away_score = score_map[away]

        # ─── Mercado h2h (moneyline / 1X2) ─────────────────────
        if bet.market == "h2h":
            return self._settle_h2h(bet, home, away, home_score, away_score)

        # ─── Mercado totals (over/under) ────────────────────────
        if bet.market == "totals":
            return self._settle_totals(bet, home_score, away_score)

        # ─── Mercado spreads (handicap) ─────────────────────────
        if bet.market == "spreads":
            return self._settle_spreads(bet, home, away, home_score, away_score)

        logger.warning(f"Mercado no soportado para liquidación: {bet.market}")
        return None

    @staticmethod
    def _settle_h2h(
        bet: Bet, home: str, away: str,
        home_score: int, away_score: int,
    ) -> str:
        """Liquida apuesta moneyline/1X2."""
        if home_score > away_score:
            winner = home
        elif away_score > home_score:
            winner = away
        else:
            winner = "Draw"

        if bet.outcome_name == winner:
            return "win"
        return "loss"

    @staticmethod
    def _settle_totals(
        bet: Bet,
        home_score: int, away_score: int,
    ) -> str:
        """Liquida apuesta over/under."""
        total = home_score + away_score
        line = bet.outcome_point

        if line is None:
            return None

        if bet.outcome_name == "Over":
            if total > line:
                return "win"
            elif total < line:
                return "loss"
            else:
                return "push"
        elif bet.outcome_name == "Under":
            if total < line:
                return "win"
            elif total > line:
                return "loss"
            else:
                return "push"
        return None

    @staticmethod
    def _settle_spreads(
        bet: Bet, home: str, away: str,
        home_score: int, away_score: int,
    ) -> str:
        """Liquida apuesta de handicap/spread."""
        spread = bet.outcome_point
        if spread is None:
            return None

        # El spread se aplica al equipo apostado
        if bet.outcome_name == home:
            adjusted = home_score + spread
            opponent = away_score
        elif bet.outcome_name == away:
            adjusted = away_score + spread
            opponent = home_score
        else:
            return None

        if adjusted > opponent:
            return "win"
        elif adjusted < opponent:
            return "loss"
        else:
            return "push"
