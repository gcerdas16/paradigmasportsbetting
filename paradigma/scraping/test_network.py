"""
Diagnóstico de red: captura TODAS las requests para ver qué endpoints usa Pinnacle.
"""

import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def diagnose():
    from playwright.sync_api import sync_playwright

    all_urls: list[str] = []
    json_responses: list[tuple[str, int]] = []

    def on_response(response):
        url = response.url
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path

        # Ignorar recursos estáticos
        skip_ext = (".js", ".css", ".png", ".jpg", ".svg", ".woff", ".woff2", ".ico", ".gif")
        if any(path.endswith(ext) for ext in skip_ext):
            return

        all_urls.append(f"{domain}{path}")

        # Capturar JSON responses
        content_type = response.headers.get("content-type", "")
        if "json" in content_type or "javascript" in content_type:
            try:
                body = response.json()
                size = len(str(body))
                json_responses.append((f"{domain}{path}", size))
            except Exception:
                pass

    print("\n" + "=" * 60)
    print("DIAGNÓSTICO DE RED: Pinnacle")
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

        print("\nNavegando a pinnacle.com ...")
        try:
            page.goto(
                "https://www.pinnacle.com/en/soccer/matchups/",
                wait_until="networkidle",
                timeout=45_000,
            )
            page.wait_for_timeout(5_000)
        except Exception as e:
            print(f"Error: {e}")

        # Check URL actual (por si redirige)
        current_url = page.url
        print(f"\nURL actual: {current_url}")

        # Check título
        title = page.title()
        print(f"Título: {title}")

        # Screenshot para debug
        page.screenshot(path="scraping_debug/pinnacle_test.png")
        print("Screenshot guardado en scraping_debug/pinnacle_test.png")

        # Scroll para cargar más
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2_000)

        browser.close()

    # Analizar dominios
    domains = {}
    for url in all_urls:
        domain = url.split("/")[0]
        domains[domain] = domains.get(domain, 0) + 1

    print(f"\n{'='*60}")
    print(f"Dominios contactados ({len(domains)}):")
    print(f"{'='*60}")
    for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
        marker = " 👈 API?" if "pinnacle" in domain.lower() or "arcadia" in domain.lower() else ""
        print(f"  {domain}: {count} requests{marker}")

    # JSON responses
    print(f"\n{'='*60}")
    print(f"Respuestas JSON ({len(json_responses)}):")
    print(f"{'='*60}")
    for url, size in sorted(json_responses, key=lambda x: -x[1])[:30]:
        marker = " 👈" if "pinnacle" in url.lower() or "arcadia" in url.lower() or "matchup" in url.lower() else ""
        print(f"  [{size:>8} chars] {url[:100]}{marker}")

    # Buscar patrones de API de Pinnacle
    print(f"\n{'='*60}")
    print("URLs con 'pinnacle' o 'matchup' o 'odds' o 'market':")
    print(f"{'='*60}")
    keywords = ["pinnacle", "matchup", "odds", "market", "arcadia", "api", "guest"]
    for url in sorted(set(all_urls)):
        if any(kw in url.lower() for kw in keywords):
            print(f"  {url[:120]}")


if __name__ == "__main__":
    diagnose()
