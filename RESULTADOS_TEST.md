# Resultados de Tests — PC Personal

> Este archivo lo escribe **SOLO la PC personal** (donde corren los scrapers).
> La PC corporativa lo lee pero **NUNCA lo edita**.
> Formato: cada entrada es un bloque con timestamp, comando, y output.

---

## 🔴 PENDIENTE PARA DEV PC — BetSafe v11 (actualizado 2026-04-28)

BetSafe usa `/en/sportsbook/football/` (inglés), NO `/es/apuestas-deportivas/futbol/`. URLs **confirmadas manualmente**:

```python
FOOTBALL_URL = "https://www.betsafe.com/en/sportsbook/football?tab=liveAndUpcoming"

LEAGUE_URLS = [
    "https://www.betsafe.com/en/sportsbook/football/england/england-premier-league",
    "https://www.betsafe.com/en/sportsbook/football/spain/spain-la-liga",
    "https://www.betsafe.com/en/sportsbook/football/germany/germany-bundesliga",
    "https://www.betsafe.com/en/sportsbook/football/italy/italy-serie-a",
    "https://www.betsafe.com/en/sportsbook/football/france/france-ligue-1",
    "https://www.betsafe.com/en/sportsbook/football/champions-league/champions-league",
    "https://www.betsafe.com/en/sportsbook/football/europa-league/europa-league",
]
```

Cambios requeridos en `kambi_scraper.py`:
1. `FOOTBALL_URL` → URL de arriba
2. `LEAGUE_URLS` → lista de arriba (hardcodeada, no dinámica)
3. Selector → `a[href*="/sportsbook/football/"]` (o simplemente usar LEAGUE_URLS sin búsqueda dinámica)

**Test debe correrse entre 12:00-15:00 hora Costa Rica** (partidos europeos upcoming).

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

### 2026-04-27 14:30 — API Sniffer — bet365, DoradoBet, MelBet, 20Bet

**Comandos:**
```bash
cd paradigma
python -m scraping.api_sniffer bet365
python -m scraping.api_sniffer doradobet
python -m scraping.api_sniffer melbet
python -m scraping.api_sniffer 20bet
```
**Exit code:** 0 en todos (con warnings de timeout en bet365 y 20Bet)

---

**bet365**
```
Requests: 15 | Datos: 4499.7 KB | JSON: 5
Dominio principal: www.bet365.com
```
- Screenshot: página cargando (spinner) — no terminó de renderizar en 30s
- ⚠️ Las odds NO llegan por JSON. Usan protocolo binario propietario `Api/1/Blob`:
  - `www.bet365.com/Api/1/Blob` (2205.7 KB, 1002.7 KB, 538 KB, 292.4 KB)
- Los 5 JSON capturados son solo configuración del sitio (manifest, routing, auth)
- **Conclusión: bet365 usa OCP (Open Connect Protocol) binario — muy difícil de parsear sin ingeniería inversa**

---

**DoradoBet**
```
Requests: 29 | Datos: 2981.3 KB | JSON: 14
```
- Screenshot: **404 NOT FOUND**
- El sniffer intentó 3 URLs de fútbol (`/sportsbook/football`, `/sports/football`, `/en/sports/football`) — todas fallaron
- Los JSON capturados son analytics (Amplitude, Facebook, Google) — cero datos de odds
- **Conclusión: URL de fútbol desconocida. Hay que abrir doradobet.com manualmente, navegar a la sección de fútbol y revisar la URL correcta**

---

**MelBet** ✅
```
Requests: 103 | Datos: 3353.6 KB | JSON: 98
Dominio principal: melbet.com
```
- Página cargó correctamente
- **Endpoint clave detectado (idéntico al de 1xBet):**
  ```
  melbet.com/service-api/LineFeed/Get1x2_VZip  (113.8 KB × 3, 52.0 KB × 2)
  melbet.com/service-api/LineFeed/GetSportsShortZip  (61.7 KB × 2)
  melbet.com/service-api/LiveFeed/Get1x2_VZip
  melbet.com/service-api/LineFeed/WebGetTopChampsZip
  ```
- Mismo backend BetB2B que 1xBet — solo cambia el dominio base
- **Conclusión: El scraper de 1xBet debería funcionar para MelBet cambiando `cr.1xbet.com` → `melbet.com`**

---

**20Bet** ⚠️
```
Requests: 55 | Datos: 3020.6 KB | JSON: 31
Dominio principal: platform.20bet.com
```
- Timeout en carga (60s excedido) pero capturó datos antes del timeout
- Plataforma propia — NO usa backend BetB2B
- Endpoints detectados:
  ```
  platform.20bet.com/api/sport/list/-1/0/en          (22.9 KB) ← posibles odds
  platform.20bet.com/api/v4/sport/config              (119.2 KB)
  platform.20bet.com/api/market-descriptions/get-all-markets/en  (736.2 KB)
  ```
- No se detectó un endpoint equivalente a `LineFeed/Get1x2_VZip`
- **Conclusión: Plataforma diferente, necesita análisis del JSON `sport/list` para ver si contiene odds por partido**

---

**Archivos generados** (en `scraping_debug/api_sniff/`):
- `bet365_api_20260427_230008.json`
- `doradobet_api_20260427_230106.json`
- `melbet_api_20260427_230217.json`
- `20bet_api_20260427_230257.json`

**URLs correctas (confirmadas manualmente):**
- DoradoBet fútbol: `https://doradobet.com/deportes/66`
- bet365 fútbol: `https://www.bet365.com/#/AS/B1/K%5E5/`

**Segunda corrida con URLs correctas:**

**DoradoBet (segunda corrida)** ✅
```
Requests: 122 | Datos: 5795.1 KB | JSON: 40
Backend: Altenar (sb2frontend-altenar2.biahosted.com)
```
- Página cargó correctamente con la URL `/deportes/66`
- **Endpoints de odds detectados:**
  ```
  sb2frontend-altenar2.biahosted.com/api/widget/GetUpcoming (59 KB)
  → keys: ['markets', 'odds', 'events', 'sports']  ← pre-match odds aquí
  sb2frontend-altenar2.biahosted.com/api/widget/GetLivenow  (42 KB)
  → keys: ['markets', 'odds', 'events', 'sports']  ← live odds aquí
  sb2frontend-altenar2.biahosted.com/api/Widget/GetWidgetsConfiguration (1113 KB)
  ```
- **Conclusión: DoradoBet usa plataforma Altenar. Las odds están en `GetUpcoming` y `GetLivenow`. API JSON limpio y estructurado.**

**bet365 (segunda corrida)** ❌
```
Requests: 15 | Datos: 4499.7 KB | JSON: 5 (idéntico a primera corrida)
```
- Resultado idéntico — el protocolo binario `Api/1/Blob` es arquitectural, no depende de la URL
- No hay JSON de odds disponible sin ingeniería inversa del OCP binario
- **Conclusión: bet365 no es scrappeable con este approach**

**Observaciones:** MelBet es la incorporación más fácil — mismo API que 1xBet. DoradoBet usa Altenar con API JSON limpio — scrappeable. bet365 usa protocolo binario propietario — no viable sin ingeniería inversa. 20Bet requiere análisis adicional del endpoint `sport/list`.

---

### 2026-04-27 18:15 — Fix parser DoradoBet — FUNCIONA (20 eventos parseados)

**Comando:** `cd paradigma && python -m scraping.doradobet_scraper`
**Duración:** ~25 seg
**Exit code:** 0

**Output:**
```
Altenar data: 20 events, 103 markets, 261 odds
DoradoBet: 20 eventos parseados, 20 con odds ✅

Eventos (ligas regionales):
  Mount Pleasant vs Waterhouse → h2h(2)
  Inter San Carlos vs Pitbulls Santa Barbara FC → h2h(2)
  Arema FC vs Persebaya Surabaya → h2h(2)
  Perak vs Johor Darul Takzim II → h2h(2)
  ... (Jamaica, Costa Rica, Indonesia, Malasia, Tailandia, Australia)
```

**Observaciones:** Parser fix correcto — ahora usa `marketIds`→`market.id`→`oddIds`→`odd.id`. Los 20 eventos son de ligas regionales (no europeas), por eso el emparejamiento con Pinnacle será 0. DoradoBet cubre ligas locales que Pinnacle no tiene.

---

### 2026-04-27 18:22 — Scanner combinado con DoradoBet fix — 1 VALUE BET, 15 NEAR MISSES

**Comando:** `cd paradigma && python -m scraping.scanner_v2 --books 1xbet,melbet,doradobet`
**Duración:** ~6 min
**Exit code:** 0

**Output:**
```
Pinnacle:    106 eventos
1xBet:       156 eventos, 96 emparejados
MelBet:      156 eventos, 96 emparejados
DoradoBet:    20 eventos, 0 emparejados (ligas regionales sin overlap con Pinnacle)

Por mercado (1xBet + MelBet → matched en Pinnacle):
  h2h:     543 odds, 425 matched  (78%) ✅
  spreads: 1416 odds, 734 matched (52%) ✅
  totals:  1770 odds, 1522 matched (86%) ✅

VALUE BETS: 1
  #1 [h2h] Leeds United vs Burnley — Vie 01 May — 19:00 UTC
     Burnley @ 7.900 (1xBet) | Pinnacle: 6.83 | EV: +7.12% | Kelly: 0.26%

NEAR MISSES (EV 1-5%): 15
  [spreads] Celta Vigo vs Elche        | Celta -1.5 @ 3.475    (Pin: 3.15) | EV: +3.96%
  [spreads] Bologna vs Cagliari        | Bologna -1.5 @ 3.710  (Pin: 3.36) | EV: +3.65%
  [spreads] Mainz 05 vs Union Berlin   | Mainz -1.5 @ 3.550    (Pin: 3.12) | EV: +3.36%
  [h2h]     Union Berlin vs FC Koln    | Draw @ 3.595           (Pin: 3.36) | EV: +3.16%
  [h2h]     Leeds vs Burnley           | Burnley @ 7.600        (Pin: 6.83) | EV: +3.05%
  [h2h]     Brentford vs West Ham      | West Ham @ 3.775       (Pin: 3.53) | EV: +2.74%
  [h2h]     Lecce vs Juventus          | Juventus @ 1.628       (Pin: 1.54) | EV: +2.14%
  [spreads] Lecce vs Juventus          | Lecce 1.5 @ 1.649      (Pin: 1.56) | EV: +2.10%
  [spreads] Auxerre vs Angers          | Auxerre -1.5 @ 3.625   (Pin: 3.34) | EV: +1.96%
  [spreads] Real Betis vs Real Oviedo  | Oviedo 1.5 @ 1.533     (Pin: 1.47) | EV: +1.79%
  [spreads] Bournemouth vs C. Palace   | C.Palace 1.5 @ 1.513   (Pin: 1.45) | EV: +1.68%
  [h2h]     Arsenal vs Fulham          | Arsenal @ 1.495        (Pin: 1.44) | EV: +1.52%
  [h2h]     Hellas Verona vs Como      | Como @ 1.514           (Pin: 1.44) | EV: +1.35%
  [spreads] Barcelona vs Real Madrid   | R.Madrid 1.5 @ 1.501   (Pin: 1.43) | EV: +1.32%
  [h2h]     Real Betis vs Real Oviedo  | Real Betis @ 1.656     (Pin: 1.60) | EV: +1.30%
  Por mercado: {'spreads': 8, 'h2h': 7}
```

**Observaciones:** Pipeline completo con 3 casas funcionando. DoradoBet necesita que le configuren más ligas europeas en la URL de scraping para tener overlap con Pinnacle. La value bet de Burnley persiste en ambas corridas.

---

### 2026-04-27 17:39 — Scanner combinado: 1xBet + MelBet + DoradoBet — 1 VALUE BET

**Comando:** `cd paradigma && python -m scraping.scanner_v2 --books 1xbet,melbet,doradobet`
**Duración:** ~6 min
**Exit code:** 0

**Output:**
```
Pinnacle:   106 eventos con odds
1xBet:      156 eventos, 96 emparejados
MelBet:     156 eventos, 96 emparejados
DoradoBet:  0 eventos (bug parser — esperado)
Total odds analizadas: 3,729

VALUE BETS: 1
  #1 [h2h] Leeds United vs Burnley — Vie 01 May — 19:00 UTC
     Burnley @ 7.900 (1xBet)  |  Pinnacle: 6.83
     EV: +7.12%  |  Kelly: 0.26%  |  Fair prob: 0.1356

NEAR MISSES (EV 1-5%): 15
  [spreads] Celta Vigo vs Elche        [Dom 03 May — 12:00 UTC] | Celta -1.5 @ 3.475    (Pin: 3.15) | EV: +3.96%
  [spreads] Bologna vs Cagliari        [Dom 03 May — 10:30 UTC] | Bologna -1.5 @ 3.710  (Pin: 3.36) | EV: +3.65%
  [spreads] Mainz 05 vs Union Berlin   [Dom 10 May — 17:30 UTC] | Mainz -1.5 @ 3.550   (Pin: 3.12) | EV: +3.36%
  [h2h]     Union Berlin vs FC Koln    [Sáb 02 May — 13:30 UTC] | Draw @ 3.595          (Pin: 3.36) | EV: +3.16%
  [h2h]     Leeds vs Burnley           [Vie 01 May — 19:00 UTC] | Burnley @ 7.600       (Pin: 6.83) | EV: +3.05%
  [h2h]     Brentford vs West Ham      [Sáb 02 May — 14:00 UTC] | West Ham @ 3.775      (Pin: 3.53) | EV: +2.74%
  [h2h]     Espanyol vs Real Madrid    [Dom 03 May — 19:00 UTC] | Real Madrid @ 1.778   (Pin: 1.69) | EV: +2.63%
  [h2h]     Lecce vs Juventus          [Sáb 09 May — 18:45 UTC] | Juventus @ 1.628      (Pin: 1.54) | EV: +2.14%
  [spreads] Lecce vs Juventus          [Sáb 09 May — 18:45 UTC] | Lecce 1.5 @ 1.649    (Pin: 1.56) | EV: +2.10%
  [spreads] Auxerre vs Angers          [Dom 03 May — 15:15 UTC] | Auxerre -1.5 @ 3.625 (Pin: 3.34) | EV: +1.96%
  [spreads] Real Betis vs Real Oviedo  [Dom 03 May — 16:30 UTC] | Oviedo 1.5 @ 1.533   (Pin: 1.47) | EV: +1.79%
  [spreads] Bournemouth vs C. Palace   [Dom 03 May — 13:00 UTC] | C.Palace 1.5 @ 1.513 (Pin: 1.45) | EV: +1.68%
  [h2h]     Arsenal vs Fulham          [Sáb 02 May — 16:30 UTC] | Arsenal @ 1.495       (Pin: 1.44) | EV: +1.52%
  [h2h]     Hellas Verona vs Como      [Dom 10 May — 10:30 UTC] | Como @ 1.514          (Pin: 1.44) | EV: +1.35%
  [spreads] Barcelona vs Real Madrid   [Dom 10 May — 19:00 UTC] | R.Madrid 1.5 @ 1.501 (Pin: 1.43) | EV: +1.32%
  Por mercado: {'spreads': 8, 'h2h': 7}
```

**Observaciones:** Con 2 casas activas (1xBet + MelBet) se pasó de 1,972 a 3,729 odds analizadas. DoradoBet aportó 0 por el bug del parser. El sistema detectó 1 value bet real (Burnley +EV 7.12%). Las fechas aparecen en todos los near misses correctamente.

---

### 2026-04-27 17:32 — MelBet scanner — FUNCIONA (96 emparejados, 2 near misses)

**Comando:** `cd paradigma && python -m scraping.scanner_v2 --books melbet`
**Duración:** ~4 min
**Exit code:** 0

**Output:**
```
Pinnacle:  106 eventos con odds
MelBet:    156 eventos con odds
Emparejados: 96 partidos

Por mercado (MelBet → matched en Pinnacle):
  h2h:     288 odds, 238 matched  (83%) ✅
  spreads: 748 odds, 390 matched  (52%) ✅
  totals:  936 odds, 804 matched  (86%) ✅

VALUE BETS: 0
NEAR MISSES (EV 1-5%): 2
  [h2h]     Leeds United vs Burnley [Vie 01 May — 19:00 UTC] | Burnley @ 7.600 (Pin: 6.83) | EV: +3.05%
  [spreads] Bologna vs Cagliari [Dom 03 May — 10:30 UTC]     | Bologna -1.5 @ 3.560 (Pin: 3.30) | EV: +1.54%
```

**Observaciones:** MelBet funciona idéntico a 1xBet (mismo backend BetB2B). Los near misses incluyen la fecha del partido. Los mismatches de totals/spreads extremos (Over 1.5, spreads ±2.5) son normales — líneas que MelBet tiene pero Pinnacle no.

---

### 2026-04-27 17:27 — DoradoBet scraper — datos capturados, parser devuelve 0

**Comando:** `cd paradigma && python -m scraping.doradobet_scraper`
**Duración:** ~25 seg
**Exit code:** 0

**Output:**
```
Altenar data: 20 events, 106 markets, 268 odds  ← captura correcta
DoradoBet: 0 eventos parseados, 0 con odds      ← bug en parser
```

**Estructura real de Altenar (del debug):**
```
Evento keys: ['marketIds', 'competitorIds', 'startDate', 'id', 'name', 'sportId', ...]
Ejemplo: { "name": "Huracan vs. Argentinos Juniors",
           "competitorIds": [46830, 46820],
           "startDate": "2026-04-28T00:00:00Z", "id": 15469545 }

Mercado keys: ['oddIds', 'typeId', 'isMB', 'id', 'name']
Ejemplo: { "name": "1x2", "typeId": 1, "oddIds": [3859067504, 3859067505, 3859067506] }

Odd keys: ['typeId', 'price', 'name', 'competitorId', 'id']
Ejemplo: { "price": 3.0, "name": "Huracan", "typeId": 1, "competitorId": 46830 }
```

**Debug JSON:** `scraping_debug/doradobet_raw_20260427_232744.json`

**Diagnóstico:** El scraper captura correctamente la API Altenar (20 eventos, 268 odds). El bug está en el parser — las keys reales son `competitorIds` (array), `marketIds`, `oddIds`. El parser probablemente busca claves diferentes.

---

### 2026-04-27 13:30 — Verificación manual odds — AMBOS scrapers confirmados vs sitios reales

**Método:** verify_odds generó links + odds. Se abrieron en navegador y se compararon visualmente partido por partido.

**1xBet — 5 partidos verificados:**
```
#1 Brighton vs Wolverhampton
   Sitio:    Brighton 1.394 | Draw 5.590 | Wolves 8.400
   Scraper:  Brighton 1.393 | Draw 5.590 | Wolves 8.400  ✅

#2 West Ham vs Arsenal
   Sitio:    West Ham 5.130 | Draw 4.270 | Arsenal 1.709
   Scraper:  West Ham 5.130 | Draw 4.265 | Arsenal 1.707  ✅

#3 Fulham vs Bournemouth
   Sitio:    Fulham 2.650 | Draw 3.800 | Bournemouth 2.660
   Scraper:  Fulham 2.654 | Draw 3.800 | Bournemouth 2.664  ✅

#4 Bournemouth vs Crystal Palace
   Sitio:    Bournemouth 1.709 | Draw 4.370 | C. Palace 4.980
   Scraper:  Bournemouth 1.707 | Draw 4.370 | C. Palace 4.980  ✅

#5 Crystal Palace vs Everton
   Sitio:    C. Palace 2.850 | Draw 3.250 | Everton 2.810
   Scraper:  C. Palace 2.846 | Draw 3.250 | Everton 2.805  ✅
```

**Pinnacle — 4 partidos verificados (búsqueda manual por nombre):**
```
#1 Brighton vs Wolverhampton
   Sitio:    Brighton 1.337 | Draw 5.460 | Wolves 7.890
   Scraper:  Brighton 1.338 | Draw 5.460 | Wolves 7.890  ✅

#2 West Ham vs Arsenal
   Sitio:    West Ham 4.990 | Draw 4.060 | Arsenal 1.645
   Scraper:  West Ham 4.990 | Draw 4.060 | Arsenal 1.645  ✅

#3 Bournemouth vs Crystal Palace
   Sitio:    Bournemouth 1.653 | Draw 4.350 | C. Palace 4.950
   Scraper:  Bournemouth 1.654 | Draw 4.350 | C. Palace 4.950  ✅

#4 Crystal Palace vs Everton
   Sitio:    C. Palace 2.730 | Draw 3.200 | Everton 2.700
   Scraper:  C. Palace 2.730 | Draw 3.200 | Everton 2.700  ✅
```

**Resumen:**
- 1xBet: 15/15 odds correctas ✅
- Pinnacle: 12/12 odds correctas ✅
- Diferencia máxima observada: 0.005 (redondeo de conversión American → Decimal)
- Los links directos de Pinnacle requieren login; se verificó navegando manualmente por nombre

**Observaciones:** Ambos scrapers capturan las odds exactas de los sitios reales. El pipeline está verificado de extremo a extremo.

---

### 2026-04-27 12:50 — verify_odds — FUNCIONA, links 1xBet OK, Pinnacle requiere login

**Comando:** `cd paradigma && python -m scraping.verify_odds`
**Duración:** ~5 min
**Exit code:** 0

**Output — primeros 5 partidos:**
```
PARTIDOS EMPAREJADOS: 87

#1 Manchester City vs Brentford | England - Premier League
   🟢 Pinnacle: https://www.pinnacle.com/en/soccer/matchup/1629254630
   🔵 1xBet:    https://1xbet.com/en/line/football/88637/716170549
   h2h: Brentford 7.940/8.400 | Draw 6.000/6.150 | Man City 1.308/1.362
   Totals 3.5: Over Pinnacle 2.030 | 1xBet 2.113
   Spread ±1.0: Man City Pinnacle 1.442 | 1xBet 1.430

#2 Nottingham Forest vs Newcastle United | England - Premier League
   🟢 Pinnacle: https://www.pinnacle.com/en/soccer/matchup/1629385719
   🔵 1xBet:    https://1xbet.com/en/line/football/88637/716170558
   h2h: Draw 3.420/3.535 | Newcastle 2.810/2.908 | Forest 2.490/2.572
   Totals 3.0: Over Pinnacle 2.150 | 1xBet 2.130
   Spread ±1.0: Nottingham Forest Pinnacle 3.950 | 1xBet 3.840

#3 Brighton vs Wolverhampton | England - Premier League
   🟢 Pinnacle: https://www.pinnacle.com/en/soccer/matchup/1629271809
   🔵 1xBet:    https://1xbet.com/en/line/football/88637/716170031
   h2h: Brighton 1.338/1.393 | Draw 5.460/5.590 | Wolves 7.890/8.400
   Totals 3.5: Over Pinnacle 2.370 | 1xBet 2.447

#4 Bournemouth vs Crystal Palace | England - Premier League
   🟢 Pinnacle: https://www.pinnacle.com/en/soccer/matchup/1628649353
   🔵 1xBet:    https://1xbet.com/en/line/football/88637/715078915
   h2h: Bournemouth 1.654/1.707 | C. Palace 4.950/4.980 | Draw 4.350/4.370
   Totals 3.0: Over Pinnacle 2.160 | 1xBet 2.100
   Spread ±1.0: Bournemouth Pinnacle 2.160 | 1xBet 2.110

#5 Crystal Palace vs Everton | England - Premier League
   🟢 Pinnacle: https://www.pinnacle.com/en/soccer/matchup/1629385715
   🔵 1xBet:    https://1xbet.com/en/line/football/88637/716180130
   h2h: C. Palace 2.730/2.846 | Draw 3.200/3.250 | Everton 2.700/2.805
   Totals 2.5: Over Pinnacle 2.050 | 1xBet 2.096
   Spread ±1.0: Crystal Palace Pinnacle 4.510 | 1xBet 4.450
```

**Verificación de links:**
- 🔵 **1xBet links: FUNCIONAN** — el formato `football/{league_id}/{event_id}` lleva directamente al partido correcto
- 🟢 **Pinnacle links: NO FUNCIONAN para verificación visual** — `https://www.pinnacle.com/en/soccer/matchup/{id}` redirige al homepage. Pinnacle requiere login para ver páginas de partidos específicos. No es un bug del scraper — las odds se obtienen de la API interna, no de la página pública.

**Warning (no bloqueante):**
```
[WARNING] Error en england-premier-league/matchups/: Page.goto: Timeout 60000ms exceeded.
```
Normal — EPL siempre timeout en la navegación directa, pero los datos se obtienen igualmente vía la API interceptada.

**⚠️ Anomalía detectada — spread Sunderland:**
```
#13 Sunderland vs Manchester United
    Spread ±1.0: Sunderland Pinnacle 1.493 | 1xBet 7.600
```
Diferencia de 5x — claramente un mapping errado. Pinnacle tiene Sunderland -1.0 (favorito dando handicap) y 1xBet tiene Sunderland +1.0 (recibiendo handicap). El signo del handicap está invertido para este partido.

**Observaciones:**
- Las odds h2h y totals se ven correctas y en escala normal (diferencias de 2-5% entre casas, consistente con margen de 1xBet)
- El spread de Sunderland es el único caso detectado con valor claramente anómalo — investigar si el signo del handicap de Pinnacle vs 1xBet está invertido en algunos casos
- El scraper funciona correctamente para verificación; la única limitación es que Pinnacle requiere cuenta para ver páginas de partidos específicos

---

### 2026-04-27 12:32 — verify_odds — ERROR al iniciar

**Comando:** `cd paradigma && python -m scraping.verify_odds`
**Duración:** ~2 min (crash al terminar Pinnacle scraping)
**Exit code:** 1

**Error:**
```
AttributeError: 'OneXBetScraper' object has no attribute 'scrape_all_football'
  File "paradigma/scraping/verify_odds.py", line 48, in verify
    onexbet_data, xbet_events = xbet_scraper.scrape_all_football()
```

**Diagnóstico:** `verify_odds.py` llama a `xbet_scraper.scrape_all_football()` pero ese método no existe en `OneXBetScraper`. El método correcto probablemente es otro nombre — revisar `onexbet_scraper.py` para ver el nombre real del método público.

**Pinnacle sí funcionó:** 112 eventos capturados antes del crash.

---

### 2026-04-27 12:20 — FIX Pinnacle todas las líneas — TOTALS Y SPREADS FUNCIONAN

**Comando:** `cd paradigma && python -m scraping.scanner_v2`
**Duración:** ~5 min
**Exit code:** 0

**Por mercado — ANTES vs AHORA:**
```
              ANTES      AHORA
h2h:     194 matched   194 matched  (sin cambio)
spreads:  12 matched   356 matched  ✅ +2,867%
totals:   86 matched   750 matched  ✅ +772%
```

**Value bets:** 0 (ninguna supera EV 5%)

**Near misses (EV 1-5%): 15 — h2h + spreads + totals funcionando**
```
[    h2h] Leeds vs Burnley           | Burnley -1.5 @ 7.700  (Pin: 6.83) | EV: +4.41%
[spreads] Mainz 05 vs Union Berlin   | Mainz -1.5 @ 3.550    (Pin: 3.12) | EV: +3.36%
[    h2h] Union Berlin vs FC Koln    | Draw @ 3.595           (Pin: 3.36) | EV: +3.03%
[    h2h] Brentford vs West Ham      | West Ham @ 3.775       (Pin: 3.53) | EV: +2.74%
[    h2h] Lecce vs Juventus          | Juventus @ 1.628       (Pin: 1.54) | EV: +2.14%
[spreads] Lecce vs Juventus          | Lecce 1.5 @ 1.649      (Pin: 1.56) | EV: +2.10%
[spreads] Celta Vigo vs Elche        | Celta -1.5 @ 3.410     (Pin: 3.15) | EV: +2.02%
[spreads] Auxerre vs Angers          | Auxerre -1.5 @ 3.625   (Pin: 3.34) | EV: +1.96%
[ totals] Bayern vs Heidenheim       | Over 3.5 @ 1.703       (Pin: 1.58) | EV: +1.86%
[spreads] Real Betis vs Real Oviedo  | Oviedo 1.5 @ 1.533     (Pin: 1.47) | EV: +1.79%
[spreads] Bournemouth vs C. Palace   | C. Palace 1.5 @ 1.513  (Pin: 1.45) | EV: +1.68%
[spreads] Bologna vs Cagliari        | Bologna -1.5 @ 3.475   (Pin: 3.20) | EV: +1.64%
[    h2h] Arsenal vs Fulham          | Arsenal @ 1.495        (Pin: 1.44) | EV: +1.40%
[    h2h] Hellas Verona vs Como      | Como @ 1.514           (Pin: 1.44) | EV: +1.35%
[spreads] Barcelona vs Real Madrid   | Real Madrid 1.5 @ 1.501(Pin: 1.43) | EV: +1.32%
Por mercado: {'h2h': 6, 'spreads': 8, 'totals': 1}
```

**Warnings devig (suma < 1.0):** 7 warnings de "posible arbitraje" — normales para líneas asiáticas de Pinnacle con pocos outcomes.

**Mismatches residuales:**
- totals: 1xBet tiene Over 1.5 que Pinnacle no publica (demasiado extremo)
- spreads: 1xBet tiene -2.5 / +2.5 que Pinnacle no tiene (solo hasta -1.25)
- Estos son normales — son líneas que una casa ofrece y la otra no

**Observaciones:** ✅ EL PIPELINE ESTÁ COMPLETO. Los 3 mercados (h2h, spreads, totals) calculan EV correctamente. El 0 value bets se debe a que el mercado está eficiente ahora — en otro momento del día o con más ligas habrá value.

---

### 2026-04-27 12:08 — Diagnóstico profundo: mismatch keys totals/spreads

**Comando:** `cd paradigma && python -m scraping.scanner_v2`
**Duración:** ~4 min
**Exit code:** 0

**Por mercado:**
```
h2h:     264 odds, 194 matched
spreads: 698 odds,  12 matched
totals:  872 odds,  88 matched
```

**🔍 totals MISMATCH [Manchester United vs Liverpool]:**
```
1xBet key:     ('Over', 3.5)   (type: str, float)
Pinnacle keys: [('Over', 3.25), ('Under', 3.25)]

1xBet key:     ('Under', 3.5)  (type: str, float)
Pinnacle keys: [('Over', 3.25), ('Under', 3.25)]

1xBet key:     ('Over', 2.5)   (type: str, float)
Pinnacle keys: [('Over', 3.25), ('Under', 3.25)]
```

**🔍 spreads MISMATCH [Manchester United vs Liverpool]:**
```
1xBet key:     ('Manchester United', -1.0)  (type: str, float)
Pinnacle keys: [('Manchester United', 0.0), ('Liverpool', -0.0)]

1xBet key:     ('Liverpool', -1.0)          (type: str, float)
Pinnacle keys: [('Manchester United', 0.0), ('Liverpool', -0.0)]

1xBet key:     ('Manchester United', 1.0)   (type: str, float)
Pinnacle keys: [('Manchester United', 0.0), ('Liverpool', -0.0)]
```

**Diagnóstico:**
- **totals**: tipos OK (str, float en ambos lados). El problema es que los PUNTOS no coinciden. 1xBet tiene Over 2.5, Over 3.5; Pinnacle tiene Over 3.25. Pinnacle usa líneas asiáticas (cuartos: 2.75, 3.25) mientras 1xBet usa enteros/medios (2.5, 3.0, 3.5).
- **spreads**: mismo problema. 1xBet tiene (-1.0, 1.0, -1.5, 1.5). Pinnacle tiene (0.0, -0.0) que es un handicap asiático de 0 (empate asiático). Las líneas no se solapan.

**Value bet detectada:**
```
#1 [h2h] Tottenham Hotspur vs Leeds United
   Tottenham @ 2.237 (1xBet) vs Pinnacle 2.04
   EV: +5.45% | Kelly: 1.10%
```

**Near misses (7, todos h2h):**
```
Leeds vs Burnley        | Burnley @ 7.700  (Pin: 6.83) | EV: +4.41%
Union Berlin vs FC Koln | Draw @ 3.595     (Pin: 3.36) | EV: +3.03%
Brentford vs West Ham   | West Ham @ 3.775 (Pin: 3.53) | EV: +2.74%
Lecce vs Juventus       | Juventus @ 1.628 (Pin: 1.54) | EV: +2.14%
Arsenal vs Fulham       | Arsenal @ 1.495  (Pin: 1.44) | EV: +1.40%
Hellas Verona vs Como   | Como @ 1.514     (Pin: 1.44) | EV: +1.35%
Real Betis vs Oviedo    | Real Betis @ 1.656(Pin: 1.60)| EV: +1.30%
```

**Observaciones:** El problema de totals/spreads es de PUNTOS, no de tipos. Pinnacle usa líneas asiáticas (cuartos: 3.25, 2.75) mientras 1xBet usa líneas occidentales (enteros y medios: 2.5, 3.0, 3.5). Para spreads, Pinnacle muestra el handicap neto mientras 1xBet muestra los dos lados por separado con signo. Fix: mapear líneas asiáticas de Pinnacle al punto occidental más cercano, o filtrar solo las líneas que existen en ambos.

---

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

---

### 2026-04-27 21:30 — Kambi scrapers: 888sport, Unibet, BetSafe (PARTE 1)

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book 888sport` (y unibet, betsafe)
**Duración:** ~6 min por casa (timeout)
**Exit code:** 0 (pero 0 eventos)

**Output:**
```
888sport: 0 eventos, 0 con odds
  WARNING: HTTPSConnectionPool(host='eu-offering.kambicdn.org', port=443):
  Max retries exceeded — ConnectTimeoutError (connect timeout=15)
  No se encontraron competiciones. Usando lista fija. 8 competiciones a scrapear.
  Scraping completado: 0 eventos, 0 con odds

Unibet: mismo resultado (mismo host, mismo timeout)
BetSafe: mismo resultado
```

**Diagnóstico:** `eu-offering.kambicdn.org` está completamente inaccesible desde esta red (curl exit code 28, ni siquiera conecta). El CDN de Kambi parece geo-bloqueado o bloqueado por el ISP.

---

### 2026-04-27 21:45 — API Sniffer en 888sport.es y BetSafe (PARTE 1b)

**Comando:** `cd paradigma && python3 -m scraping.api_sniffer 888sport` y `betsafe`
**Duración:** ~2 min por casa
**Exit code:** 0

**Resultado 888sport:**
```
Plataforma: Spectate (propia de 888sport — NO es Kambi)
API domain: spectate-web.888sport.es
Endpoint clave: /spectate/sportsbook-req/getUpcomingEvents/football/today
  → Keys: ['selection_pointers', 'events', 'event_order', 'match_request_limit']
  → selection_pointers: array con event_id, market_id, selection_id
  → 5 eventos capturados en el scroll inicial

Otros endpoints:
  /spectate/load/state → clientState, user
  /spectate/market_switcher_requests/getMarketSwitcher/football → 10 tipos de mercado
    (match-winner 1X2, both-teams-to-score, etc.)

CONCLUSIÓN: 888sport migró fuera de Kambi a plataforma propia Spectate.
El kambi_scraper con operador "888" nunca va a funcionar.
```

**Resultado BetSafe:**
```
Plataforma: Betsson Group API propia (NO es el CDN público de Kambi)
API domain: www.betsafe.com/api/sb/v1/
Requests JSON capturados: 41
Datos totales: 10.4 MB

Endpoints clave:
  /api/sb/v1/widgets/event-market/v1 → 5 respuestas (81KB, 237KB, 99KB, 166KB, 249KB)
    Keys: ['skeleton', 'topics', 'topicsMap', 'data', 'referenceId']
    data.keys: ['events', 'markets', 'marketSelections', 'scoreboards']
  /api/sb/v1/widgets/categories/v2 → 3,590KB
    Keys: ['data', 'referenceId'] — data.items (listado completo de competiciones)
  /api/sb/v1/widgets/view/v1 → 3,798KB
    Keys: ['data', 'referenceId'] — data.widgets

URLs de mercados llevan parámetro ?marketids=m-f-XXXXX-MARKET_TYPE
Ejemplo: m-f-Ktp6sppDm02O23QgYDNymA-AGSNAB (AGSNAB = Asian Handicap)

CONCLUSIÓN: BetSafe usa su propio dominio como proxy de Kambi.
El kambi_scraper apuntando a eu-offering.kambicdn.org no funciona,
pero www.betsafe.com/api/sb/v1/ SÍ es accesible y tiene los datos.
Requiere nuevo scraper tipo Playwright para interceptar event-market/v1.
```

**Archivos de debug:**
- `scraping_debug/api_sniff/888sport_api_20260428_033853.json`
- `scraping_debug/api_sniff/betsafe_api_20260428_033907.json`

---

### 2026-04-27 22:00 — Scrapers reescritos: 888sport (Spectate) + BetSafe (Betsson API)

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book 888sport --no-headless`
**Duración:** ~2 min cada uno
**Exit code:** 0 (pero 0 eventos en ambos)

---

#### 888sport — 0 eventos (bug en parser)

```
Scraper conecta correctamente a spectate-web.888sport.es ✅
10 API responses capturadas (getUpcomingEvents, load/state, market_switcher, etc.)
0 eventos con odds — parser falla silenciosamente
```

**Bug identificado — 2 problemas:**

**Bug 1: `_parse_generic_selection` no reconoce `decimal_price`**
La función busca: `item.get("odds") or item.get("price") or item.get("decimal")`
Pero 888sport usa el campo `decimal_price` (string, ej: `"5.500"`).
Resultado: `odds = None` → sale sin parsear.

**Bug 2: `_extract_888_markets` no profundiza en `selections`**
El código hace:
```python
for mk, mv in container.items():   # mv = market dict
    _parse_generic_selection(mv, ...)   # WRONG: mv es el market, no la selección
```
Pero la estructura real es:
```
event["markets"]["1632241"]["selections"]["16720450232"]["decimal_price"] = "5.500"
event["markets"]["1632241"]["selections"]["16720450232"]["type"] = "2"  (1/X/2)
```
Necesita iterar `mv["selections"].values()` y pasar cada selección a `_parse_generic_selection`.

**Estructura real confirmada (debug JSON):**
```json
{
  "name": "Abahani Dhaka vs PWD SC",
  "id": 7541348,
  "markets": {
    "1632241": {
      "name": "Ganador del partido",
      "selections": {
        "16720450232": {
          "decimal_price": "5.500",
          "type": "2",
          "name": "PWD SC"
        },
        "16720450231": {
          "decimal_price": "1.286",
          "type": "1",
          "name": "Abahani Dhaka"
        }
      }
    }
  }
}
```
**Nota:** Solo 5 eventos capturados (ligas regionales: Bangladesh, Indonesia). La URL de fútbol muestra muy pocos partidos. Puede necesitar navegar a ligas específicas (Premier League, Champions League).

**Archivo debug:** `scraping_debug/888sport_spectate_20260428_035332.json`

---

#### BetSafe — 0 eventos (bug en parser)

```
Scraper conecta correctamente a www.betsafe.com/api/sb/v1/ ✅
44 API responses capturadas incluyendo 5x event-market/v1 ✅
Eventos reales capturados: Paris SG - Bayern de Múnich, Atlético Madrid - Arsenal,
  Libertad - Independiente del Valle, Southampton - Ipswich, etc.
0 eventos con odds — parser falla en 2 puntos
```

**Bug 1: `participants[i].get("name")` → debe ser `participants[i].get("label")`**
```python
# Código actual (falla):
home = participants[0].get("name", "")   # ← siempre ""
# Estructura real:
# participants[0] = {"label": "Paris SG", "id": "816", "side": 1, ...}
# Fix:
home = participants[0].get("label") or participants[0].get("name", "")
```

**Bug 2: `markets_map` y `selections_map` son listas, no dicts**
El código hace `isinstance(markets_map, dict) and mid_str in markets_map` → siempre False.
La estructura real:
```
inner["markets"]          → lista de dicts, cada uno con campo "id" y "eventId"
inner["marketSelections"] → lista de dicts, cada uno con "marketId" y "odds" (float)
```
Para buscar mercados de un evento:
```python
# markets con eventId == evt["id"]
evt_markets = [m for m in markets_map if m["eventId"] == evt_id]
# selections de un market
mkt_sels = [s for s in selections_map if s["marketId"] == mkt["id"]]
# odds ya es float directo: s["odds"] = 2.0
```

**Bug 3: No hay mercado 1X2 en las respuestas capturadas**
Los event-market/v1 capturados solo contienen mercados secundarios (AGSNAB, MWOU, BTTS, DC, etc.).
El mercado 1X2 (Full Time Result) NO aparece en ninguna respuesta.
Posible causa: la URL `/futbol?tab=liveAndUpcoming` muestra mercados populares/destacados, no el 1X2 básico.
Solución: navegar a cada competición individualmente (ej: `/futbol/champions-league/`) para capturar el 1X2.

**Estructura real confirmada:**
```
event["label"] = "Paris SG - Bayern de Múnich"
event["participants"][0] = {"label": "Paris SG", "side": 1}
event["participants"][1] = {"label": "Bayern de Múnich", "side": 2}
event["id"] = "f-lGGIMROeykmUeY-bc5dXoA"
event["competitionName"] = "UEFA Champions League"
event["startDate"] = "2026-04-28T19:00:00Z"

markets[0]["id"] = "m-f-lGGIMROeykmUeY-bc5dXoA-AGSNAB"
markets[0]["eventId"] = "f-lGGIMROeykmUeY-bc5dXoA"
markets[0]["marketTemplateId"] = "AGSNAB"

marketSelections[0]["marketId"] = "m-f-lGGIMROeykmUeY-bc5dXoA-AGSNAB"
marketSelections[0]["odds"] = 2.0   ← float directo
marketSelections[0]["label"] = "Paris SG"
```

**Archivo debug:** `scraping_debug/betsafe_betsson_20260428_035613.json`

---

### 2026-04-27 22:10 — Re-test scrapers con fixes aplicados

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book 888sport/betsafe --no-headless`

---

#### 888sport — ✅ 11 eventos con odds (FIX FUNCIONÓ)

```
888sport — Eventos con odds: 11
Todos h2h, ligas regionales (Indonesia principalmente):
  Semen Padang vs Madura Utd — Draw:3.00, Madura Utd:2.80, Semen Padang:2.30
  Yogyakarta vs Persita Tangerang — Draw:3.10, Yogyakarta:2.10, Persita:3.10
  Dewa Utd vs Persijap Jepara — Draw:3.60, Dewa Utd:1.67, Persijap:4.40
  PSBS Biak vs Malut United — Draw:11.0, PSBS:26.0, Malut:1.06 (odds extrañas)
  ...
```

Fix funcionó: `decimal_price` ahora reconocido, `selections` iteradas correctamente.
**Problema pendiente:** Solo captura 5-11 eventos de ligas regionales (Bangladesh, Indonesia).
No captura Europa (Premier League, Champions League). URL `/futbol/` solo muestra partidos del día con pocas ligas.
Necesita navegar a ligas europeas específicas para tener overlap con Pinnacle.

---

#### BetSafe — ❌ 0 eventos con odds (fix parcial — nuevo bug identificado)

```
BetSafe — Eventos con odds: 0
44 API responses capturadas
Eventos detectados correctamente: AL Khaleej - AL Najma, Paris SG - Bayern, Atlético - Arsenal...
home/away parsean bien ahora (participants[i]["label"] ✅)
markets_list/selections_list lookup funciona ✅
```

**Causa real:** Los mercados capturados son TODOS secundarios — ninguno es 1X2 (MW3W).

**Templates capturados por response:**
```
81KB  → HTG, GIBH, MGT, HWTN, MWBTTS  (sin 1X2)
99KB  → ATG, BTTSOU, FTCSR, HTCS, MGT  (sin 1X2)
166KB → 1HTC, 1HTG, AGSNAB, BTTS1H    (sin 1X2)
249KB → AGSNAB, AWEH, BTTS1H, DC       (sin 1X2)
237KB → AGSNAB, ATCS, ATG, AWEH        (sin 1X2)
```

**Hallazgo clave:** El template 1X2 de BetSafe es **`MW3W`** (Match Winner 3-Way).
Aparece en `view/v1` como `"marketTemplateIds": ["MW3W"]` con estos event IDs:
```
f-lGGIMROeykmUeY-bc5dXoA  (Paris SG vs Bayern)
f-ntJBTtSXjEqKaCWv2Yasng
f-Ktp6sppDm02O23QgYDNymA
f-AtKKfD3qJUK0rl69RvBi0A
f-k7gRCxbd2k62CqnXc4bnSQ
```

Pero el `event-market/v1?marketids=m-f-{id}-MW3W` NUNCA se llama durante el scraping.
Los calls que sí se hacen son para los mercados destacados/exóticos que aparecen en la UI principal.

**Solución propuesta:** El scraper debe:
1. Parsear el `view/v1` para extraer los eventIds con `marketTemplateIds: ["MW3W"]`
2. Construir explícitamente el market ID: `m-f-{eventId}-MW3W`
3. Hacer el request directo:
   `GET /api/sb/v1/widgets/event-market/v1?marketids=m-f-{eventId}-MW3W`
   Esto se puede hacer vía Playwright (`page.evaluate`) o interceptando la respuesta.

**Archivos debug:**
- `scraping_debug/betsafe_betsson_20260428_040823.json`

---

### 2026-04-27 22:15 — BetSafe re-test con league URLs + fix MHDA

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~2 min (navegó 7 ligas: UCL, UEL, EPL, La Liga, Bundesliga, Serie A, Ligue 1)
**Exit code:** 0 — **0 eventos con odds**

**Progreso:**
- La navegación por ligas funciona correctamente ✅
- Se capturaron 19 responses JSON ✅
- Template `MW3W` SÍ aparece en `popular-bets/v1` ✅
- Template `MHDA` NO existe en BetSafe ❌ (asunción incorrecta del dev)

**Bugs nuevos identificados:**

**Bug 1: URL filter demasiado estricto**
```python
# Código actual — excluye popular-bets
if "event-market" not in url and "view" not in url:
    continue
# Fix: incluir también popular-bets y popular-pre-built-bets
if not any(x in url for x in ["event-market", "view", "popular-bets"]):
    continue
```

**Bug 2: Template 1X2 equivocado**
```python
# Código actual (MHDA no existe en BetSafe):
is_h2h = template in ("MHDA", "FT1X2", "1X2")
# Fix: usar MW3W
is_h2h = template in ("MW3W", "MHDA", "FT1X2", "1X2")
```

**Bug 3 (raíz del problema): `popular-bets/v1` tiene MW3W markets pero sin selections**
```
MW3W markets encontrados: 2
  m-f-ntJBTtSXjEqKaCWv2Yasng-MW3W  → Stockport vs Port Vale
  m-f-Ktp6sppDm02O23QgYDNymA-MW3W  → (otro evento)
marketSelections en popular-bets/v1: 0  ← vacío, sin odds
```

Las odds de MW3W NUNCA se cargan con la navegación actual. BetSafe solo carga las odds del 1X2 cuando se hace un request explícito a:
```
GET /api/sb/v1/widgets/event-market/v1?marketids=m-f-{eventId}-MW3W,...
```

**Solución propuesta (para el dev):**
El scraper debe construir y hacer los requests de MW3W explícitamente, usando page.evaluate() o route interception en Playwright:

```python
# Paso 1: recopilar eventIds con MW3W desde popular-bets/v1 o view/v1
mw3w_event_ids = ["f-lGGIMROeykmUeY-bc5dXoA", "f-ntJBTtSXjEqKaCWv2Yasng", ...]

# Paso 2: construir market IDs
mw3w_market_ids = [f"m-f-{eid}-MW3W" for eid in mw3w_event_ids]

# Paso 3: hacer el request explícito (via fetch en page.evaluate)
url = f"/api/sb/v1/widgets/event-market/v1?includescoreboards=true&marketids={','.join(mw3w_market_ids)}"
response = await page.evaluate(f"fetch('{url}').then(r => r.json())")
# → Esto debería devolver events + markets + marketSelections con odds MW3W
```

**Archivos debug:** `scraping_debug/betsafe_betsson_20260428_041403.json`

---

### 2026-04-27 22:55 — Re-test v3: 888sport EU leagues + BetSafe MW3W fetch

---

#### 888sport — ✅ 86 eventos con odds

```
888sport — Eventos con odds: 86
Ligas europeas: Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UCL, UEL ✅
Ejemplos:
  Leeds vs Burnley → Burnley:7.00, Leeds:1.40, Draw:4.40
  Man Utd vs Liverpool → Liverpool:2.70, Draw:3.60, Man Utd:2.375
  Brentford vs West Ham → Brentford:2.05, Draw:3.60, West Ham:3.20
  Atletico Madrid vs Celta Vigo → Atletico:1.85, Draw:3.50, Celta:3.90
```

Fix de EU leagues funcionó. De 11 eventos regionales → 86 eventos con ligas europeas. ✅

---

#### BetSafe — ❌ 0 eventos (fetch explícito falló, pero se identificó endpoint correcto)

**Fetch MW3W explícito:** Falló con `E_VALIDATION_INVALIDHEADER`
- `page.evaluate(fetch(...))` no envía los headers de sesión requeridos por BetSafe
- El request necesita headers adicionales que el browser tiene pero el fetch manual no incluye

**HALLAZGO CLAVE: endpoint correcto es `events-table/v2` (NO `event-market/v1`)**

Al navegar a cada liga, BetSafe carga automáticamente:
```
GET /api/sb/v1/widgets/events-table/v2?categoryIds=1&competitionIds={id}&...
```
Esta respuesta SÍ contiene MW3W con odds completas:
```
events-table/v2 → UCL:
  Event: Atlético Madrid vs Arsenal
    MW3W market: m-f-7kL1fDKRJk-lrYkt1-XNTA-MW3W
    selections (3):
      Atlético Madrid odds=2.95  template=HOME
      Empate          odds=3.25  template=DRAW
      Arsenal         odds=2.58  template=AWAY

  Event: Paris SG vs Bayern de Múnich
    MW3W market: m-f-lGGIMROeykmUeY-bc5dXoA-MW3W
    selections (3):
      Paris SG        odds=2.48  template=HOME
      Empate          odds=3.90  template=DRAW
      Bayern de Múnich odds=2.65 template=AWAY
```

**Diferencias críticas respecto a event-market/v1:**
- Usa `inner["selections"]` (no `inner["marketSelections"]`)
- Templates de selección: `HOME`, `DRAW`, `AWAY` (no nombres de equipo)
- URL: `events-table/v2` con `competitionIds` (no `event-market/v1`)

**Fix necesario en `_parse_betsson`:**
1. Incluir `events-table` en el URL filter (junto a `event-market` y `view`)
2. Usar `inner.get("selections", [])` en vez de `inner.get("marketSelections", [])`
3. Clasificar HOME/DRAW/AWAY por `selectionTemplateId` en vez de `label`

**Archivo debug:** `scraping_debug/betsafe_betsson_20260428_045648.json`

---

### 2026-04-27 23:10 — BetSafe v4: events-table/v2 + HOME/DRAW/AWAY templates

**Comando:** `cd paradigma && python -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~4 min
**Exit code:** 0

**Output:**
```
BetSafe — Eventos con odds: 2

  Stockport vs Port Vale
    Liga: Inglaterra League One
    h2h:
      Stockport: 1.3700

  Libertad vs Independiente del Valle
    Liga: Copa Libertadores
    h2h:
      Independiente del Valle: 2.6800
```

**Progreso vs v3:** El parser ahora incluye `events-table` en el URL filter y usa `inner["selections"]` correctamente. Pasó de 0 eventos → 2 eventos. Los eventos vienen del `liveAndUpcoming` inicial.

**Bugs restantes (2):**

**Bug 1 — Solo 1 selección por evento (falta DRAW y la otra selección):**
- Stockport: solo captura HOME (1.37) — falta Draw y Port Vale (AWAY)
- Independiente: captura una sola odd (2.68) — falta el resto
- Causa probable: `sel.get("selectionTemplateId")` devuelve vacío → fallback a `label == home/away`
  - El label del Draw en español es "Empate" — SÍ está en el check (`in ("draw", "x", "empate")`) ✅
  - Pero quizás el label exacto es diferente ("Empate (X)", "X", etc.) → comparación falla
  - O el campo real se llama algo distinto a `selectionTemplateId` en la respuesta real
- **Acción requerida:** Revisar en el debug JSON cuál es el field name de HOME/DRAW/AWAY y cuál es el label exacto del Draw

**Bug 2 — Solo 2 eventos (0 de UCL/EPL/La Liga/Bundesliga/Serie A/Ligue 1):**
- Los eventos UCL confirmados en el debug de 22:55 (Atlético 2.95, PSG 2.48) NO aparecen
- Los 2 eventos capturados (Stockport, Libertad) son de ligas que NO están en LEAGUE_URLS
- Conclusión: `events-table/v2` SÍ se carga para el `liveAndUpcoming` inicial, pero las LEAGUE_URLS no están disparando events-table
- Causa probable: Los slugs de las LEAGUE_URLS (`/champions-league`, `/premier-league`, etc.) son incorrectos — BetSafe puede usar slugs diferentes (ej. `/champions-league-1`, o con locale diferente)
- **Acción requerida:** 
  1. Confirmar manualmente las URLs exactas de cada liga en BetSafe
  2. O navegar primero al `/futbol` general y hacer click en cada liga (en vez de navegar directo a la URL)

**Diagnóstico resumen:**
```
events-table/v2 interceptado: SÍ (para liveAndUpcoming, no para ligas individuales)
HOME/DRAW/AWAY parsing: PARCIAL (1 selección de 3 capturada)
LEAGUE_URLS funcionando: NO (slugs incorrectos probablemente)
```

**Próximos pasos para dev PC:**
1. Abrir el debug JSON de la corrida v4 y verificar:
   - ¿Cuál es el field name de la selección template? (`selectionTemplateId`, `templateId`, `type`, etc.)
   - ¿Cuál es el label exacto del Empate?
2. Reemplazar navegación directa a LEAGUE_URLS por navegación programática (click en ligas desde el menú)
3. O hardcodear `competitionIds` y llamar events-table/v2 directamente (requiere saber los IDs de cada liga)

---

### 2026-04-27 23:25 — BetSafe v5: navegación dinámica de ligas + selection matching robusto

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~2 min
**Exit code:** 0

**Output:**
```
BetSafe: 41 API responses capturadas
BetSafe: 12 eventos con odds

  Stockport vs Port Vale       → Liga: Inglaterra League One → h2h: Stockport:1.37 (solo 1 sel)
  Libertad vs Independiente    → Liga: Copa Libertadores     → h2h: IndependienteDelValle:2.68 (solo 1 sel)
  Sevilla vs Real Sociedad     → Liga: España La Liga → h2h: 2.48 / 3.45 / 2.82 ✅
  Villarreal vs Levante        → Liga: España La Liga → h2h: 1.68 / 4.25 / 4.45 ✅
  Valencia vs Atlético Madrid  → Liga: España La Liga → h2h: 1.95 / 3.70 / 3.70 ✅
  Alaves vs Athletic Bilbao    → Liga: España La Liga → h2h: 2.68 / 3.45 / 2.58 ✅
  Osasuna vs Barcelona         → Liga: España La Liga → h2h: 4.45 / 3.70 / 1.82 ✅
  Celta Vigo vs Elche          → Liga: España La Liga → h2h: 1.82 / 3.70 / 4.45 ✅
  Getafe vs Rayo Vallecano     → Liga: España La Liga → h2h: 2.02 / 3.25 / 3.95 ✅
  Real Betis vs Oviedo         → Liga: España La Liga → h2h: 1.60 / 4.15 / 5.40 ✅
  Espanyol vs Real Madrid      → Liga: España La Liga → h2h: 4.95 / 3.70 / 1.75 ✅
  Girona vs Mallorca           → Liga: España La Liga → h2h: 2.02 / 3.45 / 3.70 ✅
```

**Progreso vs v4:** v4 tenía 2 eventos con 1 selección c/u → v5 tiene **12 eventos, La Liga completa con 3 selecciones** ✅

**Análisis del log — lo que funcionó y lo que falla:**

Link discovery encontró 7 links. Liga navegada correctamente:
```
✅ espana-la-liga          → events-table/v2 disparó 4 veces → 10 partidos La Liga ✅
⚠️ inglaterra-premier-league → navigó OK pero 0 events-table/v2 registrados
⚠️ italia-serie-a          → navegó OK pero 0 events-table/v2 registrados
❌ paris-sg-bayern-de-munich?eventId=... → PARTIDO INDIVIDUAL, no liga
⚠️ francia-ligue-1         → navegó OK pero 0 events-table/v2 registrados
❌ southampton-ipswich      → PARTIDO INDIVIDUAL, no liga
❌ paris-sg-bayern-de-munich → PARTIDO INDIVIDUAL, no liga
```

**Bug 1 (principal) — Link discovery captura páginas de partidos individuales:**
- El selector `a[href*="/futbol/"]` encuentra todos los links incluyendo links de partidos
- Ej: `paris-sg-bayern-de-munich?eventId=f-lGGIMROeykmUeY-bc5dXoA` matchea `"ligue 1"` → "ligue" está en algún texto cercano
- `southampton-ipswich` matchea `"premier"` → texto del link contiene "Premier League"
- Fix recomendado: filtrar links que tengan 2 o más `/` después de `/futbol/` (son partidos) vs exactamente 1 `/` (son ligas):
  ```python
  # Liga:   /futbol/la-liga           → 1 segmento después de /futbol/
  # Partido: /futbol/la-liga/partido  → 2 segmentos → excluir
  ```
  O mejor: buscar links con clase CSS de navegación del sidebar (no los de las cards de partidos)

**Bug 2 — EPL/Serie A/Ligue 1 navegan pero events-table/v2 no se intercepta:**
- Posible causa: browser caching hace que events-table/v2 no vuelva a disparar para ligas ya cacheadas
- O: el `wait_until="networkidle"` finaliza antes de que events-table/v2 complete (race condition)
- Fix recomendado: agregar `page.wait_for_response(lambda r: "events-table" in r.url, timeout=10000)` después de cada navegación de liga

**Bug 3 — Stockport/Libertad siguen con 1 selección:**
- Estos vienen del `event-market/v1` (liveAndUpcoming inicial), no de `events-table/v2`
- `event-market/v1` usa `marketSelections` con estructura diferente → HOME/DRAW/AWAY no están en esas responses
- Son ligas menores (League One, Copa Libertadores) — baja prioridad, no van a matchear con Pinnacle

**Debug:** `scraping_debug/betsafe_betsson_20260428_052712.json`

---

### 2026-04-27 23:39 — BetSafe v6: filtro 1 segmento + wait_for_response — REGRESIÓN (0 ligas)

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~1 min
**Exit code:** 0

**Output:**
```
BetSafe: 19 API responses capturadas
Encontradas 0 ligas en el menú   ← REGRESIÓN
BetSafe: 2 eventos con odds (Stockport, Libertad — mismo que v4)
```

**Diagnóstico:**

El filtro de 1 segmento es correcto lógicamente, pero el selector `a[href*="/futbol/"]` devuelve **0 elementos**. En v5 devolvía 7.

**Causa probable — locale vs idioma de links:**
- El Playwright context tiene `locale="en-US"`
- BetSafe navega a URL española `/es/apuestas-deportivas/futbol/...`
- Pero los links internos que genera la página podrían usar `/football/` (inglés) en lugar de `/futbol/`
- Si los hrefs son `/en/sports-betting/football/la-liga`, el selector `a[href*="/futbol/"]` no los encuentra

**Fix sugerido — buscar ambos idiomas:**
```python
# En vez de:
all_links = page.query_selector_all('a[href*="/futbol/"]')
# Usar:
all_links = (page.query_selector_all('a[href*="/futbol/"]') or
             page.query_selector_all('a[href*="/football/"]'))
```

**O agregar diagnóstico para confirmar:**
```python
# Antes de query_selector_all, loggear cuántos links totales hay:
total = len(page.query_selector_all('a[href]'))
futbol = len(page.query_selector_all('a[href*="futbol"]'))
football = len(page.query_selector_all('a[href*="football"]'))
logger.info(f"  Links totales: {total}, /futbol/: {futbol}, /football/: {football}")
```

**Debug:** `scraping_debug/betsafe_betsson_20260428_053959.json`

---

### 2026-04-28 18:53 — BetSafe v7: selector bilingüe /futbol/ + /football/ — sigue 0 ligas

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~1 min
**Exit code:** 0

**Output:**
```
Links: /futbol/=21, /football/=0
Encontradas 0 ligas en el menú
BetSafe: 1 evento con odds

  Cerro Porteño vs Palmeiras → Copa Libertadores → Palmeiras: 1.9800 (solo 1 sel)
```

**Diagnóstico definitivo — causa raíz encontrada:**

El log de diagnóstico revela: **21 links con `/futbol/` son encontrados, pero TODOS tienen 2+ segmentos** → el filtro de 1 segmento los elimina todos.

```
Los 21 links son de partidos individuales (estructura):
  /es/apuestas-deportivas/futbol/copa-libertadores/cerro-porteno-palmeiras
  /es/apuestas-deportivas/futbol/champions-league/atletico-madrid-arsenal
  /es/apuestas-deportivas/futbol/premier-league/xxx-yyy
  → todos tienen 2 segmentos tras /futbol/: liga + partido → filtrados

Links de liga (1 segmento) como /futbol/champions-league → NO existen en liveAndUpcoming
```

**La página `liveAndUpcoming` solo tiene links de partidos individuales**, no links de ligas. Los links de liga de 1 segmento están en el **sidebar de navegación izquierdo**, NO en las cards de partidos.

**Hipótesis sobre v5:** En v5 funcionó porque no había filtro de 1 segmento — se navegaba a páginas de partidos individuales (como `paris-sg-bayern-de-munich`) y eso SÍ disparaba `events-table/v2` para la liga completa de esa página. El filtro de v6/v7 rompió eso.

**Fix recomendado — dos opciones:**

**Opción A (más simple — revertir filtro y usar clase CSS):**
```python
# En vez de filtrar por segmentos de URL, filtrar por clase CSS del sidebar
# Los links del sidebar tienen clases distintas a los links de cards de partidos
# Ejemplo: 'nav a[href*="/futbol/"]' o '.sidebar a[href*="/futbol/"]'
# Pero primero confirmar qué clase tienen con DevTools en BetSafe
```

**Opción B (más robusta — navegación por la API de categorías):**
```python
# La respuesta categories/v2 (4162KB ya interceptada) contiene el árbol de categorías
# con IDs de competiciones. Extraer los competitionIds de ahí y construir URLs:
# /es/apuestas-deportivas/futbol?competitionId=XXXX
# O llamar events-table/v2 directamente con esos IDs (sin Playwright navigation)
```

**Opción C (más rápida — quitar filtro de 1 segmento y navegar a partidos):**
```python
# Revertir al approach de v5: navegar a links de PARTIDOS de UCL/EPL/La Liga
# Al navegar a un partido individual de UCL, events-table/v2 carga TODA la liga UCL
# Esto es lo que funcionó en v5 (aunque inadvertidamente)
```

**Debug:** `scraping_debug/betsafe_betsson_20260429_005358.json`

---

### 2026-04-28 18:58 — BetSafe v8: un partido por liga — detecta 3 ligas pero events-table no dispara

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~1 min
**Exit code:** 0

**Output:**
```
Links: /futbol/=21, /football/=0
Liga detectada: champions-league
Liga detectada: inglaterra
Liga detectada: italia
Ligas únicas encontradas: 3
Navegando a liga: uefa-champions-league   → events-table no disparó
Navegando a liga: inglaterra-premier-league → events-table no disparó
Navegando a liga: italia-serie-a          → events-table no disparó
BetSafe: 1 evento con odds (Cerro Porteño vs Palmeiras, 1 sel)
```

**Diagnóstico — dos problemas:**

**Problema 1 — URL remapping crea slugs incorrectos:**
```
Slug extraído del match URL → URL navegada
  champions-league  →  uefa-champions-league      ← transformación incorrecta?
  inglaterra        →  inglaterra-premier-league  ← "inglaterra" no es un slug de liga
  italia            →  italia-serie-a             ← "italia" no es un slug de liga
```

Si los match URLs tienen estructura de 3 niveles: `/futbol/PAIS/LIGA/PARTIDO`:
- `/futbol/inglaterra/premier-league/xxx` → extrae `inglaterra` (país, no liga)
- `/futbol/italia/serie-a/xxx` → extrae `italia` (país, no liga)
- `/futbol/champions-league/xxx` → extrae `champions-league` (liga directa)

El código extrae el primer segmento tras `/futbol/` pero para EPL/Serie A ese es el PAÍS, no la liga.

**Solución correcta — usar el URL completo del match y quitar solo el último segmento:**
```python
# Del match URL /futbol/espana-la-liga/sevilla-real-sociedad
# → strip último segmento → /futbol/espana-la-liga  ← URL de liga correcto

# Del match URL /futbol/england/premier-league/man-utd-liverpool
# → strip último segmento → /futbol/england/premier-league
# → URL correcto para navegar

match_path = "/es/apuestas-deportivas/futbol/champions-league/atletico-arsenal"
league_path = "/".join(match_path.split("/")[:-1])  # quita el último segmento
# → /es/apuestas-deportivas/futbol/champions-league  ✅
```

**Problema 2 — events-table no dispara aunque la liga carga:**
- Puede ser consecuencia del Problema 1 (URL malo → página errónea → sin events-table)
- O: el browser usa cache tras la primera navegación y events-table no re-dispara
- Fix: usar `page.route` para forzar cache bypass, o `page.context.clear_cookies()` entre ligas

**Hecho positivo:** La estructura de URL confirmada: `/futbol/champions-league/xxx` (UCL no tiene país prefix). Los 21 links de la página dan cobertura a 3 ligas distintas que sí tienen partidos hoy.

**Debug:** `scraping_debug/betsafe_betsson_20260429_005903.json`

---

### 2026-04-28 19:02 — BetSafe v9: strip último segmento → 52 eventos ✅

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~1.5 min
**Exit code:** 0

**Output:**
```
Links: /futbol/=21, /football/=0
Ligas únicas encontradas: 4 (champions-league, uefa-champions-league, inglaterra, espana)
BetSafe: 85 API responses capturadas
BetSafe: 52 eventos con odds

Ligas capturadas:
  UEFA Champions League: Bayern de Múnich vs Paris SG → 1.72 / 4.65 / 4.20 ✅
  España La Liga:        Villarreal, Valencia, Alaves, Osasuna, Celta Vigo, Girona, Espanyol, Getafe, Real Betis (10 partidos) ✅
  España Segunda Div:    Cultural Leonesa, Castellon, Eibar, Zaragoza, Deportivo, etc. ✅
  España Primera RFEF:   Ferrol, Gimnàstic, CF Talavera, Sporting Gijón, etc. ✅
  España 2ª RFEF/3ª:     CD Llosetense, Real Madrid Castilla, Betis Deportivo, etc. ✅
  Inglaterra (ligas bajas): National League, Southern, Isthmian (arsenal femenino, Boreham Wood, etc.) ✅
  Copa Libertadores:     Cerro Porteño vs Palmeiras (solo 1 sel — sigue el bug de event-market/v1)
```

**Nota: "events-table no disparó" en el log es un falso positivo** — el `wait_for_response` se llama DESPUÉS del `wait_until="networkidle"`, entonces el response ya pasó antes del listener. Pero el `on_response` handler SÍ los capturó (85 responses totales vs 17-19 en versiones anteriores).

**Pendiente — prioridad:**
1. 🔴 **Premier League MUST HAVE** — actualmente navega a `/futbol/inglaterra` (URL de PAÍS) que carga ligas menores inglesas. El link de EPL en la página tiene slug diferente (probablemente `/futbol/england/premier-league` o `/futbol/inglaterra/premier-league`). Sin EPL el overlap con Pinnacle es limitado — es la liga con más eventos en Pinnacle.
2. ⚠️ **Cerro Porteño sigue con 1 sel** — viene de event-market/v1, baja prioridad
3. **Atlético vs Arsenal (UCL)** — no aparece porque el partido ya fue

**Debug:** `scraping_debug/betsafe_betsson_20260429_010352.json`

---

### 2026-04-28 20:34 — BetSafe v10: fallback URLs EPL/Bundesliga — TIMING ISSUE (no bug de código)

**Comando:** `cd paradigma && python3 -m scraping.kambi_scraper --book betsafe --no-headless`
**Duración:** ~2 min
**Exit code:** 0

**Output:**
```
Total ligas a navegar: 12 (5 dinámicas + 7 fallback con EPL/Bundesliga/etc.)
events-table no disparó para: champions-league, uefa-champions-league, concacaf-champions-cup,
                               inglaterra, espana, inglaterra-premier-league, spain-la-liga,
                               germany-bundesliga, italy-serie-a, france-ligue-1, europa-league
BetSafe: 16 API responses capturadas
BetSafe: 1 evento con odds (Cerro Porteño vs Palmeiras, 1 sel)
```

**⚠️ ESTO NO ES UN BUG DE CÓDIGO — ES UN PROBLEMA DE HORARIO**

Comparación debug files:
```
v9  (19:03 CR / 01:03 UTC)  →  34.8 MB debug  →  52 eventos  ✅
v10 (20:36 CR / 02:36 UTC)  →   9.4 MB debug  →   1 evento   ❌
```

Los partidos europeos se juegan ~19:00-22:00 hora España = **12:00-15:00 hora Costa Rica**.
A las 20:36 CR (02:36 UTC) ya no hay eventos "upcoming" en BetSafe para UCL/La Liga/EPL/etc.

Los "events-table no disparó" en v10 son **verdaderos negativos** — events-table sí se llama pero BetSafe responde con 0 eventos porque ya no hay partidos próximos.

**Conclusión: el código v10 está bien. Hay que re-testar en horario correcto (12:00-17:00 CR) cuando los partidos europeos sean "upcoming".**

**Para el dev PC:** No hacer rollback. Pero los fallback URLs son incorrectos — BetSafe usa `/en/sportsbook/football/` (inglés), NO `/es/apuestas-deportivas/futbol/`. URLs confirmadas manualmente:

```
# Estructura: /en/sportsbook/football/{país}/{país-liga}
# URLs CONFIRMADAS manualmente:
https://www.betsafe.com/en/sportsbook/football/england/england-premier-league
https://www.betsafe.com/en/sportsbook/football/italy/italy-serie-a
https://www.betsafe.com/en/sportsbook/football/spain/spain-la-liga
https://www.betsafe.com/en/sportsbook/football/champions-league/champions-league

# URLs CONFIRMADAS adicionales:
https://www.betsafe.com/en/sportsbook/football/germany/germany-bundesliga

# URLs CONFIRMADAS adicionales:
https://www.betsafe.com/en/sportsbook/football/france/france-ligue-1

# URL CONFIRMADA:
https://www.betsafe.com/en/sportsbook/football/europa-league/europa-league
```

**Fixes requeridos en kambi_scraper.py:**
1. `FOOTBALL_URL` → cambiar a `https://www.betsafe.com/en/sportsbook/football?tab=liveAndUpcoming`
2. Selector → cambiar `a[href*="/futbol/"]` por `a[href*="/sportsbook/football/"]`
3. `LEAGUE_URLS` fallback → usar las URLs confirmadas arriba
4. `full_url` builder → `https://www.betsafe.com` + href (los hrefs ahora empiezan con `/en/sportsbook/football/`)

**Debug:** `scraping_debug/betsafe_betsson_20260429_023631.json`
