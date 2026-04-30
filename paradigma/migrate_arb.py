"""Add new columns to bets table."""
from sqlalchemy import create_engine, text

DB = "postgresql://postgres:qeNbEaHEVuMjcWxhmcarFamuWdLyHhrm@shortline.proxy.rlwy.net:45254/railway"
e = create_engine(DB)
c = e.connect()

c.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS bet_type VARCHAR(16) DEFAULT 'value'"))
c.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS arb_group_id VARCHAR(64)"))
c.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS arb_profit_percent FLOAT"))
c.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS avg_ev_percent FLOAT"))
c.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS num_books INTEGER"))
c.commit()
c.close()
print("Columns added successfully")
