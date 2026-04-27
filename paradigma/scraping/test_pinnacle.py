"""
Test rápido del Pinnacle scraper.

Scrapea solo la página principal (sin navegar a partidos individuales)
para verificar que la red permite acceder a pinnacle.com y que la
interceptación de arcadia.pinnacle.com funciona.

Uso:
    python -m scraping.test_pinnacle
"""

import json
import logging
import re
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def test_basic_access():
    """Test mínimo: ¿podemos acceder a Pinnacle y capturar matchups?"""

    from playwright.sync_api import sync_playwright

    matchups_captured: list[dict] = []
    markets_captured: list[dict] = []
    api_responses: list[str] = []

    def on_response(response):
        url = response.url
        if "arcadia.pinnacle.com" not in url:
            return
        try:
            path = urlparse(url).path
            api_responses.append(path)
            body = response.json()
            if not isinstance(body, list) or not body:
                return
            if "/matchups" in path and "/related" not in path:
                matchups_captured.extend(body)
            elif "/markets" in path:
                markets_captured.extend(body)
        except Exception:
            pass

    print("\n" + "=" * 60)
    print("TEST: Acceso a Pinnacle desde esta red")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = ctx.new_page()
        page.on("response", on_response)

        # Test 1: ¿Carga la página?
        print("\n[1/4] Navegando a pinnacle.com/en/soccer/matchups/ ...")
        try:
            page.goto(
                "https://www.pinnacle.com/en/soccer/matchups/",
                wait_until="networkidle",
                timeout=30_000,
            )
            page.wait_for_timeout(3_000)
            print("  ✅ Página cargada correctamente")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print("\n  DIAGNÓSTICO: Pinnacle podría estar bloqueado en esta red.")
            print("  Intentar con VPN o desde otra red.")
            browser.close()
            return False

        # Test 2: ¿Interceptamos la API?
        print(f"\n[2/4] Respuestas de arcadia.pinnacle.com capturadas: {len(api_responses)}")
        if api_responses:
            unique_paths = set()
            for path in api_responses:
                # Simplificar path
                simplified = re.sub(r'/\d+', '/{id}', path)
                unique_paths.add(simplified)
            print("  Endpoints capturados:")
            for path in sorted(unique_paths):
                print(f"    • {path}")
            print("  ✅ API interna interceptada correctamente")
        else:
            print("  ❌ No se capturó ninguna respuesta de la API interna")
            print("  Posible causa: Cloudflare bloqueando, o estructura de página cambió")
            browser.close()
            return False

        # Test 3: ¿Tenemos matchups?
        # Deduplicar
        seen = set()
        unique = []
        for m in matchups_captured:
            mid = m.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                unique.append(m)

        print(f"\n[3/4] Matchups (partidos) capturados: {len(unique)}")
        if unique:
            # Agrupar por liga
            leagues = {}
            for m in unique:
                league = m.get("league", {}).get("name", "Desconocida")
                leagues[league] = leagues.get(league, 0) + 1

            print("  Ligas encontradas:")
            for league, count in sorted(leagues.items(), key=lambda x: -x[1])[:15]:
                print(f"    • {league}: {count} partidos")
            if len(leagues) > 15:
                print(f"    ... y {len(leagues) - 15} ligas más")
            print("  ✅ Matchups capturados correctamente")

            # Mostrar ejemplo
            sample = unique[0]
            parts = sample.get("participants", [])
            home = next((p["name"] for p in parts if p.get("alignment") == "home"), "?")
            away = next((p["name"] for p in parts if p.get("alignment") == "away"), "?")
            print(f"\n  Ejemplo: {home} vs {away}")
            print(f"    Liga: {sample.get('league', {}).get('name', '?')}")
            print(f"    Inicio: {sample.get('startTime', '?')}")
        else:
            print("  ❌ No se capturaron matchups")

        # Test 4: ¿Tenemos markets?
        print(f"\n[4/4] Market entries capturadas: {len(markets_captured)}")
        if markets_captured:
            types = {}
            for m in markets_captured:
                t = m.get("type", "?")
                types[t] = types.get(t, 0) + 1
            print("  Tipos de mercado:")
            for t, count in sorted(types.items(), key=lambda x: -x[1]):
                print(f"    • {t}: {count}")
            print("  ✅ Markets capturados correctamente")
        else:
            print("  ⚠️  No se capturaron markets (normal si no entramos a partidos)")
            print("      Los markets se capturan al navegar a páginas individuales")

        browser.close()

    # Resumen
    print(f"\n{'='*60}")
    print("RESULTADO:")
    if unique and api_responses:
        print("  ✅ Pinnacle ACCESIBLE desde esta red")
        print(f"     {len(unique)} partidos de {len(leagues)} ligas disponibles")
        print(f"     {len(markets_captured)} market entries capturadas")
        print("\n  Siguiente paso: correr el scraper completo")
        print("    python -m scraping.pinnacle_scraper")
        return True
    else:
        print("  ❌ Pinnacle NO accesible o datos insuficientes")
        return False


if __name__ == "__main__":
    test_basic_access()
