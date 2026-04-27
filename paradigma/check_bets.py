"""Script temporal para inspeccionar apuestas registradas."""
from tracker import Tracker, Bet

t = Tracker()
session = t.Session()
bets = session.query(Bet).all()

print(f"Total apuestas: {len(bets)}\n")
for b in bets:
    pt = f" {b.outcome_point}" if b.outcome_point else ""
    print(
        f"#{b.id} | {b.sport_title[:20]:20s} | "
        f"{b.home_team[:15]:15s} vs {b.away_team[:15]:15s} | "
        f"{b.market:8s} | {b.outcome_name}{pt:10s} | "
        f"odds={b.odds_at_bet:6.2f} | fair_p={b.fair_prob:.3f} | "
        f"EV={b.ev_percent:7.1f}% | Kelly={b.kelly_stake_percent:.2f}% | "
        f"stake=${b.stake:.2f}"
    )

session.close()
