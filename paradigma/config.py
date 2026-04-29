import os
from dotenv import load_dotenv

load_dotenv()


# ─── API Keys ───────────────────────────────────────────────
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///paradigma.db")

# ─── The Odds API ───────────────────────────────────────────
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# Regiones (fallback si no se usa bookmakers param)
ODDS_REGIONS = ["eu", "us", "uk", "au"]

# Mercados soportados por The Odds API
ODDS_MARKETS = ["h2h", "totals", "spreads"]

# ─── Bookmakers objetivo (param bookmakers reduce costo 4x) ────
# Usar param 'bookmakers' en vez de 'regions' → 6 books = 1 región equiv.
# Hasta 10 bookmakers cuentan como 1 región.
TARGET_BOOKMAKERS = [
    "pinnacle",       # Referencia sharp (SIEMPRE incluir)
    "onexbet",        # 1xBet ✓ LATAM
    "marathonbet",    # Marathon Bet ✓ LATAM
    "coolbet",        # Coolbet ✓ (odds útiles)
    "sport888",       # 888sport ✓ (odds útiles)
    "betway",         # Betway ✓ LATAM
    "unibet",         # Unibet ✓ (odds útiles)
    "leovegas",       # LeoVegas ✓ (odds útiles)
    "nordicbet",      # Nordic Bet ✓ (odds útiles)
    "bovada",         # Bovada ✓ LATAM — reemplaza betsson
    # ── 10 bookmakers = 1 región = costo mínimo ──
    # Agregar más → 2 regiones → doble costo
    # ❌ No disponibles en API: betsafe, melbet, 20bet, bet365
]

# Exchanges a EXCLUIR de casas blandas (no son bookmakers tradicionales)
EXCHANGE_BOOK_KEYS = {
    "betfair_ex_eu",
    "betfair_ex_uk",
    "betfair_ex_au",
    "betfair",
    "matchbook",
    "smarkets",
    "betdaq",
}

# Deportes a monitorear (multi-deporte para acelerar validación)
# Usar None para todos los deportes activos
SPORTS = [
    # --- Fútbol (3-way) --- genera la mayoría de señales
    "soccer_epl",               # Premier League
    "soccer_spain_la_liga",     # La Liga
    "soccer_germany_bundesliga",# Bundesliga
    "soccer_italy_serie_a",     # Serie A
    "soccer_france_ligue_one",  # Ligue 1
    "soccer_uefa_champs_league",# Champions League
    # --- Basketball (2-way) ---
    "basketball_nba",           # NBA
    # ── Presupuesto: 7 deportes × 3 markets × 1 región = 21 créditos/scan
    # ── A 30 min: 1,008 créditos/día → 20K duran ~20 días
]

# ─── Pinnacle ───────────────────────────────────────────────
PINNACLE_BOOK_KEY = "pinnacle"

# ─── Umbrales de apuesta ────────────────────────────────────
MIN_EV_PERCENT = 5.0            # Solo apostar si EV > 5%
KELLY_FRACTION = 0.25           # Kelly ÷4 (conservador)
MAX_KELLY_PERCENT = 2.0         # Cap máximo 2% del bankroll por apuesta
MAX_DAILY_EXPOSURE = 10.0       # Máximo 10% del bankroll apostado por día
MAX_TOTAL_EXPOSURE = 30.0       # Máximo 30% del bankroll abierto al mismo tiempo
STOP_LOSS_WEEKLY_PERCENT = 15.0 # Pausar si bankroll baja 15% en una semana

# Bankroll inicial (paper trading)
INITIAL_BANKROLL = 500.0

# ─── Filtros adicionales ────────────────────────────────────
MIN_ODDS_DECIMAL = 1.30         # No apostar a odds < 1.30 (muy bajas)
MAX_ODDS_DECIMAL = 10.0         # No apostar a odds > 10.0 (muy volátiles)
MIN_BOOKMAKERS = 3              # Mínimo 3 casas con el mercado para confiar

# ─── Scanner ────────────────────────────────────────────────
SCAN_INTERVAL_MINUTES = 45      # Cada 45 min (20K créditos duran ~30 días)
ODDS_FORMAT = "decimal"         # Formato de odds (decimal para cálculos)
USE_BOOKMAKERS_PARAM = True     # True = usar param bookmakers (4x más barato)

# ─── Paper Trading ──────────────────────────────────────────
PAPER_TRADING = True            # True = no apostar dinero real
MIN_BETS_TO_VALIDATE = 200      # Mínimo de apuestas antes de evaluar

# ─── URLs de casas de apuestas ──────────────────────────────
# Mapeo book_key -> URL base para construir links aproximados
BOOKMAKER_URLS = {
    "1xbet": "https://1xbet.com",
    "bet365": "https://www.bet365.com",
    "betfair": "https://www.betfair.com/exchange/plus/",
    "betsson": "https://www.betsson.com/en/sportsbook",
    "unibet": "https://www.unibet.com/betting/sports",
    "unibet_eu": "https://www.unibet.eu/betting/sports",
    "matchbook": "https://www.matchbook.com/events",
    "ladbrokes": "https://sports.ladbrokes.com",
    "smarkets": "https://smarkets.com/listing/sport",
    "nordicbet": "https://www.nordicbet.com/en/sportsbook",
    "20bet": "https://20bet.com/en/sports",
    "melbet": "https://melbet.com",
    "williamhill": "https://sports.williamhill.com/betting",
    "betclic": "https://www.betclic.com",
    "marathon_bet": "https://www.marathonbet.com",
    "pinnacle": "https://www.pinnacle.com/en/sports",
    "bovada": "https://www.bovada.lv/sports",
    "draftkings": "https://sportsbook.draftkings.com",
    "fanduel": "https://sportsbook.fanduel.com",
    "pointsbetus": "https://pointsbet.com",
    "betus": "https://www.betus.com.pa",
    "betmgm": "https://sports.betmgm.com",
    "betrivers": "https://www.betrivers.com",
    "coolbet": "https://www.coolbet.com/en/sports",
    "everygame": "https://www.everygame.eu/sportsbook",
    "gtbets": "https://www.gtbets.eu",
    "livescorebet_eu": "https://www.livescorebet.com",
    "sport888": "https://www.888sport.com",
    "betway": "https://betway.com/en/sports",
}

# Mapeo sport_key -> slug de deporte en las casas (aproximado)
SPORT_SLUGS = {
    "soccer_epl": {"default": "football/england/premier-league"},
    "soccer_spain_la_liga": {"default": "football/spain/la-liga"},
    "soccer_germany_bundesliga": {"default": "football/germany/bundesliga"},
    "soccer_italy_serie_a": {"default": "football/italy/serie-a"},
    "soccer_france_ligue_one": {"default": "football/france/ligue-1"},
    "soccer_uefa_champs_league": {"default": "football/uefa-champions-league"},
    "basketball_nba": {"default": "basketball/usa/nba"},
    "baseball_mlb": {"default": "baseball/usa/mlb"},
    "icehockey_nhl": {"default": "ice-hockey/usa/nhl"},
    "mma_mixed_martial_arts": {"default": "mma"},
}
