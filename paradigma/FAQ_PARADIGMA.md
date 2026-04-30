# FAQ Paradigma — Preguntas y Respuestas

Todas las preguntas frecuentes sobre el sistema Paradigma, explicadas con palabras sencillas.

---

## 1. ¿Cómo funciona el Stop-Loss?

El stop-loss es un **freno de emergencia**. Si pierdes demasiado dinero, el sistema se detiene automáticamente para proteger tu bankroll.

### Cómo se calcula:
1. Toma tu bankroll inicial: **$500**
2. Suma todas las ganancias y pérdidas de apuestas YA LIQUIDADAS (no pendientes)
3. Calcula el porcentaje de pérdida: `pérdida% = (1 - bankroll_actual / 500) × 100`
4. Si la pérdida llega al **15%** (es decir, tu bankroll baja de $500 a $425 o menos) → **TODO SE PARA**

### Ejemplo:
- Bankroll inicial: $500
- Apuestas liquidadas: ganaste $20, perdiste $100 → PnL = -$80
- Bankroll realizado: $500 + (-$80) = $420
- Pérdida: (1 - 420/500) × 100 = **16%** → ⚠️ STOP-LOSS ACTIVADO

### Detalles importantes:
- **Solo cuenta pérdidas REALES** — Si tienes $50 en apuestas pendientes, eso NO se cuenta. Solo se cuentan las que ya se liquidaron.
- **No se resetea solo** — El nombre dice "semanal" pero en la implementación actual mide pérdida acumulada desde el inicio. Para resetearlo habría que hacerlo manualmente o programar un reset semanal.
- **Cuando se activa:** el scanner no gasta más créditos de API, no busca más apuestas, y envía una alerta por Telegram.

---

## 2. Arbitraje: ¿Consideramos los 3 resultados (ganar, empate, perder)?

**SÍ**, Paradigma soporta tanto 2-way como 3-way:

### En fútbol (3-way):
- Se necesitan 3 apuestas: **Home + Draw + Away**
- Ejemplo: Real Madrid vs Barcelona
  - Home @2.20 en 1xBet
  - Draw @3.50 en Betway
  - Away @3.80 en Coolbet
- Verificación: 1/2.20 + 1/3.50 + 1/3.80 = 0.455 + 0.286 + 0.263 = **1.004** → NO es arb (suma > 1)
- Si la suma fuera **0.97** → Arb con 3.1% de ganancia garantizada

### En basketball/NBA (2-way):
- Solo 2 apuestas: **Home + Away** (no hay empate)
- Más fácil de encontrar porque solo necesitas 2 casas con buenas odds

### En totals y spreads (siempre 2-way):
- Over 2.5 + Under 2.5
- Home -1.5 + Away +1.5

---

## 3. ¿Por qué cada 45 minutos? ¿Más o menos frecuencia?

### El problema: cada escaneo cuesta créditos de API

| Componente | Créditos |
|------------|----------|
| 7 deportes × 3 mercados × 1 región | ~21 créditos |
| Settlement (scores): ~2 deportes con pendientes | ~4 créditos |
| **Total por escaneo** | **~25 créditos** |

### A 45 minutos:
- 32 escaneos/día × 25 = **800 créditos/día**
- 20,000 créditos/mes → dura **~25 días**

### Si escaneas más rápido (cada 15 min):
- 96 escaneos/día × 25 = **2,400 créditos/día**
- 20,000 créditos → dura **~8 días** ❌

### Si escaneas más lento (cada 90 min):
- 16 escaneos/día × 25 = **400 créditos/día**
- 20,000 créditos → dura **~50 días** ✅ pero pierdes oportunidades

### Recomendación:
- **Para arbitraje:** las oportunidades duran MINUTOS. Con 45 min de intervalo, la mayoría aparecen y desaparecen entre escaneos. Idealmente 15-20 min.
- **Para value betting:** las oportunidades duran HORAS. 45-60 min está bien.
- **Compromiso actual:** 45 min es un balance entre costo y detección. Si subes el plan de API, baja el intervalo.

---

## 4. Stop-Loss 15% en detalle

### ¿Qué significa el 15%?
Si tu bankroll de $500 pierde $75 (15%), el sistema para. Te quedan $425.

### ¿Por qué 15% y no 10% o 20%?
- **10%** = Muy conservador. En value betting, rachas de pérdida de 10% son normales estadísticamente (variance). Se activaría demasiado pronto.
- **15%** = Balance. Permite la varianza natural pero protege de una espiral de pérdidas real.
- **20%** = Agresivo. Perderías $100 antes de parar.

### ¿Qué pasa cuando se activa?
1. El scanner detecta la pérdida al inicio de cada ciclo
2. Envía alerta por Telegram: "⚠️ STOP-LOSS ACTIVADO"
3. Retorna inmediatamente sin buscar más apuestas
4. NO gasta créditos de API (el check es antes de pedir odds)
5. Se queda así hasta que alguien lo resetee manualmente

### ¿Cómo se resetea?
Actualmente no hay reset automático semanal. Opciones:
- Manualmente: ajustar `INITIAL_BANKROLL` al bankroll actual
- Programar un reset semanal (feature futura)

---

## 5. Scouting gratuito: Lista de partidos disponibles

### ¿Qué es?
Antes de gastar créditos pidiendo odds, el sistema pregunta "¿cuántos partidos hay?" usando `get_events()`, que es **GRATIS** (no gasta créditos de API).

### ¿Qué retorna?
Una lista de eventos con: ID, equipos, hora de inicio, deporte. **NO incluye odds** (para eso hay que pagar).

### ¿Por qué es útil?
- Si no hay partidos disponibles → no gastar créditos pidiendo odds
- Permite saber cuántos partidos están activos por deporte
- **Nuevo:** ahora se guardará esta lista y se mostrará en el dashboard (pestaña "Eventos") sin duplicados

---

## 6. ¿Para qué pide totals y spreads? ¿Ayuda al arbitraje?

### h2h (head-to-head) — "¿Quién gana?"
- **2-way** (NBA): Home o Away
- **3-way** (fútbol): Home, Draw, o Away
- Es el mercado principal y más líquido

### totals — "¿Más o menos de X goles/puntos?"
- Over 2.5 goles / Under 2.5 goles
- Ejemplo de arb en totals:
  - Over 2.5 @2.10 en Marathonbet
  - Under 2.5 @2.05 en Coolbet
  - 1/2.10 + 1/2.05 = 0.476 + 0.488 = 0.964 → **3.7% de ganancia** 💰

### spreads (handicap) — "¿Gana por cuánto?"
- Home -1.5 significa que el equipo local necesita ganar por 2 o más goles
- Away +1.5 significa que el visitante puede perder por 1 y aún ganas
- Ejemplo de arb en spreads:
  - Home -1.5 @2.30 en 1xBet
  - Away +1.5 @1.85 en Betway
  - 1/2.30 + 1/1.85 = 0.435 + 0.541 = 0.975 → **2.6% de ganancia** 💰

### ¿Por qué los 3?
- Más mercados = más oportunidades de encontrar arbs y value bets
- Si quitaras totals y spreads, solo buscarías arb en h2h → perderías ~60% de las oportunidades
- Costo: 3 mercados vs 1 = 3× más créditos, pero 3× más chances de encontrar algo

---

## 7. DNS Trick: ¿Me afecta?

### ¿Qué es?
La red corporativa (donde trabajas) bloquea `api.the-odds-api.com`. El código resuelve la IP directamente usando Google DNS (8.8.8.8) para saltarse el bloqueo.

### ¿Afecta en producción (Railway)?
**NO.** Railway tiene DNS normal, no hay bloqueo. El código detecta automáticamente si puede resolver el DNS normalmente:
1. Intenta `socket.gethostbyname("api.the-odds-api.com")`
2. Si funciona → no hace nada (Railway)
3. Si falla → aplica el parche DNS (tu computadora corporativa)

### Conclusión:
- **En tu PC corporativa:** necesario para que funcione
- **En Railway (producción):** no se activa, no afecta nada
- **En tu casa/otro lugar:** probablemente no se necesita

---

## 8. ¿Por qué 3 mercados? (21 créditos por escaneo)

La fórmula es: `deportes × mercados × regiones = créditos`

| Factor | Valor | Por qué |
|--------|-------|---------|
| Deportes | 7 | 6 ligas de fútbol + NBA |
| Mercados | 3 | h2h + totals + spreads |
| Regiones | 1 | Usamos param `bookmakers` (10 casas = 1 región) |
| **Total** | **21** | 7 × 3 × 1 |

Si solo pidieras h2h: 7 × 1 × 1 = 7 créditos/escaneo (3× más barato, pero perderías oportunidades en totals/spreads).

---

## 9. ¿Cómo puede fallar el devig?

El Shin devig es un algoritmo matemático que puede fallar en estos casos:

### Caso 1: Odds inválidas (≤ 1.0)
- Odds de 0.90 significaría que pagas $1 para ganar $0.90 → pérdida garantizada
- Esto indica error en los datos de la API

### Caso 2: Suma de probabilidades < 1.0
- Si 1/odds_H + 1/odds_D + 1/odds_A < 1.0, ya hay arbitraje en las odds de Pinnacle
- Esto es extremadamente raro pero posible

### Caso 3: El solver no converge
- La ecuación de Shin usa `brentq` (método numérico). Si no encuentra solución en el rango [0, 0.5], falla.

### Caso 4: El resultado no suma ~1.0
- Error numérico: las probabilidades calculadas no suman 1.0 (tolerancia: ±0.01)

### ¿Qué pasa cuando falla?
**Fallback automático:** usa normalización simple → divide cada probabilidad implícita por la suma total. Es menos preciso pero funcional.

---

## 10. ¿Cómo saco probabilidades teniendo odds?

### Fórmula básica:
```
probabilidad_implícita = 1 / odds_decimal
```

### Ejemplos:
| Odds | Cálculo | Probabilidad |
|------|---------|-------------|
| 1.50 | 1/1.50 | 66.7% (favorito fuerte) |
| 2.00 | 1/2.00 | 50.0% (moneda al aire) |
| 2.50 | 1/2.50 | 40.0% |
| 3.00 | 1/3.00 | 33.3% |
| 5.00 | 1/5.00 | 20.0% (underdog) |
| 10.00 | 1/10.00 | 10.0% (muy improbable) |

### El problema del margen:
Si sumas las probabilidades implícitas de TODAS las opciones:
- Real Madrid 1.80 → 55.6%
- Empate 3.50 → 28.6%
- Barcelona 4.20 → 23.8%
- **Suma: 108%** (no 100%)

Ese 8% extra es el **margen del bookmaker** (su ganancia). Por eso usamos **devig** para quitar ese margen y obtener las probabilidades "justas" que suman 100%.

---

## 11. Kelly Criterion explicado sencillo

### La idea:
"Apuesta una fracción de tu dinero **proporcional a tu ventaja**. Si tienes mucha ventaja, apuesta más. Si tienes poca, apuesta poco."

### Fórmula en palabras:
```
fracción_a_apostar = (prob_de_ganar × ganancia_por_dólar - prob_de_perder) / ganancia_por_dólar
```

### Ejemplo paso a paso:
1. **Probabilidad justa** (Pinnacle devig): 55% de que gane el equipo A
2. **Odds en casa blanda:** 2.10 (pagas $1, recibes $2.10 si ganas)
3. **Ganancia por dólar:** 2.10 - 1 = $1.10

Cálculo:
```
f = (0.55 × 1.10 - 0.45) / 1.10
f = (0.605 - 0.45) / 1.10
f = 0.155 / 1.10
f = 0.141 → 14.1% del bankroll
```

### ¿14.1% es mucho?
¡SÍ! Kelly puro es MUY agresivo. Por eso aplicamos dos frenos:
- **Kelly ÷4** (fracción 0.25): 14.1% ÷ 4 = **3.5%**
- **Cap del 2%**: como 3.5% > 2%, apostamos **2%** del bankroll = **$10**

### ¿Por qué Kelly ÷4?
- Kelly ÷1 (puro): máximo crecimiento teórico, pero volatilidad extrema. Puedes perder 50% del bankroll en una mala racha.
- Kelly ÷2: menos volátil, aún agresivo
- **Kelly ÷4**: conservador. Crecimiento más lento pero mucho más estable. Es lo que usan los profesionales.

---

## 12. ¿Cuáles criterios decide el bot para apostar? ¿Puede gastar todo el límite diario en una corrida?

### Criterios para que una apuesta sea aceptada:

| Criterio | Valor | Por qué |
|----------|-------|---------|
| EV mínimo | > 5% | Solo apuesta si la ventaja esperada es significativa |
| Odds mínimas | > 1.30 | Odds muy bajas no valen la pena (poca ganancia) |
| Odds máximas | < 10.00 | Odds muy altas son volátiles (casi nunca ganan) |
| Mín. casas | ≥ 3 | Si solo 1-2 casas tienen ese mercado, los datos son poco confiables |
| 1 apuesta por evento | Sí | No apostar 2 veces al mismo partido |
| No duplicar en DB | Sí | Si ya hay apuesta pendiente para ese evento, saltar |

### ¿Puede gastar el límite diario en una corrida?
**SÍ.** Si en un solo escaneo encuentra 5 value bets que pasan todos los filtros:
- 5 bets × $10 (2% de $500) = $50 = 10% del bankroll = **límite diario alcanzado**
- A partir de ahí, los escaneos siguientes del día saltan la búsqueda de value bets
- **Pero:** arbitraje sigue funcionando (no tiene límite diario)

---

## 13. ¿El arbitraje considera empates?

**SÍ.** En fútbol, el mercado h2h es 3-way: Home + Draw + Away.

Para que haya arb en fútbol 3-way:
```
1/odds_Home + 1/odds_Draw + 1/odds_Away < 1.0
```

Necesitas encontrar la MEJOR odd para Home en una casa, la MEJOR para Draw en OTRA casa, y la MEJOR para Away en OTRA casa. Las 3 casas deben ser DIFERENTES.

Ejemplo con arb real:
- Home @3.20 en 1xBet → 1/3.20 = 0.3125
- Draw @3.80 en Marathonbet → 1/3.80 = 0.2632
- Away @3.50 en Betway → 1/3.50 = 0.2857
- Suma: 0.8614 → **ganancia garantizada de 16.1%** (esto sería excepcionalmente bueno, normalmente es 0.5-3%)

---

## 14. Términos explicados: h2h, totals, spreads

### h2h (Head to Head) — "¿Quién gana?"
Imagina que vas al estadio. Al final del partido, ¿quién ganó?

- **2-way** (NBA, tenis): Solo hay 2 opciones: Home o Away. No hay empate (en NBA juegan tiempo extra hasta que alguien gane).
- **3-way** (fútbol): 3 opciones: Home, Draw (empate), o Away. Si apuestas a Home y empatan, pierdes.

### totals — "¿Cuántos goles/puntos habrá en total?"
No importa quién gane. Solo importa el total de goles/puntos SUMANDO ambos equipos.

- **Over 2.5 goles:** Apuestas a que habrá 3 o más goles en total (ej: 2-1, 3-0, 2-2, etc.)
- **Under 2.5 goles:** Apuestas a que habrá 2 o menos goles (ej: 1-0, 0-0, 1-1)
- ¿Por qué 2.5? Porque es un número decimal que no puede empatar. Si hay 2 goles → Under gana. Si hay 3 → Over gana.

### spreads (Handicap) — "¿Gana por cuánto?"
Se le da ventaja o desventaja a un equipo antes de empezar.

- **Home -1.5:** El equipo local "empieza perdiendo 1.5". Para que tu apuesta gane, necesita ganar por 2 o más goles (ej: 2-0, 3-1).
- **Away +1.5:** El visitante "empieza ganando 1.5". Tu apuesta gana si el visitante gana, empata, o pierde por solo 1 gol.
- ¿Por qué? Permite apostar en partidos desiguales. Si Barcelona juega contra un equipo débil, las odds de que gane son muy bajas (1.10). Pero con handicap -1.5, las odds suben a 1.80.

---

## 15. ¿Qué es el group_id de arbitraje?

Un arbitraje no es UNA apuesta, son **2 o 3 apuestas que van juntas**. El `arb_group_id` es el número que las conecta.

### Ejemplo visual:
```
Arb Group #1001:
├── Leg 1: Real Madrid (Home) @2.20 en 1xBet    → apostar $45.45
├── Leg 2: Empate (Draw) @3.50 en Betway         → apostar $28.57
└── Leg 3: Barcelona (Away) @3.80 en Coolbet     → apostar $26.32
    Total apostado: $100.34
    Ganancia garantizada: ~$0.50 (0.5%)
```

Sin importar el resultado:
- Si gana Madrid: $45.45 × 2.20 = $100.00 → ganaste ~$0.50
- Si empate: $28.57 × 3.50 = $100.00 → ganaste ~$0.50
- Si gana Barcelona: $26.32 × 3.80 = $100.02 → ganaste ~$0.50

### ¿Para qué sirve?
1. **Dashboard:** muestra las 3 patas juntas como UN bloque, no como 3 apuestas separadas
2. **Liquidación:** se liquidan juntas
3. **Tracking:** sabes cuánto invertiste y ganaste por arb completo

---

## 16. ¿Cuando el bankroll llega al límite, el arbitraje también para?

### Antes (problema):
Sí, si el límite diario se alcanzaba, TODO paraba — incluyendo arb. Esto no tiene sentido porque arb es sin riesgo.

### Ahora (cambio implementado):
**Límites SEPARADOS por estrategia:**

| Control | Value Betting | Arbitraje |
|---------|--------------|-----------|
| Límite diario | 10% del bankroll | **SIN LÍMITE** ♾️ |
| Límite total (exposición abierta) | 30% del bankroll | 30% del bankroll |
| Stop-loss | 15% pérdida → para | 15% pérdida → para |

### Lógica:
1. Si value betting llega al 10% diario → deja de buscar value bets, **SIGUE buscando arbs**
2. Si arb llega al 30% total abierto → para arb también (no quieres tener todo tu dinero comprometido)
3. Stop-loss aplica a ambos (si perdiste 15%, para todo)

---

## 17. Controles de riesgo — Explicación detallada

### 1. EV mínimo 5%
- "Solo apuesta si esperas ganar al menos 5 centavos por cada dólar apostado"
- ¿Por qué no 1%? Porque con edge tan pequeño, los costos de latencia/staleness te comen la ganancia
- ¿Por qué no 10%? Porque perderías demasiadas oportunidades buenas

### 2. Kelly ÷4 con cap 2%
- Nunca apuesta más del 2% del bankroll en una sola apuesta ($10 de $500)
- Si pierdes 10 apuestas seguidas: $500 → $500 - 10×$10 = $400 (solo -20%)
- Con Kelly puro sin cap, podrías apostar $70+ en una sola bet

### 3. Límite diario 10% (value)
- Máximo $50/día en value bets (10% de $500)
- Evita que un mal día de detección (errores de API, odds stale) te cueste demasiado

### 4. Límite total 30%
- Máximo $150 en apuestas pendientes AL MISMO TIEMPO
- Si tienes $150 apostados esperando resultados, no puedes apostar más
- Protege contra el escenario "todos los partidos del fin de semana se pierden"

### 5. Stop-loss 15%
- Freno de emergencia total. Si el bankroll baja de $500 a $425 → para todo
- Te da tiempo de analizar qué salió mal antes de seguir

### 6. Odds mínimas 1.30
- No apostar a favoritos extremos (odds < 1.30 = > 77% de probabilidad implícita)
- Poca ganancia por mucho riesgo

### 7. Odds máximas 10.00
- No apostar a underdogs extremos (odds > 10 = < 10% probabilidad)
- Demasiado volátil, casi nunca ganas

### 8. Mínimo 3 casas
- Si solo 1-2 casas tienen el mercado, los datos son poco confiables
- Con 3+, puedes comparar y confiar más en el precio

### 9. 1 apuesta por evento
- No hacer múltiples apuestas al mismo partido
- Evita sobreexposición a un solo resultado

### 10. Deduplicación persistente
- Si ya tienes apuesta pendiente para un partido, no apostar otra vez aunque se vea buena
- Funciona entre reinicios del sistema (guardado en base de datos)

### 11. Profit mínimo 0.5% (arb)
- No perseguir arbs de 0.1% — el tiempo que tardas en actuar probablemente eliminará la oportunidad
- 0.5% mínimo cubre la latencia y cambios de odds

---

## 18. ¿Por qué no hay oportunidades de arbitraje recientes?

### Razón #1: Los arbs son EXTREMADAMENTE raros
- Los bookmakers profesionales ajustan sus odds constantemente para eliminar arbs
- Menos del 0.1% de los mercados tienen arb en cualquier momento dado
- Cuando aparecen, duran **minutos**, no horas

### Razón #2: Escaneo cada 45 minutos
- Un arb puede aparecer a las 10:05 y desaparecer a las 10:08
- Si tu escaneo fue a las 10:00 y el siguiente a las 10:45, lo perdiste
- Solución: escanear más frecuentemente (pero cuesta más créditos)

### Razón #3: Solo 10 bookmakers
- Arbs aparecen cuando HAY DIFERENCIA entre casas. Con más casas, más probabilidad de encontrar diferencias.
- Actualmente monitoreamos 10 casas. Con 20-30, encontraríamos más.

### Razón #4: Filtro de 0.5% mínimo
- Arbs de 0.1-0.4% sí pueden existir pero los descartamos por ser demasiado pequeños para actuar

### ¿Es porque el bankroll lo detuvo?
**NO.** El check de límites es ANTES de pedir odds. Si el bankroll no detuvo la búsqueda de value bets, tampoco detuvo arb. Puedes verificar en los logs — si ves "Arbitraje: 0 oportunidades encontradas", significa que buscó pero no encontró. Si ves "Límite alcanzado. Saltando escaneo", entonces sí fue el límite.

---

## 19. Consumo de API — ¿Cómo se gastan los créditos?

### Costos por operación:

| Operación | Créditos | ¿Cuándo? |
|-----------|----------|----------|
| Scouting (listar eventos) | **0 (gratis)** | Cada escaneo |
| Odds por deporte×mercado×región | **1** | Cada escaneo |
| Scores (resultados) por deporte | **2** | Solo si hay pendientes |

### Desglose de un escaneo típico:
```
Scouting (7 deportes)          =  0 créditos (gratis)
Odds: 7 deportes × 3 mercados = 21 créditos
Scores: 2 deportes con bets    =  4 créditos
                          Total = 25 créditos
```

### Tu consumo actual:
- Plan: 500 créditos/mes (plan gratuito) o 20,000/mes (pagado)
- 949 tokens usados en 2 días ≈ 475/día
- A ese ritmo: 20,000 / 475 = **~42 días** ✅

### ¿Dónde ver el historial?
- **The Odds API dashboard:** https://the-odds-api.com/account/
- **Nuevo en Paradigma:** la pestaña "API & Tokens" en el dashboard mostrará el consumo por escaneo

### Dato clave:
El truco de `bookmakers` param ahorra **4×** de créditos. Sin él, pagarías 4 regiones en vez de 1 por cada petición.

---

## 20. ¿Podemos ver el historial de datos de la API?

**Sí.** The Odds API tiene un panel web donde puedes ver:
- Créditos usados / restantes
- Historial de requests
- Uso por día

**URL:** https://the-odds-api.com/account/

Además, nuestro código guarda en los headers de cada respuesta:
- `x-requests-remaining`: créditos que quedan
- `x-requests-used`: créditos usados en total

Estos datos ahora se mostrarán en la nueva pestaña **"API & Tokens"** del dashboard.
