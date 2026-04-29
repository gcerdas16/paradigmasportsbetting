# The Odds API v4 — Documentación Completa

> Extraída de https://the-odds-api.com/liveapi/guides/v4/
> Fecha de extracción: 2026-04-28
> API Key: en `.env` como `ODDS_API_KEY`
> **Créditos disponibles en cuenta: 31** (usar con cuidado)

---

## Índice

1. [Overview / Host](#overview)
2. [Sistema de Créditos](#créditos)
3. [GET /sports](#get-sports)
4. [GET /odds](#get-odds)
5. [GET /scores](#get-scores)
6. [GET /events](#get-events)
7. [GET /event odds](#get-event-odds)
8. [GET /event markets](#get-event-markets)
9. [GET /participants](#get-participants)
10. [GET /historical odds](#get-historical-odds)
11. [GET /historical events](#get-historical-events)
12. [GET /historical event odds](#get-historical-event-odds)
13. [Bookmakers por Región](#bookmakers)
14. [Sport Keys — Fútbol](#sport-keys-fútbol)
15. [Sport Keys — Todos los deportes](#sport-keys-completo)
16. [Notas de implementación para Paradigma](#notas-paradigma)

---

## Overview

**Base URL:** `https://api.the-odds-api.com`
**IPv6:** `https://ipv6-api.the-odds-api.com`

Todos los requests requieren `?apiKey={apiKey}`.

**Response headers en TODOS los endpoints:**
| Header | Descripción |
|--------|-------------|
| `x-requests-remaining` | Créditos restantes hasta el reset |
| `x-requests-used` | Créditos usados desde el último reset |
| `x-requests-last` | Costo del último request |

---

## Créditos

| Endpoint | Costo |
|----------|-------|
| GET /sports | **0** (gratis) |
| GET /events | **0** (gratis) |
| GET /participants | **0** (gratis)  |
| GET /odds | `[markets] × [regions]` |
| GET /scores (sin daysFrom) | 1 |
| GET /scores (con daysFrom) | 2 |
| GET /event odds | `[unique markets devueltos] × [regions]` |
| GET /event markets | 1 |
| GET /historical odds | `10 × [markets] × [regions]` |
| GET /historical events | 1 (0 si no hay eventos) |
| GET /historical event odds | `[unique markets devueltos] × [regions]` |

**Regla de bookmakers:** Especificar `bookmakers=a,b,c,...` en vez de `regions`:
- Hasta 10 bookmakers = 1 región equivalente
- Ej: `bookmakers=pinnacle,onexbet,sport888,betsson` (4 books) = 1 región = costo mínimo

**Respuestas vacías NO gastan créditos.**

### Ejemplo de costos para Paradigma (7 ligas, `bookmakers` param = 1 región):
| Mercados | Costo por liga | Costo total 7 ligas |
|----------|---------------|---------------------|
| h2h solamente | 1 | **7 créditos** |
| h2h + spreads | 2 | **14 créditos** |
| h2h + spreads + totals | 3 | **21 créditos** |

---

## GET /sports

**URL:** `GET /v4/sports/?apiKey={apiKey}`
**Costo:** 0

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `apiKey` | requerido | API key |
| `all` | opcional | `all=true` incluye deportes fuera de temporada |

**Response — array de objetos:**
```json
{
  "key": "soccer_epl",
  "group": "Soccer",
  "title": "EPL",
  "description": "English Premier League",
  "active": true,
  "has_outrights": false
}
```

---

## GET /odds

**URL:** `GET /v4/sports/{sport}/odds/?apiKey={apiKey}&regions={regions}&markets={markets}`
**Costo:** `[markets] × [regions]`

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `sport` | requerido | Sport key (ej: `soccer_epl`) o `upcoming` para todos |
| `apiKey` | requerido | API key |
| `regions` | requerido* | `us`, `us2`, `uk`, `au`, `eu` — separados por coma |
| `markets` | opcional | Default: `h2h`. Opciones: `h2h`, `spreads`, `totals`, `outrights` — separados por coma |
| `oddsFormat` | opcional | `decimal` (default) o `american` |
| `dateFormat` | opcional | `iso` (default) o `unix` |
| `eventIds` | opcional | IDs de eventos específicos, separados por coma |
| `bookmakers` | opcional* | Lista de bookmakers específicos. Toma prioridad sobre `regions` si ambos están especificados. Cada 10 bookmakers = 1 región |
| `commenceTimeFrom` | opcional | ISO 8601 — filtrar partidos que empiezan desde esta fecha. **No aplica si sport=`upcoming`** |
| `commenceTimeTo` | opcional | ISO 8601 — filtrar partidos que empiezan hasta esta fecha |
| `includeLinks` | opcional | `true` → incluye links directos al partido/mercado en cada bookmaker |
| `includeSids` | opcional | `true` → incluye source IDs (IDs internos del bookmaker) útiles para construir links custom |
| `includeBetLimits` | opcional | `true` → incluye límites de apuesta (principalmente para exchanges) |
| `includeRotationNumbers` | opcional | `true` → incluye rotation numbers home/away si están disponibles |

*`regions` o `bookmakers` — usar uno de los dos.

**Response:**
```json
[
  {
    "id": "bda33adca828c09dc3cac3a856aef176",
    "sport_key": "soccer_epl",
    "sport_title": "EPL",
    "commence_time": "2026-05-01T19:00:00Z",
    "home_team": "Leeds United",
    "away_team": "Burnley",
    "bookmakers": [
      {
        "key": "pinnacle",
        "title": "Pinnacle",
        "last_update": "2026-04-28T22:00:00Z",
        "markets": [
          {
            "key": "h2h",
            "outcomes": [
              { "name": "Leeds United", "price": 1.45 },
              { "name": "Burnley", "price": 6.98 },
              { "name": "Draw", "price": 4.20 }
            ]
          },
          {
            "key": "spreads",
            "outcomes": [
              { "name": "Leeds United", "price": 1.91, "point": -1.5 },
              { "name": "Burnley", "price": 1.91, "point": 1.5 }
            ]
          },
          {
            "key": "totals",
            "outcomes": [
              { "name": "Over", "price": 1.87, "point": 2.5 },
              { "name": "Under", "price": 1.95, "point": 2.5 }
            ]
          }
        ]
      },
      {
        "key": "onexbet",
        "title": "1xBet",
        "last_update": "2026-04-28T22:00:00Z",
        "markets": [
          {
            "key": "h2h",
            "outcomes": [
              { "name": "Leeds United", "price": 1.50 },
              { "name": "Burnley", "price": 8.00 },
              { "name": "Draw", "price": 4.35 }
            ]
          }
        ]
      }
    ]
  }
]
```

**Notas importantes:**
- `upcoming` como sport devuelve partidos en vivo + los próximos 8 partidos en todos los deportes
- Si `commence_time` < hora actual → partido en vivo
- Partidos completados NO aparecen en /odds
- Si no hay eventos → no gasta créditos
- Los eventos listados "mirrors events that are listed by major bookmakers" — normalmente la jornada actual

---

## GET /scores

**URL:** `GET /v4/sports/{sport}/scores/?apiKey={apiKey}`
**Costo:** 1 sin `daysFrom`, 2 con `daysFrom`

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `sport` | requerido | Sport key |
| `apiKey` | requerido | API key |
| `daysFrom` | opcional | Entero 1-3: incluye partidos completados de los últimos N días |
| `dateFormat` | opcional | `iso` (default) o `unix` |
| `eventIds` | opcional | Filtrar por IDs específicos |

**Response:**
```json
[
  {
    "id": "abc123",
    "sport_key": "soccer_epl",
    "sport_title": "EPL",
    "commence_time": "2026-05-01T19:00:00Z",
    "completed": false,
    "home_team": "Leeds United",
    "away_team": "Burnley",
    "scores": null,
    "last_update": "2026-04-28T22:00:00Z"
  }
]
```

Actualiza aproximadamente cada 30 segundos para partidos en vivo.

---

## GET /events

**URL:** `GET /v4/sports/{sport}/events?apiKey={apiKey}`
**Costo:** 0 (gratis)

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `sport` | requerido | Sport key |
| `apiKey` | requerido | API key |
| `dateFormat` | opcional | `iso` o `unix` |
| `eventIds` | opcional | Filtrar por IDs |
| `commenceTimeFrom` | opcional | ISO 8601 |
| `commenceTimeTo` | opcional | ISO 8601 |
| `includeRotationNumbers` | opcional | Boolean |

**Response:** Lista de eventos SIN odds (solo metadata).
```json
[
  {
    "id": "bda33adca828c09dc3cac3a856aef176",
    "sport_key": "soccer_epl",
    "sport_title": "EPL",
    "commence_time": "2026-05-01T19:00:00Z",
    "home_team": "Leeds United",
    "away_team": "Burnley"
  }
]
```

**Uso:** Scouting previo sin gastar créditos. Obtener IDs de eventos para /event odds.

---

## GET /event odds

**URL:** `GET /v4/sports/{sport}/events/{eventId}/odds?apiKey={apiKey}&regions={regions}&markets={markets}`
**Costo:** `[unique markets devueltos] × [regions]`

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `sport` | requerido | Sport key |
| `eventId` | requerido | ID del evento (de /events) |
| `apiKey` | requerido | API key |
| `regions` | requerido | Regiones de bookmakers |
| `markets` | requerido | Cualquier market key disponible (incluyendo props, líneas alternas, etc.) |
| `oddsFormat` | opcional | `decimal` o `american` |
| `dateFormat` | opcional | `iso` o `unix` |
| `includeMultipliers` | opcional | Para DFS sites de EEUU |

**Diferencia clave vs /odds:** Acepta CUALQUIER market key (player props, alternate lines, period markets, etc.), no solo h2h/spreads/totals. El `last_update` aparece a nivel de market (no de bookmaker).

**Costo usa markets DEVUELTOS, no solicitados.** Si pide 5 markets pero solo 2 existen → cuesta 2.

**Response:**
```json
{
  "id": "a512a48a58c4329048174217b2cc7ce0",
  "sport_key": "soccer_epl",
  "sport_title": "EPL",
  "commence_time": "2026-05-01T19:00:00Z",
  "home_team": "Leeds United",
  "away_team": "Burnley",
  "bookmakers": [
    {
      "key": "pinnacle",
      "title": "Pinnacle",
      "markets": [
        {
          "key": "h2h",
          "last_update": "2026-04-28T22:00:00Z",
          "outcomes": [
            { "name": "Leeds United", "price": 1.45 },
            { "name": "Burnley", "price": 6.98 },
            { "name": "Draw", "price": 4.20 }
          ]
        }
      ]
    }
  ]
}
```

---

## GET /event markets

**URL:** `GET /v4/sports/{sport}/events/{eventId}/markets?apiKey={apiKey}&regions={regions}`
**Costo:** 1 crédito

**Parámetros:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `sport` | requerido | Sport key |
| `eventId` | requerido | ID del evento |
| `apiKey` | requerido | API key |
| `regions` | requerido | Regiones |
| `bookmakers` | opcional | Lista específica de bookmakers |
| `dateFormat` | opcional | `iso` o `unix` |

**Response:** Qué markets tiene cada bookmaker para este evento (sin precios).
```json
{
  "id": "abc123",
  "sport_key": "soccer_epl",
  "home_team": "Leeds United",
  "away_team": "Burnley",
  "bookmakers": [
    {
      "key": "pinnacle",
      "title": "Pinnacle",
      "markets": [
        { "key": "h2h", "last_update": "2026-04-28T22:00:00Z" },
        { "key": "spreads", "last_update": "2026-04-28T22:00:00Z" },
        { "key": "totals", "last_update": "2026-04-28T22:00:00Z" }
      ]
    }
  ]
}
```

**Nota:** Solo muestra markets observados recientemente — no es exhaustivo. Más markets aparecen conforme se acerca el partido.

---

## GET /participants

**URL:** `GET /v4/sports/{sport}/participants?apiKey={apiKey}`
**Costo:** 1

**Response:** Lista de equipos/atletas para un deporte.
```json
[
  { "full_name": "Leeds United", "id": "abc123" },
  { "full_name": "Burnley", "id": "def456" }
]
```

---

## GET /historical odds

**URL:** `GET /v4/historical/sports/{sport}/odds?apiKey={apiKey}&regions={regions}&markets={markets}&date={date}`
**Costo:** `10 × [markets] × [regions]` — **solo planes de pago**

**Parámetros adicionales vs /odds:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `date` | requerido | ISO 8601 timestamp. Devuelve el snapshot más cercano igual o anterior a esta fecha |

**Disponibilidad de snapshots:**
- Desde: 6 junio 2020
- Intervalo: cada 10 minutos hasta septiembre 2022
- Intervalo: cada 5 minutos desde septiembre 2022

**Response:**
```json
{
  "timestamp": "2026-04-28T22:00:00Z",
  "previous_timestamp": "2026-04-28T21:55:00Z",
  "next_timestamp": "2026-04-28T22:05:00Z",
  "data": [ /* mismo formato que /odds */ ]
}
```

**Notas:**
- Odds americanas antes de Sept 18 2022 se calculan desde decimal → posible error de redondeo
- "Bookmakers, sports and markets solo disponibles en historical desde que fueron agregados al API actual"
- Datos vacíos no consumen créditos

---

## GET /historical events

**URL:** `GET /v4/historical/sports/{sport}/events?apiKey={apiKey}&date={date}`
**Costo:** 1 (0 si no hay eventos) — **solo planes de pago**

Igual a GET /events pero con el parámetro `date` requerido.

**Response:**
```json
{
  "timestamp": "2026-04-28T22:00:00Z",
  "previous_timestamp": "...",
  "next_timestamp": "...",
  "data": [ /* mismo formato que /events */ ]
}
```

---

## GET /historical event odds

**URL:** `GET /v4/historical/sports/{sport}/events/{eventId}/odds?apiKey={apiKey}&regions={regions}&markets={markets}&date={date}`
**Costo:** `[unique markets devueltos] × [regions]` — **solo planes de pago**

**Nota:** Datos para markets adicionales (props, alternate lines, period markets) disponibles solo después de `2023-05-03T05:30:00Z`. Snapshots de 5 minutos disponibles después de esa fecha.

**Response:** igual a /event odds pero envuelto con metadata de timestamp.

---

## Bookmakers

### EU (los que nos interesan para Paradigma)
| Key | Nombre |
|-----|--------|
| `pinnacle` | Pinnacle ⭐ (referencia sharp) |
| `onexbet` | 1xBet ✅ |
| `sport888` | 888sport ✅ |
| `betsson` | Betsson ✅ |
| `marathonbet` | Marathon Bet |
| `coolbet` | Coolbet |
| `nordicbet` | NordicBet |
| `betvictor` | Bet Victor |
| `unibet_eu` | Unibet (EU) |
| `unibet_fr` | Unibet (FR) |
| `unibet_it` | Unibet (IT) |
| `unibet_nl` | Unibet (NL) |
| `unibet_se` | Unibet (SE) |
| `betclic_fr` | Betclic (FR) |
| `everygame` | Everygame |
| `leovegas_se` | LeoVegas (SE) |
| `winamax_fr` | Winamax (FR) |
| `winamax_de` | Winamax (DE) |
| `tipico_de` | Tipico (DE) |
| `betfair_ex_eu` | Betfair Exchange (EU) |
| `matchbook` | Matchbook |
| `suprabets` | Suprabets |
| `codere_it` | Codere (IT) |
| `gtbets` | GTbets |
| `pmu_fr` | PMU (FR) |

### UK
| Key | Nombre |
|-----|--------|
| `sport888` | 888sport |
| `betfair_ex_uk` | Betfair Exchange |
| `betfair_sb_uk` | Betfair Sportsbook |
| `betfred_uk` | Betfred |
| `betway` | Betway |
| `williamhill` | William Hill |
| `skybet` | Sky Bet |
| `paddypower` | Paddy Power |
| `coral` | Coral |
| `ladbrokes_uk` | Ladbrokes |
| `boylesports` | BoyleSports |
| `casumo` | Casumo |
| `smarkets` | Smarkets |
| `matchbook` | Matchbook |
| `unibet_uk` | Unibet (UK) |

### NO disponibles en The Odds API
- ❌ BetSafe
- ❌ MelBet
- ❌ 20Bet

---

## Sport Keys — Fútbol

### Competiciones internacionales
| Key | Liga |
|-----|------|
| `soccer_uefa_champs_league` | UEFA Champions League |
| `soccer_uefa_europa_league` | UEFA Europa League |
| `soccer_uefa_europa_conference_league` | UEFA Europa Conference League |
| `soccer_uefa_nations_league` | UEFA Nations League |
| `soccer_uefa_european_championship` | UEFA Euro |
| `soccer_fifa_world_cup` | FIFA World Cup |
| `soccer_fifa_club_world_cup` | FIFA Club World Cup |
| `soccer_conmebol_copa_libertadores` | Copa Libertadores |
| `soccer_conmebol_copa_sudamericana` | Copa Sudamericana |
| `soccer_concacaf_gold_cup` | CONCACAF Gold Cup |
| `soccer_africa_cup_of_nations` | Africa Cup of Nations |

### Ligas domésticas — Europa (las que nos interesan)
| Key | Liga |
|-----|------|
| `soccer_epl` | Premier League (England) |
| `soccer_efl_champ` | Championship (England) |
| `soccer_england_league1` | League 1 (England) |
| `soccer_england_league2` | League 2 (England) |
| `soccer_fa_cup` | FA Cup |
| `soccer_england_efl_cup` | EFL Cup |
| `soccer_spain_la_liga` | La Liga (Spain) |
| `soccer_spain_segunda_division` | La Liga 2 (Spain) |
| `soccer_spain_copa_del_rey` | Copa del Rey |
| `soccer_germany_bundesliga` | Bundesliga (Germany) |
| `soccer_germany_bundesliga2` | Bundesliga 2 |
| `soccer_germany_liga3` | 3. Liga |
| `soccer_germany_dfb_pokal` | DFB-Pokal |
| `soccer_italy_serie_a` | Serie A (Italy) |
| `soccer_italy_serie_b` | Serie B |
| `soccer_italy_coppa_italia` | Coppa Italia |
| `soccer_france_ligue_one` | Ligue 1 (France) |
| `soccer_france_ligue_two` | Ligue 2 |
| `soccer_france_coupe_de_france` | Coupe de France |
| `soccer_netherlands_eredivisie` | Eredivisie |
| `soccer_portugal_primeira_liga` | Primeira Liga |
| `soccer_belgium_first_div` | Belgium First Div |
| `soccer_turkey_super_league` | Turkey Super League |
| `soccer_greece_super_league` | Super League Greece |
| `soccer_spl` | Premiership (Scotland) |
| `soccer_austria_bundesliga` | Austrian Bundesliga |
| `soccer_switzerland_superleague` | Swiss Superleague |
| `soccer_denmark_superliga` | Denmark Superliga |
| `soccer_norway_eliteserien` | Eliteserien (Norway) |
| `soccer_sweden_allsvenskan` | Allsvenskan (Sweden) |
| `soccer_finland_veikkausliiga` | Veikkausliiga (Finland) |
| `soccer_poland_ekstraklasa` | Ekstraklasa (Poland) |

### Otras ligas
| Key | Liga |
|-----|------|
| `soccer_usa_mls` | MLS |
| `soccer_mexico_ligamx` | Liga MX |
| `soccer_brazil_campeonato` | Brazil Série A |
| `soccer_argentina_primera_division` | Primera División (Argentina) |
| `soccer_russia_premier_league` | Premier League (Russia) |
| `soccer_saudi_arabia_pro_league` | Saudi Pro League |
| `soccer_australia_aleague` | A-League |
| `soccer_japan_j_league` | J League |
| `soccer_korea_kleague1` | K League 1 |
| `soccer_china_superleague` | Super League China |

---

## Sport Keys — Completo

### American Football
`americanfootball_nfl`, `americanfootball_ncaaf`, `americanfootball_ncaaf_championship_winner`, `americanfootball_nfl_preseason`, `americanfootball_nfl_super_bowl_winner`, `americanfootball_cfl`, `americanfootball_ufl`

### Baseball
`baseball_mlb`, `baseball_mlb_preseason`, `baseball_mlb_world_series_winner`, `baseball_milb`, `baseball_npb`, `baseball_kbo`, `baseball_ncaa`

### Basketball
`basketball_nba`, `basketball_nba_preseason`, `basketball_nba_championship_winner`, `basketball_wnba`, `basketball_ncaab`, `basketball_euroleague`, `basketball_nbl`

### Ice Hockey
`icehockey_nhl`, `icehockey_nhl_preseason`, `icehockey_nhl_championship_winner`, `icehockey_ahl`, `icehockey_liiga`, `icehockey_sweden_hockey_league`

### Tennis ATP
`tennis_atp_aus_open_singles`, `tennis_atp_french_open`, `tennis_atp_wimbledon`, `tennis_atp_us_open`, `tennis_atp_indian_wells`, `tennis_atp_miami_open`, `tennis_atp_madrid_open`, `tennis_atp_italian_open`, `tennis_atp_canadian_open`, `tennis_atp_cincinnati_open`, `tennis_atp_shanghai_masters`, `tennis_atp_paris_masters`, `tennis_atp_barcelona_open`, `tennis_atp_monte_carlo_masters`, `tennis_atp_dubai`, `tennis_atp_qatar_open`, `tennis_atp_munich`, `tennis_atp_china_open`

### Tennis WTA
`tennis_wta_aus_open_singles`, `tennis_wta_french_open`, `tennis_wta_wimbledon`, `tennis_wta_us_open`, `tennis_wta_indian_wells`, `tennis_wta_miami_open`, `tennis_wta_madrid_open`, `tennis_wta_italian_open`, `tennis_wta_canadian_open`, `tennis_wta_cincinnati_open`, `tennis_wta_dubai`, `tennis_wta_qatar_open`, `tennis_wta_charleston_open`, `tennis_wta_stuttgart_open`, `tennis_wta_wuhan_open`, `tennis_wta_china_open`

### MMA / Boxing / Rugby / Cricket / Golf / Otros
`mma_mixed_martial_arts`, `boxing_boxing`, `rugbyleague_nrl`, `rugbyunion_six_nations`, `cricket_ipl`, `cricket_test_match`, `cricket_odi`, `cricket_international_t20`, `golf_masters_tournament_winner`, `golf_pga_championship_winner`, `golf_the_open_championship_winner`, `golf_us_open_winner`, `basketball_euroleague`, `handball_germany_bundesliga`, `lacrosse_pll`, `aussierules_afl`

---

## Notas de implementación para Paradigma

### Estrategia óptima con 31 créditos restantes

**Con `bookmakers=pinnacle,onexbet,sport888,betsson` (4 books = 1 región = costo mínimo):**

```
Opción A — Solo h2h, 7 ligas clave:
  7 ligas × 1 market × 1 región = 7 créditos
  Quedan: 24 créditos

Opción B — h2h + spreads + totals, solo EPL:
  1 liga × 3 markets × 1 región = 3 créditos
  Quedan: 28 créditos (buen test piloto)
```

### Ligas clave para Paradigma
```python
TARGET_SPORTS = [
    "soccer_epl",                      # Premier League
    "soccer_spain_la_liga",            # La Liga
    "soccer_germany_bundesliga",       # Bundesliga
    "soccer_italy_serie_a",            # Serie A
    "soccer_france_ligue_one",         # Ligue 1
    "soccer_uefa_champs_league",       # UCL
    "soccer_uefa_europa_league",       # Europa League
]
```

### Bookmakers disponibles para Paradigma
```python
TARGET_BOOKMAKERS = "pinnacle,onexbet,sport888,betsson"
# NO disponibles: betsafe, melbet, 20bet
```

### Request de ejemplo para EPL
```
GET https://api.the-odds-api.com/v4/sports/soccer_epl/odds/
  ?apiKey=YOUR_KEY
  &bookmakers=pinnacle,onexbet,sport888,betsson
  &markets=h2h,spreads,totals
  &oddsFormat=decimal
  &dateFormat=iso
  &includeLinks=true
```

### Ventajas vs scraping
- ✅ No requiere browser/Playwright
- ✅ Partidos ya emparejados — Pinnacle y soft books en la misma respuesta
- ✅ `includeLinks=true` da links directos a cada partido en cada casa
- ✅ Segundos vs 20 minutos del scraping
- ✅ Más estable — no depende de que el sitio cargue correctamente

### Desventajas vs scraping
- ❌ Cuesta créditos (plan de pago)
- ❌ BetSafe, MelBet, 20Bet no disponibles
- ❌ Datos pueden tener pequeño delay vs scraping directo

### Estructura de respuesta con `includeLinks=true`
Cuando se activa `includeLinks`, la response agrega campos de link en el nivel de bookmaker y/o outcome:
```json
{
  "bookmakers": [
    {
      "key": "onexbet",
      "title": "1xBet",
      "link": "https://1xbet.com/...",   ← link al evento
      "markets": [
        {
          "key": "h2h",
          "outcomes": [
            {
              "name": "Leeds United",
              "price": 1.50,
              "link": "https://1xbet.com/betslip/..."  ← link al betslip
            }
          ]
        }
      ]
    }
  ]
}
```

### Eventos activos actualmente (verificado 2026-04-28)
53 ligas de fútbol activas en la cuenta.
EPL: 20 eventos disponibles (próximas jornadas).
Créditos: **31 restantes**.
