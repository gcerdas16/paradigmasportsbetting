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
| EV calc — totals | ❓ Diagnóstico pendiente (0 near misses) |
| EV calc — spreads | ❓ Diagnóstico pendiente (0 near misses) |

---

## Entradas

### 🔴 2026-04-27 11:52 — Diagnóstico totals/spreads + fix spread names

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
