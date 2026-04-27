"""
Historial de odds para detectar precios estancados.

Guarda snapshots de precios por escaneo y detecta cuándo una odd
no se ha movido en N escaneos consecutivos.

El campo last_update de The Odds API mide frecuencia de POLLING,
no cambio de precio (confirmado empíricamente 2026-04-27).
Por eso construimos nuestro propio tracking.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Directorio para snapshots
HISTORY_DIR = Path(__file__).parent / "odds_history_data"


class OddsHistory:
    """Rastrea cambios de precios entre escaneos sucesivos."""

    def __init__(self, max_snapshots: int = 10):
        """
        Args:
            max_snapshots: Máximo de snapshots a conservar en memoria.
        """
        self.max_snapshots = max_snapshots
        self.snapshots: list[dict] = []
        HISTORY_DIR.mkdir(exist_ok=True)

    def record_snapshot(self, events: list[dict]) -> dict:
        """
        Registra un snapshot de todos los precios actuales.

        Args:
            events: Lista de eventos raw de la API.

        Returns:
            Dict con estadísticas del snapshot.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        prices = {}

        for event in events:
            event_id = event["id"]
            for bookmaker in event.get("bookmakers", []):
                book_key = bookmaker["key"]
                for market in bookmaker.get("markets", []):
                    market_key = market["key"]
                    for outcome in market.get("outcomes", []):
                        key = _make_key(
                            event_id, book_key, market_key,
                            outcome["name"], outcome.get("point"),
                        )
                        prices[key] = outcome["price"]

        snapshot = {
            "timestamp": timestamp,
            "prices": prices,
            "count": len(prices),
        }

        self.snapshots.append(snapshot)

        # Mantener solo los últimos N snapshots en memoria
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

        # Guardar a disco
        filename = HISTORY_DIR / f"snap_{timestamp.replace(':', '-')}.json"
        try:
            filename.write_text(json.dumps(snapshot, indent=2))
        except Exception as e:
            logger.warning(f"Error guardando snapshot: {e}")

        logger.info(f"Snapshot registrado: {len(prices)} precios @ {timestamp}")
        return {"timestamp": timestamp, "prices_count": len(prices)}

    def detect_stale_odds(
        self,
        event_id: str,
        book_key: str,
        market_key: str,
        outcome_name: str,
        outcome_point: Optional[float],
        min_unchanged_scans: int = 3,
    ) -> dict:
        """
        Detecta si una odd específica está potencialmente estancada.

        Args:
            event_id, book_key, etc.: Identificadores de la odd.
            min_unchanged_scans: Cuántos escaneos sin cambio para considerarla estancada.

        Returns:
            Dict con:
                - is_stale: bool
                - unchanged_scans: int (cuántos escaneos consecutivos sin cambio)
                - last_price: float o None
                - price_history: lista de precios recientes
        """
        if len(self.snapshots) < 2:
            return {"is_stale": False, "unchanged_scans": 0,
                    "last_price": None, "price_history": []}

        key = _make_key(event_id, book_key, market_key, outcome_name, outcome_point)

        # Recorrer snapshots de más reciente a más antiguo
        price_history = []
        for snap in reversed(self.snapshots):
            price = snap["prices"].get(key)
            if price is not None:
                price_history.append(price)

        if not price_history:
            return {"is_stale": False, "unchanged_scans": 0,
                    "last_price": None, "price_history": []}

        # Contar escaneos consecutivos sin cambio (desde el más reciente)
        unchanged = 0
        current_price = price_history[0]
        for price in price_history[1:]:
            if price == current_price:
                unchanged += 1
            else:
                break

        return {
            "is_stale": unchanged >= min_unchanged_scans,
            "unchanged_scans": unchanged,
            "last_price": current_price,
            "price_history": price_history[:5],  # Solo últimos 5
        }

    def get_movement_stats(self) -> dict:
        """
        Compara los últimos 2 snapshots y reporta cuántos precios cambiaron.
        Útil para entender la actividad del mercado.
        """
        if len(self.snapshots) < 2:
            return {"error": "Necesito al menos 2 snapshots"}

        prev = self.snapshots[-2]["prices"]
        curr = self.snapshots[-1]["prices"]

        all_keys = set(prev.keys()) | set(curr.keys())
        common = set(prev.keys()) & set(curr.keys())

        changed = 0
        unchanged = 0
        new_keys = 0
        removed_keys = 0

        for key in common:
            if prev[key] != curr[key]:
                changed += 1
            else:
                unchanged += 1

        new_keys = len(set(curr.keys()) - set(prev.keys()))
        removed_keys = len(set(prev.keys()) - set(curr.keys()))

        total = changed + unchanged
        change_pct = (changed / total * 100) if total > 0 else 0

        return {
            "total_prices": len(all_keys),
            "compared": total,
            "changed": changed,
            "unchanged": unchanged,
            "change_percent": round(change_pct, 1),
            "new": new_keys,
            "removed": removed_keys,
            "prev_timestamp": self.snapshots[-2]["timestamp"],
            "curr_timestamp": self.snapshots[-1]["timestamp"],
        }


def _make_key(
    event_id: str, book_key: str, market_key: str,
    outcome_name: str, outcome_point: Optional[float],
) -> str:
    """Crea una clave única para identificar una odd específica."""
    point_str = f"_{outcome_point}" if outcome_point is not None else ""
    return f"{event_id}|{book_key}|{market_key}|{outcome_name}{point_str}"
