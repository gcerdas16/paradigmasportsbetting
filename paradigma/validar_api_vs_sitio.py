"""
Validación API vs Sitio Real.

PROTOCOLO:
1. Antes de ejecutar este script, abrí las pestañas de:
   - onexbet (1xbet.com) → navegar a NHL o EPL
   - betsson.com → mismo deporte
   - betway.com → mismo deporte
2. Ejecutá: python validar_api_vs_sitio.py <deporte>
   Ejemplo: python validar_api_vs_sitio.py icehockey_nhl
3. En ≤20 segundos después de ver la salida, compará con el sitio.
4. Anotá: ✅ coincide, ≈ difiere ±1 tick, ❌ difiere mucho

Resultado esperado: >80% coincidencia para considerar la API usable.
"""

import sys
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.WARNING)

from odds_client import OddsClient
import config

sport = sys.argv[1] if len(sys.argv) > 1 else "icehockey_nhl"

# Bookmakers a verificar (los más relevantes)
VERIFY_BOOKS = ["onexbet", "betsson", "betway", "marathonbet", "unibet"]

client = OddsClient()

print(f"Escaneando {sport}...")
print(f"Timestamp: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")
print()

events = client.get_odds(sport, markets=["h2h"])

if not events:
    print("No hay eventos. Intentá con otro deporte.")
    sys.exit(1)

# Mostrar los primeros 5 eventos con formato para comparación rápida
shown = 0
for event in events[:8]:
    home = event["home_team"]
    away = event["away_team"]
    commence = event["commence_time"][:16]

    # Filtrar solo bookmakers que queremos verificar + pinnacle
    relevant = {}
    for bk in event.get("bookmakers", []):
        if bk["key"] in VERIFY_BOOKS or bk["key"] == "pinnacle":
            for mkt in bk.get("markets", []):
                if mkt["key"] == "h2h":
                    outcomes = {o["name"]: o["price"] for o in mkt["outcomes"]}
                    relevant[bk["key"]] = outcomes

    if len(relevant) < 2:
        continue

    shown += 1
    print(f"{'=' * 65}")
    print(f"  {home} vs {away}  ({commence})")
    print(f"{'=' * 65}")

    # Header
    outcome_names = list(list(relevant.values())[0].keys())
    header = f"  {'Bookmaker':20s}"
    for name in outcome_names:
        header += f" | {name:>15s}"
    print(header)
    print(f"  {'-' * 60}")

    # Pinnacle primero
    if "pinnacle" in relevant:
        row = f"  {'PINNACLE (ref)':20s}"
        for name in outcome_names:
            val = relevant['pinnacle'].get(name)
            row += f" | {val:>15.2f}" if val else " |             N/A"
        print(row)
        print(f"  {'-' * 60}")

    # Luego cada soft book
    for bk_key in VERIFY_BOOKS:
        if bk_key not in relevant:
            continue
        row = f"  {bk_key:20s}"
        for name in outcome_names:
            price = relevant[bk_key].get(name)
            if price is None:
                row += " |             N/A"
                continue
            # Marcar si la diferencia con Pinnacle es >10%
            pin_price = relevant.get("pinnacle", {}).get(name, price)
            if pin_price and pin_price > 0:
                diff_pct = abs(price - pin_price) / pin_price * 100
            else:
                diff_pct = 0
            marker = " ⚠️" if diff_pct > 10 else ""
            row += f" | {price:>12.2f}{marker}"
        print(row)

    print()

    if shown >= 5:
        break

print(f"Timestamp fin: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")
print(f"API remaining: {client.remaining_requests}")
print()
print("INSTRUCCIONES: Compará cada fila con el sitio real AHORA (≤20 seg)")
print("Anotá: ✅ coincide | ≈ ±1 tick | ❌ diferente")
