# PARADIGMA
## Sistema Inteligente de Apuestas Deportivas con Machine Learning

**Versión**: 1.0  
**Fecha**: Abril 2026  
**Autor**: Equipo Paradigma  

---

# TABLA DE CONTENIDOS

1. [Introducción y Visión del Proyecto](#1-introducción-y-visión-del-proyecto)
2. [Problema que Resolvemos](#2-problema-que-resolvemos)
3. [Arquitectura General del Sistema](#3-arquitectura-general-del-sistema)
4. [Capa 1: Fuentes de Datos y Recolección](#4-capa-1-fuentes-de-datos-y-recolección)
5. [Capa 2: Feature Engineering](#5-capa-2-feature-engineering)
6. [Capa 3: Modelos de Predicción](#6-capa-3-modelos-de-predicción)
7. [Capa 4: Detección de Valor y Gestión de Riesgo](#7-capa-4-detección-de-valor-y-gestión-de-riesgo)
8. [Capa 5: Interfaces de Usuario](#8-capa-5-interfaces-de-usuario)
9. [Capa 6: Post-Game Learning](#9-capa-6-post-game-learning)
10. [Gestión de Bankroll](#10-gestión-de-bankroll)
11. [Validación: ¿Cómo Sabemos que Funciona?](#11-validación-cómo-sabemos-que-funciona)
12. [Stack Tecnológico](#12-stack-tecnológico)
13. [Plan de Implementación](#13-plan-de-implementación)
14. [Repositorios de Referencia](#14-repositorios-de-referencia)
15. [Glosario de Términos](#15-glosario-de-términos)

---

# 1. Introducción y Visión del Proyecto

## 1.1 ¿Qué es Paradigma?

Paradigma es un sistema integral de apuestas deportivas que utiliza machine learning, modelos estadísticos avanzados e inteligencia artificial para:

- **Predecir** resultados de partidos deportivos con mayor precisión que las casas de apuestas.
- **Detectar** apuestas con valor esperado positivo (donde las odds del mercado son más altas que las probabilidades reales).
- **Gestionar** el bankroll de forma matemáticamente óptima, protegiendo el capital a largo plazo.
- **Aprender** de cada resultado para mejorar continuamente.

## 1.2 ¿Por qué este proyecto es diferente?

El proyecto está construido a partir del análisis exhaustivo de **75 repositorios de código abierto** especializados en apuestas deportivas, machine learning y análisis estadístico. Se extrajeron las mejores ideas, modelos, patrones de arquitectura y técnicas de cada uno para crear un sistema que ningún repo individual ofrece.

Las ventajas competitivas de Paradigma son:

1. **Triple motor de predicción**: Combina modelos estadísticos (Dixon-Coles), machine learning (XGBoost, Neural Networks) y agentes AI (LangGraph + LLMs) en un ensemble ponderado.
2. **Gestión profesional de riesgo**: Implementa Kelly Criterion fraccionario, Shin devig para eliminar el margen del bookmaker, y CLV tracking para medir si realmente tenemos edge.
3. **Automatización completa**: Pipeline diario que recolecta datos, genera predicciones, envía alertas por Telegram, y después del partido revisa los resultados para mejorar.
4. **Multi-fuente de datos**: Recopila información de más de 10 fuentes incluyendo datos históricos, odds en vivo, estadísticas avanzadas (xG), lesiones, clima y noticias.

## 1.3 Alcance Inicial

- **Deportes**: Fútbol (soccer) como deporte principal. Extensible a NBA, NFL, MLB, Tennis.
- **Ligas**: Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League.
- **Mercados**: 1X2 (resultado final), Over/Under 2.5 goles, Asian Handicap, Both Teams To Score (BTTS).
- **Modo**: Predicción + recomendación. La ejecución automática de apuestas es opcional y configurable.

---

# 2. Problema que Resolvemos

## 2.1 El Problema del Apostador Promedio

El apostador promedio pierde dinero porque:

1. **Toma decisiones emocionales**: Apuesta por su equipo favorito, por "corazonadas" o por lo que dicen los comentaristas.
2. **No entiende probabilidades**: No sabe calcular si una odd ofrece valor real o no.
3. **No gestiona su bankroll**: Apuesta cantidades arbitrarias, arriesga demasiado en una sola apuesta, o "persigue pérdidas" apostando más después de perder.
4. **No tiene acceso a datos**: Las casas de apuestas tienen equipos enteros de analistas, modelos y datos. El apostador individual tiene intuición.

## 2.2 El Problema de las Casas de Apuestas

Las casas de apuestas no establecen odds basándose únicamente en probabilidades reales. Las odds reflejan:

- **Probabilidad estimada del evento**: Lo que realmente creen que va a pasar.
- **Margen de la casa (overround)**: Un porcentaje adicional (típicamente 3-8%) que garantiza ganancia para la casa.
- **Flujo de apuestas del público**: Las odds se ajustan según cuánto dinero entra en cada selección.
- **Factores de sesgo del público**: El público sobrevalora equipos grandes, partidos televisados, rachas recientes.

Esto crea **ineficiencias** — momentos donde las odds están "mal puestas" y ofrecen valor al apostador informado.

## 2.3 Nuestra Solución

Paradigma ataca cada uno de estos problemas:

| Problema | Solución de Paradigma |
|----------|----------------------|
| Decisiones emocionales | Modelos matemáticos objetivos |
| No entender probabilidades | Cálculo automático de probabilidades justas (fair odds) |
| Mala gestión de bankroll | Kelly Criterion con límites de riesgo |
| Sin acceso a datos | Pipeline automático de 10+ fuentes de datos |
| Margen de la casa | Shin devig para eliminar el overround |
| Sesgo del público | Modelos que detectan cuando el público se equivoca |

---

# 3. Arquitectura General del Sistema

## 3.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                     PARADIGMA - ARQUITECTURA                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CAPA 1: DATOS                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Históricos│ │ Odds API │ │ Scrapers │ │ Live Data│           │
│  │CSV/DB    │ │The Odds  │ │Pinnacle  │ │FotMob    │           │
│  │football- │ │API       │ │Bet365    │ │Sofascore │           │
│  │data.co.uk│ │          │ │          │ │ESPN      │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       └─────────────┴────────────┴─────────────┘                 │
│                          │                                       │
│                    ┌─────▼─────┐                                 │
│                    │PostgreSQL │                                  │
│                    └─────┬─────┘                                 │
│                          │                                       │
│  CAPA 2: FEATURES        │                                       │
│  ┌───────────────────────▼────────────────────────────┐         │
│  │ Elo ratings │ xG/xGA │ Form │ H2H │ Injuries │    │         │
│  │ Pi ratings  │ Clima  │ Rest │ Odds│ Travel   │    │         │
│  └───────────────────────┬────────────────────────────┘         │
│                          │                                       │
│  CAPA 3: PREDICCIÓN      │                                       │
│  ┌───────────┐ ┌─────────▼──┐ ┌───────────┐                    │
│  │Estadístico│ │  Machine   │ │ AI Agent  │                    │
│  │Dixon-Coles│ │  Learning  │ │ LangGraph │                    │
│  │Poisson    │ │  XGBoost   │ │ GPT/Claude│                    │
│  │Bayesian   │ │  Neural Net│ │           │                    │
│  └─────┬─────┘ └─────┬──────┘ └─────┬─────┘                    │
│        └──────────────┼──────────────┘                           │
│                 ┌─────▼─────┐                                    │
│                 │ ENSEMBLE  │                                    │
│                 └─────┬─────┘                                    │
│                       │                                          │
│  CAPA 4: VALOR/RIESGO │                                          │
│  ┌────────────────────▼───────────────────────┐                 │
│  │ Shin Devig → Value Bet → Kelly → CLV Track │                 │
│  └────────────────────┬───────────────────────┘                 │
│                       │                                          │
│  CAPA 5: UI           │                                          │
│  ┌──────────┐ ┌───────▼──┐ ┌───────────┐                       │
│  │ Telegram │ │Streamlit │ │ Web App   │                       │
│  │   Bot    │ │Dashboard │ │ (Next.js) │                       │
│  └──────────┘ └──────────┘ └───────────┘                       │
│                       │                                          │
│  CAPA 6: LEARNING     │                                          │
│  ┌────────────────────▼───────────────────────┐                 │
│  │ Resultado → Métricas → Ajuste → Retraining │                 │
│  └────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3.2 Flujo de Datos Diario

El sistema opera en un ciclo diario automatizado:

1. **00:00** — Ingesta nocturna: descarga resultados del día anterior, actualiza la base de datos.
2. **06:00** — Feature engineering: calcula ratings, forma, estadísticas rolling para todos los equipos.
3. **08:00** — Predicción matutina: genera predicciones para los partidos del día, compara con odds del mercado.
4. **09:00** — Alertas: envía picks con valor positivo por Telegram.
5. **Durante el día** — Monitoreo: actualiza odds, detecta movimientos de línea.
6. **Post-partido** — Review: compara predicciones vs resultados, actualiza métricas de rendimiento.
7. **Semanal** — Reporte: genera informe de P&L, accuracy, CLV, mejores/peores ligas.

---

# 4. Capa 1: Fuentes de Datos y Recolección

## 4.1 ¿De Dónde Viene la Data?

La calidad de las predicciones depende directamente de la calidad de los datos. Paradigma recopila datos de múltiples fuentes categorizadas en cuatro tipos:

### 4.1.1 Datos Históricos (entrenamiento de modelos)

**football-data.co.uk** — La fuente estándar de la industria
- Datos desde 1993 hasta la fecha
- 20+ ligas europeas
- Incluye: resultado, goles, tiros, córners, faltas, tarjetas
- Incluye odds de cierre de Pinnacle, Bet365, William Hill
- Formato: CSV descargable gratuitamente
- Actualización: semanal

**Uso en Paradigma**: Es el dataset principal para entrenar todos los modelos. Los datos de odds de cierre de Pinnacle son fundamentales para calcular CLV (Closing Line Value).

### 4.1.2 Odds en Tiempo Real (detección de valor)

**The Odds API** — Agregador multi-casa de apuestas
- 20+ casas de apuestas (FanDuel, DraftKings, Bet365, Pinnacle, etc.)
- Mercados: Moneyline, Spreads, Totals, Outrights
- 40+ deportes y ligas
- Formato: JSON vía REST API
- Tier gratuito: 500 requests/mes
- Tier pagado: desde $19/mes

**Uso en Paradigma**: Comparar nuestras probabilidades contra las odds de todas las casas para encontrar las mejores value bets. El sistema busca la casa que ofrece la mejor odd para cada apuesta.

**Pinnacle (Scraper con Playwright)** — La referencia del mercado
- Pinnacle es conocida como la casa de apuestas más eficiente del mundo
- Sus odds de cierre son la mejor aproximación a las probabilidades "reales"
- Mercados: Moneyline, Asian Handicap (todas las líneas), Totals, Team Totals, BTTS, Double Chance, Correct Score, HT/FT, Corners, Bookings, Player Props
- El scraper utiliza Playwright para abrir un navegador headless e interceptar las respuestas de la API interna de Pinnacle (`arcadia.pinnacle.com`)

**Uso en Paradigma**: Las odds de Pinnacle sirven como "ancla" de referencia. Si nuestro modelo dice que algo tiene 60% de probabilidad y Pinnacle implica 55%, eso es una señal fuerte de valor.

### 4.1.3 Estadísticas Avanzadas (features para modelos)

**FBref / Understat** — Estadísticas xG (Expected Goals)
- xG (Expected Goals): Mide la calidad de las oportunidades de gol. Un xG de 0.3 significa que esa oportunidad se convierte en gol el 30% de las veces históricamente.
- xGA (Expected Goals Against): Lo mismo pero para goles recibidos.
- npxG (Non-Penalty Expected Goals): xG sin penales.
- xA (Expected Assists): Probabilidad de que un pase se convierta en asistencia.
- Disponible gratuitamente vía scraping (Understat) o API (StatsBomb Open Data)

**Uso en Paradigma**: xG es mejor predictor del rendimiento futuro que los goles reales. Un equipo con 0 goles pero 3.0 xG probablemente jugó bien y fue desafortunado; un equipo con 3 goles y 0.5 xG tuvo suerte y regresará a la media.

**American Soccer Analysis (para MLS)** — Paquete Python `itscalledsoccer`
- xG, xA, Goals Added para todos los equipos y jugadores de la MLS
- Gratuito y bien mantenido
- Datos desde 2013

**football-data.org** — API de datos de fútbol
- Fixtures, resultados, clasificaciones, equipos
- 12+ competiciones
- Tier gratuito: 10 requests/minuto
- Formato: JSON REST API

### 4.1.4 Datos Contextuales (ventaja cualitativa)

**FotMob** — Datos de partidos en vivo
- Alineaciones confirmadas, formaciones tácticas
- Eventos en vivo (goles, tarjetas, sustituciones)
- Forma reciente detallada

**Open-Meteo** — Datos meteorológicos
- Temperatura, viento, lluvia, humedad para la ubicación del estadio
- Gratuito, sin API key
- El clima afecta el juego: lluvia favorece resultados bajos, viento afecta la precisión.

**ESPN / Sofascore** — Lesiones y noticias
- Estado de jugadores clave (lesionado, dudoso, suspendido)
- Las ausencias de jugadores estrella cambian significativamente las probabilidades

## 4.2 Pipeline de Recolección

```python
# Pseudo-código del pipeline diario de datos
async def daily_data_pipeline():
    # 1. Resultados de ayer
    results = await football_data_uk.fetch_latest_results()
    await db.store_results(results)
    
    # 2. Fixtures de hoy y mañana
    fixtures = await football_data_org.fetch_upcoming_fixtures()
    await db.store_fixtures(fixtures)
    
    # 3. Odds actuales de todas las casas
    for fixture in fixtures:
        odds = await the_odds_api.fetch_odds(fixture)
        await db.store_odds(odds)
    
    # 4. Odds de Pinnacle (scraper)
    pinnacle_odds = await pinnacle_scraper.fetch_all_markets(fixtures)
    await db.store_pinnacle_odds(pinnacle_odds)
    
    # 5. Estadísticas xG
    xg_data = await understat.fetch_team_xg(leagues)
    await db.store_xg(xg_data)
    
    # 6. Lesiones
    injuries = await espn.fetch_injuries(leagues)
    await db.store_injuries(injuries)
    
    # 7. Clima para cada estadio
    for fixture in fixtures:
        weather = await open_meteo.fetch_weather(fixture.stadium_coords, fixture.datetime)
        await db.store_weather(fixture.id, weather)
```

## 4.3 Esquema de Base de Datos

```sql
-- Tablas principales
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    league_id INTEGER REFERENCES leagues(id),
    stadium_lat FLOAT, stadium_lon FLOAT
);

CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    date DATE, kickoff_time TIME,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    league_id INTEGER REFERENCES leagues(id),
    home_goals INTEGER, away_goals INTEGER,
    status VARCHAR(20) -- scheduled, live, finished
);

CREATE TABLE odds_snapshots (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    bookmaker VARCHAR(50),
    market VARCHAR(20), -- 1x2, ou25, ah, btts
    selection VARCHAR(20), -- home, draw, away, over, under
    line FLOAT, -- para asian handicap y over/under
    price FLOAT, -- odds decimales
    captured_at TIMESTAMP
);

CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    model_name VARCHAR(50),
    prob_home FLOAT, prob_draw FLOAT, prob_away FLOAT,
    prob_over25 FLOAT, prob_under25 FLOAT,
    recommended_bet VARCHAR(50),
    edge_pct FLOAT, kelly_fraction FLOAT,
    created_at TIMESTAMP
);

CREATE TABLE bets (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    prediction_id INTEGER REFERENCES predictions(id),
    market VARCHAR(20), selection VARCHAR(20),
    bookmaker VARCHAR(50), odds_placed FLOAT,
    stake FLOAT, stake_pct FLOAT,
    result VARCHAR(20), -- win, loss, push, pending
    pnl FLOAT,
    placed_at TIMESTAMP
);

CREATE TABLE team_stats (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    season VARCHAR(10),
    xg FLOAT, xga FLOAT, npxg FLOAT,
    goals_scored INTEGER, goals_conceded INTEGER,
    elo_rating FLOAT, form_points FLOAT,
    updated_at TIMESTAMP
);
```

---

# 5. Capa 2: Feature Engineering

## 5.1 ¿Qué es Feature Engineering?

Feature engineering es el proceso de transformar datos crudos en "features" (variables) que los modelos de machine learning pueden usar para hacer predicciones. Es la parte más importante del pipeline — un modelo mediocre con excelentes features supera a un modelo sofisticado con features pobres.

## 5.2 Features del Sistema

### 5.2.1 Ratings de Equipo

**Elo Rating** (de `penaltyblog`)
- Sistema de rating que sube cuando ganás y baja cuando perdés
- La magnitud del cambio depende de la fuerza del rival
- Un equipo con Elo 1600 vs uno con 1400 tiene ~69% de probabilidad de ganar
- Se calcula con: `Elo_nuevo = Elo_viejo + K × (Resultado - Esperado)`
- K = factor de ajuste (típicamente 20-40 en fútbol)

**Pi Rating** (de `penaltyblog`)
- Rating que separa rendimiento ofensivo y defensivo
- Cada equipo tiene dos números: uno de ataque y uno de defensa
- Permite detectar equipos que atacan bien pero defienden mal (y viceversa)

**SRS (Simple Rating System)** (de `sports-projection`)
- Rating que considera la fuerza del calendario
- Un equipo que gana contra rivales fuertes sube más que uno que gana contra rivales débiles
- Se calcula resolviendo un sistema de ecuaciones lineales

### 5.2.2 Forma Reciente

```
Para cada equipo, se calculan rolling windows de los últimos 5 y 10 partidos:
- Puntos por partido (3 victoria, 1 empate, 0 derrota)
- Goles a favor promedio
- Goles en contra promedio  
- xG promedio (si disponible)
- xGA promedio (si disponible)
- Tasa de victorias
- Tasa de clean sheets (partidos sin recibir goles)

Se calcula por separado para:
- Todos los partidos
- Solo partidos como local
- Solo partidos como visitante
```

### 5.2.3 Head-to-Head (H2H)

- Últimos 5-10 enfrentamientos entre los mismos equipos
- Goles promedio en esos enfrentamientos
- Tendencia (¿el equipo local domina el H2H?)

### 5.2.4 Contexto del Partido

- **Días de descanso** desde el último partido (3+ días es bueno, 2 o menos es malo)
- **Importancia del partido**: ¿Pelea por el título? ¿Pelea por descenso? ¿Ya clasificado?
- **Local vs Visitante**: La ventaja de local es real (~45% victorias local vs ~28% visitante en la Premier League)
- **Distancia de viaje** del equipo visitante (relevante especialmente en MLS y copas internacionales)
- **Tipo de superficie**: Césped natural vs artificial (algunos equipos rinden peor en artificial)

### 5.2.5 Información del Mercado

- **Odds de apertura** de Pinnacle
- **Odds actuales** de Pinnacle
- **Movimiento de línea**: Si las odds bajan, significa que dinero inteligente entró en esa selección
- **Asian Handicap line**: La línea del handicap asiático es la mejor medida de qué tan favorito es un equipo

### 5.2.6 Lesiones y Ausencias

- Número de jugadores titulares ausentes
- "Puntos ausentes" ponderados por importancia del jugador
- El impacto se mide en puntos de margen esperado (de `sports-projection`)

### 5.2.7 Clima

- Temperatura, lluvia, viento en el estadio
- Partidos con lluvia fuerte tienden a tener menos goles
- Viento fuerte afecta pases largos y centros

## 5.3 Diferenciadores de Features (diferencias entre equipos)

Para cada par de features (ej. Elo de ambos equipos), se calcula:

```
delta_elo = elo_home - elo_away
delta_form = form_home - form_away
delta_xg = xg_home - xg_away
ratio_attack = attack_home / defense_away
```

Estos "deltas" son frecuentemente más informativos que los valores absolutos.

---

# 6. Capa 3: Modelos de Predicción

## 6.1 Enfoque Triple

Paradigma no depende de un solo modelo. Usa tres enfoques complementarios que se combinan en un ensemble:

### Motor 1: Modelos Estadísticos

### 6.2 Dixon-Coles (Modelo Principal)

**Origen**: Paper académico de Dixon & Coles, 1997. Implementación de `penaltyblog` (optimizada con Cython).

**¿Qué es?** Un modelo matemático diseñado específicamente para fútbol que calcula la probabilidad de cada marcador posible (0-0, 1-0, 0-1, 1-1, 2-0, ...).

**¿Cómo funciona?**

1. **Asume que los goles siguen una distribución de Poisson**: Si un equipo tiene un promedio de 1.5 goles por partido, la distribución de Poisson dice:
   - P(0 goles) = 22.3%
   - P(1 gol) = 33.5%
   - P(2 goles) = 25.1%
   - P(3 goles) = 12.6%
   - P(4+ goles) = 6.5%

2. **Estima parámetros de ataque y defensa para cada equipo**: Cada equipo tiene un parámetro de "fuerza de ataque" (α) y uno de "debilidad defensiva" (β). Los goles esperados del equipo local se calculan como:

   ```
   λ_local = exp(ventaja_local + α_local + β_visitante)
   λ_visitante = exp(α_visitante + β_local)
   ```

   Donde:
   - `α_local` = fuerza de ataque del equipo local (más alto = mejor atacando)
   - `β_visitante` = debilidad defensiva del visitante (más alto = peor defendiendo)
   - `ventaja_local` ≈ 0.25 (equivale a ~0.3 goles extra por jugar en casa)

3. **Corrección de Dixon-Coles (parámetro ρ)**: El Poisson estándar asume que los goles de ambos equipos son independientes. Pero en la realidad hay correlación en marcadores bajos: si un partido va 0-0, ambos equipos juegan más defensivamente. El parámetro ρ (rho) ajusta las probabilidades para marcadores 0-0, 1-0, 0-1 y 1-1.

4. **Time decay (ξ)**: Los partidos recientes importan más que los antiguos. Se aplica un peso exponencial decreciente:
   
   ```
   peso = exp(-ξ × días_desde_partido)
   ```
   
   Con ξ = 0.0019 (half-life de ~365 días), un partido de hace 6 meses tiene ~70% del peso de uno de hoy.

5. **Output**: Una matriz de probabilidades para cada marcador posible:

   ```
            Visitante: 0    1      2      3
   Local: 0           5.2%  8.1%   6.3%   3.2%
   Local: 1          10.4% 16.2%  12.7%   6.5%
   Local: 2          10.4% 16.2%  12.7%   6.5%
   Local: 3           6.9% 10.8%   8.5%   4.3%
   ```

   De esta matriz se derivan:
   - P(victoria local) = suma de todas las celdas donde goles_local > goles_visitante
   - P(empate) = suma de la diagonal
   - P(victoria visitante) = suma de celdas donde goles_visitante > goles_local
   - P(over 2.5) = suma de celdas donde total > 2.5
   - P(BTTS) = suma de celdas donde ambos > 0

### 6.3 Poisson Bivariado (Modelo Complementario)

Similar a Dixon-Coles pero modela la correlación entre goles de ambos equipos directamente usando un término de covarianza, en lugar del ajuste discreto de ρ.

### 6.4 Bayesiano MCMC (Modelo de Incertidumbre)

En lugar de dar un solo número ("60% de probabilidad"), el modelo bayesiano genera una **distribución posterior** completa: "entre 55% y 65% con 90% de confianza". Esto es crucial para:
- Saber cuándo estamos seguros vs cuándo hay mucha incertidumbre
- Ajustar el tamaño de apuesta según la confianza

### Motor 2: Machine Learning

### 6.5 XGBoost (Modelo ML Principal)

**Origen**: Implementaciones de `ProphitBet`, `NBA-ML-Sports-Betting`, `mls-predictions`.

**¿Qué es?** XGBoost (eXtreme Gradient Boosting) es un algoritmo que crea cientos de "árboles de decisión" pequeños, donde cada árbol nuevo corrige los errores del anterior.

**¿Por qué XGBoost?**
- Es el algoritmo #1 en competencias de machine learning con datos tabulares
- Maneja bien features heterogéneos (numéricos, categóricos)
- Es rápido de entrenar y predecir
- Tiene regularización incorporada (evita overfitting)
- Permite ver qué features son más importantes

**Hiperparámetros clave** (de `ProphitBet`):
- `n_estimators`: 50-500 árboles
- `max_depth`: 1-15 niveles de profundidad
- `learning_rate`: 0.005-0.5 (qué tan rápido aprende)
- `min_child_weight`: 1-5 (mínimo de datos por hoja)
- `reg_lambda`: 0.1-2.0 (regularización L2)
- `reg_alpha`: 0.0-1.0 (regularización L1)

**Optimización de hiperparámetros**: Se usa Optuna (framework de optimización bayesiana) para encontrar los mejores hiperparámetros automáticamente, probando diferentes combinaciones y midiendo el rendimiento con validación cruzada.

### 6.6 Ensemble (Combinación de Modelos ML)

**Origen**: `mls-predictions` usa soft voting ensemble.

Se combinan múltiples modelos con voto ponderado:

```
P_final = w1 × P_XGBoost + w2 × P_RandomForest + w3 × P_GradientBoosting + w4 × P_LogReg
```

Los pesos (w1, w2, w3, w4) se optimizan en el conjunto de validación.

### 6.7 Neural Network con Custom Loss

**Origen**: `sports-betting-customloss` y `ProphitBet`.

Una red neuronal estándar optimiza accuracy (% de predicciones correctas). Pero en apuestas, accuracy no es lo que importa — lo que importa es **profit**. Un modelo con 55% de accuracy puede ser más rentable que uno con 65% si acierta las apuestas con mejores odds.

La custom loss function incorpora las odds directamente:

```
loss = -Σ (resultado_real × log(p_predicha) × odds_disponible)
```

Esto hace que el modelo aprenda a ser más preciso específicamente en los partidos donde hay mejor valor.

### Motor 3: Agentes AI

### 6.8 LangGraph Agent

**Origen**: `SoccerSmartBet`.

Un agente AI orquestado con LangGraph que analiza información cualitativa que los modelos numéricos no pueden capturar:

- Lee noticias sobre lesiones de último minuto
- Analiza declaraciones del entrenador
- Evalúa la importancia táctica del partido
- Considera factores como rivalidades, presión mediática, rotaciones

El agente tiene acceso a 11 herramientas de datos:
1. Fixtures del día
2. Historial H2H
3. Datos del venue/estadio
4. Clima
5. Odds actuales
6. Forma reciente
7. Lesiones/suspensiones
8. Posición en la liga
9. Días de descanso/recuperación
10. Noticias del equipo
11. Estadísticas avanzadas

### 6.9 El Meta-Ensemble

Los tres motores se combinan:

```
P_final = w_stat × P_Dixon_Coles + w_ml × P_XGBoost_Ensemble + w_ai × P_AI_Agent
```

Los pesos se ajustan dinámicamente basándose en el rendimiento reciente de cada motor. Si el modelo estadístico ha acertado más últimamente, su peso sube.

---

# 7. Capa 4: Detección de Valor y Gestión de Riesgo

## 7.1 ¿Qué es una "Value Bet"?

Una value bet es una apuesta donde **la probabilidad real del evento es mayor que la probabilidad implícita en las odds**. Es el concepto más importante en apuestas profesionales.

**Ejemplo**: Si nuestro modelo estima que Liverpool tiene 60% de probabilidad de ganar, y las odds son 2.00 (implican 50%), hay valor:

```
EV = 0.60 × 2.00 - 1.0 = +0.20 = +20% de retorno esperado
```

A largo plazo, apostar consistentemente con EV positivo genera ganancia.

## 7.2 Shin Devig — Eliminación del Margen

**Origen**: `the-pitchs-edge`

Las odds de las casas de apuestas incluyen un margen (overround). Por ejemplo, para un partido:

```
Odds: Local 2.10, Empate 3.40, Visitante 3.60
Probabilidades implícitas: 47.6% + 29.4% + 27.8% = 104.8%
El 4.8% extra es el margen de la casa.
```

Para comparar nuestras probabilidades con las del mercado, necesitamos **eliminar ese margen**. El método de Shin es el más preciso porque:

1. No asume que el margen se distribuye uniformemente entre todos los resultados
2. Reconoce que los eventos menos probables tienen proporcionalmente más margen ("favorite-longshot bias")

La fórmula de Shin resuelve para `z` (proporción de "insiders") tal que:

```
p_i(z) = (√(z² + 4(1-z) × q_i² / S) - z) / (2(1-z))
```

donde `q_i = 1/odds_i` y `S = Σq_i`. Se resuelve por bisección hasta que `Σp_i(z) = 1`.

## 7.3 Expected Value (EV)

```
EV = P_modelo × Odds - 1

Si EV > 0 → Apostar (hay valor)
Si EV ≤ 0 → No apostar (no hay valor)
```

El umbral mínimo en Paradigma es **EV > 5%** (configurable). Esto significa que solo apostamos cuando el edge es suficientemente grande para compensar la incertidumbre del modelo.

## 7.4 CLV (Closing Line Value) — La Métrica que Importa

**Origen**: `the-pitchs-edge`

CLV es la métrica más importante para saber si realmente tenemos edge:

```
CLV = (Odds_cuando_apostamos / Odds_al_cierre) - 1
```

Si apostaste a odds 2.10 y las odds cerraron en 1.95:
```
CLV = (2.10 / 1.95) - 1 = +7.7%
```

Esto significa que obtuviste mejores odds que el mercado al cierre. Si tu CLV promedio es positivo sobre cientos de apuestas, **sos rentable a largo plazo**, independientemente de los resultados a corto plazo.

Pinnacle cierra es la referencia porque es la casa más eficiente del mundo — sus odds de cierre son la mejor aproximación a las probabilidades "reales".

---

# 8. Capa 5: Interfaces de Usuario

## 8.1 Telegram Bot (Día a Día)

- Recibe alertas de picks con valor
- Muestra: partido, mercado, odd recomendada, EV%, stake recomendado
- Botones inline para confirmar/rechazar apuestas
- Resumen de P&L al final del día
- Comandos: `/picks`, `/bankroll`, `/stats`, `/report`

## 8.2 Streamlit Dashboard (Análisis)

- Tab 1: Predicciones del día con probabilidades y odds
- Tab 2: Backtesting histórico de estrategias
- Tab 3: Rendimiento por liga, modelo, mercado
- Tab 4: CLV tracking
- Tab 5: Configuración de modelos y parámetros

## 8.3 Web App (Producción, Futuro)

- Next.js con TailwindCSS
- Login, historial de apuestas, configuración avanzada
- Dashboard visual con gráficos de rendimiento

---

# 9. Capa 6: Post-Game Learning

## 9.1 Review Automático

Después de cada partido:

1. **Comparar predicción vs resultado**: ¿Acertamos el resultado? ¿Por cuánto nos equivocamos en probabilidades?
2. **Calcular métricas**: Log loss, Brier score, RPS (no accuracy — estas métricas miden la calidad de las probabilidades, no solo si acertaste).
3. **Registrar CLV**: ¿Las odds a las que apostamos eran mejores que las de cierre?
4. **Actualizar P&L**: ¿Cuánto ganamos/perdimos?

## 9.2 Ajuste de Pesos del Ensemble

Si un motor predice mejor que los otros consistentemente, su peso sube:

```python
# Después de cada semana:
for motor in [estadistico, ml, ai]:
    rendimiento = calcular_brier_score(motor.predicciones_semana)
    motor.peso = 1.0 / rendimiento  # Menor Brier = mejor = más peso
normalizar_pesos([estadistico, ml, ai])
```

## 9.3 Re-entrenamiento

- **Modelos ML**: Se re-entrenan mensualmente con los nuevos datos
- **Dixon-Coles**: Se re-ajusta semanalmente (es rápido gracias a Cython)
- **Ratings Elo**: Se actualizan después de cada partido

---

# 10. Gestión de Bankroll

## 10.1 Kelly Criterion

**Origen**: `the-pitchs-edge`

El Kelly Criterion es una fórmula matemática que calcula el **tamaño óptimo de apuesta** que maximiza el crecimiento del bankroll a largo plazo:

```
f* = (p × b - q) / b
```

Donde:
- `f*` = fracción del bankroll a apostar
- `p` = probabilidad estimada de ganar
- `b` = odds - 1 (ganancia neta por unidad apostada)
- `q` = 1 - p (probabilidad de perder)

**Ejemplo**: Si estimamos 60% de probabilidad y las odds son 2.0:
```
f* = (0.60 × 1.0 - 0.40) / 1.0 = 0.20 = 20%
```

### 10.2 Kelly Fraccionario (Protección)

Kelly completo (20%) es demasiado agresivo. Las estimaciones de probabilidad tienen error, y apostar 20% del bankroll en un partido es arriesgado. Paradigma usa:

```
f_real = f* × escala    (donde escala = 0.25, es decir Kelly ÷ 4)
f_real = min(f_real, cap)  (donde cap = 0.02, es decir máximo 2% del bankroll)
```

Con el ejemplo anterior:
```
f_real = 0.20 × 0.25 = 0.05 = 5%
f_real = min(0.05, 0.02) = 0.02 = 2%

Si bankroll = $1,000 → Apostar $20
```

### 10.3 Reglas de Bankroll

1. **Máximo 2% por apuesta**: Nunca arriesgar más del 2% del bankroll en una sola apuesta.
2. **Máximo 10% por día**: Nunca tener más del 10% del bankroll en juego simultáneamente.
3. **Recalcular bankroll diariamente**: El stake se basa en el bankroll actual, no en el inicial. Si ganás, apostás más. Si perdés, apostás menos. Esto protege contra rachas negativas.
4. **Stop-loss semanal**: Si el bankroll baja más del 15% en una semana, pausar apuestas y revisar los modelos.

---

# 11. Validación: ¿Cómo Sabemos que Funciona?

## 11.1 Validación Temporal (Walk-Forward)

**NUNCA** usar validación cruzada aleatoria (random k-fold) con datos deportivos. Los datos tienen orden temporal — usar datos futuros para predecir el pasado es trampa.

Walk-forward validation:
```
Entrenamiento: Temporadas 2018-2022
Validación:    Temporada 2023
Test:          Temporada 2024 (nunca se toca hasta el final)
```

Se mueve la ventana hacia adelante:
```
Fold 1: Train 2018-2020, Test 2021
Fold 2: Train 2018-2021, Test 2022
Fold 3: Train 2018-2022, Test 2023
```

## 11.2 Métricas de Evaluación

**NO usar accuracy.** Un modelo que siempre predice "victoria local" tiene ~45% de accuracy en la Premier League. Las métricas correctas son:

| Métrica | Qué mide | Valor ideal |
|---------|----------|-------------|
| **Log Loss** | Qué tan calibradas están las probabilidades | < 1.0 (para 1X2) |
| **Brier Score** | Error cuadrático de probabilidades | < 0.20 |
| **RPS (Ranked Probability Score)** | Calidad de distribución de probabilidades completa | < 0.20 |
| **ROI (Return on Investment)** | Retorno sobre inversión | > 0% |
| **CLV promedio** | ¿Obtenemos mejores odds que el cierre? | > 0% |
| **Yield** | Ganancia por unidad apostada | > 2% |

## 11.3 Backtesting

Antes de apostar dinero real, se hace backtesting sobre datos históricos:

```python
# Pseudo-código de backtesting
bankroll = 1000
for match in historico_2023_2024:
    # Generar predicción con datos disponibles ANTES del partido
    prob = modelo.predict(features_pre_partido)
    
    # Obtener odds de cierre histórico
    odds = match.odds_cierre_pinnacle
    
    # Calcular si hay valor
    ev = prob * odds - 1
    if ev > 0.05:
        stake = kelly(prob, odds, scale=0.25, cap=0.02) * bankroll
        if match.resultado == prediccion:
            bankroll += stake * (odds - 1)
        else:
            bankroll -= stake

print(f"Bankroll final: ${bankroll}")
print(f"ROI: {(bankroll - 1000) / total_apostado * 100}%")
```

## 11.4 Señales de Alerta

El sistema monitorea estas señales para detectar problemas:

- **CLV promedio negativo**: El modelo no está encontrando valor real
- **Drawdown > 20%**: La estrategia está en una racha perdedora significativa
- **Log loss peor que las odds de cierre**: El modelo predice peor que Pinnacle
- **Una liga consistentemente mala**: Desactivar modelos para esa liga

---

# 12. Stack Tecnológico

## 12.1 Backend

| Tecnología | Propósito | Justificación |
|-----------|-----------|---------------|
| **Python 3.11+** | Lenguaje principal | Dominante en ML, abundancia de librerías |
| **FastAPI** | API REST | Moderno, asíncrono, documentación automática |
| **PostgreSQL 16** | Base de datos principal | Robusto, escalable, buen soporte JSON |
| **SQLite** | DB local/desarrollo | Simple, sin servidor, ideal para prototipos |
| **Celery + Redis** | Tareas asíncronas | Ejecutar scraping y modelos en background |
| **Alembic** | Migraciones de DB | Versionado del esquema de base de datos |

## 12.2 Machine Learning

| Tecnología | Propósito |
|-----------|-----------|
| **scikit-learn** | Pipeline ML, preprocesamiento, métricas |
| **XGBoost** | Modelo principal de clasificación |
| **TensorFlow/Keras** | Redes neuronales con custom loss |
| **penaltyblog** | Dixon-Coles, Poisson, Bayesian MCMC |
| **Optuna** | Optimización de hiperparámetros |
| **LangGraph + OpenAI/Claude** | Agentes AI |

## 12.3 Datos y Scraping

| Tecnología | Propósito |
|-----------|-----------|
| **Playwright** | Scraping avanzado (Pinnacle, Bet365) |
| **httpx / requests** | API calls a The Odds API, football-data.org |
| **pandas** | Manipulación de datos |
| **numpy** | Cálculos numéricos |

## 12.4 Frontend

| Tecnología | Propósito |
|-----------|-----------|
| **Streamlit** | Dashboard de análisis rápido |
| **python-telegram-bot** | Bot de Telegram |
| **Next.js + TailwindCSS** | Web app production (futuro) |

## 12.5 Infraestructura

| Tecnología | Propósito |
|-----------|-----------|
| **Docker** | Containerización |
| **GitHub Actions** | CI/CD |
| **APScheduler / cron** | Scheduler de tareas diarias |

---

# 13. Plan de Implementación

## Fase 1: Fundación (Semanas 1-2)

- Configurar PostgreSQL + esquema
- Implementar descarga de datos de football-data.co.uk
- Implementar conector de The Odds API
- Implementar modelo Dixon-Coles (usando penaltyblog)
- Implementar backtesting básico
- **Entregable**: Modelo que genera predicciones para la Premier League

## Fase 2: Machine Learning (Semanas 3-4)

- Feature engineering pipeline completo
- Modelo XGBoost con Optuna tuning
- Ensemble (Dixon-Coles + XGBoost)
- Kelly Criterion + Shin devig
- Dashboard Streamlit básico
- **Entregable**: Sistema que detecta value bets con gestión de riesgo

## Fase 3: Automatización (Semanas 5-6)

- Pipeline diario automatizado
- Bot de Telegram (picks diarios)
- CLV tracking
- Post-game review automático
- Scraper de Pinnacle (Playwright)
- Multi-liga (La Liga, Serie A, Bundesliga, Ligue 1)
- **Entregable**: Sistema automatizado que envía picks diarios

## Fase 4: AI + Producción (Semanas 7-8)

- Agente AI con LangGraph
- Neural Network con custom loss
- Web app completa
- Extensión a otros deportes (NBA)
- Reportes semanales automáticos
- Docker deployment
- **Entregable**: Sistema completo en producción

---

# 14. Repositorios de Referencia

Los 15 repos más valiosos de los que se extrajeron ideas, arquitectura y código:

| # | Repo | Lo que tomamos |
|---|------|---------------|
| 1 | **penaltyblog** | Modelos Dixon-Coles, Poisson, Bayesiano; ratings Elo/Pi/Massey; Cython optimization |
| 2 | **ProphitBet-Soccer-Bets-Predictor** | 9 modelos ML, Boruta feature selection, Optuna tuning, sliding cross-validation |
| 3 | **sports-betting** (georgedouzas) | Framework de backtesting, dataloaders, ClassifierBettor pattern |
| 4 | **SoccerSmartBet** | Arquitectura LangGraph agent, 11 data tools, Telegram bot, flujo diario |
| 5 | **the-pitchs-edge** | Shin devig, Kelly fraccionario, CLV tracking, walk-forward validation, principios profesionales |
| 6 | **NBA-ML-Sports-Betting** | Pipeline XGBoost + Neural Net, Kelly sizing, SQLite storage |
| 7 | **SoccerBetMLOptimizer** | Docker/K8s architecture, Airflow pipelines, PostgreSQL |
| 8 | **Pinnacle_Football_Odds_Scraper** | Playwright API intercept, mercados exhaustivos de Pinnacle |
| 9 | **SoccerBettingAgent** | Agentes Claude AI, post-game review, Playwright scraping |
| 10 | **Live-Sports-Arbitrage-Bet-Finder** | Arbitraje en vivo, multithreading, undetected-chromedriver |
| 11 | **mls-predictions** | Ensemble model, features MLS-específicos, Streamlit 5-tab app |
| 12 | **sports-projection** | Walk-forward CV riguroso, injury adjustments, NiceGUI dashboard |
| 13 | **sport-betting-analytics** | Pipeline E2E con SQLite, CLI jobs, scheduler automático |
| 14 | **sports-betting-customloss** | Custom loss function profit-aware para Keras/TensorFlow |
| 15 | **soccer-predict** | 5-step quantitative analysis para Asian Handicap + over/under |

---

# 15. Glosario de Términos

| Término | Definición |
|---------|-----------|
| **1X2** | Mercado de resultado: 1=local gana, X=empate, 2=visitante gana |
| **Asian Handicap (AH)** | Handicap que elimina la posibilidad de empate. Ej: -1.5 significa que el equipo debe ganar por 2+ goles |
| **Over/Under (O/U)** | Mercado de total de goles. Ej: Over 2.5 = 3 o más goles en el partido |
| **BTTS** | Both Teams To Score — ¿Ambos equipos marcan al menos un gol? |
| **Odds decimales** | Multiplicador de la apuesta. Odds 2.50 × $10 apostados = $25 retorno ($15 ganancia) |
| **Overround** | El margen de la casa. Si las probabilidades implícitas suman 105%, el overround es 5% |
| **Value Bet** | Apuesta donde nuestra probabilidad estimada es mayor que la implícita en las odds |
| **EV (Expected Value)** | Valor esperado. EV = P × Odds - 1. Positivo = buena apuesta a largo plazo |
| **Kelly Criterion** | Fórmula para calcular el tamaño óptimo de apuesta |
| **CLV (Closing Line Value)** | Diferencia entre las odds a las que apostamos y las odds de cierre |
| **xG (Expected Goals)** | Métrica que mide la calidad de las oportunidades de gol |
| **Dixon-Coles** | Modelo estadístico de Poisson ajustado para fútbol |
| **Shin devig** | Método para eliminar el margen del bookmaker de las odds |
| **Walk-forward** | Método de validación temporal que respeta el orden cronológico |
| **Brier Score** | Métrica de calibración de probabilidades (0=perfecto, 1=peor) |
| **Log Loss** | Penaliza probabilidades confiadas pero incorrectas |
| **Bankroll** | Capital total disponible para apostar |
| **ROI** | Return on Investment = Ganancias / Total apostado × 100 |
| **Edge** | Ventaja sobre el mercado |
| **Ensemble** | Combinación de múltiples modelos para mejor predicción |
| **Feature** | Variable de entrada para un modelo ML |
| **Backtesting** | Probar una estrategia con datos históricos |

---

*Documento generado para el Proyecto Paradigma. Todos los modelos, fórmulas y arquitecturas descritos están basados en implementaciones reales de los 75 repositorios analizados.*
