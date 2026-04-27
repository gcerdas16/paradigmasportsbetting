"""
Calculadora de Expected Value y Kelly Criterion.

Compara odds de casas blandas vs. probabilidades justas de Pinnacle
para encontrar value bets (EV > 0).
"""

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import config
from devig import shin_devig

logger = logging.getLogger(__name__)


@dataclass
class ValueBet:
    """Representa una apuesta con valor positivo detectada."""
    event_id: str
    sport_key: str
    sport_title: str
    commence_time: str
    home_team: str
    away_team: str
    book_key: str
    book_title: str
    market: str
    outcome_name: str
    outcome_point: Optional[float]
    odds: float
    fair_prob: float
    ev_percent: float
    kelly_fraction: float
    kelly_stake_percent: float
    pinnacle_odds: Optional[float] = None     # Odds de Pinnacle al momento de detectar
    book_link: Optional[str] = None           # Link directo al bookmaker (de la API)
    market_link: Optional[str] = None         # Link directo al mercado
    outcome_link: Optional[str] = None        # Link directo al betslip

    @property
    def display_name(self) -> str:
        """Nombre legible del evento."""
        return f"{self.home_team} vs {self.away_team}"

    @property
    def display_bet(self) -> str:
        """Descripción legible de la apuesta."""
        point_str = f" {self.outcome_point}" if self.outcome_point is not None else ""
        return f"{self.outcome_name}{point_str} @ {self.odds:.2f}"

    @property
    def best_link(self) -> Optional[str]:
        """El link más específico disponible (betslip > market > book)."""
        return self.outcome_link or self.market_link or self.book_link



def find_value_bets(
    soft_book_odds: list[dict],
    pinnacle_data: dict,
) -> list[ValueBet]:
    """
    Encuentra value bets comparando odds de casas blandas con Pinnacle.

    Args:
        soft_book_odds: Lista de odds individuales de casas blandas
                        (output de OddsClient.extract_soft_book_odds)
        pinnacle_data:  Dict de odds de Pinnacle por evento
                        (output de OddsClient.extract_pinnacle_odds)

    Returns:
        Lista de ValueBet ordenada por EV descendente.
    """
    value_bets = []

    # Pre-calcular: cuántos outcomes tiene cada (event, book, market)
    # para detectar comparaciones 2-way vs 3-way (ej: NHL h2h)
    soft_outcome_counts: Counter = Counter()
    for row in soft_book_odds:
        key = (row["event_id"], row["book_key"], row["market"])
        soft_outcome_counts[key] += 1

    market_mismatch_count = 0

    for row in soft_book_odds:
        event_id = row["event_id"]
        market = row["market"]
        outcome_name = row["outcome_name"]
        outcome_point = row["outcome_point"]
        book_odds = row["odds"]

        # ¿Tenemos Pinnacle para este evento y mercado?
        if event_id not in pinnacle_data:
            continue
        if market not in pinnacle_data[event_id]:
            continue

        pinnacle_market = pinnacle_data[event_id][market]

        # CRÍTICO para h2h: Verificar que el bookmaker tiene el mismo número
        # de outcomes que Pinnacle. Evita comparar 2-way (moneyline incl OT)
        # vs 3-way (reglamentario con Draw).
        # Para totals/spreads NO aplica: cada línea es siempre 2-way
        # (Over/Under o Home/Away HC), pero el total de líneas varía.
        if market == "h2h":
            pinnacle_n = len(pinnacle_market)
            book_n = soft_outcome_counts[(event_id, row["book_key"], market)]
            if book_n != pinnacle_n:
                market_mismatch_count += 1
                continue

        outcome_key = (outcome_name, outcome_point)

        # ¿Pinnacle tiene este outcome exacto?
        if outcome_key not in pinnacle_market:
            continue

        # Aplicar filtros básicos
        if book_odds < config.MIN_ODDS_DECIMAL or book_odds > config.MAX_ODDS_DECIMAL:
            continue

        # Para totals/spreads: devig por LÍNEA (par Over/Under o Home/Away HC)
        # Para h2h: devig sobre todos los outcomes (Home/Draw/Away)
        if market in ("totals", "spreads") and outcome_point is not None:
            # Encontrar el par complementario para esta línea
            if market == "totals":
                complement_name = "Under" if outcome_name == "Over" else "Over"
            else:  # spreads
                # El complementario es el otro equipo en la misma línea
                complement_point = -outcome_point
                complement_candidates = [
                    (k, v) for k, v in pinnacle_market.items()
                    if k[1] is not None and abs(k[1] - complement_point) < 0.001
                ]
                if not complement_candidates:
                    continue
                complement_key, complement_odds = complement_candidates[0]
                line_odds = [pinnacle_market[outcome_key], complement_odds]
                line_keys = [outcome_key, complement_key]
                fair_probs = shin_devig(line_odds)
                if not fair_probs:
                    continue
                fair_prob = fair_probs[0]  # Primer elemento = nuestro outcome
                # Saltar al cálculo de EV
                ev_pct = calculate_ev_percent(book_odds, fair_prob)
                if ev_pct < config.MIN_EV_PERCENT:
                    continue
                kelly_full = calculate_kelly(book_odds, fair_prob)
                kelly_stake = min(
                    kelly_full * config.KELLY_FRACTION,
                    config.MAX_KELLY_PERCENT / 100.0,
                )
                if kelly_stake <= 0:
                    continue
                pinnacle_odds_now = pinnacle_market.get(outcome_key)
                vb = ValueBet(
                    event_id=event_id,
                    sport_key=row["sport_key"],
                    sport_title=row["sport_title"],
                    commence_time=row["commence_time"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    book_key=row["book_key"],
                    book_title=row["book_title"],
                    market=market,
                    outcome_name=outcome_name,
                    outcome_point=outcome_point,
                    odds=book_odds,
                    fair_prob=fair_prob,
                    ev_percent=ev_pct,
                    kelly_fraction=kelly_full,
                    kelly_stake_percent=kelly_stake * 100,
                    pinnacle_odds=pinnacle_odds_now,
                    book_link=row.get("book_link"),
                    market_link=row.get("market_link"),
                    outcome_link=row.get("outcome_link"),
                )
                value_bets.append(vb)
                continue

            # Totals: par Over/Under en la misma línea
            complement_key = (complement_name, outcome_point)
            if complement_key not in pinnacle_market:
                continue
            line_odds = [pinnacle_market[outcome_key], pinnacle_market[complement_key]]
            line_keys = [outcome_key, complement_key]
            fair_probs = shin_devig(line_odds)
            if not fair_probs:
                continue
            fair_prob = fair_probs[0]  # Primer elemento = nuestro outcome

        else:
            # h2h: devig sobre todos los outcomes (Home/Draw/Away)
            pinnacle_odds_list = list(pinnacle_market.values())
            fair_probs = shin_devig(pinnacle_odds_list)
            if not fair_probs:
                continue
            pinnacle_keys = list(pinnacle_market.keys())
            try:
                idx = pinnacle_keys.index(outcome_key)
            except ValueError:
                continue
            fair_prob = fair_probs[idx]

        # Calcular EV%
        ev_pct = calculate_ev_percent(book_odds, fair_prob)

        # ¿Supera el umbral?
        if ev_pct < config.MIN_EV_PERCENT:
            continue

        # Kelly Criterion
        kelly_full = calculate_kelly(book_odds, fair_prob)
        kelly_stake = min(
            kelly_full * config.KELLY_FRACTION,
            config.MAX_KELLY_PERCENT / 100.0,
        )

        # No apostar si Kelly es negativo (no hay edge real)
        if kelly_stake <= 0:
            continue

        # Guardar odds de Pinnacle al momento de detectar (para CLV futuro)
        pinnacle_odds_now = pinnacle_market.get(outcome_key)

        vb = ValueBet(
            event_id=event_id,
            sport_key=row["sport_key"],
            sport_title=row["sport_title"],
            commence_time=row["commence_time"],
            home_team=row["home_team"],
            away_team=row["away_team"],
            book_key=row["book_key"],
            book_title=row["book_title"],
            market=market,
            outcome_name=outcome_name,
            outcome_point=outcome_point,
            odds=book_odds,
            fair_prob=fair_prob,
            ev_percent=ev_pct,
            kelly_fraction=kelly_full,
            kelly_stake_percent=kelly_stake * 100,
            pinnacle_odds=pinnacle_odds_now,
            book_link=row.get("book_link"),
            market_link=row.get("market_link"),
            outcome_link=row.get("outcome_link"),
        )
        value_bets.append(vb)

    # Ordenar por EV descendente
    value_bets.sort(key=lambda x: x.ev_percent, reverse=True)

    if market_mismatch_count:
        logger.warning(
            f"Filtradas {market_mismatch_count} odds por market type mismatch "
            f"(2-way vs 3-way)"
        )
    logger.info(
        f"Value bets encontradas: {len(value_bets)} "
        f"(de {len(soft_book_odds)} odds analizadas)"
    )
    return value_bets


def calculate_ev_percent(odds_decimal: float, fair_prob: float) -> float:
    """
    Calcula el Expected Value como porcentaje.

    EV% = (fair_prob * (odds - 1) - (1 - fair_prob)) * 100
        = (fair_prob * odds - 1) * 100

    Ejemplo:
        odds = 2.10, fair_prob = 0.52
        EV% = (0.52 * 2.10 - 1) * 100 = 9.2%
    """
    return (fair_prob * odds_decimal - 1.0) * 100.0


def calculate_kelly(odds_decimal: float, fair_prob: float) -> float:
    """
    Kelly Criterion completo (full Kelly).

    f* = (p * b - q) / b
    donde:
        p = probabilidad justa de ganar
        q = 1 - p
        b = odds - 1 (ganancia neta por unidad apostada)

    Retorna fracción del bankroll (ej: 0.05 = 5%).
    """
    b = odds_decimal - 1.0
    if b <= 0:
        return 0.0
    q = 1.0 - fair_prob
    kelly = (fair_prob * b - q) / b
    return max(kelly, 0.0)
