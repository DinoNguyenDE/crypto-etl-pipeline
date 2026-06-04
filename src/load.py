import sqlite3
import os
import pandas as pd
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)

CREATE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS coin_snapshots (
    id                          TEXT,
    symbol                      TEXT,
    name                        TEXT,
    current_price               REAL,
    market_cap                  REAL,
    market_cap_rank             INTEGER,
    total_volume                REAL,
    high_24h                    REAL,
    low_24h                     REAL,
    price_change_percentage_24h REAL,
    price_change_percentage_7d  REAL,
    circulating_supply          REAL,
    last_updated                TEXT,
    price_range_24h             REAL,
    price_range_pct             REAL,
    volume_to_market_cap_pct    REAL,
    ingested_at                 TEXT
)
"""

CREATE_RUNS = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at          TEXT,
    records_loaded  INTEGER,
    status          TEXT,
    error_message   TEXT
)
"""


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _connect()
    conn.execute(CREATE_SNAPSHOTS)
    conn.execute(CREATE_RUNS)
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def load_coins(df: pd.DataFrame):
    conn = _connect()
    df.to_sql("coin_snapshots", conn, if_exists="append", index=False)
    conn.close()
    logger.info(f"Loaded {len(df)} records into coin_snapshots")


def log_run(records_loaded: int, status: str, error_message: str = None):
    conn = _connect()
    conn.execute(
        "INSERT INTO pipeline_runs (ran_at, records_loaded, status, error_message) VALUES (?,?,?,?)",
        (datetime.utcnow().isoformat(), records_loaded, status, error_message),
    )
    conn.commit()
    conn.close()
