"""
Test rápido: ¿cuáles casas de apuestas blandas son accesibles desde esta red?

El proxy corporativo sale por Miami, US.
- 1xBet: BLOQUEADO en US
- Pinnacle: OK (con DNS bypass)
- ¿888sport, Betway, DraftKings, FanDuel, BetMGM?
"""

import logging
import subprocess
import re
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def resolve_dns(hostname: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["nslookup", hostname, "8.8.8.8"],
            capture_output=True, text=True, timeout=10,
        )
        in_answer = False
        for line in result.stdout.splitlines():
            line = line.strip()
            if "Non-authoritative" in line:
                in_answer = True
                continue
            if in_answer:
                # Buscar IPv4 en cualquier línea
                match = re.search(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", line)
                if match:
                    return match.group(1)
    except Exception:
        pass
    return None


BOOKMAKERS = {
    "888sport.com": {"url": "https://www.888sport.com/football/", "us_ok": True},
    "betway.com": {"url": "https://betway.com/en/sports/grp/soccer", "us_ok": False},
    "draftkings.com": {"url": "https://sportsbook.draftkings.com/leagues/soccer", "us_ok": True},
    "fanduel.com": {"url": "https://sportsbook.fanduel.com/soccer", "us_ok": True},
    "betmgm.com": {"url": "https://sports.betmgm.com/en/sports/soccer", "us_ok": True},
    "bet365.com": {"url": "https://www.bet365.com/", "us_ok": False},
    "williamhill.com": {"url": "https://sports.williamhill.com/betting/en-gb/football", "us_ok": False},
    "unibet.com": {"url": "https://www.unibet.com/betting/sports/filter/football", "us_ok": False},
}


def test():
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("TEST: Accesibilidad de casas de apuestas blandas")
    print("=" * 60)

    # Resolver DNS para todos los dominios
    all_rules = []
    for domain in BOOKMAKERS:
        ip = resolve_dns(domain)
        www_domain = f"www.{domain}"
        www_ip = resolve_dns(www_domain)
        if ip:
            all_rules.append(f"MAP {domain} {ip}")
        if www_ip:
            all_rules.append(f"MAP {www_domain} {www_ip}")

    host_rules = ", ".join(all_rules) if all_rules else ""

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

        results = {}

        for domain, info in BOOKMAKERS.items():
            url = info["url"]
            print(f"\n  Probando {domain}...", end=" ", flush=True)

            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                page.wait_for_timeout(3_000)
                current_url = page.url
                title = page.title()

                if "opendns.com" in current_url or "block.opendns" in current_url:
                    status = "⛔ DNS BLOQUEADO"
                elif "block" in current_url.lower() and "denied" in (page.inner_text("body")[:200]).lower():
                    status = "⛔ GEO-BLOQUEADO"
                elif "malware" in current_url.lower():
                    status = "⛔ DNS BLOQUEADO (malware)"
                elif title and len(title) > 3:
                    status = f"✅ OK — {title[:40]}"
                else:
                    status = f"⚠️  Cargó pero sin título — {current_url[:60]}"

                results[domain] = status
                print(status)

            except Exception as e:
                err = str(e).split("\n")[0][:60]
                results[domain] = f"❌ Error: {err}"
                print(results[domain])
            finally:
                page.close()

        browser.close()

    # Resumen
    print(f"\n{'='*60}")
    print("RESUMEN:")
    print(f"{'='*60}")
    for domain, status in results.items():
        us_ok = "US-OK" if BOOKMAKERS[domain]["us_ok"] else "NO-US"
        print(f"  [{us_ok:>5}] {domain:>25}: {status}")

    print(f"\nNota: La red sale por Miami, US (proxy corporativo).")
    print("Las casas marcadas 'NO-US' podrían funcionar desde casa en CR.")


if __name__ == "__main__":
    test()
