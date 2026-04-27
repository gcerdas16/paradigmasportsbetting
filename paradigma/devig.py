"""
Shin devig: elimina el margen del bookmaker para obtener probabilidades justas.

Basado en el método Shin (1991,1993) implementado en the-pitchs-edge.
La idea: el bookmaker infla las odds para cubrir la presencia de "insiders"
que conocen el resultado. Shin estima la proporción de insiders (z) y
ajusta las probabilidades para que sumen exactamente 1.0.

Referencia: Shin, H.S. (1993) "Measuring the Incidence of Insider Trading
in a Market for State-Contingent Claims"
"""

import logging
from scipy.optimize import brentq

logger = logging.getLogger(__name__)


def shin_devig(odds: list[float]) -> list[float]:
    """
    Aplica Shin devig a una lista de odds decimales.

    Args:
        odds: Lista de odds decimales (ej: [1.80, 3.50, 4.20] para 1X2)

    Returns:
        Lista de probabilidades justas que suman ~1.0

    Ejemplo:
        >>> shin_devig([1.80, 3.50, 4.20])
        [0.528, 0.267, 0.205]  # suman 1.0
    """
    if not odds or any(o <= 1.0 for o in odds):
        logger.warning(f"Odds inválidas para Shin devig: {odds}")
        return _simple_devig(odds)

    n = len(odds)
    implied_probs = [1.0 / o for o in odds]
    total_implied = sum(implied_probs)

    # Si las probabilidades ya suman ~1.0, no hay margen que quitar
    if abs(total_implied - 1.0) < 0.001:
        return implied_probs

    # Si la suma es < 1.0, algo está mal (¿arbitraje?)
    if total_implied < 1.0:
        logger.warning(
            f"Suma de probabilidades implícitas < 1.0 ({total_implied:.4f}). "
            f"Posible arbitraje. Usando normalización simple."
        )
        return _simple_devig(odds)

    try:
        z = _solve_shin_z(implied_probs, n)
        fair_probs = _shin_probabilities(implied_probs, z, n)

        # Validar
        total = sum(fair_probs)
        if abs(total - 1.0) > 0.01:
            logger.warning(
                f"Shin devig: probabilidades no suman 1.0 ({total:.4f}). "
                f"Fallback a normalización simple."
            )
            return _simple_devig(odds)

        return fair_probs

    except Exception as e:
        logger.warning(f"Shin devig falló ({e}). Usando normalización simple.")
        return _simple_devig(odds)


def _solve_shin_z(implied_probs: list[float], n: int) -> float:
    """
    Resuelve la ecuación de Shin para encontrar z (proporción de insiders).

    La ecuación es:
    sum( sqrt(z^2 + 4*(1-z) * (pi^2 / sum_pi)) ) = 2*(1-z+n*z)

    donde pi = probabilidad implícita de cada outcome, sum_pi = sum(pi)
    """
    sum_pi = sum(implied_probs)

    def equation(z):
        lhs = sum(
            (z ** 2 + 4 * (1 - z) * (pi ** 2 / sum_pi)) ** 0.5
            for pi in implied_probs
        )
        rhs = 2 - 2 * z + n * z  # = 2 + z*(n-2)
        return lhs - rhs

    # z está entre 0 (sin margen) y un valor pequeño (típicamente < 0.1)
    z = brentq(equation, 0.0, 0.5)
    return z


def _shin_probabilities(
    implied_probs: list[float], z: float, n: int
) -> list[float]:
    """
    Calcula probabilidades justas usando z de Shin.

    fair_prob_i = (sqrt(z^2 + 4*(1-z)*(pi^2/sum_pi)) - z) / (2*(1-z))
    """
    sum_pi = sum(implied_probs)
    fair_probs = []

    for pi in implied_probs:
        numerator = (z ** 2 + 4 * (1 - z) * (pi ** 2 / sum_pi)) ** 0.5 - z
        denominator = 2 * (1 - z)
        fair_probs.append(numerator / denominator)

    return fair_probs


def _simple_devig(odds: list[float]) -> list[float]:
    """
    Fallback: normalización simple (dividir por la suma).
    Menos precisa que Shin pero funcional.
    """
    if not odds or any(o <= 1.0 for o in odds):
        return []
    implied = [1.0 / o for o in odds]
    total = sum(implied)
    if total == 0:
        return []
    return [p / total for p in implied]
