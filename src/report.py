import sqlite3
import os
import json
from datetime import datetime, timezone
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


def generate_html_report(df: pd.DataFrame):
    os.makedirs("reports", exist_ok=True)

    run_time = str(df["ingested_at"].iloc[0]) if "ingested_at" in df.columns else "â"
    total_records = len(df)
    top_gainer = df.nlargest(1, "price_change_percentage_24h").iloc[0]
    top_loser  = df.nsmallest(1, "price_change_percentage_24h").iloc[0]
    avg_mcap_b = df["market_cap"].mean() / 1e9

    df_mc  = df.sort_values("market_cap", ascending=True).tail(10)
    mc_labels = json.dumps(df_mc["symbol"].str.upper().tolist())
    mc_values = json.dumps((df_mc["market_cap"] / 1e9).round(2).tolist())

    df_ch = df.sort_values("symbol")
    ch_labels = json.dumps(df_ch["symbol"].str.upper().tolist())
    ch_values = json.dumps(df_ch["price_change_percentage_24h"].round(2).tolist())
    ch_colors = json.dumps(["#10b981" if v > 0 else "#ef4444"
                            for v in df_ch["price_change_percentage_24h"]])

    top10 = df.sort_values("market_cap", ascending=False).head(10)
    rows_html = ""
    for i, row in enumerate(top10.itertuples(), 1):
        chg = row.price_change_percentage_24h
        chg_cls = "pos" if chg > 0 else "neg"
        sign = "+" if chg > 0 else ""
        mcap = f"${row.market_cap / 1e9:.2f}B"
        price = f"${row.current_price:,.4f}" if row.current_price < 10 else f"${row.current_price:,.2f}"
        rows_html += (
            f'<tr><td class="num t2">{i}</td>'
            f'<td><span class="cname">{row.name}</span> '
            f'<span class="csym">{row.symbol.upper()}</span></td>'
            f'<td class="num">{price}</td>'
            f'<td class="num {chg_cls}">{sign}{chg:.2f}%</td>'
            f'<td class="num">{mcap}</td></tr>\n'
        )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crypto ETL Pipeline &mdash; Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg:    #06080f;
  --surf:  #0c1220;
  --surf2: #131e30;
  --brd:   #1a2d48;
  --txt:   #d9e4f0;
  --t2:    #617799;
  --sky:   #38bdf8;
  --buy:   #10b981;
  --sell:  #ef4444;
  --warn:  #f59e0b;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--txt); font-family: 'Inter', system-ui, sans-serif; font-size: 14px; }}

/* HEADER */
.hdr {{
  background: var(--surf); border-bottom: 1px solid var(--brd);
  padding: 14px 28px; display: flex; align-items: center; justify-content: space-between;
}}
.hdr-brand {{ display: flex; align-items: center; gap: 10px; }}
.hdr-icon {{
  width: 30px; height: 30px; border: 1.5px solid var(--sky); border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
}}
.hdr-name {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.08em; }}
.hdr-name em {{ color: var(--t2); font-style: normal; font-weight: 400; }}
.hdr-right {{
  display: flex; align-items: center; gap: 12px;
  font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: var(--t2);
}}
.ok-badge {{
  display: flex; align-items: center; gap: 6px;
  background: rgba(16,185,129,.08); border: 1px solid rgba(16,185,129,.22);
  border-radius: 3px; padding: 4px 10px; color: var(--buy);
}}
.ok-dot {{ width: 5px; height: 5px; border-radius: 50%; background: var(--buy); box-shadow: 0 0 6px var(--buy); }}

/* MAIN */
.wrap {{ max-width: 1300px; margin: 0 auto; padding: 24px 28px 52px; }}

/* CARDS */
.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 28px; }}
.card {{
  background: var(--surf); border: 1px solid var(--brd);
  border-top: 2px solid transparent; border-radius: 6px; padding: 16px 18px;
}}
.card-sky  {{ border-top-color: var(--sky); }}
.card-buy  {{ border-top-color: var(--buy); }}
.card-sell {{ border-top-color: var(--sell); }}
.card-warn {{ border-top-color: var(--warn); }}
.clbl {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.6rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.14em;
  color: var(--t2); margin-bottom: 10px;
}}
.cval {{ font-family: 'IBM Plex Mono', monospace; font-size: 2rem; font-weight: 600; line-height: 1; }}
.card-sky  .cval {{ color: var(--sky); }}
.card-buy  .cval {{ color: var(--buy); }}
.card-sell .cval {{ color: var(--sell); }}
.card-warn .cval {{ color: var(--warn); }}
.csub {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: var(--t2); margin-top: 6px; }}

/* SECTION HEADER */
.sec {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
.sec-txt {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.14em;
  color: var(--t2); white-space: nowrap;
}}
.sec-line {{ flex: 1; height: 1px; background: var(--brd); }}

/* PIPELINE */
.pipe-wrap {{
  background: var(--surf); border: 1px solid var(--brd); border-radius: 6px;
  padding: 22px 24px; margin-bottom: 28px;
  display: flex; align-items: center;
}}
.pipe-stage {{
  flex: 1; background: var(--surf2); border: 1px solid var(--brd);
  border-radius: 6px; padding: 16px 18px; position: relative;
}}
.pipe-stage-num {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.6rem; font-weight: 500; color: var(--sky);
  letter-spacing: 0.12em; margin-bottom: 4px;
}}
.pipe-stage-name {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 1rem; font-weight: 600; color: var(--txt);
}}
.pipe-stage-sub {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem; color: var(--t2); margin-top: 3px;
}}
.pipe-status {{
  position: absolute; top: 12px; right: 12px;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--buy); box-shadow: 0 0 7px var(--buy);
}}
.pipe-conn {{
  width: 48px; flex-shrink: 0; height: 2px;
  margin: 0 -1px; position: relative; overflow: hidden;
  background: var(--brd);
}}
.pipe-conn::after {{
  content: '';
  position: absolute; top: 0; left: -100%; width: 200%; height: 100%;
  background: repeating-linear-gradient(
    90deg,
    transparent 0, transparent 6px,
    var(--sky) 6px, var(--sky) 12px
  );
  animation: flow-dash 0.9s linear infinite;
}}
@keyframes flow-dash {{ to {{ transform: translateX(50%); }} }}

/* CHARTS */
.charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 28px; }}
.chart-card {{
  background: var(--surf); border: 1px solid var(--brd); border-radius: 6px; padding: 14px 16px;
}}
.chart-title {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.7rem; font-weight: 500; color: var(--t2);
  margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.08em;
}}
.chart-wrap {{ height: 220px; position: relative; }}

/* TABLE */
.tbl-outer {{ border: 1px solid var(--brd); border-radius: 6px; overflow: hidden; margin-bottom: 24px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.86rem; }}
thead th {{
  background: var(--surf2); padding: 9px 14px; text-align: left;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.6rem; font-weight: 500; color: var(--t2);
  text-transform: uppercase; letter-spacing: 0.1em;
  border-bottom: 1px solid var(--brd);
}}
tbody td {{ padding: 10px 14px; border-bottom: 1px solid rgba(26,45,72,.5); }}
tbody tr:last-child td {{ border-bottom: none; }}
tbody tr:hover td {{ background: rgba(19,30,48,.6); }}
.cname {{ font-weight: 600; }}
.csym  {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; color: var(--t2); margin-left: 5px; }}
.num   {{ font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }}
.t2    {{ color: var(--t2); }}
.pos   {{ color: var(--buy); }}
.neg   {{ color: var(--sell); }}

footer {{
  border-top: 1px solid var(--brd); padding-top: 14px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.65rem; color: var(--t2); text-align: center;
}}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-brand">
    <div class="hdr-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
    </div>
    <div class="hdr-name">ETL<em>/CRYPTO</em></div>
  </div>
  <div class="hdr-right">
    <span>Run: {run_time}</span>
    <div class="ok-badge"><div class="ok-dot"></div>Completed</div>
  </div>
</div>

<div class="wrap">

  <div class="cards">
    <div class="card card-sky">
      <div class="clbl">Records Loaded</div>
      <div class="cval">{total_records}</div>
      <div class="csub">Coins in snapshot</div>
    </div>
    <div class="card card-buy">
      <div class="clbl">Top Gainer 24h</div>
      <div class="cval">{top_gainer['symbol'].upper()}</div>
      <div class="csub">+{top_gainer['price_change_percentage_24h']:.2f}%</div>
    </div>
    <div class="card card-sell">
      <div class="clbl">Top Loser 24h</div>
      <div class="cval">{top_loser['symbol'].upper()}</div>
      <div class="csub">{top_loser['price_change_percentage_24h']:.2f}%</div>
    </div>
    <div class="card card-warn">
      <div class="clbl">Avg Market Cap</div>
      <div class="cval">${avg_mcap_b:.1f}B</div>
      <div class="csub">Across all coins</div>
    </div>
  </div>

  <div class="sec"><div class="sec-txt">ETL Pipeline Status</div><div class="sec-line"></div></div>
  <div class="pipe-wrap">
    <div class="pipe-stage">
      <div class="pipe-status"></div>
      <div class="pipe-stage-num">01 &middot; EXTRACT</div>
      <div class="pipe-stage-name">Extract</div>
      <div class="pipe-stage-sub">CoinGecko API</div>
    </div>
    <div class="pipe-conn"></div>
    <div class="pipe-stage">
      <div class="pipe-status"></div>
      <div class="pipe-stage-num">02 &middot; TRANSFORM</div>
      <div class="pipe-stage-name">Transform</div>
      <div class="pipe-stage-sub">pandas &middot; feature eng.</div>
    </div>
    <div class="pipe-conn"></div>
    <div class="pipe-stage">
      <div class="pipe-status"></div>
      <div class="pipe-stage-num">03 &middot; LOAD</div>
      <div class="pipe-stage-name">Load</div>
      <div class="pipe-stage-sub">SQLite database</div>
    </div>
  </div>

  <div class="sec"><div class="sec-txt">Market Overview</div><div class="sec-line"></div></div>
  <div class="charts-row">
    <div class="chart-card">
      <div class="chart-title">Market Cap Ranking (B USD)</div>
      <div class="chart-wrap"><canvas id="mcChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">24h Price Change (%)</div>
      <div class="chart-wrap"><canvas id="chChart"></canvas></div>
    </div>
  </div>

  <div class="sec"><div class="sec-txt">Top 10 by Market Cap</div><div class="sec-line"></div></div>
  <div class="tbl-outer">
    <table>
      <thead>
        <tr><th>#</th><th>Asset</th><th>Price</th><th>24h &Delta;</th><th>Market Cap</th></tr>
      </thead>
  2   <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <footer>ETL/CRYPTO &nbsp;&middot;&nbsp; Generated {now_utc} &nbsp;&middot;&nbsp; Data: CoinGecko &nbsp;&middot;&nbsp; Not financial advice.</footer>
</div>

<script>
var mcLabels = {mc_labels};
var mcValues = {mc_values};
var chLabels = {ch_labels};
var chValues = {ch_values};
var chColors = {ch_colors};

new Chart(document.getElementById('mcChart'), {{
  type: 'bar',
  data: {{
    labels: mcLabels,
    datasets: [{{
      data: mcValues,
      backgroundColor: function(ctx) {{
        var chart = ctx.chart, a = chart.chartArea;
        if (!a) return 'rgba(56,189,248,0.5)';
        var g = chart.ctx.createLinearGradient(a.left, 0, a.right, 0);
        g.addColorStop(0, 'rgba(56,189,248,0.1)');
        g.addColorStop(1, 'rgba(56,189,248,0.7)');
        return g;
      }},
      borderRadius: 2, borderSkipped: false
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: function(i) {{ return ' $' + i.raw + 'B'; }} }} }}
    }},
    scales: {{
      x: {{
        grid: {{ color: 'rgba(26,45,72,0.8)' }},
        ticks: {{ color: '#617799', font: {{ family: 'IBM Plex Mono, monospace', size: 9 }} }}
      }},
      y: {{
        grid: {{ display: fa
