"""
Scraper de Pinnacle para fútbol.

Intercepta la API interna de Pinnacle (arcadia.pinnacle.com) usando Playwright.
No requiere API key ni cuenta de Pinnacle.

Basado en: https://github.com/ACHBIDHAN/Pinnacle_Football_Odds_Scraper
Adaptado para Paradigma: extrae TODOS los partidos de fútbol disponibles,
no solo una lista predefinida, y produce datos en el formato compatible
con ev_calculator.py.

Uso:
    from paradigma.scraping.pinnacle_scraper import PinnacleScraper
    scraper = PinnacleScraper()
    pinnacle_data, events_info = scraper.scrape_all_football()
"""

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

PINNACLE_SOCCER_URL = "https://www.pinnacle.com/en/soccer/matchups/"

# Dominio correcto de la API interna de Pinnacle
PINNACLE_API_DOMAIN = "guest.api.arcadia.pinnacle.com"

# Dominios que necesitan bypass de DNS (OpenDNS corporativo los bloquea)
DNS_DOMAINS = [
    "www.pinnacle.com",
    "pinnacle.com",
    "guest.api.arcadia.pinnacle.com",
    "arcadia.pinnacle.com",
    "cdn.pinnacle.com",
]

# URLs de ligas específicas para navegar y capturar datos
# Pinnacle usa IDs de liga internos
LEAGUE_URLS = [
    "https://www.pinnacle.com/en/soccer/england-premier-league/matchups/",
    "https://www.pinnacle.com/en/soccer/spain-la-liga/matchups/",
    "https://www.pinnacle.com/en/soccer/germany-bundesliga/matchups/",
    "https://www.pinnacle.com/en/soccer/italy-serie-a/matchups/",
    "https://www.pinnacle.com/en/soccer/france-ligue-1/matchups/",
    "https://www.pinnacle.com/en/soccer/uefa-champions-league/matchups/",
    "https://www.pinnacle.com/en/soccer/uefa-europa-league/matchups/",
    "https://www.pinnacle.com/en/soccer/usa-mls/matchups/",
    "https://www.pinnacle.com/en/soccer/costa-rica-primera-division/matchups/",
]

# Ligas que nos interesan (substrings para filtrar).
# Si está vacío, se traen TODAS las ligas.
TARGET_LEAGUES = [
    "England - Premier League",
    "Spain - La Liga",
    "Germany - Bundesliga",
    "Italy - Serie A",
    "France - Ligue 1",
    "UEFA - Champions League",
    "UEFA - Europa League",
    "USA - MLS",
    "Costa Rica",
]

# Directorio de debug output
DEBUG_DIR = Path("scraping_debug")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def american_to_decimal(american: float) -> float:
    """Convierte odds americanas a decimales."""
    if american > 0:
        return round(american / 100 + 1, 4)
    return round(100 / abs(american) + 1, 4)


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

def _resolve_dns(hostname: str) -> Optional[str]:
    """Resuelve hostname via Google DNS (8.8.8.8) para bypass de OpenDNS."""
    try:
        result = subprocess.run(
            ["nslookup", hostname, "8.8.8.8"],
            capture_output=True, text=True, timeout=10,
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


def _build_dns_rules() -> str:
    """Construye reglas de DNS bypass para Chromium."""
    rules = []
    for domain in DNS_DOMAINS:
        ip = _resolve_dns(domain)
        if ip:
            rules.append(f"MAP {domain} {ip}")
            logger.info(f"DNS: {domain} -> {ip}")
        else:
            # Intentar resolver el dominio principal como fallback
            main_ip = _resolve_dns("www.pinnacle.com")
            if main_ip:
                rules.append(f"MAP {domain} {main_ip}")
                logger.info(f"DNS: {domain} -> {main_ip} (fallback)")
    return ", ".join(rules)


class PinnacleScraper:
    """Scrapea odds de Pinnacle interceptando la API interna guest.api.arcadia.pinnacle.com."""

    def __init__(self, headless: bool = True, timeout_ms: int = 60_000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    def scrape_all_football(
        self,
        league_filter: Optional[list[str]] = None,
    ) -> tuple[dict, list[dict]]:
        """
        Scrapea TODOS los partidos de fútbol disponibles en Pinnacle.

        Args:
            league_filter: Lista de substrings de liga para filtrar.
                          Si None, usa TARGET_LEAGUES.
                          Si lista vacía [], trae TODO.

        Returns:
            pinnacle_data: dict compatible con ev_calculator.py
                          event_id -> {market -> {(outcome_name, point) -> odds}}
            events_info: lista de dicts con info de cada evento
                        [{"event_id", "home_team", "away_team", "league",
                          "commence_time", "sport_key", "sport_title"}]
        """
        from playwright.sync_api import sync_playwright, Response

        if league_filter is None:
            league_filter = TARGET_LEAGUES

        # Contenedores para datos interceptados
        all_matchups: list[dict] = []
        all_markets: list[dict] = []
        all_related: dict[int, list] = {}
        seen_mkt: set = set()

        def on_response(response: Response):
            """Callback que intercepta respuestas de guest.api.arcadia.pinnacle.com."""
            url = response.url
            if PINNACLE_API_DOMAIN not in url:
                return
            try:
                path = urlparse(url).path
                body = response.json()
                if not isinstance(body, list) or not body:
                    return

                if "/related" in path and "/matchups/" in path:
                    m = re.search(r"/matchups/(\d+)/related", path)
                    if m:
                        main_id = int(m.group(1))
                        if main_id not in all_related:
                            all_related[main_id] = body
                elif "/matchups" in path:
                    all_matchups.extend(body)
                elif "/markets" in path:
                    for item in body:
                        k = (
                            item.get("matchupId"),
                            item.get("type"),
                            item.get("period"),
                            item.get("side"),
                            item.get("key"),
                            item.get("isAlternate"),
                        )
                        if k not in seen_mkt:
                            seen_mkt.add(k)
                            all_markets.append(item)
            except Exception:
                pass

        logger.info("Iniciando scraping de Pinnacle fútbol...")

        # Resolver DNS para bypass de OpenDNS corporativo
        dns_rules = _build_dns_rules()
        logger.info(f"DNS rules: {dns_rules[:100]}...")

        with sync_playwright() as p:
            launch_args = [
                "--ignore-certificate-errors",
            ]
            if dns_rules:
                launch_args.append(f"--host-resolver-rules={dns_rules}")

            browser = p.chromium.launch(
                headless=self.headless,
                args=launch_args,
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                ignore_https_errors=True,
            )
            page = ctx.new_page()
            page.on("response", on_response)

            # Navegar a cada liga para capturar matchups y markets
            for league_url in LEAGUE_URLS:
                logger.info(f"Navegando a {league_url}")
                try:
                    page.goto(league_url,
                              wait_until="networkidle", timeout=self.timeout_ms)
                    page.wait_for_timeout(3_000)

                    # Scroll para cargar todos los partidos
                    for _ in range(3):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1_000)
                except Exception as e:
                    logger.warning(f"Error en {league_url}: {e}")
                    continue

            # Deduplicar matchups
            seen_ids: set = set()
            unique_matchups: list[dict] = []
            for m in all_matchups:
                mid = m.get("id")
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    unique_matchups.append(m)

            logger.info(
                f"Matchups capturados: {len(unique_matchups)} partidos, "
                f"{len(all_markets)} market entries"
            )

            # Filtrar por ligas de interés (si se especificó filtro)
            if league_filter:
                filtered = []
                for m in unique_matchups:
                    league_name = m.get("league", {}).get("name", "")
                    if any(lf.lower() in league_name.lower() for lf in league_filter):
                        filtered.append(m)
                logger.info(
                    f"Filtrado por ligas: {len(filtered)} de {len(unique_matchups)} partidos"
                )
                unique_matchups = filtered

            # Si obtuvimos matchups pero no markets, navegar a partidos individuales
            if unique_matchups and not all_markets:
                logger.info("No se capturaron markets en listado. Navegando a partidos...")
                for matchup in unique_matchups[:20]:  # Limitar a 20 para no tardar
                    mid = matchup["id"]
                    parts = matchup.get("participants", [])
                    home = next((p_["name"] for p_ in parts if p_.get("alignment") == "home"), "")
                    away = next((p_["name"] for p_ in parts if p_.get("alignment") == "away"), "")

                    match_url = self._build_match_url(matchup)
                    logger.info(f"  Abriendo: {home} vs {away}")

                    try:
                        page.goto(match_url, wait_until="networkidle", timeout=45_000)
                        page.wait_for_timeout(2_000)
                    except Exception as e:
                        logger.warning(f"  Error: {e}")
                        continue

            browser.close()

        logger.info(
            f"Scraping completado. {len(all_markets)} market entries total, "
            f"{len(all_related)} related matchups"
        )

        # Guardar debug
        self._save_debug(all_markets, all_related)

        # Convertir a formato Paradigma
        pinnacle_data, events_info = self._to_paradigma_format(
            unique_matchups, all_markets, all_related
        )

        logger.info(f"Datos formateados: {len(pinnacle_data)} eventos con odds")
        return pinnacle_data, events_info

    # ---------------------------------------------------------------------------
    # Conversión a formato compatible con ev_calculator.py
    # ---------------------------------------------------------------------------

    def _to_paradigma_format(
        self,
        matchups: list[dict],
        markets: list[dict],
        related: dict,
    ) -> tuple[dict, list[dict]]:
        """
        Convierte los datos scrapeados al formato que usa ev_calculator.py:

        pinnacle_data: {
            event_id: {
                market_key: {
                    (outcome_name, point): odds_decimal
                }
            }
        }

        events_info: [{
            "event_id", "home_team", "away_team", "league",
            "commence_time", "sport_key", "sport_title"
        }]
        """
        pinnacle_data = {}
        events_info = []

        for matchup in matchups:
            mid = matchup["id"]
            event_id = str(mid)
            parts = matchup.get("participants", [])
            home = next((p["name"] for p in parts if p.get("alignment") == "home"), "")
            away = next((p["name"] for p in parts if p.get("alignment") == "away"), "")
            league = matchup.get("league", {}).get("name", "")
            start_time = matchup.get("startTime", "")

            events_info.append({
                "event_id": event_id,
                "home_team": home,
                "away_team": away,
                "league": league,
                "commence_time": start_time,
                "sport_key": "soccer",
                "sport_title": f"Soccer - {league}",
                "event_link": self._build_match_url(matchup),
            })

            event_markets = {}

            # --- Moneyline (h2h) ---
            ml = self._get_main(markets, mid, "moneyline", 0)
            if ml:
                h2h_odds = {}
                for price in ml[0].get("prices", []):
                    des = price.get("designation", "")
                    american = price.get("price")
                    if american is None:
                        continue
                    decimal = american_to_decimal(american)
                    if des == "home":
                        h2h_odds[(home, None)] = decimal
                    elif des == "away":
                        h2h_odds[(away, None)] = decimal
                    elif des == "draw":
                        h2h_odds[("Draw", None)] = decimal
                if h2h_odds:
                    event_markets["h2h"] = h2h_odds

            # --- Totals ---
            tot_rows = self._get_rows(markets, mid, "total", 0)
            if tot_rows:
                totals_odds = {}
                for row in tot_rows:
                    # Incluir TODAS las líneas (main + alternativas)
                    # para maximizar matching con 1xBet
                    for price in row.get("prices", []):
                        des = price.get("designation", "")
                        pts = price.get("points")
                        american = price.get("price")
                        if american is None or pts is None:
                            continue
                        pts = float(pts)
                        decimal = american_to_decimal(american)
                        if des == "over":
                            totals_odds[("Over", pts)] = decimal
                        elif des == "under":
                            totals_odds[("Under", pts)] = decimal
                if totals_odds:
                    event_markets["totals"] = totals_odds

            # --- Spreads (Asian Handicap) ---
            sp_rows = self._get_rows(markets, mid, "spread", 0)
            if sp_rows:
                spreads_odds = {}
                for row in sp_rows:
                    # Incluir TODAS las líneas (main + alternativas)
                    for price in row.get("prices", []):
                        des = price.get("designation", "")
                        pts = price.get("points")
                        american = price.get("price")
                        if american is None or pts is None:
                            continue
                        pts = float(pts)
                        decimal = american_to_decimal(american)
                        if des == "home":
                            spreads_odds[(home, pts)] = decimal
                        elif des == "away":
                            spreads_odds[(away, pts)] = decimal
                if spreads_odds:
                    event_markets["spreads"] = spreads_odds

            if event_markets:
                pinnacle_data[event_id] = event_markets

        return pinnacle_data, events_info

    # ---------------------------------------------------------------------------
    # Helpers internos
    # ---------------------------------------------------------------------------

    @staticmethod
    def _build_match_url(matchup: dict) -> str:
        parts = matchup.get("participants", [])
        home = next((p["name"] for p in parts if p.get("alignment") == "home"), "")
        away = next((p["name"] for p in parts if p.get("alignment") == "away"), "")
        league = matchup.get("league", {}).get("name", "")
        league_slug = slugify(league.replace(" - ", "-").replace(" – ", "-"))
        mid = matchup["id"]
        return (
            f"https://www.pinnacle.com/en/soccer/{league_slug}/"
            f"{slugify(home)}-vs-{slugify(away)}/{mid}/#all"
        )

    @staticmethod
    def _get_main(markets, matchup_id, mtype, period):
        return [
            m for m in markets
            if m.get("matchupId") == matchup_id
            and str(m.get("type", "")).lower() == mtype.lower()
            and m.get("period") == period
            and not m.get("isAlternate", False)
        ]

    @staticmethod
    def _get_rows(markets, matchup_id, mtype, period, side=None):
        return [
            m for m in markets
            if m.get("matchupId") == matchup_id
            and str(m.get("type", "")).lower() == mtype.lower()
            and m.get("period") == period
            and (side is None or str(m.get("side", "")).lower() == side.lower())
        ]

    @staticmethod
    def _save_debug(markets, related):
        DEBUG_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        mkt_path = DEBUG_DIR / f"pinnacle_markets_{ts}.json"
        rel_path = DEBUG_DIR / f"pinnacle_related_{ts}.json"
        mkt_path.write_text(json.dumps(markets, indent=2))
        rel_path.write_text(json.dumps(
            {str(k): v for k, v in related.items()}, indent=2
        ))
        logger.info(f"Debug guardado: {mkt_path}, {rel_path}")


# ---------------------------------------------------------------------------
# CLI para prueba independiente
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scraper = PinnacleScraper(headless=True)
    pinnacle_data, events_info = scraper.scrape_all_football()

    print(f"\n{'='*60}")
    print(f"Eventos con odds: {len(pinnacle_data)}")
    print(f"{'='*60}")

    for info in events_info:
        eid = info["event_id"]
        if eid in pinnacle_data:
            markets = pinnacle_data[eid]
            market_names = list(markets.keys())
            print(f"\n  {info['home_team']} vs {info['away_team']}")
            print(f"    Liga: {info['league']}")
            print(f"    Mercados: {market_names}")
            for mkt_name, outcomes in markets.items():
                print(f"    {mkt_name}:")
                for (name, point), odds in outcomes.items():
                    pt_str = f" {point}" if point is not None else ""
                    print(f"      {name}{pt_str}: {odds:.4f}")
