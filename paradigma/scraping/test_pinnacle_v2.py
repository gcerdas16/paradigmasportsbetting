"""
Test Pinnacle v2: mapea TODOS los subdominios de pinnacle.com a la misma IP
y captura todas las respuestas JSON para identificar los endpoints de datos.
"""

import logging
import subprocess
import re
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def resolve_via_google_dns(hostname: str) -> str | None:
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
    except Exception:
        pass
    return None


def test():
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("TEST v2: Pinnacle con DNS bypass completo")
    print("=" * 60)

    # Resolver IP principal
    main_ip = resolve_via_google_dns("www.pinnacle.com")
    if not main_ip:
        print("❌ No se pudo resolver www.pinnacle.com")
        return

    print(f"\nIP principal: {main_ip}")

    # Mapear www + todos los subdominios conocidos a la misma IP
    subdomains = [
        "www.pinnacle.com",
        "pinnacle.com",
        "arcadia.pinnacle.com",
        "guest.api.arcadia.pinnacle.com",
        "cdn.pinnacle.com",
        "guest.pinnacle.com",
        "api.pinnacle.com",
    ]
    rules = []
    for d in subdomains:
        ip = resolve_via_google_dns(d)
        if ip:
            rules.append(f"MAP {d} {ip}")
            print(f"  ✅ {d} -> {ip}")
        else:
            # Fallback a la IP principal
            rules.append(f"MAP {d} {main_ip}")
            print(f"  ⚠️  {d} -> {main_ip} (fallback)")
    host_rules = ", ".join(rules)
    print(f"\nReglas DNS: {len(rules)} dominios")

    # Contenedores
    all_json: list[tuple[str, str, int, str]] = []  # (domain, path, size, snippet)
    all_domains: dict[str, int] = {}

    def on_response(response):
        url = response.url
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path

        # Contar dominios
        all_domains[domain] = all_domains.get(domain, 0) + 1

        # Capturar JSON
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            try:
                body = response.json()
                text = str(body)
                snippet = text[:200]
                all_json.append((domain, path, len(text), snippet))
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                f"--host-resolver-rules={host_rules}",
                "--ignore-certificate-errors",
                "--disable-web-security",
            ],
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

        print("\nNavegando...")
        try:
            page.goto(
                "https://www.pinnacle.com/en/soccer/matchups/",
                wait_until="networkidle",
                timeout=45_000,
            )
            page.wait_for_timeout(5_000)
        except Exception as e:
            print(f"  Error: {e}")

        url = page.url
        title = page.title()
        print(f"  URL: {url}")
        print(f"  Título: {title}")

        if "block" in url.lower():
            print("  ❌ Todavía bloqueado")
            browser.close()
            return

        # Scroll agresivo
        for _ in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2_000)

        # Intentar click en alguna liga para forzar carga de datos
        try:
            # Buscar links a ligas
            links = page.query_selector_all("a[href*='/soccer/']")
            print(f"\n  Links de fútbol encontrados: {len(links)}")
            if links:
                for link in links[:3]:
                    href = link.get_attribute("href") or ""
                    text = link.inner_text()[:50]
                    print(f"    • {text} -> {href[:80]}")
        except Exception:
            pass

        browser.close()

    # Análisis
    print(f"\n{'='*60}")
    print(f"Dominios contactados ({len(all_domains)}):")
    for domain, count in sorted(all_domains.items(), key=lambda x: -x[1]):
        tag = ""
        if "pinnacle" in domain.lower():
            tag = " 👈"
        elif "block" in domain.lower() or "opendns" in domain.lower():
            tag = " ⛔"
        print(f"  {domain}: {count}{tag}")

    print(f"\nRespuestas JSON ({len(all_json)}):")
    for domain, path, size, snippet in sorted(all_json, key=lambda x: -x[2]):
        tag = ""
        if "matchup" in path.lower() or "market" in path.lower() or "odds" in path.lower():
            tag = " 👈 DATA"
        print(f"  [{size:>8}] {domain}{path[:80]}{tag}")
        if size > 100:
            print(f"            snippet: {snippet[:150]}...")


if __name__ == "__main__":
    test()
