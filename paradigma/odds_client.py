"""
Cliente para The Odds API.
Obtiene odds de Pinnacle (región eu) y casas blandas.
Basado en oddsapi_ev + SportsArbFinder.
"""

import logging
import subprocess
import warnings
import requests
import urllib3.util.connection
from typing import Optional

# Suprimir warnings de SSL (necesario por proxy corporativo)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import config

logger = logging.getLogger(__name__)


class OddsClient:
    """Wrapper para The Odds API v4."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.ODDS_API_KEY
        self.base_url = config.ODDS_API_BASE_URL
        self.remaining_requests: Optional[int] = None
        self.used_requests: Optional[int] = None

        if not self.api_key:
            raise ValueError("ODDS_API_KEY no configurada. Revisar .env")

    # ─── Deportes activos ────────────────────────────────────

    def get_active_sports(self) -> list[dict]:
        """Retorna lista de deportes activos (in-season, sin outrights)."""
        resp = self._get("/sports")
        if resp is None:
            return []
        sports = [s for s in resp if not s.get("has_outrights", False)]
        logger.info(f"Deportes activos: {len(sports)}")
        return sports

    # ─── Odds por deporte ────────────────────────────────────

    def get_events(self, sport: str) -> list[dict]:
        """
        Lista eventos sin odds (GRATIS, no gasta quota).
        Útil para scouting: saber cuántos eventos hay antes de pedir odds.
        """
        resp = self._get(f"/sports/{sport}/events")
        if resp is None:
            return []
        logger.info(f"{sport}: {len(resp)} eventos (scouting gratuito)")
        return resp

    def get_odds(
        self,
        sport: str,
        regions: Optional[list[str]] = None,
        markets: Optional[list[str]] = None,
        bookmakers: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Obtiene odds para un deporte.
        Si USE_BOOKMAKERS_PARAM=True, usa param bookmakers (4x más barato).
        Retorna lista de eventos con bookmakers y mercados.
        """
        markets = markets or config.ODDS_MARKETS

        params = {
            "markets": ",".join(markets),
            "oddsFormat": config.ODDS_FORMAT,
            "dateFormat": "iso",
            "includeLinks": "true",
        }

        # Usar bookmakers param (más barato) o regions (más amplio)
        if config.USE_BOOKMAKERS_PARAM and not regions:
            bks = bookmakers or config.TARGET_BOOKMAKERS
            params["bookmakers"] = ",".join(bks)
        else:
            regs = regions or config.ODDS_REGIONS
            params["regions"] = ",".join(regs)

        resp = self._get(f"/sports/{sport}/odds", params=params)
        if resp is None:
            return []

        logger.info(f"{sport}: {len(resp)} eventos obtenidos")
        return resp

    def get_scores(
        self,
        sport: str,
        days_from: int = 3,
    ) -> list[dict]:
        """
        Obtiene resultados de partidos completados.
        Costo: 2 si days_from está especificado, 1 si no.
        """
        params = {"daysFrom": str(days_from), "dateFormat": "iso"}
        resp = self._get(f"/sports/{sport}/scores", params=params)
        if resp is None:
            return []
        completed = [g for g in resp if g.get("completed")]
        logger.info(f"{sport}: {len(completed)} partidos completados (de {len(resp)} total)")
        return resp

    def get_all_odds(
        self,
        sports: Optional[list[str]] = None,
        regions: Optional[list[str]] = None,
        markets: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Obtiene odds de todos los deportes configurados.
        Si sports=None, usa la lista de config.SPORTS.
        """
        if sports is None:
            sports = config.SPORTS

        all_events = []
        for sport in sports:
            events = self.get_odds(sport, regions=regions, markets=markets)
            all_events.extend(events)

            if self.remaining_requests is not None and self.remaining_requests < 10:
                logger.warning(
                    f"Quedan {self.remaining_requests} requests. Deteniendo."
                )
                break

        logger.info(
            f"Total: {len(all_events)} eventos de {len(sports)} deportes. "
            f"API requests restantes: {self.remaining_requests}"
        )
        return all_events

    # ─── Extracción de Pinnacle ──────────────────────────────

    @staticmethod
    def extract_pinnacle_odds(events: list[dict]) -> dict:
        """
        Extrae las odds de Pinnacle de los eventos.
        Retorna dict: event_id -> {market -> {outcome_key -> odds_decimal}}

        outcome_key es una tupla (name, point) para identificar unívocamente
        cada outcome. Ejemplo: ("Over", 2.5), ("Home Team", None)
        """
        pinnacle_data = {}

        for event in events:
            event_id = event["id"]
            pinnacle_markets = {}

            for bookmaker in event.get("bookmakers", []):
                if bookmaker["key"] != config.PINNACLE_BOOK_KEY:
                    continue

                for market in bookmaker.get("markets", []):
                    market_key = market["key"]
                    outcomes = {}

                    for outcome in market.get("outcomes", []):
                        name = outcome["name"]
                        point = outcome.get("point")
                        price = outcome["price"]
                        outcome_key = (name, point)
                        outcomes[outcome_key] = price

                    if outcomes:
                        pinnacle_markets[market_key] = outcomes

            if pinnacle_markets:
                pinnacle_data[event_id] = pinnacle_markets

        logger.info(
            f"Pinnacle: odds extraídas para {len(pinnacle_data)} eventos"
        )
        return pinnacle_data

    # ─── Extracción de casas blandas ─────────────────────────

    @staticmethod
    def extract_soft_book_odds(events: list[dict]) -> list[dict]:
        """
        Extrae odds de casas blandas (excepto Pinnacle y exchanges).
        Retorna lista de dicts con toda la info de cada odd individual.
        Incluye links directos al bookmaker si están disponibles.
        """
        rows = []
        excluded_exchanges = 0

        for event in events:
            event_base = {
                "event_id": event["id"],
                "sport_key": event["sport_key"],
                "sport_title": event["sport_title"],
                "commence_time": event["commence_time"],
                "home_team": event["home_team"],
                "away_team": event["away_team"],
            }

            for bookmaker in event.get("bookmakers", []):
                book_key = bookmaker["key"]

                # Excluir Pinnacle (es nuestra referencia)
                if book_key == config.PINNACLE_BOOK_KEY:
                    continue

                # Excluir exchanges
                if book_key in config.EXCHANGE_BOOK_KEYS:
                    excluded_exchanges += 1
                    continue

                # Excluir mercados lay (de exchanges)
                for market in bookmaker.get("markets", []):
                    if market["key"].endswith("_lay"):
                        continue

                    for outcome in market.get("outcomes", []):
                        row = {
                            **event_base,
                            "book_key": book_key,
                            "book_title": bookmaker["title"],
                            "market": market["key"],
                            "outcome_name": outcome["name"],
                            "outcome_point": outcome.get("point"),
                            "odds": outcome["price"],
                            "book_link": bookmaker.get("link"),
                            "market_link": market.get("link"),
                            "outcome_link": outcome.get("link"),
                        }
                        rows.append(row)

        if excluded_exchanges:
            logger.info(f"Exchanges excluidos: {excluded_exchanges}")
        logger.info(f"Casas blandas: {len(rows)} odds individuales extraídas")
        return rows

    # ─── HTTP helpers ────────────────────────────────────────

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[list]:
        """GET request a The Odds API."""
        url = f"{self.base_url}{endpoint}"
        all_params = {"api_key": self.api_key}
        if params:
            all_params.update(params)

        try:
            # verify=False: necesario por proxy SSL corporativo (OpenDNS/Umbrella)
            resp = requests.get(url, params=all_params, timeout=30, verify=False)

            # Actualizar contadores de uso
            self.remaining_requests = _safe_int(
                resp.headers.get("x-requests-remaining")
            )
            self.used_requests = _safe_int(resp.headers.get("x-requests-used"))

            if resp.status_code == 401:
                logger.error("API key inválida o expirada")
                return None
            if resp.status_code == 422:
                logger.warning(f"Deporte/mercado no soportado: {endpoint}")
                return None
            if resp.status_code == 429:
                logger.error("Rate limit alcanzado. Esperar o subir de plan.")
                return None

            resp.raise_for_status()
            return resp.json()

        except requests.RequestException as e:
            logger.error(f"Error en request a {endpoint}: {e}")
            return None


def _safe_int(value) -> Optional[int]:
    """Convierte a int de forma segura."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ─── DNS Workaround ──────────────────────────────────────────
# OpenDNS (red corporativa) bloquea api.the-odds-api.com.
# Resolvemos via Google DNS (8.8.8.8) y parcheamos urllib3.

_DNS_OVERRIDES: dict[str, str] = {}


def _resolve_via_google_dns(hostname: str) -> Optional[str]:
    """Resuelve un hostname usando Google DNS (8.8.8.8)."""
    # Primero intentar resolución estándar (funciona en Railway/Linux)
    try:
        import socket
        ip = socket.gethostbyname(hostname)
        if ip and ip[0].isdigit():
            return ip
    except Exception:
        pass

    # Fallback: nslookup via Google DNS (para redes corporativas con OpenDNS)
    try:
        result = subprocess.run(
            ["nslookup", hostname, "8.8.8.8"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Address") and "8.8.8.8" not in line:
                ip = line.split(":")[-1].strip()
                if ip and ip[0].isdigit():
                    return ip
    except Exception as e:
        logger.warning(f"DNS resolve failed for {hostname}: {e}")
    return None


def _patch_dns():
    """Parchea urllib3 para usar IPs resueltas via Google DNS."""
    host = "api.the-odds-api.com"
    if host in _DNS_OVERRIDES:
        return  # Ya parcheado

    ip = _resolve_via_google_dns(host)
    if not ip:
        logger.warning("No se pudo resolver DNS alternativo. Usando default.")
        return

    _DNS_OVERRIDES[host] = ip
    logger.info(f"DNS override: {host} -> {ip}")

    _original_create_connection = urllib3.util.connection.create_connection

    def _patched_create_connection(address, *args, **kwargs):
        host, port = address
        resolved = _DNS_OVERRIDES.get(host, host)
        return _original_create_connection((resolved, port), *args, **kwargs)

    urllib3.util.connection.create_connection = _patched_create_connection


# Aplicar parche al importar el módulo
_patch_dns()
