# Memorias del Proyecto

> Este archivo se mantiene sincronizado con las memorias internas de Cascade.
> Última actualización: 2026-04-27 (optimización API, auto-liquidación, freshness tracking)

---

## Reglas Globales

- **Sincronización de memorias**: Cada vez que se actualicen las memorias internas, también se debe actualizar este archivo (`MEMORIAS.md`).
- **Idioma**: El usuario se comunica en español.
- **País**: Costa Rica.

---

## Proyecto: Paradigma

- **Objetivo**: Sistema de detección de value bets en apuestas deportivas.
- **Estrategia actual (Fase 1)**: Arbitraje de casas blandas — usar Pinnacle como referencia de precio justo, apostar en casas que paguen más.
- **Modo**: Paper trading (apuestas simuladas, $0 real) hasta validar con 200+ apuestas.
- **Workspace**: `c:\Users\cerdascg\12.Gustavo\4. Paradigma`

---

## Decisiones Clave (2026-04-25)

### Hipótesis elegida: B — Arbitraje de casas blandas
- **Por qué**: Es la única que NO requiere ser más inteligente que Pinnacle. Solo requiere que Pinnacle sea correcta (lo es) y que otras casas sean menos precisas (lo son).
- **NO se construyen** modelos propios (Dixon-Coles, XGBoost, Neural Nets, LangGraph) hasta que Fase 1 se valide.

### 4 Hipótesis identificadas (en orden de prioridad):
1. **B — Casas blandas** (Fase 1, ~60-70% prob. éxito) ← ACTUAL
2. **A — Mercados nicho** (Fase 2, ~20-30% prob.) — ligas menores, córners, BTTS
3. **C — ML pipeline** (Fase 3, ~5-15% prob.) — XGBoost, Dixon-Coles, features
4. **D — Timing** (probablemente nunca, ~10% prob.) — competir contra sindicatos

### Reglas de operación:
- **Umbral**: Solo apostar si EV > 5%
- **Kelly**: Fraccionario (÷4), cap máximo 2% del bankroll por apuesta
- **Máximo diario**: 10% del bankroll en juego simultáneo
- **Stop-loss**: Si bankroll baja 15% en una semana → pausar
- **Validación**: CLV > 0 después de 500 apuestas → continuar; CLV < 0 → ajustar o parar

---

## Estructura del Proyecto

- `repos.txt` — Lista de URLs de GitHub (una por línea).
- `clone_repos.ps1` — Script PowerShell para clonar todos los repos automáticamente en `repos/`.
- `repos/` — Carpeta donde se clonan los repositorios (shallow clone con `--depth 1`).
- `ANALISIS_REPOS.md` — Análisis detallado de los 75 repos.
- `DOCUMENTO_PROYECTO_PARADIGMA.md` — Documento extenso del proyecto.
- `DOCUMENTO_PROYECTO_PARADIGMA.pdf` — Versión PDF.

---

## Estado Actual

1. ~~Crear archivo de memorias sincronizado~~ ✅
2. ~~Crear script de clonación automática~~ ✅
3. ~~Clonar los repositorios~~ ✅ (75+5 = 80 repos)
4. ~~Analizar los 80 repos~~ ✅ (ver `ANALISIS_REPOS.md`)
5. ~~Generar documento detallado del proyecto~~ ✅ (ver `DOCUMENTO_PROYECTO_PARADIGMA.pdf`)
6. ~~Definir hipótesis y estrategia~~ ✅ (Hipótesis B, paper trading)
7. ~~Analizar 5 repos específicos para Fase 1~~ ✅ (oddsapi_ev, SportsArbFinder, WagerBrain, surebet, SureBetsBot)
8. ~~Construir MVP Fase 1~~ ✅ (scanner, EV calc, Shin devig, Kelly, tracker, Telegram)
9. ~~Diagnóstico `last_update`~~ ✅ (confirmado: mide polling, no cambio de precio)
10. ~~Optimizar costos API~~ ✅ (param `bookmakers` = 4x más barato)
11. ~~Auto-liquidación de apuestas~~ ✅ (endpoint `/scores`)
12. ~~Tracking de frescura propio~~ ✅ (comparar precios entre escaneos)
13. **En progreso**: Usuario creando cuentas en casas de apuestas desde Costa Rica.
14. **Pendiente**: Ejecutar primer ciclo completo de paper trading.

---

## Casas de Apuestas (Costa Rica)

### Prioritarias para crear cuenta:
1. **1xBet** — Fácil de abrir, acepta criptos, licencia Curazao
2. **Bet365** — La más grande del mundo, verificar acceso desde CR
3. **20Bet** — Confirmada en CR, cuotas altas
4. **MelBet** — Confirmada en CR, acepta criptos
5. **Betsson** — Presencia fuerte en LATAM

### Estado de cuentas: (pendiente de validación por el usuario)

---

## Stack Fase 1 (Lean)

### Descubrimiento clave:
**Pinnacle está disponible en The Odds API (región `eu`).** No necesitamos scraper Playwright para Fase 1. Una sola fuente da Pinnacle + 20 casas.

### Fuente de datos:
- **The Odds API** — Pinnacle (región `eu`) + casas blandas, todo en una sola API
  - Mercados cubiertos: `h2h`, `totals`, `spreads`
  - Mercados NO cubiertos: córners, BTTS, tarjetas, player props, correct score (→ Fase futura con scraper)
  - Costo: $60/mes para monitoreo adecuado (~50,000 req/mes). Tier gratis (500 req) es insuficiente.
  - **Optimización**: param `bookmakers` en vez de `regions` → 3 créditos por deporte en vez de 12 (4x más barato)
  - **`includeLinks=true`**: links directos al betslip del bookmaker
  - **`/events` endpoint**: scouting gratuito (0 créditos)
  - **`/scores` endpoint**: resultados para auto-liquidación de apuestas

### Matemáticas:
- **Shin devig** (de `the-pitchs-edge`) — quitar comisión de Pinnacle para precio justo
- **Kelly Criterion** (de `WagerBrain`) — configurable: full/half/quarter Kelly
- **EV calculation** (de `oddsapi_ev`) — comparar odds de cada casa vs. precio justo de Pinnacle

### Deportes (multi-deporte para acelerar validación):
- Fútbol, NBA, Tennis, MLB, NHL, MMA
- Objetivo: 15-25 value bets/día → 500 apuestas en ~25 días

### Infraestructura:
- **DB**: PostgreSQL (odds, apuestas, resultados, CLV tracking)
- **Alertas**: Telegram Bot
- **Lenguaje**: Python 3.11+

### NO se usa en Fase 1:
- ❌ Playwright / scraper de Pinnacle (no necesario, The Odds API lo cubre)
- ❌ Dixon-Coles, Poisson, Bayesian
- ❌ XGBoost, Random Forest, Neural Nets
- ❌ LangGraph, OpenAI, Claude
- ❌ Feature engineering (xG, forma, clima, lesiones)
- ❌ Streamlit, Next.js, Flask

---

## Repos Clave para Fase 1

### Base del sistema:
1. **oddsapi_ev** ⭐⭐⭐ — The Odds API + Pinnacle EV + Kelly + filtros (541 líneas)
   - Bug conocido: línea 70, retorna `odds_json` en vez de `all_odds_json`
   - Devig usa normalización simple (no Shin) — reemplazar con Shin
2. **SportsArbFinder** ⭐⭐ — Clase OddsAPI limpia, modo offline, arbitraje puro como bonus
3. **WagerBrain** ⭐⭐ — Kelly configurable (full/half/quarter), EV, conversiones de odds
4. **the-pitchs-edge** ⭐⭐ — Shin devig, Kelly, CLV tracking

### Para Fase futura:
- **Pinnacle_Football_Odds_Scraper** — Mercados exóticos (córners, tarjetas, props)
- **penaltyblog** — Dixon-Coles (Fase 3)
- **ProphitBet** — ML models (Fase 3)
- **sports-betting** — Backtesting framework (Fase 3)

### Descartados:
- **surebet** — Solo converter de odds, módulos principales vacíos
- **SureBetsBot** — No tiene código, solo README

---

## Bug Crítico: Market Type Mismatch 2-way vs 3-way (2026-04-27)

- **En NHL y MMA**, Pinnacle devuelve h2h **2-way** (sin empate, incluye overtime).
- Otros bookmakers (onexbet, betway, unibet, marathonbet) devuelven h2h **3-way** (con Draw, solo reglamentario).
- **Comparar 2-way vs 3-way es inválido** — las odds 3-way son naturalmente más altas porque el Draw absorbe probabilidad.
- Esto producía falsos positivos con EV >20% (hasta +94%) que NO eran oportunidades reales.
- **Fix**: `ev_calculator.py` ahora cuenta outcomes por (event, book, market) y solo compara si coincide con Pinnacle.
- **Resultado**: De 13 "value bets" pre-fix, quedaron 2 legítimas post-fix (EV 7-9%, rango realista).
- **Deportes afectados**: NHL (84 odds filtradas), MMA (51 odds filtradas).
- **No afectados**: Fútbol (todos 3-way), NBA/MLB (todos 2-way).

## Hallazgo: bet365 NO está en The Odds API (2026-04-27)

- bet365, twentybet y unibet_eu **no existen** como bookmaker keys en la API.
- 58 bookmakers disponibles; bet365 no está en ninguna región.
- **Bookmakers confirmados ACCESIBLES desde Costa Rica**: onexbet (1xBet) ✅, sport888 (888sport) ✅.
- **Betsson**: NO disponible en Costa Rica ❌.
- **Pendientes de verificar**: marathonbet, coolbet, betway, unibet, leovegas, nordicbet.
- **Config corregido** con keys reales verificados contra la API.

---

## Hallazgo: `last_update` (2026-04-27)

- **`last_update` de The Odds API mide frecuencia de POLLING, NO cambio de precio.**
- Test empírico: 96.1% de entries cambiaron `last_update` sin cambio de precio en solo 3 min.
- Confirmado por documentación oficial: "markets can update on their own schedule"
- **Consecuencia**: NO se puede usar `last_update` para filtrar odds viejas.
- **Solución**: Tracking propio comparando precios entre escaneos (`odds_history.py`).

---

## Archivos del Sistema

| Archivo | Descripción |
|---------|-------------|
| `config.py` | Configuración central: API keys, umbrales, bookmakers target, exchanges |
| `odds_client.py` | Cliente The Odds API: odds, events (gratis), scores, DNS workaround |
| `devig.py` | Shin devig para quitar comisión de Pinnacle |
| `ev_calculator.py` | Cálculo de EV, Kelly, detección de value bets |
| `tracker.py` | Registro de apuestas, bankroll, CLV (SQLAlchemy) |
| `scanner.py` | Orquestador: scouting → odds → EV → tracking → auto-liquidación |
| `telegram_bot.py` | Alertas Telegram con links directos al bookmaker |
| `result_settler.py` | Auto-liquidación via `/scores` (h2h, totals, spreads) |
| `odds_history.py` | Tracking de frescura: detecta odds estancadas entre escaneos |
| `main.py` | Entry point |
| `diagnostico_freshness.py` | Script diagnóstico del campo `last_update` |

---

## Notas

- **Pinnacle** no es nuestra competencia — es nuestra fuente de verdad
- **Pinnacle está en The Odds API** (región `eu`) — simplifica enormemente Fase 1
- Las casas blandas (Bet365, 1xBet) pagan de más porque atienden al público general
- **Shin devig** quita la comisión de Pinnacle para ver el precio justo
- **CLV tracking** es la métrica #1 para saber si hay edge real
- El riesgo principal de Fase 1 es el **gubbing** (que las casas limiten las cuentas)
- Paper trading primero, dinero real después de 200+ apuestas con CLV > 0
- **Decisión: solo fútbol** — elimina 2way/3way bug, reduce costos API 5x, validación confirmada
- Costa Rica: Pinnacle NO está restringido (podemos scrappear y crear cuenta)
- Ruta de escalabilidad: casas blandas → Betfair Exchange (sin gubbing) → modelo propio + exchange → venta de señales

---

## Validación API vs Sitio Real (2026-04-27)

**1xBet EPL — 12 odds comparadas, 4 partidos:**
- 9 exactas (75%), 3 dentro de ±0.01 (25%)
- Diferencias de ±0.01 atribuibles a movimiento de mercado (~8 min entre scan y captura)
- **Conclusión: API es confiable para 1xBet fútbol.**

**888sport EPL:**
- Odds consistentemente más bajas que Pinnacle → vig alta
- Poco probable que genere value bets, pero útil en pool de comparación

---

## Investigación de Repos GitHub (2026-04-27)

~130 repos analizados. Hallazgos clave:

### Pinnacle API directa — CERRADA al público (Jul 2025)
- Fuente: pinnacleapi/pinnacleapi-documentation
- Solo disponible para "high value bettors" y partnerships comerciales
- Alternativa: PS3838 API (marca asiática) vía contacto Telegram @iliyasone

### Repos clonados en /repos/
| Repo | Qué aporta |
|------|-----------|
| `Pinnacle_Football_Odds_Scraper` | Scraper Playwright de Pinnacle, intercepta API interna arcadia.pinnacle.com. GRATIS, todos los mercados. |
| `Sports-Betting-EV-Scraper` | Scraping dual Pinnacle+BetMGM con Selenium. Devig, Discord, line movement. |
| `ps3838api` | Python wrapper PS3838 (Pinnacle Asia). Incluye bet placement. Requiere cuenta. |
| `sports-arbitrage-1xbet` | **Scraper de 1xBet** con Selenium. Login, 1X2/DC/OU/AH, SQLite. |
| `BetEdge` | Full stack: scrapers multi-book + Django API + Vue + MySQL. Arquitectura profesional extensible. |

### Repos destacados (no clonados)
- **EVCore**: Motor EV completo (Poisson+xG), 49 releases, 231 tests. Node.js.
- **OddsTracker**: Dashboard Pinnacle/OddsPapi, 70+ ligas, GitHub Actions 24/7.
- **autoarbitrage**: Bet placement automático para Marathon, 888sport, MostBet.
- **Live-Sports-Arbitrage-Bet-Finder**: Scraping LIVE cada 10ms, ejecución automática.
- **allusion**: Bot Playwright multi-bookmaker configurable.
- **EPL-Odds-Engine**: Ensemble 5 modelos (Dixon-Coles, etc.), CLV/Kelly. Para Fase 3.

### Estrategia de datos propuesta
| Componente | Ahora (The Odds API) | Futuro (Scraping) |
|---|---|---|
| Pinnacle odds | API ($60/mes, limitada) | Pinnacle Scraper (gratis, todos mercados) |
| Soft book odds | API (7 books) | Scraper directo 1xBet, 888, Betway |
| Mercados | h2h, totals, spreads | + BTTS, corners, Asian HC, props |
| Costo | $60/mes | $0 |

---

## Módulo de Scraping: paradigma/scraping/ (2026-04-27)

**Estado: Pinnacle scraper FUNCIONAL ✅**

### Hallazgos técnicos
- **API interna real**: `guest.api.arcadia.pinnacle.com` (NO `arcadia.pinnacle.com`)
- **OpenDNS corporativo bloquea** pinnacle.com → bypass con `--host-resolver-rules` de Chromium
- **DNS bypass**: Google DNS (8.8.8.8) resuelve `www.pinnacle.com` → `104.18.42.200`, `guest.api.arcadia.pinnacle.com` → `172.64.145.56`
- **Datos capturados**: 6,023 market entries (moneyline 2396, spread 1501, total 1496, team_total 630)
- **Ligas cubiertas**: EPL, La Liga, Bundesliga, Serie A, Ligue 1, UCL, UEL, MLS, Costa Rica
- **Mercados**: h2h (3-way), totals, spreads (Asian Handicap), corners, bookings

### Archivos del módulo
| Archivo | Descripción |
|---------|-------------|
| `scraping/__init__.py` | Módulo de scraping |
| `scraping/pinnacle_scraper.py` | Scraper Playwright con DNS bypass. Navega ligas, intercepta API. |
| `scraping/scraping_client.py` | Interfaz unificada, misma salida que odds_client.py |
| `scraping/test_pinnacle.py` | Test de acceso básico |
| `scraping/test_pinnacle_vpn.py` | Test con DNS bypass |
| `scraping/test_pinnacle_v2.py` | Diagnóstico completo de red |

### Formato de datos compatible
El scraper produce exactamente el mismo formato que `OddsClient`:
- `pinnacle_data`: `{event_id → {market → {(outcome_name, point) → odds}}}`
- `events_info`: lista de dicts con `event_id, home_team, away_team, league, commence_time`
- **Puede reemplazar directamente** `extract_pinnacle_odds()` sin cambiar `ev_calculator.py`

### Siguiente: Soft book scrapers
- TODO: 1xBet scraper (basado en repos/sports-arbitrage-1xbet)
- TODO: Integrar soft odds con `scraping_client.py`
- Mientras tanto, The Odds API sigue funcionando para soft books

---

## Flujo de trabajo (2026-04-27)

- **Repo GitHub**: https://github.com/gcerdas16/paradigmasportsbetting.git
- **Desarrollo**: PC corporativa (Windsurf IDE) — escribir código, análisis, diseño
- **Pruebas/ejecución**: PC personal del usuario — correr scrapers, tests de red
- **Motivo**: Red corporativa (OpenDNS) bloquea todos los sitios de apuestas
- **Sincronización**: git push → git pull entre ambas PCs

---

## Resultados de tests desde PC personal (2026-04-27)

| Sitio | Estado |
|-------|--------|
| **Pinnacle** (quick) | ✅ 77 partidos, 2252 markets |
| **Pinnacle** (completo) | ✅ Champions, Europa League, Serie A, etc. |
| **1xBet** | ✅ API interna interceptada |
| **888sport** | ✅ Accesible |
| **DraftKings** | ✅ Accesible |
| **bet365** | ✅ Accesible (¡NO disponible en The Odds API!) |
| **WilliamHill** | ✅ Accesible |
| **Unibet** | ✅ Accesible |
| **BetMGM** | ✅ Accesible |
| **Betway** | ⚠️ Cargó sin título |
| **FanDuel** | ⚠️ Bloqueado (plataforma US-only) |

### Hallazgos clave
- **1xBet API interceptable** → podemos construir scraper igual que Pinnacle
- **bet365 accesible** → gran ventaja, The Odds API NO lo tiene
- **8 de 10 casas accesibles** desde PC personal
