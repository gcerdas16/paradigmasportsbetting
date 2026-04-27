# Resultados de Tests — PC Personal

> Este archivo lo escribe **SOLO la PC personal** (donde corren los scrapers).
> La PC corporativa lo lee pero **NUNCA lo edita**.
> Formato: cada entrada es un bloque con timestamp, comando, y output.

---

## Cómo usar

1. Hacer `git pull` para obtener los últimos cambios de código
2. Correr el comando indicado en `NOTAS_DEV.md`
3. Pegar el resultado aquí abajo siguiendo el formato
4. Hacer `git add RESULTADOS_TEST.md && git commit -m "test: [descripción corta]" && git push`
5. Avisar al otro lado que ya está listo

---

## Formato de cada entrada

```
### [YYYY-MM-DD HH:MM] — [Descripción corta]

**Comando:** `[comando exacto que se corrió]`
**Duración:** [tiempo aprox]
**Exit code:** [0 o error]

**Output:**
[pegar output relevante aquí, no TODO el log — solo las secciones importantes]

**Observaciones:** [notas del usuario si las hay]
```

---

## Entradas

### 2026-04-27 11:59 — Diagnóstico totals/spreads + fix spread names

**Comando:** `cd paradigma && python -m scraping.scanner_v2`
**Duración:** ~4 min
**Exit code:** 0

**Output — sección clave (Por mercado):**
```
Por mercado (1xBet → matched en Pinnacle):
  h2h:     264 odds, 194 matched   ✅
  spreads: 698 odds,  14 matched   ⚠️ MUY BAJO
  totals:  872 odds,  86 matched   ⚠️ BAJO
```

**Value bets:** 0 (ninguna supera EV 5%)

**Near misses (EV 1-5%):** 8 — todos h2h, ninguno en totals/spreads
```
[h2h] Leeds United vs Burnley        | Burnley @ 7.700  (Pin: 6.83) | EV: +4.41%
[h2h] Union Berlin vs FC Koln        | Draw @ 3.595     (Pin: 3.36) | EV: +3.03%
[h2h] Brentford vs West Ham United   | West Ham @ 3.775 (Pin: 3.53) | EV: +2.74%
[h2h] Lecce vs Juventus              | Juventus @ 1.628 (Pin: 1.54) | EV: +2.14%
[h2h] Lazio vs Udinese               | Lazio @ 2.317    (Pin: 2.22) | EV: +1.95%
[h2h] Arsenal vs Fulham              | Arsenal @ 1.495  (Pin: 1.44) | EV: +1.40%
[h2h] Hellas Verona vs Como          | Como @ 1.514     (Pin: 1.44) | EV: +1.35%
[h2h] Real Betis vs Real Oviedo      | Real Betis @ 1.656(Pin: 1.60)| EV: +1.30%
Por mercado: {'h2h': 8}
```

**Diagnóstico:**
- `spreads: 14 matched de 698` → solo ~2% de líneas casan. El punto de handicap de 1xBet y Pinnacle difieren en formato o valor.
- `totals: 86 matched de 872` → ~10%. Algunos pares Over/Under casan, pero la mayoría no.
- `h2h: 194 matched de 264` → ~73%. Funciona bien.
- El near-miss de totals/spreads = 0 confirma: o no están casando o el devig por línea no produce resultados válidos.

**Observaciones:** Prioridad: investigar por qué spreads solo matchea 14/698. Probablemente los puntos de handicap tienen formato diferente (ej: Pinnacle usa `1.25` y 1xBet usa `1.0`/`1.5` separados).

---

### 2026-04-27 11:49 — Scanner v2 con near-misses

**Comando:** `cd paradigma && python -m scraping.scanner_v2`
**Duración:** ~5 min
**Exit code:** 0

**Output:**
```
Pinnacle: 115 eventos con odds
1xBet: 155 eventos con odds
Con odds: 115 Pinnacle, 155 1xBet
Excluidos por mercado especial (Bookings/Corners): 11
Emparejados: 94 partidos
Pinnacle: 94 eventos | 1xBet: 1,834 odds individuales

VALUE BETS: 0
NEAR MISSES (EV 1-5%): 7 (todos h2h)
- Leeds vs Burnley | Burnley @ 7.700 (Pin: 6.78) | EV: +4.41%
- y 6 más en h2h

Totals/spreads: 0 near misses (no están pasando al EV calc)
Market mismatch: desapareció después del fix
```

**Observaciones:** Totals y spreads no generan resultados. El h2h funciona bien. Leeds/Burnley bajó de 5.28% a 4.41% (odds se movieron).

---

### 2026-04-27 10:01 — Scanner v2 post-fix matching limpio

**Comando:** `cd paradigma && python -m scraping.scanner_v2`
**Duración:** ~5 min
**Exit code:** 0

**Output:**
```
Excluidos por mercado especial (Bookings/Corners): 11
Man City vs Brentford correctamente emparejado
0 warnings de EV falso
Value bet: Leeds/Burnley | Burnley @ 7.700 | EV: +5.28%
```

**Observaciones:** Todos los fixes aplicaron correctamente.

---

### 2026-04-27 09:43 — Scanner v2 con fix de odds-only matching

**Comando:** `cd paradigma && python -m scraping.scanner_v2`
**Duración:** ~5 min
**Exit code:** 0

**Output:**
```
Con odds: 115 Pinnacle, 155 1xBet
Emparejados: 94 reales
Eventos al EV calc: 94 (antes: 2)
Odds analizadas: 1,978
Value bets: 3
  #1 Man Utd vs Brentford | Brentford @ 8.400 | EV: +113% ⚠️
  #2 Man Utd vs Brentford | Draw @ 6.150 | EV: +55.5% ⚠️
  #3 Leeds vs Burnley | Burnley @ 7.700 | EV: +5.28% ✅
```

**Observaciones:** #1 y #2 son falsos positivos por mismatch Bookings/Corners y Man Utd≠Man City.

---

### 2026-04-27 09:35 — Scanner v2 primera ejecución exitosa

**Comando:** `cd paradigma && python -m scraping.scanner_v2`
**Duración:** ~5 min
**Exit code:** 0

**Output:**
```
Pinnacle: 115 eventos con odds
1xBet: 156 eventos con odds
Emparejados: 156 (inflado — incluía eventos sin odds)
Pinnacle al EV calc: solo 2 (bug)
Odds analizadas: 3,286
Value bets: 1 — Leeds vs Burnley | Burnley @ 7.700 | EV: +5.28%
```

**Observaciones:** Bug — matcher recibía todos los matchups, no solo los con odds. Solo 2/115 Pinnacle llegaban al EV calc.
