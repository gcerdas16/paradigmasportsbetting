# Análisis Detallado de 75 Repositorios — Proyecto Paradigma

> Generado: 2026-04-24
> Objetivo: Extraer lo mejor de cada repo para construir una herramienta de apuestas deportivas con ML.

---

## Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Clasificación por Categoría](#clasificación-por-categoría)
3. [Análisis Detallado por Repo](#análisis-detallado-por-repo)
4. [Componentes Clave Extraíbles](#componentes-clave-extraíbles)
5. [Stack Tecnológico Recomendado](#stack-tecnológico-recomendado)
6. [Top 15 Repos Más Valiosos](#top-15-repos-más-valiosos)

---

## Resumen Ejecutivo

De los 75 repos analizados, se identificaron las siguientes categorías principales:

| Categoría | Cantidad | Descripción |
|-----------|----------|-------------|
| **ML/Predicción** | 22 | Modelos de machine learning para predicción de resultados |
| **Scraping de Odds** | 12 | Scrapers para casas de apuestas (Bet365, Pinnacle, etc.) |
| **Arbitraje** | 6 | Detección de apuestas de arbitraje entre casas |
| **Data Pipeline** | 8 | Pipelines de datos, ETL y almacenamiento |
| **Plataformas/UI** | 15 | Apps web, dashboards, interfaces de usuario |
| **Trading Bots** | 5 | Bots de trading automático (Polymarket, Betfair) |
| **Análisis Estadístico** | 7 | Herramientas de análisis puro y visualización |

---

## Clasificación por Categoría

### A. ML / Predicción de Resultados (⭐ CORE)

| # | Repo | Lenguaje | Modelos ML | Deporte | Valor |
|---|------|----------|-----------|---------|-------|
| 1 | **ProphitBet-Soccer-Bets-Predictor** | Python | LogReg, DTree, RF, XGBoost, KNN, NaiveBayes, SVM, DNN+Attention | Fútbol | ⭐⭐⭐⭐⭐ |
| 2 | **NBA-Machine-Learning-Sports-Betting** | Python | XGBoost, Neural Net, LogReg | NBA | ⭐⭐⭐⭐⭐ |
| 3 | **sports-betting** (georgedouzas) | Python | Scikit-learn pipeline, ClassifierBettor, backtesting | Fútbol multi-liga | ⭐⭐⭐⭐⭐ |
| 4 | **penaltyblog** | Python/Cython | Poisson, Bivariate Poisson, Dixon-Coles, Bayesian MCMC, Hierarchical Bayesian | Fútbol | ⭐⭐⭐⭐⭐ |
| 5 | **SoccerSmartBet** | Python | LangGraph + OpenAI GPT (agente AI) | Fútbol | ⭐⭐⭐⭐⭐ |
| 6 | **SoccerBettingAgent** | TypeScript | Claude AI agents (predicción, presentación, review) | Fútbol | ⭐⭐⭐⭐ |
| 7 | **the-pitchs-edge** | Python | Dixon-Coles bivariate Poisson + Shin devig + Kelly | Fútbol 6 ligas | ⭐⭐⭐⭐⭐ |
| 8 | **Bet-on-Sibyl** | Python | Lasso Logistic Regression (L1 penalty) | Multi-deporte (NFL, NBA, MLB, NHL, Soccer, Tennis) | ⭐⭐⭐⭐ |
| 9 | **sports-betting-customloss** | Python | Neural Net con custom loss (profit-aware) en Keras/TF | Fútbol | ⭐⭐⭐⭐ |
| 10 | **mls-predictions** | Python | Ensemble: XGBoost + RF + GradientBoosting + LogReg (soft voting) | MLS | ⭐⭐⭐⭐ |
| 11 | **sports-projection** | Python | XGBoost (margin + total), walk-forward CV, injury adjustments | NBA | ⭐⭐⭐⭐ |
| 12 | **soccer-predict** | Python | Logistic Regression (Asian handicap + over/under), 5-step quant analysis | Fútbol | ⭐⭐⭐⭐ |
| 13 | **SoccerBetMLOptimizer** | Python | ML pipeline con Docker/K8s/Airflow, PostgreSQL | Fútbol | ⭐⭐⭐⭐ |
| 14 | **soccer-betting-model-codex** | Python | XGBoost + scikit-learn, Celery/Redis async, PostgreSQL | Fútbol | ⭐⭐⭐⭐ |
| 15 | **soccer-prediction-betting-system** | Python | Risk-aware stake recommendation, FastAPI backend | Fútbol | ⭐⭐⭐ |
| 16 | **Soccer-Betting** (cardchase) | Python | RandomForestRegressor + football-data.co.uk | Fútbol EU | ⭐⭐⭐ |
| 17 | **sports-betting-ai** (Accuribet) | Rust/Python | TensorFlow, 42-48 features, ~60% accuracy | Multi-deporte | ⭐⭐⭐ |
| 18 | **betsmart-pro** | Python | Poisson Distribution, Value Picker, Kelly Criterion | Fútbol (ZAR) | ⭐⭐⭐ |
| 19 | **evollution-soccer-pro** | Python | Probabilidad estadística, Fair Odds, Kelly Criterion, Value Bets | Fútbol BR | ⭐⭐⭐ |
| 20 | **ChatGPT_Sports_Betting_Bot** | JS/Python | Arbitrage Bot + Deep Learning Bot (Colab) | Multi-deporte | ⭐⭐ |
| 21 | **sports_betting_with_reinforcement_learning** | Python | Value Iteration (RL) | General | ⭐⭐ |
| 22 | **kicktipp-betbot** | Python | Prediction algorithms modulares, auto-bet | Fútbol DE | ⭐⭐ |

### B. Scraping de Odds y Datos

| # | Repo | Target | Tecnología | Valor |
|---|------|--------|-----------|-------|
| 1 | **Pinnacle_Football_Odds_Scraper** | Pinnacle (TODOS los mercados) | Playwright + API intercept | ⭐⭐⭐⭐⭐ |
| 2 | **soccerapi** | 888sport, Bet365, Unibet | Python requests + Docker | ⭐⭐⭐⭐ |
| 3 | **bet365-live-soccer-scraper** | Bet365 (live scores) | Puppeteer + Node.js + Docker | ⭐⭐⭐⭐ |
| 4 | **bet365-scraper** | Bet365 (matches) | Node.js | ⭐⭐⭐ |
| 5 | **bet365parser** | Bet365 mobile | Java | ⭐⭐⭐ |
| 6 | **bet365** (hyu96) | Bet365 | PHP/JS | ⭐⭐ |
| 7 | **smartBetika** | Betika (Kenia) | Selenium + Chrome | ⭐⭐⭐ |
| 8 | **bettingbook-cli** | Sportsmonks API | Python CLI | ⭐⭐⭐ |
| 9 | **Bets-on-Soccer-Dataset-and-Analysis** | Oddspedia | Selenium, clustering, anomaly detection | ⭐⭐⭐ |
| 10 | **soccerbet** | 500.com (odds chinas) | Python | ⭐⭐ |
| 11 | **SoccerBettingAlgorithm** | Varias fuentes | Python | ⭐⭐ |
| 12 | **sport-betting-analytics** | Playwright scraper + SQLite pipeline | Python | ⭐⭐⭐⭐ |

### C. Arbitraje y Value Bets

| # | Repo | Enfoque | Tecnología | Valor |
|---|------|---------|-----------|-------|
| 1 | **Live-Sports-Arbitrage-Bet-Finder** | Arb en vivo FanDuel/DraftKings/WilliamHill | Python + multithreading + undetected-chromedriver | ⭐⭐⭐⭐⭐ |
| 2 | **surebets** | Sure Bets multi-casa | Java + jsoup | ⭐⭐⭐ |
| 3 | **sports-betting-arbitrage-project** | Arbitraje con The Odds API | Python + Jupyter | ⭐⭐⭐ |
| 4 | **soccerbet** | Arbitraje por diferencia de odds entre casas | Python | ⭐⭐⭐ |
| 5 | **oddshub** | TUI para visualizar odds multi-deporte | Go | ⭐⭐⭐⭐ |

### D. Data Pipelines y ETL

| # | Repo | Fuentes de Datos | Stack | Valor |
|---|------|-----------------|-------|-------|
| 1 | **sports-betting-pipeline** | MLB Stats API (gratuita) | Python, CSV master files, Windows Task Scheduler | ⭐⭐⭐⭐ |
| 2 | **soccer-betting-model-codex** | Web scraping + APIs | SQLAlchemy, PostgreSQL, Celery, Redis, Alembic | ⭐⭐⭐⭐ |
| 3 | **SoccerBetMLOptimizer** | the-odds-api.com + otros | Docker, K8s, Airflow, PostgreSQL, Helm | ⭐⭐⭐⭐⭐ |
| 4 | **sport-betting-analytics** | Playwright scraper | SQLite, CLI jobs, scheduler launchd | ⭐⭐⭐⭐ |
| 5 | **Soccer-Results-Dataset-Builder** | Varias fuentes | Streamlit dashboard, predicciones | ⭐⭐⭐ |
| 6 | **Bet-on-Sibyl** | 6+ websites (Selenium, BS4) | SQLite, numpy .npz, CSV | ⭐⭐⭐ |

### E. Plataformas y UI

| # | Repo | Tipo | Stack | Valor |
|---|------|------|-------|-------|
| 1 | **ProphitBet-Soccer-Bets-Predictor** | Desktop GUI completa | Python, tkinter | ⭐⭐⭐⭐⭐ |
| 2 | **sports-betting** (georgedouzas) | GUI + CLI + API + PyPI package | Reflex (web), Python CLI, scikit-learn | ⭐⭐⭐⭐⭐ |
| 3 | **SoccerSmartBet** | Telegram Bot + PostgreSQL | Python, LangGraph, Telegram | ⭐⭐⭐⭐⭐ |
| 4 | **SoccerBettingAgent** | Web dashboard + CLI | TypeScript, Vercel, Playwright | ⭐⭐⭐⭐ |
| 5 | **the-pitchs-edge** | Streamlit dashboard | Python, Streamlit, SQLite | ⭐⭐⭐⭐ |
| 6 | **mls-predictions** | Streamlit app (5 tabs) | Python, Streamlit | ⭐⭐⭐⭐ |
| 7 | **sports-projection** | NiceGUI dashboard | Python, NiceGUI | ⭐⭐⭐⭐ |
| 8 | **oddshub** | Terminal UI (TUI) | Go, BubbleTea | ⭐⭐⭐⭐ |
| 9 | **SmartBots** | Docker platform + JupyterLab + Telegram | Python, Docker, MongoDB, RabbitMQ | ⭐⭐⭐⭐ |
| 10 | **Sport-Betting-APP-Betfair-Market** | Web app completa | PHP (CodeIgniter), MySQL, Betfair API | ⭐⭐⭐ |
| 11 | **futbets** | Web app | Next.js, TypeScript | ⭐⭐ |
| 12 | **casino-template** | Template casino | React/Next.js | ⭐⭐ |
| 13 | **KKbets-betting** | Web app betting | JS framework | ⭐⭐ |
| 14 | **friendly-bets-soccer-app** | Social betting app | React Native | ⭐⭐ |
| 15 | **reactnative_sports_betting_app** | Mobile app | React Native | ⭐⭐ |

### F. Trading Bots Automatizados

| # | Repo | Mercado | Stack | Valor |
|---|------|---------|-------|-------|
| 1 | **Polymarket-Sports-Bot** | Polymarket (tenis, basket, football) | TypeScript, Node.js, Polygon CLOB | ⭐⭐⭐⭐ |
| 2 | **SmartBots** | Betfair + Crypto + Financial | Python, Docker, MongoDB, RabbitMQ, Telegram | ⭐⭐⭐⭐ |
| 3 | **Polymarket-sports-copytrading-bot** | Polymarket copy trading | Node.js | ⭐⭐⭐ |
| 4 | **polymarket-sports-trading-bot** | Polymarket | Rust | ⭐⭐⭐ |
| 5 | **autobet** | Soccer outcome + algorithmic betting | Python | ⭐⭐ |

### G. Otros / Menor Relevancia

| # | Repo | Descripción | Valor |
|---|------|-------------|-------|
| 1 | **tyche** | App social "La Polla" colombiana (Flutter) | ⭐ |
| 2 | **SoccerSucker** | Tournament betting pool (R/Shiny + PostgreSQL) | ⭐⭐ |
| 3 | **LPOO---Soccer-Bet-Manager** | Java OOP project | ⭐ |
| 4 | **betting** | PHP/CodeIgniter betting script legacy | ⭐ |
| 5 | **maradona** | Ruby betting app | ⭐⭐ |
| 6 | **symfony4** | PHP Symfony betting site | ⭐ |
| 7 | **rust-soccer-betting-platform** | Rust platform | ⭐⭐ |
| 8 | **soccer_challenge** | Minimal | ⭐ |
| 9 | **working-sports-model** | Minimal | ⭐ |
| 10 | **sporty-clone** | Sportybet clone | ⭐ |
| 11 | **sporty-betting-settlement** | Settlement logic | ⭐⭐ |
| 12 | **Script-PHP-Web-Bluesky77** | PHP template | ⭐ |
| 13 | **sports-casino-bets** | Casino template | ⭐ |
| 14 | **sportsbook-sports-betting-crypto** | Crypto sportsbook | ⭐ |
| 15 | **online-sports-betting** | Generic site | ⭐ |
| 16 | **sports-betting-site** | Site template | ⭐ |
| 17 | **SportPredix** | Betting simulator minimal | ⭐ |
| 18 | **55sportsBet** | Basic betting app | ⭐⭐ |
| 19 | **Soccer-Bet-Sheet** | Spreadsheet approach | ⭐ |
| 20 | **sports-greeks-thesis** | Academic thesis | ⭐⭐ |

---

## Análisis Detallado por Repo (Top 20)

### 1. ProphitBet-Soccer-Bets-Predictor ⭐⭐⭐⭐⭐
- **Propósito**: App completa de predicción de apuestas de fútbol con GUI
- **Modelos ML**: LogReg, Decision Tree, Random Forest, XGBoost, KNN, Naive Bayes, SVM, DNN con Attention + Variable Selection
- **Análisis**: Descriptiva, Distribuciones, Varianza, Correlación, Boruta (feature selection), Impurity, Rules Extraction
- **Datos**: football-data.co.uk (históricos), Footystats (fixtures futuros)
- **UI**: GUI desktop (tkinter), temas claro/oscuro, exportación Excel
- **Validación**: Cross-Validation (sliding + k-fold), Holdout
- **Mercados**: 1X2, Over/Under 2.5
- **LO MEJOR**: Feature selection avanzado (Boruta), múltiples modelos, GUI completa, filtros de odds

### 2. penaltyblog ⭐⭐⭐⭐⭐
- **Propósito**: Librería production-ready para modelado de fútbol
- **Modelos**: Poisson, Bivariate Poisson, Dixon-Coles, Bayesian MCMC, Hierarchical Bayesian
- **Features**: MatchFlow (streaming JSON lazy), APIs de StatsBomb/Opta, scrapers (Understat, Club Elo, FPL)
- **Ratings**: Elo, Massey, Colley, Pi ratings
- **Odds**: Asian handicaps, over/under, implied probabilities, overround removal
- **Optimizado**: Cython para alto rendimiento
- **LO MEJOR**: Modelos estadísticos avanzados (Bayesiano jerárquico), Cython-optimized, librería PyPI lista

### 3. sports-betting (georgedouzas) ⭐⭐⭐⭐⭐
- **Propósito**: Paquete PyPI completo para crear/testear estrategias de apuestas
- **Componentes**: Dataloaders + Bettors (backtesting framework)
- **UI**: GUI (Reflex), CLI, Python API
- **Datos**: SoccerDataLoader multi-liga, multi-año
- **Backtesting**: TimeSeriesSplit, ClassifierBettor con cualquier clasificador sklearn
- **LO MEJOR**: Framework completo y extensible, backtesting robusto, GUI moderna con Reflex

### 4. SoccerSmartBet ⭐⭐⭐⭐⭐
- **Propósito**: Sistema AI de apuestas diarias (user vs AI)
- **Arquitectura**: 4 flujos (Pre-Gambling, Gambling, Post-Games, Offline Analysis)
- **AI**: OpenAI GPT-5.4 vía LangGraph con paralelismo (Send API)
- **Datos**: FotMob, football-data.org, winner.co.il, The Odds API, Open-Meteo (clima)
- **11 herramientas**: fixtures, H2H, venue, weather, odds, form, injuries, league position, recovery, team news
- **Frontend**: Telegram Bot con inline buttons
- **DB**: PostgreSQL 16
- **LO MEJOR**: Arquitectura de agentes AI completa, 11 data tools, flujo automatizado diario

### 5. the-pitchs-edge ⭐⭐⭐⭐⭐
- **Propósito**: Edge detection para 6 ligas europeas
- **Modelo**: Dixon-Coles bivariate Poisson con time decay + rho
- **Edge**: Shin devig (remoción de margen), Fractional Kelly (¼) con 2% cap
- **CLV**: Closing Line Value tracking (Pinnacle como ancla)
- **Validación**: Walk-forward temporal (nunca random k-fold)
- **Métricas**: Log loss, Brier, RPS (no accuracy)
- **Datos**: football-data.co.uk, football-data.org, The Odds API, FBref, StatsBomb
- **UI**: Streamlit dashboard
- **LO MEJOR**: Principios de modelado profesionales, CLV tracking, Shin devig

### 6. NBA-Machine-Learning-Sports-Betting ⭐⭐⭐⭐⭐
- **Propósito**: Predicción NBA con ML
- **Modelos**: XGBoost, Neural Net (TensorFlow), Logistic Regression
- **Features**: Team stats 2007-presente, matchup features, odds, days-rest
- **Output**: Expected Value, Kelly Criterion sizing
- **Pipeline**: SQLite, data fetching automático, model training scripts
- **UI**: Flask web app
- **LO MEJOR**: Pipeline completo desde datos hasta predicción + Kelly sizing

### 7. SoccerBetMLOptimizer ⭐⭐⭐⭐⭐
- **Propósito**: Predicción diaria de apuestas deportivas
- **Infraestructura**: Docker, Kubernetes (AKS), Airflow, PostgreSQL, Helm
- **Arquitectura**: Microservicios (frontend, backend, data-ingestion, pipelines)
- **Datos**: the-odds-api.com
- **LO MEJOR**: Arquitectura cloud-native production-grade, K8s, CI/CD

### 8. Pinnacle_Football_Odds_Scraper ⭐⭐⭐⭐⭐
- **Propósito**: Scraper de TODOS los mercados de Pinnacle
- **Mercados**: Moneyline, Asian Handicap, Totals, Team Totals, BTTS, Double Chance, Correct Score, HT/FT, Corners, Bookings, Player Props
- **Técnica**: Playwright + API intercept (arcadia.pinnacle.com)
- **Output**: JSON estructurado con odds decimales
- **LO MEJOR**: Captura exhaustiva de mercados, Pinnacle es la referencia del mercado

### 9. Live-Sports-Arbitrage-Bet-Finder ⭐⭐⭐⭐⭐
- **Propósito**: Arbitraje en vivo entre FanDuel, DraftKings, William Hill
- **Técnica**: Scraping cada 10ms, Nash equilibrium, multithreading
- **Auto-bet**: Calcula montos exactos y puede ejecutar apuestas
- **Bot detection**: undetected-chromedriver
- **LO MEJOR**: Velocidad extrema, arbitraje automatizado en vivo

### 10. SoccerBettingAgent ⭐⭐⭐⭐
- **Propósito**: Agente AI full-stack para +EV bets
- **AI**: Claude (Opus/Sonnet) para predicción, presentación, news y review
- **Datos**: Sofascore, Understat (xG), The Odds API, DraftKings/FanDuel (Playwright)
- **Post-game**: Review automático de predicciones vs resultados
- **UI**: Web dashboard (Vercel)
- **LO MEJOR**: Pipeline completo con AI agents, post-game learning

---

## Componentes Clave Extraíbles

### 1. Modelos de Predicción
| Componente | Mejor Fuente | Descripción |
|-----------|-------------|-------------|
| **Dixon-Coles** | `penaltyblog`, `the-pitchs-edge` | Modelo bivariate Poisson gold-standard para fútbol |
| **Bayesian MCMC** | `penaltyblog` | Posterior distributions completas para outcomes |
| **XGBoost ensemble** | `NBA-ML-Sports-Betting`, `mls-predictions` | Ensemble models con feature engineering avanzado |
| **DNN + Attention** | `ProphitBet` | Neural network con attention y variable selection |
| **Custom loss** | `sports-betting-customloss` | Loss function profit-aware para Keras/TF |
| **LangGraph AI Agent** | `SoccerSmartBet` | Orquestación de agentes AI con paralelismo |
| **Logistic Regression (Asian Handicap)** | `soccer-predict` | Modelo de regresión para handicap asiático |
| **Reinforcement Learning** | `sports_betting_with_RL` | Value iteration para bankroll management |

### 2. Fuentes de Datos
| Fuente | Repos que la usan | Costo |
|--------|-------------------|-------|
| **football-data.co.uk** | ProphitBet, the-pitchs-edge, Soccer-Betting | Gratis |
| **football-data.org** | SoccerSmartBet, mls-predictions, the-pitchs-edge | Gratis (tier) |
| **The Odds API** | SoccerSmartBet, SoccerBettingAgent, sports-projection, oddshub | Gratis (tier) |
| **FotMob** | SoccerSmartBet | Gratis (custom client) |
| **Sofascore** | SoccerBettingAgent | Scraping |
| **Understat** | SoccerBettingAgent, penaltyblog | Gratis |
| **FBref** | the-pitchs-edge, mls-predictions | Gratis |
| **StatsBomb Open** | penaltyblog, the-pitchs-edge | Gratis |
| **Pinnacle** | Pinnacle_Scraper | Scraping (Playwright) |
| **Bet365** | soccerapi, bet365-scraper, bet365-live-scraper | Scraping |
| **ESPN** | soccer-prediction-betting-system, sports-projection | Gratis |
| **American Soccer Analysis** | mls-predictions | Gratis (itscalledsoccer) |
| **MLB Stats API** | sports-betting-pipeline | Gratis |
| **NBA API** | sports-projection, NBA-ML-Sports-Betting | Gratis |
| **Open-Meteo** | SoccerSmartBet | Gratis (clima) |

### 3. Gestión de Riesgo
| Componente | Mejor Fuente |
|-----------|-------------|
| **Kelly Criterion** | the-pitchs-edge (fractional ¼ + 2% cap), evollution-soccer-pro |
| **Shin devig** (margin removal) | the-pitchs-edge |
| **CLV Tracking** | the-pitchs-edge |
| **Expected Value (EV)** | sports-projection, SoccerBettingAgent |
| **Bankroll management** | soccer-prediction-betting-system |
| **Profit Balance metric** | ProphitBet |

### 4. Feature Engineering
| Feature | Mejor Fuente |
|---------|-------------|
| **xG / xGA** | mls-predictions, SoccerBettingAgent (Understat) |
| **Elo / Pi / Massey / Colley ratings** | penaltyblog |
| **Form (rolling window)** | sports-projection, mls-predictions |
| **H2H history** | SoccerSmartBet, SoccerBettingAgent |
| **Injuries / absences** | SoccerSmartBet, sports-projection |
| **Weather / venue** | SoccerSmartBet |
| **Travel distance** | mls-predictions |
| **Surface type (turf/grass)** | mls-predictions |
| **Boruta feature selection** | ProphitBet |
| **Asian Handicap lines** | soccer-predict, Pinnacle_Scraper |

### 5. Infraestructura
| Componente | Mejor Fuente |
|-----------|-------------|
| **Docker + K8s** | SoccerBetMLOptimizer |
| **Airflow pipelines** | SoccerBetMLOptimizer |
| **PostgreSQL** | SoccerSmartBet, SoccerBetMLOptimizer |
| **SQLite** | the-pitchs-edge, sport-betting-analytics |
| **Celery + Redis** | soccer-betting-model-codex |
| **MongoDB** | SmartBots |
| **Event-driven (RabbitMQ)** | SmartBots |
| **Telegram bots** | SoccerSmartBet, SmartBots |
| **Streamlit dashboards** | the-pitchs-edge, mls-predictions, evollution-soccer-pro |

---

## Stack Tecnológico Recomendado

Basado en el análisis de los 75 repos, el stack ideal para Paradigma sería:

### Backend / Core
- **Python 3.11+** — lenguaje dominante en el ecosistema
- **FastAPI** — API REST moderna (de soccer-prediction-betting-system)
- **PostgreSQL** — DB principal (de SoccerSmartBet, SoccerBetMLOptimizer)
- **SQLite** — DB local/desarrollo (de the-pitchs-edge)
- **Celery + Redis** — tareas asíncronas (de soccer-betting-model-codex)

### ML / Modelos
- **scikit-learn** — base de modelos clásicos
- **XGBoost** — modelo principal de predicción
- **TensorFlow/Keras** — DNN + custom loss functions
- **penaltyblog** — Dixon-Coles, Poisson, Bayesian
- **LangGraph/LangChain** — orquestación de agentes AI (de SoccerSmartBet)

### Datos
- **football-data.co.uk** — datos históricos gratuitos
- **The Odds API** — odds en vivo multi-casa
- **Playwright** — scraping avanzado (Pinnacle, Bet365)
- **FotMob / Sofascore** — datos en vivo
- **Understat / FBref** — xG y métricas avanzadas

### Frontend / UI
- **Streamlit** — dashboard rápido para análisis
- **Next.js / React** — web app production
- **Telegram Bot** — notificaciones y apuestas rápidas

### Infraestructura
- **Docker** — containerización
- **GitHub Actions** — CI/CD
- **Airflow** — orquestación de pipelines (opcional)

---

## Top 15 Repos Más Valiosos

Ordenados por valor para el Proyecto Paradigma:

| Rank | Repo | Por qué |
|------|------|---------|
| 1 | **penaltyblog** | Librería PyPI con modelos estadísticos gold-standard (Dixon-Coles, Bayesian) + Cython |
| 2 | **ProphitBet-Soccer-Bets-Predictor** | App completa con 9 modelos ML, feature selection avanzado, GUI |
| 3 | **sports-betting** (georgedouzas) | Framework completo: dataloaders + bettors + backtesting + GUI |
| 4 | **SoccerSmartBet** | Arquitectura de agentes AI más sofisticada, 11 data tools, Telegram |
| 5 | **the-pitchs-edge** | Principios de modelado profesionales: Dixon-Coles, Shin devig, CLV, Kelly |
| 6 | **NBA-ML-Sports-Betting** | Pipeline completo XGBoost/NN + Kelly + Flask |
| 7 | **SoccerBetMLOptimizer** | Infraestructura cloud-native (Docker/K8s/Airflow) |
| 8 | **Pinnacle_Football_Odds_Scraper** | Scraper exhaustivo de Pinnacle (referencia del mercado) |
| 9 | **SoccerBettingAgent** | Agentes Claude AI con post-game learning |
| 10 | **Live-Sports-Arbitrage-Bet-Finder** | Arbitraje automatizado en vivo |
| 11 | **mls-predictions** | Ensemble model con features específicos (travel, turf, xG) |
| 12 | **sports-projection** | Walk-forward CV riguroso, injury adjustments |
| 13 | **sport-betting-analytics** | Pipeline E2E con SQLite, jobs CLI, scheduler |
| 14 | **sports-betting-customloss** | Custom loss profit-aware para Neural Nets |
| 15 | **soccer-predict** | 5-step quant analysis para Asian Handicap |

---

## Próximos Pasos

1. **Definir alcance inicial** — ¿Qué deportes? ¿Qué mercados? ¿Solo predicción o también ejecución?
2. **Diseñar arquitectura** — Combinar los mejores componentes identificados
3. **Implementar core** — Empezar con data pipeline + modelo Dixon-Coles + backtesting
4. **Iterar** — Agregar modelos ML, scraping de odds, UI, agentes AI
