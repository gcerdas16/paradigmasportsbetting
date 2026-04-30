"""
Detector de arbitraje entre casas de apuestas.

Busca oportunidades donde las odds combinadas de diferentes bookmakers
garantizan ganancia sin riesgo: 1/odds_A + 1/odds_B [+ 1/odds_C] < 1

Soporta mercados h2h (2-way y 3-way), totals, y spreads.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

import config

logger = logging.getLogger(__name__)

# Mínimo profit % para considerar un arb (cubre latencia y cambios de odds)
MIN_ARB_PROFIT_PERCENT = 0.5


@dataclass
class ArbLeg:
    """Una pata del arbitraje (una apuesta individual)."""
    book_key: str
    book_title: str
    outcome_name: str
    outcome_point: Optional[float]
    odds: float
    stake_fraction: float = 0.0  # Fracción del total a apostar en esta pata
    book_link: Optional[str] = None
    market_link: Optional[str] = None
    outcome_link: Optional[str] = None


@dataclass
class ArbOpportunity:
    """Oportunidad de arbitraje detectada."""
    event_id: str
    sport_key: str
    sport_title: str
    commence_time: str
    home_team: str
    away_team: str
    market: str
    profit_percent: float  # Ganancia garantizada en %
    legs: list[ArbLeg] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.home_team} vs {self.away_team}"

    @property
    def display_arb(self) -> str:
        legs_str = " | ".join(
            f"{leg.outcome_name} @{leg.odds:.2f} ({leg.book_title})"
            for leg in self.legs
        )
        return f"{legs_str} → +{self.profit_percent:.2f}%"


def find_arb_opportunities(events: list[dict]) -> list[ArbOpportunity]:
    """
    Busca oportunidades de arbitraje en los eventos de la API.

    Examina TODAS las combinaciones de bookmakers para cada evento y mercado
    buscando donde la suma inversa de odds < 1.

    Args:
        events: Lista de eventos con bookmakers y odds (de OddsClient.get_all_odds)

    Returns:
        Lista de ArbOpportunity ordenada por profit_percent descendente.
    """
    arbs = []

    for event in events:
        event_id = event["id"]
        sport_key = event["sport_key"]
        sport_title = event["sport_title"]
        commence_time = event["commence_time"]
        home_team = event["home_team"]
        away_team = event["away_team"]

        # Recopilar odds por market → outcome_key → lista de (book, odds, links)
        market_odds = defaultdict(lambda: defaultdict(list))

        for bookmaker in event.get("bookmakers", []):
            book_key = bookmaker["key"]
            book_title = bookmaker["title"]

            # Excluir exchanges
            if book_key in config.EXCHANGE_BOOK_KEYS:
                continue

            for market in bookmaker.get("markets", []):
                market_key = market["key"]
                if market_key.endswith("_lay"):
                    continue

                for outcome in market.get("outcomes", []):
                    outcome_key = (outcome["name"], outcome.get("point"))
                    market_odds[market_key][outcome_key].append({
                        "book_key": book_key,
                        "book_title": book_title,
                        "odds": outcome["price"],
                        "book_link": bookmaker.get("link"),
                        "market_link": market.get("link"),
                        "outcome_link": outcome.get("link"),
                    })

        # Para cada market, buscar arb
        for market_key, outcomes in market_odds.items():
            found = _find_arb_in_market(
                market_key, outcomes,
                event_id, sport_key, sport_title,
                commence_time, home_team, away_team,
            )
            arbs.extend(found)

    arbs.sort(key=lambda x: x.profit_percent, reverse=True)
    logger.info(f"Arbitraje: {len(arbs)} oportunidades encontradas")
    return arbs


def _find_arb_in_market(
    market_key: str,
    outcomes: dict,
    event_id: str,
    sport_key: str,
    sport_title: str,
    commence_time: str,
    home_team: str,
    away_team: str,
) -> list[ArbOpportunity]:
    """Busca arb dentro de un mercado específico de un evento."""

    if market_key == "h2h":
        return _find_h2h_arb(
            outcomes, event_id, sport_key, sport_title,
            commence_time, home_team, away_team, market_key,
        )
    elif market_key in ("totals", "spreads"):
        return _find_line_arb(
            outcomes, event_id, sport_key, sport_title,
            commence_time, home_team, away_team, market_key,
        )
    return []


def _find_h2h_arb(
    outcomes: dict,
    event_id: str,
    sport_key: str,
    sport_title: str,
    commence_time: str,
    home_team: str,
    away_team: str,
    market_key: str,
) -> list[ArbOpportunity]:
    """
    Busca arb en mercado h2h.
    Para 2-way: Home vs Away. Para 3-way: Home vs Draw vs Away.
    """
    arbs = []

    # Identificar todos los outcomes (home, away, draw)
    outcome_keys = list(outcomes.keys())

    # Necesitamos al menos 2 outcomes con odds
    if len(outcome_keys) < 2:
        return []

    # Tomar la mejor odd (max) de cada outcome entre todas las casas
    best_per_outcome = {}
    for ok, book_odds_list in outcomes.items():
        best = max(book_odds_list, key=lambda x: x["odds"])
        best_per_outcome[ok] = best

    # Verificar condición de arb: sum(1/best_odds) < 1
    inv_sum = sum(1.0 / bo["odds"] for bo in best_per_outcome.values())

    if inv_sum < 1.0:
        profit_pct = (1.0 / inv_sum - 1.0) * 100.0

        # Filtro: profit mínimo para cubrir latencia
        if profit_pct < MIN_ARB_PROFIT_PERCENT:
            return []

        # Verificar que TODAS las patas usen bookmakers DISTINTOS
        books_used = [best["book_key"] for best in best_per_outcome.values()]
        if len(books_used) != len(set(books_used)):
            logger.debug(
                f"ARB descartado (mismo bookmaker en ambos lados): "
                f"{home_team} vs {away_team} books={books_used}"
            )
            return []

        # Calcular stakes proporcionales
        legs = []
        for ok, best in best_per_outcome.items():
            stake_frac = (1.0 / best["odds"]) / inv_sum
            legs.append(ArbLeg(
                book_key=best["book_key"],
                book_title=best["book_title"],
                outcome_name=ok[0],
                outcome_point=ok[1],
                odds=best["odds"],
                stake_fraction=stake_frac,
                book_link=best.get("book_link"),
                market_link=best.get("market_link"),
                outcome_link=best.get("outcome_link"),
            ))

        arbs.append(ArbOpportunity(
            event_id=event_id,
            sport_key=sport_key,
            sport_title=sport_title,
            commence_time=commence_time,
            home_team=home_team,
            away_team=away_team,
            market=market_key,
            profit_percent=profit_pct,
            legs=legs,
        ))

    return arbs


def _find_line_arb(
    outcomes: dict,
    event_id: str,
    sport_key: str,
    sport_title: str,
    commence_time: str,
    home_team: str,
    away_team: str,
    market_key: str,
) -> list[ArbOpportunity]:
    """
    Busca arb en totals/spreads.
    Agrupa por línea y busca Over/Under (o Home/Away HC) con arb.
    """
    arbs = []

    # Agrupar por point (línea)
    by_line = defaultdict(dict)
    for (name, point), book_odds_list in outcomes.items():
        if point is None:
            continue
        by_line[point][(name, point)] = book_odds_list

    # Para cada línea, buscar arb entre los dos lados
    for point, line_outcomes in by_line.items():
        if len(line_outcomes) < 2:
            continue

        # Para totals: Over vs Under. Para spreads: Team A vs Team B
        outcome_keys = list(line_outcomes.keys())

        # Encontrar pares complementarios
        if market_key == "totals":
            over_key = None
            under_key = None
            for ok in outcome_keys:
                if ok[0] == "Over":
                    over_key = ok
                elif ok[0] == "Under":
                    under_key = ok
            if not over_key or not under_key:
                continue
            pair = [over_key, under_key]
        else:
            # Spreads: buscar par con puntos opuestos
            # Ej: (Home, -1.5) y (Away, +1.5)
            if len(outcome_keys) >= 2:
                pair = outcome_keys[:2]
            else:
                continue

        # Mejor odd por cada lado del par
        best_per_side = {}
        for ok in pair:
            if ok not in line_outcomes:
                continue
            best = max(line_outcomes[ok], key=lambda x: x["odds"])
            best_per_side[ok] = best

        if len(best_per_side) < 2:
            continue

        inv_sum = sum(1.0 / bo["odds"] for bo in best_per_side.values())

        if inv_sum < 1.0:
            profit_pct = (1.0 / inv_sum - 1.0) * 100.0

            # Filtro: profit mínimo
            if profit_pct < MIN_ARB_PROFIT_PERCENT:
                continue

            # Verificar bookmakers DISTINTOS en cada pata
            books_used = [best["book_key"] for best in best_per_side.values()]
            if len(books_used) != len(set(books_used)):
                logger.debug(
                    f"ARB line descartado (mismo bookmaker): "
                    f"{home_team} vs {away_team} {market_key} L={point}"
                )
                continue

            legs = []
            for ok, best in best_per_side.items():
                stake_frac = (1.0 / best["odds"]) / inv_sum
                legs.append(ArbLeg(
                    book_key=best["book_key"],
                    book_title=best["book_title"],
                    outcome_name=ok[0],
                    outcome_point=ok[1],
                    odds=best["odds"],
                    stake_fraction=stake_frac,
                    book_link=best.get("book_link"),
                    market_link=best.get("market_link"),
                    outcome_link=best.get("outcome_link"),
                ))

            arbs.append(ArbOpportunity(
                event_id=event_id,
                sport_key=sport_key,
                sport_title=sport_title,
                commence_time=commence_time,
                home_team=home_team,
                away_team=away_team,
                market=market_key,
                profit_percent=profit_pct,
                legs=legs,
            ))

    return arbs
