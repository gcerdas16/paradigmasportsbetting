# Notas de Desarrollo — PC Corporativa

> Este archivo lo escribe **SOLO la PC corporativa** (Cascade/Windsurf IDE).
> La PC personal lo lee pero **NUNCA lo edita**.
> Contiene: qué cambió, qué correr, qué buscar en el output.

---

## Cómo usar

1. Hacer `git pull` para obtener los últimos cambios de código
2. Leer la entrada más reciente de abajo (marcada con 🔴 PENDIENTE)
3. Correr el comando indicado
4. Pegar el resultado en `RESULTADOS_TEST.md`
5. Hacer `git push`
6. Avisar al otro lado que ya está listo

---

## Estado actual del pipeline

| Componente | Estado |
|---|---|
| Pinnacle scraper | ✅ Funcionando (115 eventos) |
| 1xBet scraper | ✅ Funcionando (155 eventos) |
| Event matcher | ✅ Limpio (94 emparejados, Bookings excluidos) |
| EV calc — h2h | ✅ Funcionando (7 near misses detectados) |
| EV calc — totals | ✅ Funcionando (1 near miss, 750 matched) |
| EV calc — spreads | ✅ Funcionando (8 near misses, 356 matched) |

---

## Entradas

### 🔴 2026-04-27 12:26 — Script de verificación con links directos

**Qué cambió:**
1. **Nuevo: `scraping/verify_odds.py`** — Script que scrapea ambos sitios y muestra links directos + odds lado a lado
2. **onexbet_scraper.py**: Ahora guarda `league_id` para construir links de 1xBet

**Comando:**
```bash
cd paradigmasportsbetting
git pull
cd paradigma
python -m scraping.verify_odds
```

**Qué muestra:**
Para cada partido emparejado:
- 🟢 Link directo a Pinnacle (abrir en navegador)
- 🔵 Link directo a 1xBet (abrir en navegador)
- Tabla con odds h2h (Home/Draw/Away) de ambos
- Totals y spreads de la línea principal
- Verificar que las odds del output ≈ las del sitio real (±0.01)

**Pegar en RESULTADOS_TEST.md:**
- Los primeros 5 partidos con sus links y odds
- Si las odds coinciden con lo que muestra el sitio real
- Si algún link no funciona

---

### ✅ 2026-04-27 12:13 — FIX: Pinnacle ahora incluye TODAS las líneas

**Qué cambió:**
1. **pinnacle_scraper.py**: Removido filtro `isAlternate` para totals y spreads. Ahora captura TODAS las líneas (2.5, 2.75, 3.0, 3.25, 3.5...) en vez de solo la main line
2. **pinnacle_scraper.py**: Forzado `pts = float(pts)` para garantizar coincidencia de tipos con 1xBet

**Causa del bug:** Pinnacle solo guardaba 1 línea (ej: Over 3.25). 1xBet tiene muchas líneas (Over 2.5, 3.0, 3.5). Como 3.25 no existe en 1xBet, nunca matcheaban. Ahora Pinnacle tendrá también 2.5, 3.0, 3.5 → match rate debería subir de 10% a 60%+.

**Comando:**
```bash
cd paradigmasportsbetting
git pull
cd paradigma
python -m scraping.scanner_v2
```

**Qué buscar en el output:**
1. `totals: X odds, Y matched` — esperamos Y >> 88 (antes)
2. `spreads: X odds, Y matched` — esperamos Y >> 12 (antes)
3. Near misses en totals/spreads (antes era 0)
4. ¿Más value bets?

**Pegar en RESULTADOS_TEST.md:** sección "Por mercado", value bets, near misses, y cualquier MISMATCH si aún aparecen.

---

### ✅ 2026-04-27 12:01 — Diagnóstico profundo: por qué totals/spreads no matchean

**Qué cambió:**
1. **scanner_v2.py**: Nuevo log detallado que muestra las keys EXACTAS que no matchean, con tipos de datos. Ejemplo esperado:
```
🔍 totals MISMATCH [Arsenal vs Fulham]:
    1xBet key:    ('Over', 2.5)  (type: str, float)
    Pinnacle keys: [('Over', 2.5), ('Under', 2.5)]
    Pinnacle types: [('str', 'float'), ('str', 'float')]
```

**Comando:**
```bash
cd paradigmasportsbetting
git pull
cd paradigma
python -m scraping.scanner_v2
```

**Qué buscar en el output:**
- Buscar líneas con `🔍 totals MISMATCH` y `🔍 spreads MISMATCH`
- Mostrarán: la key de 1xBet vs las keys de Pinnacle + tipos de datos
- Esto revela si el problema es: tipos (int vs float), nombres ("Over" vs "over"), o puntos diferentes

**Pegar en RESULTADOS_TEST.md:**
- Las líneas de MISMATCH (máximo 3 por mercado)
- Lo demás del output normal

---

### ✅ 2026-04-27 11:52 — Diagnóstico totals/spreads + fix spread names

**Qué cambió:**
1. **ev_calculator.py**: El filtro 2-way vs 3-way ahora solo aplica para h2h (antes bloqueaba totals/spreads)
2. **ev_calculator.py**: Devig para totals/spreads se hace por LÍNEA (par Over/Under) en vez de todo el mercado junto
3. **scanner_v2.py**: Los nombres de equipo de 1xBet se traducen a nombres de Pinnacle para spreads (ej: "Man Utd" → "Manchester United")
4. **scanner_v2.py**: Nuevo log diagnóstico muestra cuántas odds por mercado matchean entre 1xBet y Pinnacle

**Comando:**
```bash
cd paradigmasportsbetting
git pull
cd paradigma
python -m scraping.scanner_v2
```

**Qué buscar en el output:**
```
Por mercado (1xBet → matched en Pinnacle):
  h2h: X odds, Y matched      ← debería ser ~250+
  totals: X odds, Y matched   ← CLAVE: ¿cuántos matched?
  spreads: X odds, Y matched  ← CLAVE: ¿cuántos matched?
```

**Pegar en RESULTADOS_TEST.md:**
1. La sección "Por mercado" completa
2. Las value bets encontradas (si hay)
3. Los near misses — especialmente si hay alguno en totals o spreads
4. Si `totals matched = 0`: pegar un ejemplo de las keys de Pinnacle y 1xBet para un mismo partido (ver si los puntos difieren)

---

### ✅ 2026-04-27 11:38 — Near-misses diagnóstico

**Qué cambió:** Scanner ahora muestra near-misses (EV 1-5%) para confirmar que el calculador funciona.

**Resultado:** 7 near-misses, todos h2h. Totals/spreads = 0. Confirma que el calculador h2h funciona y que totals/spreads necesitan fix.

---

### ✅ 2026-04-27 10:01 — Fix matching Bookings + Man Utd ≠ Man City

**Qué cambió:** Excluir mercados especiales, require ALL words match.

**Resultado:** 11 excluidos por Bookings, matching limpio, 0 EV falsos.

---

### ✅ 2026-04-27 09:43 — Fix odds-only matching

**Qué cambió:** Solo pasar eventos con odds al matcher.

**Resultado:** 94 emparejados reales (antes: 156 falsos), 94 al EV calc (antes: 2).

---

### ✅ 2026-04-27 09:35 — Primera ejecución scanner_v2

**Qué cambió:** Pipeline completo creado.

**Resultado:** Funciona end-to-end. 1 value bet legítima + 2 falsos positivos.
