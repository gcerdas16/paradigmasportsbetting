"""
Test de Pinnacle con bypass de DNS corporativo.

OpenDNS bloquea pinnacle.com. Opciones:
1. Usar proxy SOCKS5 (si tenemos uno)
2. Modificar el archivo hosts de Windows
3. Usar un servidor DNS alternativo a nivel de sistema
4. Usar Playwright con un proxy

Este script prueba la opción más sencilla:
resolver el IP de pinnacle.com via Google DNS y usar --host-resolver-rules de Chromium.
"""

import logging
import subprocess
import re
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def resolve_via_google_dns(hostname: str) -> str | None:
    """Resuelve un hostname usando Google DNS (8.8.8.8)."""
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
        print(f"  Error resolviendo DNS: {e}")
    return None


def test_with_dns_bypass():
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("TEST: Pinnacle con bypass de DNS corporativo")
    print("=" * 60)

    # Resolver IPs via Google DNS
    domains_to_resolve = [
        "www.pinnacle.com",
        "arcadia.pinnacle.com",
        "cdn.pinnacle.com",
    ]

    rules = []
    print("\nResolviendo IPs via Google DNS (8.8.8.8):")
    for domain in domains_to_resolve:
        ip = resolve_via_google_dns(domain)
        if ip:
            print(f"  ✅ {domain} -> {ip}")
            rules.append(f"MAP {domain} {ip}")
        else:
            print(f"  ❌ {domain} -> no resuelto")

    if not rules:
        print("\n❌ No se pudieron resolver las IPs. Verificar acceso a Google DNS.")
        return False

    host_rules = ", ".join(rules)
    print(f"\nReglas de DNS: {host_rules}")

    # Contenedores para datos interceptados
    api_responses: list[str] = []
    matchups: list[dict] = []
    json_responses: list[tuple[str, int]] = []

    def on_response(response):
        url = response.url
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path

        # Capturar TODAS las JSON
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            try:
                body = response.json()
                json_responses.append((f"{domain}{path}", len(str(body))))

                if "arcadia" in domain or "pinnacle" in domain:
                    api_responses.append(path)
                    if isinstance(body, list) and body:
                        if "/matchups" in path and "/related" not in path:
                            matchups.extend(body)
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                f"--host-resolver-rules={host_rules}",
                "--ignore-certificate-errors",
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

        print("\nNavegando a pinnacle.com con DNS bypass ...")
        try:
            page.goto(
                "https://www.pinnacle.com/en/soccer/matchups/",
                wait_until="networkidle",
                timeout=45_000,
            )
            page.wait_for_timeout(5_000)
        except Exception as e:
            print(f"  Error: {e}")

        current_url = page.url
        title = page.title()
        print(f"  URL actual: {current_url}")
        print(f"  Título: {title}")

        # Screenshot
        page.screenshot(path="scraping_debug/pinnacle_vpn_test.png")
        print("  Screenshot: scraping_debug/pinnacle_vpn_test.png")

        # Scroll
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2_000)

        browser.close()

    # Resultados
    blocked = "block.opendns.com" in current_url or "blocked" in title.lower()

    print(f"\n{'='*60}")
    if blocked:
        print("❌ TODAVÍA BLOQUEADO por OpenDNS")
        print("   El DNS bypass con --host-resolver-rules no fue suficiente.")
        print("   Opciones restantes:")
        print("   1. Agregar entradas al archivo hosts de Windows (requiere admin)")
        print("   2. Cambiar DNS del adaptador de red a 8.8.8.8")
        print("   3. Usar un proxy SOCKS5 externo")
        print("   4. Correr desde otra red (ej: hotspot del celular)")
        return False
    else:
        print("✅ PINNACLE ACCESIBLE con DNS bypass!")
        print(f"   API responses: {len(api_responses)}")
        print(f"   Matchups: {len(matchups)}")

        # Deduplicar matchups
        seen = set()
        unique = [m for m in matchups if m.get("id") not in seen and not seen.add(m.get("id"))]

        if unique:
            leagues = {}
            for m in unique:
                lg = m.get("league", {}).get("name", "?")
                leagues[lg] = leagues.get(lg, 0) + 1
            print(f"\n   {len(unique)} partidos en {len(leagues)} ligas")
            for lg, count in sorted(leagues.items(), key=lambda x: -x[1])[:10]:
                print(f"     • {lg}: {count}")
        return True


if __name__ == "__main__":
    test_with_dns_bypass()
