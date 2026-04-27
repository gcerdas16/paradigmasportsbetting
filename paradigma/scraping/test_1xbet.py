"""
Test de acceso a 1xBet y diagnóstico de su estructura.

1xBet también usa una API interna para cargar odds.
Este script identifica los endpoints correctos.
"""

import logging
import subprocess
import re
from urllib.parse import urlparse
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def resolve_dns(hostname: str) -> Optional[str]:
    """Resuelve hostname a IPv4 via Google DNS."""
    try:
        result = subprocess.run(
            ["nslookup", "-type=A", hostname, "8.8.8.8"],
            capture_output=True, text=True, timeout=10,
        )
        # Buscar líneas con IPs IPv4 después de "Non-authoritative answer"
        in_answer = False
        for line in result.stdout.splitlines():
            line = line.strip()
            if "Non-authoritative" in line:
                in_answer = True
                continue
            if in_answer and line.startswith("Address"):
                # Extraer IP — puede ser "Address: 1.2.3.4" o "Addresses: ..."
                parts = line.split(":")
                if len(parts) >= 2:
                    ip = parts[-1].strip()
                    # Verificar que es IPv4 (no IPv6)
                    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
                        return ip
    except Exception:
        pass
    return None


def test():
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("TEST: Acceso a 1xBet")
    print("=" * 60)

    # 1xBet IPs conocidas (resueltas previamente via Google DNS)
    # 1xbet.com -> 104.18.41.64, 172.64.146.192
    # 1xbet.co.cr -> 217.19.248.132
    known_ips = {
        "1xbet.com": "104.18.41.64",
        "www.1xbet.com": "104.18.41.64",
        "1xbet.co.cr": "217.19.248.132",
    }

    # Intentar resolver dinámicamente, si no, usar IPs conocidas
    dns_rules = []
    for domain, fallback_ip in known_ips.items():
        ip = resolve_dns(domain) or fallback_ip
        dns_rules.append(f"MAP {domain} {ip}")
        src = "DNS" if resolve_dns(domain) else "hardcoded"
        print(f"  {domain} -> {ip} ({src})")

    host_rules = ", ".join(dns_rules)

    # Contenedores
    json_responses: list[tuple[str, str, int, str]] = []
    all_domains: dict[str, int] = {}

    def on_response(response):
        url = response.url
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        all_domains[domain] = all_domains.get(domain, 0) + 1

        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            try:
                body = response.json()
                text = str(body)
                json_responses.append((domain, path, len(text), text[:200]))
            except Exception:
                pass

    # Probar URLs (incluir variantes y mirrors)
    urls_to_try = [
        "https://1xbet.com/en/line/football",
        "https://1xbet.co.cr/en/line/football",
        "https://1xbet.com/en/live/football",
    ]

    with sync_playwright() as p:
        launch_args = ["--ignore-certificate-errors"]
        if host_rules:
            launch_args.append(f"--host-resolver-rules={host_rules}")

        browser = p.chromium.launch(headless=True, args=launch_args)
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

        for url in urls_to_try:
            print(f"\nProbando: {url}")
            json_responses.clear()
            all_domains.clear()

            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
                page.wait_for_timeout(5_000)
            except Exception as e:
                print(f"  Error: {e}")
                continue

            current_url = page.url
            title = page.title()
            print(f"  URL actual: {current_url}")
            print(f"  Título: {title}")

            if "opendns.com" in current_url.lower():
                print(f"  ⛔ BLOQUEADO por OpenDNS")
                continue

            if "/block" in current_url.lower():
                print(f"  ⚠️  1xBet redirigió a página de bloqueo propia")
                # Capturar contenido de la página de bloqueo
                try:
                    text = page.inner_text("body")[:500]
                    print(f"  Contenido: {text[:200]}")
                except Exception:
                    pass
                page.screenshot(path="scraping_debug/1xbet_block.png")
                print(f"  Screenshot: scraping_debug/1xbet_block.png")
                # No continuar, seguir con siguiente URL
                continue

            # Scroll
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1_500)

            # Screenshot
            page.screenshot(path="scraping_debug/1xbet_test.png")
            print(f"  Screenshot: scraping_debug/1xbet_test.png")

            # Dominios
            print(f"\n  Dominios contactados ({len(all_domains)}):")
            for domain, count in sorted(all_domains.items(), key=lambda x: -x[1])[:15]:
                tag = " 👈" if "1xbet" in domain.lower() or "bet" in domain.lower() else ""
                print(f"    {domain}: {count}{tag}")

            # JSON responses
            print(f"\n  Respuestas JSON ({len(json_responses)}):")
            for domain, path, size, snippet in sorted(json_responses, key=lambda x: -x[2])[:15]:
                tag = ""
                keywords = ["sport", "event", "odds", "line", "match", "game", "coef"]
                if any(kw in path.lower() for kw in keywords):
                    tag = " 👈 DATA"
                print(f"    [{size:>8}] {domain}{path[:80]}{tag}")

            # Si encontramos datos, no probar más URLs
            if json_responses:
                print(f"\n  ✅ 1xBet accesible!")
                break

        browser.close()


if __name__ == "__main__":
    test()
