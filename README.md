# Crypto ETL Pipeline

A production-style ETL pipeline that extracts real-time cryptocurrency market data from the CoinGecko API, transforms and enriches it, loads it into a SQLite data warehouse, and generates visual market reports.

## What It Does

```
CoinGecko API  →  Extract  →  Transform  →  Load (SQLite)  →  Report (Charts + Summary)
```

**Extract** — Pulls top 10 coins by market cap from the CoinGecko public API (no API key required).

**Transform** — Cleans raw JSON, selects relevant fields, and computes three derived metrics:
- `price_range_24h` — absolute high/low spread
- `price_range_pct` — spread as a % of current price (volatility proxy)
- `volume_to_market_cap_pct` — trading activity ratio

**Load** — Appends enriched records to a SQLite database with a `pipeline_runs` audit table that tracks every execution.

**Report** — Generates a PNG chart (market cap ranking + 24h change bar chart) and a plain-text summary of top gainers, losers, and most active coins.

## Project Structure

```
crypto-etl-pipeline/
├── src/
│   ├── extract.py       # API calls (CoinGecko)
│   ├── transform.py     # Data cleaning & feature engineering
│   ├── load.py          # SQLite write layer + audit logging
│   ├── pipeline.py      # Orchestration with error handling
│   └── report.py        # Chart generation & text summary
├── data/                # SQLite database (auto-created)
├── reports/             # Output charts and summaries
├── config.py            # Centralized settings
├── main.py              # CLI entry point
└── requirements.txt
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline (extract → transform → load → report)
python main.py --all

# Run pipeline only
python main.py --run

# Generate report from stored data
python main.py --report
```

## Sample Output

```
==================================================
  CRYPTO MARKET REPORT
  Generated: 2024-01-15T08:32:11 UTC
==================================================

TOP GAINERS (24h):
       name  current_price  price_change_percentage_24h
   Solana         98.42                         8.21
    Ripple          0.63                         4.15
  Ethereum       2341.10                         2.87

TOP LOSERS (24h):
       name  current_price  price_change_percentage_24h
   Dogecoin          0.08                        -3.42
    Cardano          0.51                        -1.88
    Polygon          0.87                        -1.10
```

## Tech Stack

| Layer      | Technology           |
|------------|----------------------|
| Language   | Python 3.10+         |
| HTTP       | requests             |
| Transform  | pandas               |
| Storage    | SQLite               |
| Reporting  | matplotlib           |
| Source API | CoinGecko (free tier)|

## Key Design Decisions

- **Append-only storage** — every run creates a new snapshot row, preserving full history for time-series analysis.
- **Audit table** — `pipeline_runs` records status, record count, and error messages for every execution.
- **Separation of concerns** — extract / transform / load are independent modules; swapping the database (e.g., to PostgreSQL) only requires changing `load.py`.
- **Config-driven** — `config.py` centralizes all tuneable parameters (coin count, currency, DB path).

## Extending This Project

- **Scheduler**: wrap `run_pipeline()` with `schedule` or Apache Airflow for automated runs
- **Database**: swap SQLite for PostgreSQL/BigQuery for production scale
- **Dashboard**: connect the SQLite DB to Metabase or Grafana for live monitoring
- **Alerts**: add threshold checks (e.g., notify when a coin drops >10% in 24h)
