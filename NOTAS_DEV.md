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
| MelBet scraper | ✅ Mismo engine que 1xBet |
| 20Bet scraper | ✅ Mismo engine que 1xBet |
| 888sport scraper (Spectate) | 🔴 REESCRITO — Por testear v2 |
| BetSafe scraper (Betsson API) | 🔴 REESCRITO — Por testear v2 |
| Bet365 | ❌ DESCARTADO — protocolo binario OCP, no viable |
| Unibet | ❌ Sin scraper aún (Kambi CDN bloqueado) |
| Event matcher | ✅ Limpio (94 emparejados, Bookings excluidos) |
| EV calc — h2h | ✅ Funcionando (7 near misses detectados) |
| EV calc — totals | ✅ Funcionando (1 near miss, 750 matched) |
| EV calc — spreads | ✅ Funcionando (8 near misses, 356 matched) |

---

## Entradas

### 🔴 2026-04-27 23:35 — FIX v6: BetSafe filtrar links de partidos + wait_for_response events-table

**Basado en test 23:25:** 12 eventos con La Liga completa ✅. Pero link discovery captura partidos individuales y EPL/Serie A/Ligue 1 no disparan events-table.

**Fixes:**
1. **Filtro de links** — Solo acepta links con 1 segmento tras `/futbol/` (ligas). Links con 2+ segmentos (partidos individuales como `paris-sg-bayern-de-munich`) se descartan.
2. **wait_for_response** — Después de navegar a cada liga, espera explícitamente a que `events-table` responda (hasta 10s). Esto evita race conditions donde `networkidle` termina antes de que la API responda.

**INSTRUCCIONES PARA TESTEAR:**

```bash
git pull
cd paradigma
python -m scraping.kambi_scraper --book betsafe --no-headless
```

**Qué buscar:**
1. `"Encontradas N ligas en el menú"` — N debería ser menor que v5 (sin partidos individuales)
2. `"events-table interceptado para xxx"` — ¿Aparece para EPL, Serie A, Ligue 1?
3. `"BetSafe — Eventos con odds: N"` — ¿N > 12? (La Liga + EPL + más ligas)
4. Si EPL/Serie A siguen sin events-table → pegar el log completo

---

### ✅ 2026-04-27 23:25 — FIX v5: BetSafe navegación dinámica de ligas + selection matching robusto

**Basado en test 23:10:** BetSafe pasó de 0→2 eventos, pero solo captura 1 selección de 3, y 0 ligas europeas.

**Qué se corrigió:**

1. **Navegación dinámica** — Ya NO usa URLs hardcodeadas (slugs eran incorrectos). Ahora busca links `<a href>` en la página con keywords (`champions`, `premier`, `la liga`, etc.) y navega a cada uno.
2. **Selection matching robusto** — Ahora matchea selections por `marketId`, por `id` que contenga el market ID, y por dict keys (en caso de que `events-table/v2` use dict en vez de lista).
3. **Logging diagnóstico** — Imprime `✓ Home vs Away: {markets}` por cada evento parseado.

**INSTRUCCIONES PARA TESTEAR:**

```bash
git pull
cd paradigma
python -m scraping.kambi_scraper --book betsafe --no-headless
```

**Qué buscar en el output:**
1. `"Encontradas N ligas en el menú"` — ¿N > 0? Si es 0, los links de liga no se encuentran con los keywords actuales
2. `"Navegando a liga: xxx"` — ¿Navega a UCL, EPL, La Liga, etc.?
3. `"✓ Home vs Away: {h2h: ...}"` — ¿Aparecen eventos con 3 selecciones (home, Draw, away)?
4. `"BetSafe — Eventos con odds: N"` — ¿N > 2?

**Si N ligas = 0:** Pegar en RESULTADOS_TEST.md la lista de links `<a>` visibles en la página de fútbol de BetSafe. Podés inspeccionarlo con DevTools → `document.querySelectorAll('a[href*="/futbol/"]')`.

**Si eventos > 2 pero solo 1 selección por evento:** Revisar en el debug JSON (`scraping_debug/betsafe_*.json`) un evento MW3W y pegar la estructura de `selections` para ese market. Necesito ver el field name exacto que vincula selection→market.

**Si todo funciona:** Correr el scanner completo:
```bash
python -m scraping.scanner_v2 --books 1xbet,888sport,betsafe
```

---

### ✅ 2026-04-27 22:50 — FIX v3: 888sport EU leagues + BetSafe MW3W explicit fetch

**Basado en test 22:10:** 888sport OK (11 eventos) pero solo ligas regionales. BetSafe 0 eventos — MW3W nunca se carga.

**Fixes:**

**888sport:**
- Agregadas 7 URLs de ligas europeas (UCL, UEL, EPL, La Liga, etc.)
- Antes: solo 11 eventos de Indonesia/Bangladesh
- Esperado: 30-50+ eventos con overlap a Pinnacle

**BetSafe (3 fixes):**
1. URL filter ahora incluye `popular-bets` (antes solo `event-market`/`view`)
2. Template `MW3W` agregado como 1X2 (antes solo `MHDA` que no existe)
3. **NUEVO: fetch explícito de MW3W** — después de navegar ligas, recopila eventIds con MW3W y hace `page.evaluate(fetch(...))` para obtener las odds 1X2

**Test:**
```bash
git pull
cd paradigma
python -m scraping.kambi_scraper --book 888sport --no-headless
python -m scraping.kambi_scraper --book betsafe --no-headless
```

**Qué buscar:**
- 888sport: ¿más eventos de ligas europeas?
- BetSafe: "Fetching N mercados MW3W explícitamente..." → "MW3W batch 1: OK" → eventos con h2h?
- Si MW3W fetch falla → pegar error

---

### ✅ 2026-04-27 22:05 — FIX PARSERS: 888sport (decimal_price) + BetSafe (label, lists, league URLs)

**Basado en los resultados de test de las 22:00.** Ambos scrapers conectan y capturan datos pero parsean 0 eventos.

**Fixes aplicados a `kambi_scraper.py`:**

**888sport:**
1. `decimal_price` no reconocido → ahora busca `decimal_price` además de `odds`/`price`
2. No profundizaba en `market["selections"]` → ahora itera `selections.values()`
3. `type` = "1"/"X"/"2" → se usa para clasificar 1X2 cuando label no matchea

**BetSafe:**
1. `participants[i]["label"]` no `"name"` → corregido
2. `markets` y `marketSelections` son **listas** (no dicts) → matcheo por `eventId`/`marketId`
3. Clasificación por `marketTemplateId`: `MHDA`=1X2, `MWOU`=O/U, `AGSNAB`=Handicap
4. Agregadas 7 URLs de ligas individuales (UCL, EPL, La Liga, etc.) para capturar 1X2

**Comandos de test (mismos que antes):**
```bash
git pull
cd paradigma
python -m scraping.kambi_scraper --book 888sport --no-headless
python -m scraping.kambi_scraper --book betsafe --no-headless
```

**Qué buscar esta vez:**
- 888sport: ¿parsea los 5 eventos con `decimal_price`? (esperado: ~5 eventos con h2h)
- BetSafe: ¿encuentra participantes con `label`? ¿las ligas capturan 1X2 (MHDA)?
- Si 0 eventos de nuevo → pegar el debug JSON y yo itero

---

### ✅ 2026-04-27 21:45 — (v1) REESCRITO: 888sport (Spectate) + BetSafe (Betsson API) — Playwright

**Contexto:** Los tests de la v1 revelaron:
- `eu-offering.kambicdn.org` está completamente bloqueado (timeout)
- 888sport migró de Kambi a plataforma "Spectate" propia
- BetSafe usa su propia API proxy de Betsson, no el CDN público de Kambi
- Bet365 usa protocolo binario OCP — no es scrappeable sin ingeniería inversa

**Qué cambió:**
1. **`scraping/kambi_scraper.py` REESCRITO COMPLETO** — Ya NO usa HTTP a Kambi CDN
   - **888sport**: Intercepta API Spectate (`spectate-web.888sport.es`)
   - **BetSafe**: Intercepta API Betsson (`www.betsafe.com/api/sb/v1/`)
   - Ambos usan Playwright (igual que 1xBet/Pinnacle)
2. **`scanner_v2.py`** actualizado — usa factory `create_scraper()`
3. **Bet365 DESCARTADO** — protocolo binario, no viable
4. **Unibet sin scraper** — Kambi CDN bloqueado, no sabemos su API real

**Casas disponibles:** `1xbet`, `melbet`, `20bet`, `888sport`, `betsafe`

**Comandos de test (con browser VISIBLE recomendado para primer test):**

```bash
cd paradigma

# 888sport sola (Spectate)
python -m scraping.kambi_scraper --book 888sport --no-headless

# BetSafe sola (Betsson API)
python -m scraping.kambi_scraper --book betsafe --no-headless

# Scanner combinado (si funcionan):
python -m scraping.scanner_v2 --books 1xbet,888sport,betsafe

# ALL-IN (5 casas):
python -m scraping.scanner_v2 --books 1xbet,melbet,20bet,888sport,betsafe
```

**Qué buscar:**
1. ¿Captura respuestas JSON de `spectate-web.888sport.es`?
2. ¿Captura respuestas JSON de `www.betsafe.com/api/sb/v1/`?
3. ¿Parsea eventos con nombres de equipo?
4. Revisar archivos debug en `scraping_debug/` para analizar estructura real
5. Si 0 eventos → pegar el debug JSON para que yo ajuste el parser

**Pegar en RESULTADOS_TEST.md:** Output de cada scraper + archivos debug relevantes.

---

### ✅ 2026-04-27 21:20 — (v1 OBSOLETA) 4 scrapers nuevos: Kambi (888sport, Unibet, BetSafe) + Bet365

**Qué cambió:**
1. **Nuevo: `scraping/kambi_scraper.py`** — Scraper para casas Kambi via API REST pública
   - **NO usa Playwright** — solo HTTP requests a `eu-offering.kambicdn.org`
   - 3 casas: `888sport` (op "888"), `unibet` (op "ub"), `betsafe` (op "betsafe")
   - BetSafe = grupo Betsson (cubre nuestra casa prioritaria)
   - Mercados: h2h (1X2), totals (O/U), spreads (handicap)
   - Autodescubre ligas desde `group.json`
   - ~2 segundos vs ~2 minutos de los scrapers Playwright
2. **Nuevo: `scraping/bet365_scraper.py`** — Scraper para Bet365 via Playwright
   - Intercepta API interna (JSON moderno + pipe-delimited legacy)
   - Incluye decodificador XOR para formato legacy
   - Intenta múltiples URLs/TLDs (bet365.com, bet365.cr)
   - ⚠️ Puede requerir interacción manual (captcha, geoblock)
3. **scanner_v2.py** — Todas las casas nuevas integradas
4. **DoradoBet eliminado** del pipeline (pocas ligas, no vale la pena)

**Casas disponibles ahora:** `1xbet`, `melbet`, `20bet`, `888sport`, `unibet`, `betsafe`, `bet365`

**Comandos de test — PARTE 1: Kambi (rápido, sin Playwright):**

```bash
cd paradigma

# Probar cada casa Kambi individualmente
python -m scraping.kambi_scraper --book 888sport
python -m scraping.kambi_scraper --book unibet
python -m scraping.kambi_scraper --book betsafe
```

**Comandos de test — PARTE 2: Bet365 (Playwright):**

```bash
# Con browser VISIBLE (recomendado para primer test — puede pedir captcha)
python -m scraping.bet365_scraper --no-headless

# Si funciona sin captcha, probar headless:
python -m scraping.bet365_scraper
```

**Comandos de test — PARTE 3: Scanner combinado:**

```bash
# Solo Kambi (rápido, ~5 seg):
python -m scraping.scanner_v2 --books 888sport,unibet,betsafe

# 1xBet + Kambi (lo más probable que funcione):
python -m scraping.scanner_v2 --books 1xbet,888sport,unibet,betsafe

# ALL-IN (7 casas):
python -m scraping.scanner_v2 --books 1xbet,melbet,20bet,888sport,unibet,betsafe,bet365
```

**Qué buscar:**
1. **Kambi:** ¿Descubre competiciones? ¿Cuántos eventos? Si HTTP 403 → reportar
2. **Bet365:** ¿Carga la página? ¿Captura JSON o pipe? Si captcha → reportar screenshot
3. **BetSafe:** ¿Funciona como Betsson? (es del mismo grupo)
4. **Scanner:** ¿Más value bets con 7 casas vs 3?
5. **888sport:** Podría haber migrado fuera de Kambi → si falla, normal

**⚠️ NOTA:** Kambi NO requiere Playwright, debería funcionar desde cualquier PC.
Bet365 SÍ requiere Playwright y acceso al sitio.

**Pegar en RESULTADOS_TEST.md:** Output de cada scraper individual + output del scanner combinado.

---

### ✅ 2026-04-27 18:35 — Buscar URLs de ligas europeas en DoradoBet (DESCARTADO)

**NO es código, es manual en el navegador.**

1. Abrir `https://doradobet.com` en Chrome
2. Ir a la sección de fútbol
3. Buscar cada liga y copiar la URL del address bar:

| Liga | Buscar como... | URL |
|---|---|---|
| England Premier League | Premier League, EPL, England | |
| Spain La Liga | La Liga, España | |
| Germany Bundesliga | Bundesliga, Alemania | |
| Italy Serie A | Serie A, Italia | |
| France Ligue 1 | Ligue 1, Francia | |
| UEFA Champions League | Champions League, UCL | |
| UEFA Europa League | Europa League, UEL | |

4. Pegar las 7 URLs en `RESULTADOS_TEST.md` y push

**Ejemplo de lo que necesito:**
```
Premier League → https://doradobet.com/deportes/66/123
La Liga → https://doradobet.com/deportes/66/456
...etc
```

---

### ✅ 2026-04-27 18:05 — Fix parser DoradoBet (relaciones por ID)

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
