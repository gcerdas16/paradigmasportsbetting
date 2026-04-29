"""
Tracker de apuestas (paper trading y real).
Registra cada apuesta, resultado y métricas (CLV, ROI, P&L).
Usa SQLAlchemy para soportar SQLite (dev) y PostgreSQL (prod).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

import config
from ev_calculator import ValueBet

logger = logging.getLogger(__name__)

Base = declarative_base()


class Bet(Base):
    """Modelo de una apuesta registrada."""

    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Evento
    event_id = Column(String(64), nullable=False)
    sport_key = Column(String(64))
    sport_title = Column(String(128))
    commence_time = Column(String(64))
    home_team = Column(String(128))
    away_team = Column(String(128))

    # Apuesta
    book_key = Column(String(64))
    book_title = Column(String(128))
    market = Column(String(32))
    outcome_name = Column(String(128))
    outcome_point = Column(Float, nullable=True)
    odds_at_bet = Column(Float, nullable=False)

    # Probabilidades y cálculos al momento de apostar
    fair_prob = Column(Float)
    ev_percent = Column(Float)
    kelly_fraction = Column(Float)
    kelly_stake_percent = Column(Float)
    pinnacle_odds_at_bet = Column(Float, nullable=True)  # Pinnacle al momento de apostar
    bookmaker_link = Column(Text, nullable=True)          # Link directo al bookmaker

    # Stake y bankroll
    stake = Column(Float)
    bankroll_before = Column(Float)

    # Resultado (se llena después)
    result = Column(String(16), nullable=True)  # "win", "loss", "push", "void"
    odds_at_close = Column(Float, nullable=True)  # Odds de cierre (para CLV)
    pnl = Column(Float, nullable=True)  # Profit/Loss
    bankroll_after = Column(Float, nullable=True)
    clv_percent = Column(Float, nullable=True)  # Closing Line Value %
    settled_at = Column(DateTime, nullable=True)

    # Metadata
    is_paper = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)


class BankrollSnapshot(Base):
    """Snapshot diario del bankroll para tracking."""

    __tablename__ = "bankroll_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    bankroll = Column(Float, nullable=False)
    total_bets = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    avg_ev = Column(Float, nullable=True)
    avg_clv = Column(Float, nullable=True)


class Tracker:
    """Gestiona el registro y seguimiento de apuestas."""

    def __init__(self, db_url: Optional[str] = None):
        url = db_url or config.DATABASE_URL
        self.engine = create_engine(url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._bankroll: Optional[float] = None
        logger.info(f"Tracker inicializado. DB: {url}")

    @property
    def bankroll(self) -> float:
        """Bankroll actual."""
        if self._bankroll is None:
            self._bankroll = self._calculate_bankroll()
        return self._bankroll

    def _calculate_bankroll(self) -> float:
        """Calcula el bankroll actual basado en apuestas registradas."""
        session = self.Session()
        try:
            # Buscar la última apuesta con bankroll_after
            last_bet = (
                session.query(Bet)
                .filter(Bet.bankroll_after.isnot(None))
                .order_by(Bet.id.desc())
                .first()
            )
            if last_bet:
                # Restar stakes de apuestas pendientes (sin resultado)
                pending_stakes = (
                    session.query(Bet)
                    .filter(Bet.result.is_(None))
                    .filter(Bet.id > last_bet.id)
                    .all()
                )
                bankroll = last_bet.bankroll_after
                for bet in pending_stakes:
                    bankroll -= bet.stake
                return bankroll

            # Si no hay apuestas resueltas, partir del bankroll inicial
            # menos stakes pendientes
            pending = session.query(Bet).filter(Bet.result.is_(None)).all()
            bankroll = config.INITIAL_BANKROLL
            for bet in pending:
                bankroll -= bet.stake
            return bankroll
        finally:
            session.close()

    def place_bet(self, vb: ValueBet) -> Bet:
        """
        Registra una nueva apuesta (paper o real).

        Args:
            vb: ValueBet detectada por el scanner.

        Returns:
            Bet registrada con ID.
        """
        session = self.Session()
        try:
            current_bankroll = self.bankroll
            stake = current_bankroll * (vb.kelly_stake_percent / 100.0)

            # Verificar exposición diaria
            daily_exposure = self._get_daily_exposure(session)
            max_exposure = current_bankroll * (config.MAX_DAILY_EXPOSURE / 100.0)

            if daily_exposure + stake > max_exposure:
                logger.warning(
                    f"Exposición diaria excedida. "
                    f"Actual: ${daily_exposure:.2f}, "
                    f"Stake: ${stake:.2f}, "
                    f"Máx: ${max_exposure:.2f}. "
                    f"Apuesta OMITIDA."
                )
                return None

            bet = Bet(
                event_id=vb.event_id,
                sport_key=vb.sport_key,
                sport_title=vb.sport_title,
                commence_time=vb.commence_time,
                home_team=vb.home_team,
                away_team=vb.away_team,
                book_key=vb.book_key,
                book_title=vb.book_title,
                market=vb.market,
                outcome_name=vb.outcome_name,
                outcome_point=vb.outcome_point,
                odds_at_bet=vb.odds,
                fair_prob=vb.fair_prob,
                ev_percent=vb.ev_percent,
                kelly_fraction=vb.kelly_fraction,
                kelly_stake_percent=vb.kelly_stake_percent,
                pinnacle_odds_at_bet=vb.pinnacle_odds,
                bookmaker_link=vb.best_link,
                stake=stake,
                bankroll_before=current_bankroll,
                is_paper=config.PAPER_TRADING,
            )

            session.add(bet)
            session.commit()
            session.refresh(bet)

            self._bankroll = current_bankroll - stake

            logger.info(
                f"{'📝 PAPER' if bet.is_paper else '💰 REAL'} BET #{bet.id}: "
                f"{vb.display_name} | {vb.display_bet} | "
                f"EV: {vb.ev_percent:.1f}% | "
                f"Kelly: {vb.kelly_stake_percent:.2f}% | "
                f"Stake: ${stake:.2f} | "
                f"Book: {vb.book_title}"
            )
            return bet

        finally:
            session.close()

    def settle_bet(
        self,
        bet_id: int,
        result: str,
        odds_at_close: Optional[float] = None,
    ):
        """
        Liquida una apuesta con su resultado.

        Args:
            bet_id: ID de la apuesta.
            result: "win", "loss", "push", "void"
            odds_at_close: Odds al cierre del mercado (para CLV).
        """
        session = self.Session()
        try:
            bet = session.query(Bet).get(bet_id)
            if not bet:
                logger.error(f"Apuesta #{bet_id} no encontrada")
                return

            bet.result = result
            bet.odds_at_close = odds_at_close
            bet.settled_at = datetime.now(timezone.utc)

            if result == "win":
                bet.pnl = bet.stake * (bet.odds_at_bet - 1)
            elif result == "loss":
                bet.pnl = -bet.stake
            elif result == "push":
                bet.pnl = 0.0
            elif result == "void":
                bet.pnl = 0.0
            else:
                logger.warning(f"Resultado desconocido: {result}")
                bet.pnl = 0.0

            bet.bankroll_after = bet.bankroll_before + bet.pnl

            # Calcular CLV si tenemos odds de cierre
            if odds_at_close and odds_at_close > 1.0:
                close_implied = 1.0 / odds_at_close
                bet_implied = 1.0 / bet.odds_at_bet
                bet.clv_percent = (bet_implied - close_implied) / close_implied * 100

            session.commit()
            self._bankroll = None  # Invalidar cache

            logger.info(
                f"Apuesta #{bet_id} liquidada: {result} | "
                f"P&L: ${bet.pnl:+.2f} | "
                f"CLV: {bet.clv_percent:+.1f}%"
                if bet.clv_percent
                else f"Apuesta #{bet_id} liquidada: {result} | P&L: ${bet.pnl:+.2f}"
            )

        finally:
            session.close()

    def get_stats(self) -> dict:
        """Retorna estadísticas actuales del tracker."""
        session = self.Session()
        try:
            all_bets = session.query(Bet).all()
            settled = [b for b in all_bets if b.result is not None]
            pending = [b for b in all_bets if b.result is None]
            wins = [b for b in settled if b.result == "win"]
            losses = [b for b in settled if b.result == "loss"]

            total_pnl = sum(b.pnl for b in settled if b.pnl)
            avg_ev = (
                sum(b.ev_percent for b in all_bets) / len(all_bets)
                if all_bets
                else 0
            )
            clv_bets = [b for b in settled if b.clv_percent is not None]
            avg_clv = (
                sum(b.clv_percent for b in clv_bets) / len(clv_bets)
                if clv_bets
                else None
            )
            roi = (
                total_pnl / sum(b.stake for b in settled) * 100
                if settled
                else 0
            )

            return {
                "bankroll": self.bankroll,
                "initial_bankroll": config.INITIAL_BANKROLL,
                "total_bets": len(all_bets),
                "settled": len(settled),
                "pending": len(pending),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": len(wins) / len(settled) * 100 if settled else 0,
                "total_pnl": total_pnl,
                "roi_percent": roi,
                "avg_ev": avg_ev,
                "avg_clv": avg_clv,
                "is_paper": config.PAPER_TRADING,
                "bets_to_validate": max(0, config.MIN_BETS_TO_VALIDATE - len(settled)),
            }

        finally:
            session.close()

    def get_pending_bets(self) -> list[Bet]:
        """Retorna apuestas pendientes de liquidar."""
        session = self.Session()
        try:
            return session.query(Bet).filter(Bet.result.is_(None)).all()
        finally:
            session.close()

    def _get_daily_exposure(self, session) -> float:
        """Calcula la exposición total del día actual."""
        today = datetime.now(timezone.utc).date()
        bets_today = (
            session.query(Bet)
            .filter(Bet.result.is_(None))
            .all()
        )
        return sum(b.stake for b in bets_today if b.stake)

    def is_daily_limit_reached(self) -> bool:
        """Verifica si la exposición diaria ya alcanzó el máximo."""
        session = self.SessionLocal()
        try:
            daily_exposure = self._get_daily_exposure(session)
            max_exposure = self.bankroll * (config.MAX_DAILY_EXPOSURE / 100.0)
            return daily_exposure >= max_exposure
        finally:
            session.close()

    def check_stop_loss(self) -> bool:
        """
        Verifica si se activó el stop-loss semanal.
        Retorna True si hay que pausar.
        """
        stats = self.get_stats()
        initial = config.INITIAL_BANKROLL
        current = stats["bankroll"]
        loss_pct = (1 - current / initial) * 100

        if loss_pct >= config.STOP_LOSS_WEEKLY_PERCENT:
            logger.warning(
                f"⚠️ STOP-LOSS ACTIVADO. "
                f"Pérdida: {loss_pct:.1f}% "
                f"(umbral: {config.STOP_LOSS_WEEKLY_PERCENT}%). "
                f"PAUSAR OPERACIONES."
            )
            return True
        return False
