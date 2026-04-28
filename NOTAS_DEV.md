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

### 🔴 2026-04-27 18:05 — Fix parser DoradoBet (relaciones por ID)

**Qué cambió:**
1. **doradobet_scraper.py** — Fix completo del parser. Ahora usa las relaciones correctas:
   - `event.marketIds` → busca markets por `market.id`
   - `market.oddIds` → busca odds por `odd.id`
   - Nombre del evento viene como `"Home vs. Away"` (se splitea)
   - Odds h2h: nombre del equipo o "1"/"X"/"2"

**Comandos:**

Probar DoradoBet sola:
```bash
cd paradigma
python -m scraping.doradobet_scraper
```

Si funciona, probar las 3 juntas:
```bash
python -m scraping.scanner_v2 --books 1xbet,melbet,doradobet
```

**Qué buscar:**
- ¿Ahora parsea los 20 eventos?
- ¿Detecta h2h, totals, spreads?
- Si falla, pegar el output completo

---

### ✅ 2026-04-27 17:25 — Scraper DoradoBet (Altenar) + test MelBet

**Qué cambió:**
1. **Nuevo: `scraping/doradobet_scraper.py`** — Scraper para DoradoBet usando la API de Altenar. Intercepta `GetUpcoming` y parsea eventos/odds.
2. **scanner_v2.py** — Ahora soporta `doradobet` como casa adicional.
3. Casas disponibles: `1xbet`, `melbet`, `20bet`, `doradobet`

**Comandos (uno a la vez):**

Primero probar DoradoBet sola (para ver si parsea bien):
```bash
cd paradigma
python -m scraping.doradobet_scraper
```

Luego MelBet sola en el scanner:
```bash
python -m scraping.scanner_v2 --books melbet
```

Si ambas funcionan, probar 1xBet + MelBet + DoradoBet juntas:
```bash
python -m scraping.scanner_v2 --books 1xbet,melbet,doradobet
```

**Qué buscar:**
- DoradoBet: ¿Detecta eventos? ¿Parsea las odds correctamente?
- MelBet: ¿El scanner la detecta y empareja con Pinnacle?
- Si DoradoBet falla, el debug JSON se guarda en `scraping_debug/doradobet_raw_*.json`

**Pegar en RESULTADOS_TEST.md:** Output de cada comando.

---

### ✅ 2026-04-27 14:00 — API Sniffer para bet365 y DoradoBet

**Qué cambió:**
1. **Nuevo: `scraping/api_sniffer.py`** — Script que abre cualquier bookmaker en Playwright, captura TODO el tráfico de API, y lo guarda en JSON para análisis.

**Comandos (ejecutar uno a la vez, NO headless para que se vea el browser):**

```bash
cd paradigmasportsbetting
git pull
cd paradigma

# bet365 — abre el browser visible
python -m scraping.api_sniffer bet365

# DoradoBet
python -m scraping.api_sniffer doradobet

# MelBet (si no funcionó antes)
python -m scraping.api_sniffer melbet

# 20Bet
python -m scraping.api_sniffer 20bet
```

**⚠️ IMPORTANTE:**
- El browser se abre VISIBLE (no headless) para que puedas ver si carga bien
- bet365 puede pedir captcha o redirigir — eso es OK, el sniffer captura lo que pueda
- DoradoBet: si la URL no carga, buscar la URL correcta de fútbol en el sitio
- El script captura ~30 segundos de tráfico por página

**Output:**
Los archivos se guardan en `scraping_debug/api_sniff/`:
- `bet365_api_*.json` — todos los requests interceptados
- `bet365_screenshot_*.png` — screenshot de la página
- `bet365_page_*.html` — HTML de la página

**Qué pegar en RESULTADOS_TEST.md:**
Para cada sitio, pegar:
1. El bloque "RESUMEN" del output (dominios, top endpoints JSON)
2. Si hubo captcha o redirect
3. Si la sección de fútbol cargó correctamente
4. El nombre del archivo JSON generado (para que yo lo analice después)

---

### ✅ 2026-04-27 13:35 — Multi-book: 1xBet + MelBet + 20Bet + sanity checks

**Qué cambió:**
1. **onexbet_scraper.py**: Ahora soporta 3 casas: `1xbet`, `melbet`, `20bet` (mismo backend BetB2B). Solo se cambia `book_key` en el constructor.
2. **scanner_v2.py**: Soporta múltiples soft books. Argumento `--books 1xbet,melbet,20bet` para scrapear las 3.
3. **ev_calculator.py**: Sanity check — descarta comparaciones con odds ratio >3x (protege contra datos erróneos).
4. **verify_odds.py**: Fix spreads — ahora compara por clave exacta (team, signed_point), no por abs().

**Comandos:**

Solo 1xBet (como antes):
```bash
cd paradigma
python -m scraping.scanner_v2
```

Las 3 casas (NUEVO):
```bash
cd paradigma
python -m scraping.scanner_v2 --books 1xbet,melbet,20bet
```

Probar MelBet sola:
```bash
cd paradigma
python -m scraping.scanner_v2 --books melbet
```

**⚠️ IMPORTANTE:** MelBet y 20Bet podrían no funcionar si:
- Tienen URLs diferentes (no usan `/en/line/football`)
- La API usa un dominio diferente
- Requieren cookies o geolocalización especial

**Qué buscar:**
1. ¿MelBet devuelve eventos? ¿Cuántos?
2. ¿20Bet devuelve eventos?
3. ¿Los emparejamientos con Pinnacle funcionan?
4. ¿Aparecen más value bets / near misses con más casas?

**Pegar en RESULTADOS_TEST.md:**
- Output de cada casa por separado + output combinado
- Si alguna casa falla, el error exacto

---

### ✅ 2026-04-27 12:26 — Script de verificación con links directos

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
