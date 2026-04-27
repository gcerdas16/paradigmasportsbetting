"""
Diagnóstico de frescura de odds — Paso 0 del plan técnico.

Objetivo: Determinar qué mide `last_update` en The Odds API.
- ¿Es la hora en que el bookmaker cambió el precio?
- ¿O la hora en que la API hizo polling?

Test: Dos escaneos separados por N minutos. Si last_update avanza
pero el precio no cambió → es frecuencia de polling.
Si last_update solo avanza cuando el precio cambió → es cambio real.

Uso:
  python diagnostico_freshness.py scan1       # Primer escaneo (guarda JSON)
  python diagnostico_freshness.py scan2       # Segundo escaneo (compara)
  python diagnostico_freshness.py stats       # Mostrar distribución de frescura
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Agregar el directorio actual al path para importar módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from odds_client import OddsClient

DATA_DIR = Path(__file__).parent / "diagnostico_data"


def scan_and_save(filename: str):
    """Escanea un deporte con actividad y guarda el JSON raw."""
    DATA_DIR.mkdir(exist_ok=True)

    client = OddsClient()

    # Usar solo 1 deporte para minimizar consumo de API
    # Elegir uno con actividad probable
    sport = "soccer_epl"
    print(f"Escaneando {sport}...")

    events = client.get_odds(sport)
    if not events:
        print("No se obtuvieron eventos. Intentar con otro deporte.")
        return

    # Extraer la estructura relevante: bookmaker -> last_update + precios
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sport": sport,
        "remaining_requests": client.remaining_requests,
        "events": [],
    }

    for event in events:
        evt = {
            "id": event["id"],
            "home": event["home_team"],
            "away": event["away_team"],
            "commence_time": event["commence_time"],
            "bookmakers": [],
        }

        for bk in event.get("bookmakers", []):
            bk_data = {
                "key": bk["key"],
                "title": bk["title"],
                "last_update": bk.get("last_update", "NO_FIELD"),
                "markets": [],
            }

            for mkt in bk.get("markets", []):
                mkt_data = {
                    "key": mkt["key"],
                    "last_update": mkt.get("last_update", "NO_FIELD"),
                    "outcomes": [
                        {
                            "name": o["name"],
                            "price": o["price"],
                            "point": o.get("point"),
                        }
                        for o in mkt.get("outcomes", [])
                    ],
                }
                bk_data["markets"].append(mkt_data)

            evt["bookmakers"].append(bk_data)

        snapshot["events"].append(evt)

    filepath = DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    n_events = len(snapshot["events"])
    n_bookmakers = sum(len(e["bookmakers"]) for e in snapshot["events"])
    print(f"Guardado: {filepath}")
    print(f"  {n_events} eventos, {n_bookmakers} bookmaker-entries")
    print(f"  API requests restantes: {client.remaining_requests}")
    print(f"  Timestamp: {snapshot['timestamp']}")

    # Mostrar muestra de last_update
    print(f"\n--- Muestra de last_update (primeros 3 bookmakers del primer evento) ---")
    if snapshot["events"]:
        evt = snapshot["events"][0]
        print(f"Evento: {evt['home']} vs {evt['away']}")
        for bk in evt["bookmakers"][:3]:
            bk_lu = bk["last_update"]
            print(f"  {bk['title']:20s} | bookmaker last_update: {bk_lu}")
            for mkt in bk["markets"][:2]:
                mkt_lu = mkt["last_update"]
                prices = ", ".join(
                    f"{o['name']}: {o['price']}" for o in mkt["outcomes"]
                )
                print(f"    {mkt['key']:10s} | market last_update: {mkt_lu} | {prices}")


def compare_scans():
    """Compara scan1 vs scan2 para determinar qué mide last_update."""
    f1 = DATA_DIR / "scan1.json"
    f2 = DATA_DIR / "scan2.json"

    if not f1.exists() or not f2.exists():
        print("Necesitás ambos archivos: scan1.json y scan2.json")
        print("Corré primero: python diagnostico_freshness.py scan1")
        print("Esperá 20-30 min, luego: python diagnostico_freshness.py scan2")
        return

    with open(f1, "r") as f:
        s1 = json.load(f)
    with open(f2, "r") as f:
        s2 = json.load(f)

    print(f"Scan 1: {s1['timestamp']}")
    print(f"Scan 2: {s2['timestamp']}")
    print()

    # Indexar scan1 por (event_id, book_key, market_key)
    idx1 = {}
    for evt in s1["events"]:
        for bk in evt["bookmakers"]:
            for mkt in bk["markets"]:
                key = (evt["id"], bk["key"], mkt["key"])
                idx1[key] = {
                    "bk_last_update": bk["last_update"],
                    "mkt_last_update": mkt["last_update"],
                    "prices": {
                        (o["name"], o.get("point")): o["price"]
                        for o in mkt["outcomes"]
                    },
                }

    # Comparar con scan2
    total = 0
    lu_changed_price_changed = 0
    lu_changed_price_same = 0
    lu_same_price_same = 0
    lu_same_price_changed = 0
    only_in_scan2 = 0

    details = []

    for evt in s2["events"]:
        for bk in evt["bookmakers"]:
            for mkt in bk["markets"]:
                key = (evt["id"], bk["key"], mkt["key"])
                total += 1

                if key not in idx1:
                    only_in_scan2 += 1
                    continue

                old = idx1[key]
                new_mkt_lu = mkt.get("last_update", "NO_FIELD")
                old_mkt_lu = old["mkt_last_update"]
                new_bk_lu = bk.get("last_update", "NO_FIELD")
                old_bk_lu = old["bk_last_update"]

                new_prices = {
                    (o["name"], o.get("point")): o["price"]
                    for o in mkt["outcomes"]
                }
                old_prices = old["prices"]

                # Comparar al nivel de mercado (más granular)
                lu_to_compare_old = old_mkt_lu if old_mkt_lu != "NO_FIELD" else old_bk_lu
                lu_to_compare_new = new_mkt_lu if new_mkt_lu != "NO_FIELD" else new_bk_lu

                lu_changed = lu_to_compare_old != lu_to_compare_new
                price_changed = old_prices != new_prices

                if lu_changed and price_changed:
                    lu_changed_price_changed += 1
                elif lu_changed and not price_changed:
                    lu_changed_price_same += 1
                elif not lu_changed and not price_changed:
                    lu_same_price_same += 1
                else:  # lu same but price changed (shouldn't happen)
                    lu_same_price_changed += 1

                if lu_changed or price_changed:
                    details.append({
                        "event": f"{evt['home']} vs {evt['away']}",
                        "book": bk["title"],
                        "market": mkt["key"],
                        "lu_changed": lu_changed,
                        "price_changed": price_changed,
                        "old_lu": lu_to_compare_old,
                        "new_lu": lu_to_compare_new,
                    })

    print("=" * 60)
    print("RESULTADOS DE COMPARACIÓN")
    print("=" * 60)
    print(f"Total de (evento, bookmaker, mercado) en scan2: {total}")
    print(f"Solo en scan2 (nuevos): {only_in_scan2}")
    print()
    print(f"{'Categoría':45s} | Count | %")
    print("-" * 65)

    matched = total - only_in_scan2
    def pct(n):
        return f"{n/matched*100:.1f}%" if matched > 0 else "N/A"

    print(f"{'last_update CAMBIÓ + precio CAMBIÓ':45s} | {lu_changed_price_changed:5d} | {pct(lu_changed_price_changed)}")
    print(f"{'last_update CAMBIÓ + precio IGUAL':45s} | {lu_changed_price_same:5d} | {pct(lu_changed_price_same)}")
    print(f"{'last_update IGUAL + precio IGUAL':45s} | {lu_same_price_same:5d} | {pct(lu_same_price_same)}")
    print(f"{'last_update IGUAL + precio CAMBIÓ (anomalía)':45s} | {lu_same_price_changed:5d} | {pct(lu_same_price_changed)}")

    print()
    print("=" * 60)
    print("INTERPRETACIÓN:")
    print("=" * 60)

    if matched == 0:
        print("No hay datos suficientes para comparar.")
        return

    if lu_changed_price_same > lu_changed_price_changed:
        print("⚠️  last_update CAMBIA aunque el precio NO cambie.")
        print("   → Probablemente mide frecuencia de POLLING, no cambio de precio.")
        print("   → El TTL basado en last_update NO es confiable para filtrar odds viejas.")
        print("   → Necesitamos comparar PRECIOS directamente entre escaneos.")
    elif lu_changed_price_changed >= lu_changed_price_same:
        print("✅ last_update solo cambia (o casi solo) cuando el precio cambia.")
        print("   → Mide cambio real de odds.")
        print("   → El TTL basado en last_update ES confiable.")
    
    if lu_same_price_changed > 0:
        print(f"⚠️  {lu_same_price_changed} casos donde precio cambió pero last_update no.")
        print("   → Posible bug de la API o cacheo agresivo.")

    # Mostrar detalles de cambios
    if details:
        print()
        print(f"--- Detalle de cambios (primeros 10) ---")
        for d in details[:10]:
            lu_flag = "LU↑" if d["lu_changed"] else "LU="
            pr_flag = "$$↑" if d["price_changed"] else "$$="
            print(f"  {d['event'][:30]:30s} | {d['book']:15s} | {d['market']:8s} | {lu_flag} {pr_flag}")


def show_stats():
    """Muestra distribución de frescura de un escaneo."""
    # Buscar el último archivo disponible
    for name in ["scan2.json", "scan1.json"]:
        path = DATA_DIR / name
        if path.exists():
            break
    else:
        print("No hay escaneos guardados. Corré: python diagnostico_freshness.py scan1")
        return

    with open(path, "r") as f:
        snap = json.load(f)

    scan_time = datetime.fromisoformat(snap["timestamp"])
    print(f"Escaneo: {name} | Timestamp: {snap['timestamp']}")
    print(f"Deporte: {snap['sport']}")
    print()

    ages_minutes = []
    by_bookmaker = {}

    for evt in snap["events"]:
        for bk in evt["bookmakers"]:
            # Usar market-level last_update si existe, sino bookmaker-level
            for mkt in bk["markets"]:
                lu_str = mkt.get("last_update", bk.get("last_update"))
                if not lu_str or lu_str == "NO_FIELD":
                    continue

                try:
                    lu_time = datetime.fromisoformat(lu_str.replace("Z", "+00:00"))
                    age = (scan_time - lu_time).total_seconds() / 60.0
                    if age < 0:
                        age = 0  # Reloj desincronizado
                    ages_minutes.append(age)

                    bk_name = bk["title"]
                    if bk_name not in by_bookmaker:
                        by_bookmaker[bk_name] = []
                    by_bookmaker[bk_name].append(age)
                except Exception:
                    pass

    if not ages_minutes:
        print("No se encontraron timestamps de last_update.")
        return

    # Distribución global
    print("=" * 60)
    print("DISTRIBUCIÓN DE FRESCURA (minutos desde last_update)")
    print("=" * 60)

    buckets = [
        ("< 5 min", 0, 5),
        ("5-15 min", 5, 15),
        ("15-30 min", 15, 30),
        ("30-60 min", 30, 60),
        ("1-6 horas", 60, 360),
        ("6-24 horas", 360, 1440),
        ("> 24 horas", 1440, float("inf")),
    ]

    print(f"\n{'Rango':15s} | {'Count':6s} | {'%':6s} | Barra")
    print("-" * 55)
    for label, lo, hi in buckets:
        count = sum(1 for a in ages_minutes if lo <= a < hi)
        pct = count / len(ages_minutes) * 100
        bar = "█" * int(pct / 2)
        print(f"{label:15s} | {count:6d} | {pct:5.1f}% | {bar}")

    print(f"\nTotal: {len(ages_minutes)} entries")
    print(f"Mediana: {sorted(ages_minutes)[len(ages_minutes)//2]:.1f} min")
    print(f"Promedio: {sum(ages_minutes)/len(ages_minutes):.1f} min")

    # Por bookmaker (top 10 por cantidad)
    print()
    print("=" * 60)
    print("FRESCURA POR BOOKMAKER (mediana en minutos)")
    print("=" * 60)
    sorted_bks = sorted(by_bookmaker.items(), key=lambda x: -len(x[1]))
    print(f"\n{'Bookmaker':25s} | {'Mediana':8s} | {'Count':5s} | {'% < 30min':9s}")
    print("-" * 55)
    for bk_name, ages in sorted_bks[:20]:
        ages_sorted = sorted(ages)
        median = ages_sorted[len(ages_sorted) // 2]
        fresh = sum(1 for a in ages if a < 30) / len(ages) * 100
        print(f"{bk_name:25s} | {median:7.1f}m | {len(ages):5d} | {fresh:8.1f}%")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python diagnostico_freshness.py scan1   # Primer escaneo")
        print("  python diagnostico_freshness.py scan2   # Segundo escaneo (20-30 min después)")
        print("  python diagnostico_freshness.py stats   # Distribución de frescura")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "scan1":
        scan_and_save("scan1.json")
    elif cmd == "scan2":
        scan_and_save("scan2.json")
        print("\n" + "=" * 60)
        print("Ahora comparando ambos escaneos...")
        print("=" * 60 + "\n")
        compare_scans()
    elif cmd == "stats":
        show_stats()
    else:
        print(f"Comando desconocido: {cmd}")
        print("Opciones: scan1, scan2, stats")
