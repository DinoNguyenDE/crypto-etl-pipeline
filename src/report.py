import sqlite3
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import DB_PATH


def _latest_snapshot() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT * FROM coin_snapshots WHERE ingested_at = (SELECT MAX(ingested_at) FROM coin_snapshots)",
        conn,
    )
    conn.close()
    return df


def generate_charts(df: pd.DataFrame):
    os.makedirs("reports", exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Crypto Market Snapshot", fontsize=14, fontweight="bold")

    # Market cap horizontal bar
    df_sorted = df.sort_values("market_cap")
    axes[0].barh(df_sorted["symbol"].str.upper(), df_sorted["market_cap"] / 1e9, color="steelblue")
    axes[0].set_xlabel("Market Cap (Billion USD)")
    axes[0].set_title("Market Cap Ranking")

    # 24h price change
    colors = ["#2ecc71" if v > 0 else "#e74c3c" for v in df["price_change_percentage_24h"]]
    axes[1].bar(df["symbol"].str.upper(), df["price_change_percentage_24h"], color=colors)
    axes[1].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[1].set_ylabel("Change (%)")
    axes[1].set_title("24h Price Change (%)")
    axes[1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    path = "reports/market_overview.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def generate_text_summary(df: pd.DataFrame) -> str:
    top3 = df.nlargest(3, "price_change_percentage_24h")[["name", "current_price", "price_change_percentage_24h"]]
    bot3 = df.nsmallest(3, "price_change_percentage_24h")[["name", "current_price", "price_change_percentage_24h"]]
    high_vol = df.nlargest(3, "volume_to_market_cap_pct")[["name", "volume_to_market_cap_pct"]]

    summary = f"""
{'='*50}
  CRYPTO MARKET REPORT
  Generated: {df['ingested_at'].iloc[0]} UTC
{'='*50}

TOP GAINERS (24h):
{top3.to_string(index=False)}

TOP LOSERS (24h):
{bot3.to_string(index=False)}

HIGHEST TRADING ACTIVITY (Volume/MarketCap %):
{high_vol.to_string(index=False)}

TOTAL RECORDS IN SNAPSHOT: {len(df)}
{'='*50}
"""
    return summary


def generate_report():
    df = _latest_snapshot()
    if df.empty:
        print("No data found. Run the pipeline first: python main.py --run")
        return

    chart_path = generate_charts(df)
    summary = generate_text_summary(df)

    with open("reports/summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)

    print(summary)
    print(f"Chart saved: {chart_path}")
    return df
