"""
Diagnóstico profundo de la API de 1xBet.

Captura TODA la estructura de datos para poder construir el parser correctamente.
Guarda los datos crudos en scraping_debug/ para análisis offline.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

DEBUG_DIR = Path("scraping_debug")
DEBUG_DIR.mkdir(exist_ok=True)


def test():
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("DIAGNÓSTICO PROFUNDO: 1xBet API")
    print("=" * 60)

    # Capturar TODAS las respuestas JSON
    all_json: list[dict] = []

    def on_response(response):
        url = response.url
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path

        if "1xbet" not in domain:
            return

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type and "javascript" not in content_type:
            return

        try:
            body = response.json()
            entry = {
                "url": url[:200],
                "domain": domain,
                "path": path,
                "status": response.status,
                "size": len(str(body)),
                "type": type(body).__name__,
                "body": body,
            }

            # Resumir body para no saturar la consola
            if isinstance(body, dict):
                entry["keys"] = list(body.keys())[:20]
                # Analizar primer nivel
                for k, v in body.items():
                    if isinstance(v, list) and len(v) > 0:
                        entry[f"__{k}_count"] = len(v)
                        if isinstance(v[0], dict):
                            entry[f"__{k}_first_keys"] = list(v[0].keys())[:20]
            elif isinstance(body, list) and len(body) > 0:
                entry["list_count"] = len(body)
                if isinstance(body[0], dict):
                    entry["first_item_keys"] = list(body[0].keys())[:20]

            all_json.append(entry)

        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
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

        # Paso 1: Página principal de fútbol
        print("\n1️⃣  Navegando a fútbol pre-match...")
        try:
            page.goto(
                "https://1xbet.com/en/line/football",
                wait_until="networkidle",
                timeout=45_000,
            )
            page.wait_for_timeout(5_000)
        except Exception as e:
            print(f"   Timeout (esperado): {str(e)[:60]}")

        print(f"   URL actual: {page.url}")
        print(f"   Respuestas JSON hasta ahora: {len(all_json)}")

        # Scroll
        for i in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2_000)

        # Paso 2: Una liga específica
        print("\n2️⃣  Navegando a Premier League...")
        try:
            page.goto(
                "https://1xbet.com/en/line/football/88637-england-premier-league",
                wait_until="networkidle",
                timeout=30_000,
            )
            page.wait_for_timeout(5_000)
        except Exception as e:
            print(f"   Timeout: {str(e)[:60]}")

        for i in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1_500)

        browser.close()

    # ---------------------------------------------------------------------------
    # Análisis
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"ANÁLISIS DE RESPUESTAS")
    print(f"{'='*60}")

    # Agrupar por path
    by_path: dict[str, list] = {}
    for entry in all_json:
        path = entry["path"]
        if path not in by_path:
            by_path[path] = []
        by_path[path].append(entry)

    print(f"\nEndpoints únicos: {len(by_path)}")
    for path, entries in sorted(by_path.items(), key=lambda x: -sum(e["size"] for e in x[1])):
        total_size = sum(e["size"] for e in entries)
        print(f"\n  📡 {path}")
        print(f"     Calls: {len(entries)}, Total size: {total_size:,}")
        for entry in entries[:2]:  # Mostrar 2 primeras
            print(f"     Type: {entry['type']}, Size: {entry['size']:,}")
            if "keys" in entry:
                print(f"     Keys: {entry['keys']}")
            if "first_item_keys" in entry:
                print(f"     First item keys: {entry['first_item_keys']}")
            # Mostrar info de sub-arrays
            for k, v in entry.items():
                if k.startswith("__") and k.endswith("_count"):
                    name = k[2:].replace("_count", "")
                    first_keys_key = f"__{name}_first_keys"
                    fk = entry.get(first_keys_key, [])
                    print(f"     {name}: {v} items, first_keys: {fk}")

    # ---------------------------------------------------------------------------
    # Buscar endpoints con datos de odds
    # ---------------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("ENDPOINTS CON POSIBLES ODDS")
    print(f"{'='*60}")

    odds_keywords = ["coef", "odds", "price", "1x2", "total", "handicap",
                     "E", "O1", "O2", "Opp1", "Opp2", "home", "away"]

    for path, entries in by_path.items():
        for entry in entries:
            body = entry["body"]
            body_str = str(body)[:5000].lower()
            matches = [kw for kw in odds_keywords if kw.lower() in body_str]
            if matches:
                print(f"\n  🎯 {path}")
                print(f"     Keywords: {matches}")
                print(f"     Size: {entry['size']:,}")

                # Mostrar muestra del primer evento
                if isinstance(body, dict):
                    for key in ("Value", "Result", "Events", "data"):
                        if key in body and isinstance(body[key], list) and body[key]:
                            first = body[key][0]
                            if isinstance(first, dict):
                                print(f"     [{key}][0] keys: {list(first.keys())[:25]}")
                                # Mostrar valores de los campos más relevantes
                                for fk in list(first.keys())[:30]:
                                    val = first[fk]
                                    if isinstance(val, (str, int, float)):
                                        print(f"       {fk}: {str(val)[:80]}")
                                    elif isinstance(val, list) and len(val) > 0:
                                        print(f"       {fk}: list[{len(val)}], first={str(val[0])[:80]}")
                                    elif isinstance(val, dict):
                                        print(f"       {fk}: dict, keys={list(val.keys())[:10]}")
                            break

    # ---------------------------------------------------------------------------
    # Guardar datos crudos para análisis offline
    # ---------------------------------------------------------------------------
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Guardar resumen (sin body completo)
    summary_path = DEBUG_DIR / f"1xbet_deep_summary_{ts}.json"
    summary = []
    for entry in all_json:
        s = {k: v for k, v in entry.items() if k != "body"}
        summary.append(s)
    summary_path.write_text(json.dumps(summary, indent=2, default=str))

    # Guardar datos completos de los endpoints más grandes (con odds)
    for path, entries in by_path.items():
        total_size = sum(e["size"] for e in entries)
        if total_size > 10_000:  # Solo endpoints grandes
            safe_name = path.replace("/", "_").strip("_")[:60]
            data_path = DEBUG_DIR / f"1xbet_raw_{safe_name}_{ts}.json"
            bodies = [e["body"] for e in entries]
            try:
                data_path.write_text(json.dumps(bodies, indent=2, default=str))
                print(f"\n  💾 Guardado: {data_path.name} ({total_size:,} chars)")
            except Exception:
                pass

    print(f"\n  💾 Resumen: {summary_path.name}")
    print(f"\n✅ Ahora copie los archivos de scraping_debug/ que empiecen con '1xbet_raw_'")
    print("   y pégueme el contenido de los primeros 200 líneas del más grande.")
    print("   O mejor: ejecute este comando:")
    print(f"   python -c \"import json; d=json.load(open('scraping_debug/{summary_path.name}')); [print(e['path'], e['size']) for e in sorted(d, key=lambda x:-x['size'])[:10]]\"")


if __name__ == "__main__":
    test()
