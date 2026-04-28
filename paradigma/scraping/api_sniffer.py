"""
API Sniffer — Descubre la estructura de API de cualquier bookmaker.

Abre el sitio en Playwright, navega a la sección de fútbol,
e intercepta TODAS las respuestas JSON de la API.
Guarda todo en archivos JSON para análisis posterior.

Uso:
    cd paradigma
    python -m scraping.api_sniffer bet365
    python -m scraping.api_sniffer doradobet
    python -m scraping.api_sniffer melbet
"""

import json
import sys
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Configuración de sitios a investigar
SITES = {
    "bet365": {
        "name": "bet365",
        "start_url": "https://www.bet365.com/#/AS/B1/K%5E5/",
        "football_urls": [
            "https://www.bet365.com/#/AS/B1/K%5E5/",
        ],
        "domain_hints": ["bet365"],
    },
    "doradobet": {
        "name": "DoradoBet",
        "start_url": "https://doradobet.com/deportes/66",
        "football_urls": [
            "https://doradobet.com/deportes/66",
        ],
        "domain_hints": ["doradobet"],
    },
    "melbet": {
        "name": "MelBet",
        "start_url": "https://melbet.com/en/line/football",
        "football_urls": [
            "https://melbet.com/en/line/football",
        ],
        "domain_hints": ["melbet"],
    },
    "20bet": {
        "name": "20Bet",
        "start_url": "https://20bet.com/en/line/football",
        "football_urls": [
            "https://20bet.com/en/line/football",
        ],
        "domain_hints": ["20bet"],
    },
    "888sport": {
        "name": "888sport",
        "start_url": "https://www.888sport.es/futbol/",
        "football_urls": [
            "https://www.888sport.es/futbol/",
        ],
        "domain_hints": ["888sport", "kambi"],
    },
    "betsafe": {
        "name": "BetSafe",
        "start_url": "https://www.betsafe.com/es/apuestas-deportivas/futbol?tab=liveAndUpcoming",
        "football_urls": [
            "https://www.betsafe.com/es/apuestas-deportivas/futbol?tab=liveAndUpcoming",
        ],
        "domain_hints": ["betsafe", "kambi", "betsson"],
    },
}


OUTPUT_DIR = Path("scraping_debug/api_sniff")


def sniff(site_key: str, headless: bool = False):
    """Captura todo el tráfico de API de un bookmaker."""
    from playwright.sync_api import sync_playwright, Response

    if site_key not in SITES:
        print(f"Sitio '{site_key}' no configurado. Opciones: {list(SITES.keys())}")
        return

    site = SITES[site_key]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Almacenar requests capturados
    captured = []
    total_bytes = 0

    def on_response(response: Response):
        nonlocal total_bytes
        url = response.url
        status = response.status
        content_type = response.headers.get("content-type", "")

        # Filtrar: solo JSON/JS/text responses que podrían contener datos
        is_data = any(t in content_type for t in ["json", "javascript", "text/plain", "xml"])
        if not is_data:
            return

        # Filtrar assets estáticos
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        skip_exts = (".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ttf", ".ico")
        if any(path_lower.endswith(ext) for ext in skip_exts):
            return

        try:
            body_text = response.text()
        except Exception:
            return

        if len(body_text) < 50:
            return

        # Intentar parsear como JSON
        body_json = None
        try:
            body_json = json.loads(body_text)
        except (json.JSONDecodeError, ValueError):
            pass

        entry = {
            "url": url,
            "status": status,
            "content_type": content_type,
            "domain": parsed.netloc,
            "path": parsed.path,
            "query": parsed.query[:500],
            "body_size": len(body_text),
            "is_json": body_json is not None,
            "body_preview": body_text[:2000] if not body_json else None,
            "body_json_preview": None,
        }

        # Para JSON, guardar preview estructurado
        if body_json is not None:
            if isinstance(body_json, list):
                entry["body_json_preview"] = {
                    "type": "array",
                    "length": len(body_json),
                    "first_item_keys": list(body_json[0].keys()) if body_json and isinstance(body_json[0], dict) else None,
                    "sample": json.dumps(body_json[:2], default=str)[:3000],
                }
            elif isinstance(body_json, dict):
                entry["body_json_preview"] = {
                    "type": "object",
                    "keys": list(body_json.keys())[:30],
                    "sample": {},
                }
                # Para cada key, mostrar tipo y preview
                for k, v in list(body_json.items())[:15]:
                    if isinstance(v, list):
                        sample_item = v[0] if v and isinstance(v[0], dict) else v[:2] if v else []
                        entry["body_json_preview"]["sample"][k] = {
                            "type": f"array[{len(v)}]",
                            "first_item_keys": list(v[0].keys()) if v and isinstance(v[0], dict) else None,
                            "preview": json.dumps(sample_item, default=str)[:1000],
                        }
                    elif isinstance(v, dict):
                        entry["body_json_preview"]["sample"][k] = {
                            "type": "object",
                            "keys": list(v.keys())[:20],
                        }
                    else:
                        entry["body_json_preview"]["sample"][k] = {
                            "type": type(v).__name__,
                            "value": str(v)[:200],
                        }

        captured.append(entry)
        total_bytes += len(body_text)

        # Log en tiempo real
        domain = parsed.netloc
        size_kb = len(body_text) / 1024
        json_tag = " [JSON]" if body_json else ""
        print(f"  📡 {domain}{parsed.path[:60]} ({size_kb:.1f}KB){json_tag}")

    print(f"\n{'='*70}")
    print(f"🔍 API SNIFFER — {site['name']}")
    print(f"{'='*70}")
    print(f"  Capturando tráfico de API...")
    print(f"  Headless: {headless}")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--ignore-certificate-errors"],
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

        # Navegar al sitio principal
        print(f"  🌐 Navegando a {site['start_url']}")
        try:
            page.goto(site["start_url"], wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(5_000)
        except Exception as e:
            print(f"  ⚠️ Timeout en carga inicial: {e}")

        # Scroll
        print(f"  📜 Scrolling...")
        for _ in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2_000)

        # Navegar a URLs de fútbol
        for url in site["football_urls"]:
            if url == site["start_url"]:
                continue
            print(f"\n  🌐 Navegando a {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
                page.wait_for_timeout(5_000)
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1_500)
            except Exception as e:
                print(f"  ⚠️ Error: {e}")

        # Capturar el HTML final
        try:
            html = page.content()
            html_path = OUTPUT_DIR / f"{site_key}_page_{ts}.html"
            html_path.write_text(html[:500_000], encoding="utf-8")
            print(f"\n  💾 HTML guardado: {html_path}")
        except Exception:
            pass

        # Screenshot
        try:
            ss_path = OUTPUT_DIR / f"{site_key}_screenshot_{ts}.png"
            page.screenshot(path=str(ss_path), full_page=False)
            print(f"  📸 Screenshot: {ss_path}")
        except Exception:
            pass

        browser.close()

    # Guardar resultados
    out_path = OUTPUT_DIR / f"{site_key}_api_{ts}.json"
    out_path.write_text(json.dumps(captured, indent=2, default=str, ensure_ascii=False))

    print(f"\n{'='*70}")
    print(f"📊 RESUMEN — {site['name']}")
    print(f"{'='*70}")
    print(f"  Requests capturados: {len(captured)}")
    print(f"  Datos totales: {total_bytes/1024:.1f} KB")
    print(f"  JSON responses: {sum(1 for c in captured if c['is_json'])}")
    print(f"  Output: {out_path}")

    # Mostrar dominios únicos
    domains = {}
    for c in captured:
        d = c["domain"]
        domains[d] = domains.get(d, 0) + 1
    print(f"\n  Dominios detectados:")
    for d, count in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"    {d}: {count} requests")

    # Mostrar paths con JSON más grandes (probables endpoints de datos)
    json_entries = [c for c in captured if c["is_json"]]
    json_entries.sort(key=lambda x: -x["body_size"])
    if json_entries:
        print(f"\n  Top endpoints JSON (por tamaño):")
        for entry in json_entries[:10]:
            size_kb = entry["body_size"] / 1024
            preview = ""
            if entry.get("body_json_preview"):
                bp = entry["body_json_preview"]
                if bp["type"] == "array":
                    preview = f" → array[{bp['length']}]"
                    if bp.get("first_item_keys"):
                        preview += f" keys: {bp['first_item_keys'][:8]}"
                else:
                    preview = f" → keys: {bp.get('keys', [])[:8]}"
            print(f"    [{size_kb:>7.1f}KB] {entry['domain']}{entry['path'][:70]}{preview}")

    print(f"\n  Archivo completo: {out_path}")
    print(f"  Para análisis detallado, abra el archivo JSON.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print(f"Uso: python -m scraping.api_sniffer <sitio>")
        print(f"Sitios: {', '.join(SITES.keys())}")
        sys.exit(1)

    site_key = sys.argv[1].lower()
    headless_flag = "--headless" in sys.argv

    sniff(site_key, headless=headless_flag)
