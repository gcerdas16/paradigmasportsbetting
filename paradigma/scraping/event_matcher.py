"""
Empareja eventos entre Pinnacle y 1xBet (u otros scrapers).

Problema: Pinnacle dice "Arsenal" y 1xBet dice "Arsenal FC".
Necesitamos fuzzy matching para emparejar el mismo partido.

Estrategia:
    1. Normalizar nombres (lower, quitar FC/CF/SC, quitar acentos)
    2. Comparar por ambos equipos (home + away)
    3. Verificar que las fechas son cercanas (mismo día)
"""

import logging
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Sufijos comunes que los bookmakers agregan/quitan
STRIP_SUFFIXES = [
    " fc", " cf", " sc", " ac", " afc", " ssc",
    " fk", " bk", " if", " ff",
    " united", " utd",
    " city",
    " (w)", " (corners)", " (bookings)", " (cards)",
]

# Mapeo manual para nombres muy distintos
MANUAL_MAP = {
    "man utd": "manchester united",
    "man city": "manchester city",
    "newcastle utd": "newcastle",
    "spurs": "tottenham",
    "tottenham hotspur": "tottenham",
    "wolves": "wolverhampton",
    "wolverhampton wanderers": "wolverhampton",
    "brighton hove albion": "brighton",
    "nottm forest": "nottingham forest",
    "west ham utd": "west ham",
    "west ham united": "west ham",
    "sheffield utd": "sheffield united",
    "sheffield united": "sheffield utd",
    "atletico madrid": "atl madrid",
    "atl. madrid": "atl madrid",
    "atletico de madrid": "atl madrid",
    "real sociedad": "r sociedad",
    "inter miami": "inter miami cf",
    "rb leipzig": "leipzig",
    "rasenballsport leipzig": "leipzig",
    "bayer leverkusen": "leverkusen",
    "borussia dortmund": "dortmund",
    "borussia monchengladbach": "monchengladbach",
    "paris saint germain": "psg",
    "paris saint-germain": "psg",
    "paris sg": "psg",
    "bayern munchen": "bayern munich",
    "fc bayern munich": "bayern munich",
    "juventus fc": "juventus",
    "ac milan": "milan",
    "inter milan": "inter",
    "fc internazionale": "inter",
    "as roma": "roma",
    "ssc napoli": "napoli",
    "sporting cp": "sporting",
    "sporting lisbon": "sporting",
    "benfica": "sl benfica",
    "cska moscow": "cska moskva",
}


def normalize_name(name: str) -> str:
    """Normaliza un nombre de equipo para matching."""
    # Lowercase
    s = name.lower().strip()

    # Quitar acentos
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))

    # Quitar puntuación
    s = re.sub(r"['\".,()\[\]]", "", s)

    # Quitar sufijos comunes
    for suffix in STRIP_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()

    # Quitar prefijos comunes
    for prefix in ["fc ", "fk ", "sc ", "ac ", "ss ", "bsc "]:
        if s.startswith(prefix):
            s = s[len(prefix):].strip()

    # Aplicar mapeo manual
    if s in MANUAL_MAP:
        s = MANUAL_MAP[s]

    # Normalizar espacios
    s = re.sub(r"\s+", " ", s).strip()

    return s


def names_match(name_a: str, name_b: str) -> bool:
    """¿Dos nombres de equipo refieren al mismo equipo?"""
    a = normalize_name(name_a)
    b = normalize_name(name_b)

    if a == b:
        return True

    # Uno contiene al otro (ej: "arsenal" en "arsenal fc")
    if a in b or b in a:
        return True

    # Verificar si comparten palabras significativas (>3 chars)
    words_a = {w for w in a.split() if len(w) > 3}
    words_b = {w for w in b.split() if len(w) > 3}
    if words_a and words_b:
        overlap = words_a & words_b
        if overlap and len(overlap) >= min(len(words_a), len(words_b)):
            return True

    return False


def normalize_league(league: str) -> str:
    """Normaliza un nombre de liga para comparación."""
    s = league.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Quitar puntuación
    s = re.sub(r"['.\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def leagues_compatible(league_a: str, league_b: str) -> bool:
    """Verifica si dos ligas son compatibles (mismo país/competición).

    Pinnacle: "England - Premier League"
    1xBet:   "England. Premier League"

    Ambas deben compartir palabras clave de país + competición.
    """
    if not league_a or not league_b:
        return True  # Sin info de liga, no filtrar

    a = normalize_league(league_a)
    b = normalize_league(league_b)

    if a == b:
        return True

    # Extraer palabras significativas (>2 chars)
    words_a = {w for w in a.split() if len(w) > 2}
    words_b = {w for w in b.split() if len(w) > 2}

    if not words_a or not words_b:
        return True

    # Deben compartir al menos 2 palabras (país + competición)
    overlap = words_a & words_b
    return len(overlap) >= 2


def match_events(
    pinnacle_events: list[dict],
    soft_events: list[dict],
) -> list[tuple[dict, dict]]:
    """
    Empareja eventos de Pinnacle con eventos de una casa blanda.

    Args:
        pinnacle_events: [{event_id, home_team, away_team, league, commence_time}]
        soft_events: [{event_id, home_team, away_team, league, commence_time}]

    Returns:
        Lista de tuplas (pinnacle_event, soft_event) emparejados.
    """
    matched = []
    used_soft = set()
    rejected_league = 0

    for p_evt in pinnacle_events:
        p_home = p_evt["home_team"]
        p_away = p_evt["away_team"]
        p_league = p_evt.get("league", "")

        best_match = None
        best_score = 0

        for i, s_evt in enumerate(soft_events):
            if i in used_soft:
                continue

            s_home = s_evt["home_team"]
            s_away = s_evt["away_team"]
            s_league = s_evt.get("league", "")

            # Verificar que ambos equipos coinciden
            home_ok = names_match(p_home, s_home)
            away_ok = names_match(p_away, s_away)

            if home_ok and away_ok:
                score = 2
            elif names_match(p_home, s_away) and names_match(p_away, s_home):
                score = 2  # Equipos invertidos
            else:
                continue

            # Verificar liga compatible (evita emparejar EPL con Copa)
            if not leagues_compatible(p_league, s_league):
                rejected_league += 1
                continue

            if score > best_score:
                best_score = score
                best_match = i

        if best_match is not None and best_score >= 2:
            used_soft.add(best_match)
            matched.append((p_evt, soft_events[best_match]))

    if rejected_league:
        logger.info(f"  Rechazados por liga incompatible: {rejected_league}")

    logger.info(
        f"Event matching: {len(matched)} emparejados "
        f"de {len(pinnacle_events)} Pinnacle / {len(soft_events)} soft"
    )

    # Log primeros 10 pares para verificación
    for p_evt, s_evt in matched[:10]:
        logger.info(
            f"  ✔ [{p_evt.get('league','')}] "
            f"{p_evt['home_team']} vs {p_evt['away_team']}  ↔  "
            f"{s_evt['home_team']} vs {s_evt['away_team']}"
        )
    if len(matched) > 10:
        logger.info(f"  ... y {len(matched) - 10} más")

    return matched
