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

    run_time = str(df["ingested_at"].iloc[0]) if "ingested_at" in df.columns else "—"
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
    ch_colors = json.dumps(["#10b981" if v > 0 else "#f43f5e"
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
<title>Crypto ETL Pipeline — Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg:     #f1f5f9;
  --surf:   #ffffff;
  --border: #e2e8f0;
  --text:   #1e293b;
  --t2:     #64748b;
  --accent: #6366f1;
  --a2:     #818cf8;
  --buy:    #10b981;
  --sell:   #f43f5e;
  --hdr:    #1e293b;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif; font-size: 14px; }}
.header {{
  background: var(--hdr); color: #f8fafc;
  padding: 16px 32px; display: flex; align-items: center; justify-content: space-between;
}}
.header-left {{ display: flex; align-items: center; gap: 12px; }}
.header-icon {{
  width: 36px; height: 36px; background: var(--accent);
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
}}
.header-title {{ font-size: 1.05rem; font-weight: 700; }}
.header-sub {{ font-size: 0.72rem; color: #94a3b8; margin-top: 1px; }}
.status-badge {{
  background: rgba(16,185,129,.15); color: #10b981;
  border: 1px solid rgba(16,185,129,.3);
  border-radius: 20px; padding: 4px 12px; font-size: 0.75rem; font-weight: 600;
  display: flex; align-items: center; gap: 6px;
}}
.sdot {{ width: 6px; height: 6px; background: #10b981; border-radius: 50%; }}
.wrap {{ max-width: 1320px; margin: 0 auto; padding: 24px 28px 48px; }}
.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }}
.card {{
  background: var(--surf); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px 20px;
}}
.clabel {{ font-size: 0.68rem; font-weight: 600; color: var(--t2); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }}
.cvalue {{ font-size: 1.65rem; font-weight: 700; line-height: 1; }}
.csub {{ font-size: 0.72rem; color: var(--t2); margin-top: 5px; }}
.card-a {{ border-top: 3px solid var(--accent); }}
.card-b {{ border-top: 3px solid var(--buy); }}
.card-c {{ border-top: 3px solid var(--sell); }}
.card-d {{ border-top: 3px solid #f59e0b; }}
.stitle {{
  font-size: 0.7rem; font-weight: 700; color: var(--t2);
  text-transform: uppercase; letter-spacing: 1.2px;
  display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
}}
.stitle::after {{ content: ''; flex: 1; height: 1px; background: var(--border); }}
.charts-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 24px; }}
.chart-card {{
  background: var(--surf); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px 18px;
}}
.chart-title {{ font-size: 0.82rem; font-weight: 600; color: var(--text); margin-bottom: 12px; }}
.chart-wrap {{ height: 240px; position: relative; }}
.flow-section {{
  background: var(--surf); border: 1px solid var(--border);
  border-radius: 10px; padding: 20px 24px; margin-bottom: 24px;
}}
.flow {{ display: flex; align-items: center; gap: 0; }}
.flow-step {{
  flex: 1; background: var(--bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px 16px; position: relative;
}}
.flow-step-icon {{ font-size: 1.4rem; margin-bottom: 4px; }}
.flow-step-name {{ font-weight: 700; font-size: 0.88rem; color: var(--text); }}
.flow-step-sub {{ font-size: 0.72rem; color: var(--t2); margin-top: 2px; }}
.flow-step-status {{
  position: absolute; top: 10px; right: 10px;
  width: 8px; height: 8px; border-radius: 50%; background: var(--buy);
  box-shadow: 0 0 6px var(--buy);
}}
.flow-arrow {{
  width: 36px; flex-shrink: 0; text-align: center;
  color: var(--t2); font-size: 1.1rem;
}}
.table-wrap {{
  background: var(--surf); border: 1px solid var(--border);
  border-radius: 10px; overflow: hidden; margin-bottom: 24px;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 0.86rem; }}
thead th {{
  background: #f8fafc; padding: 10px 16px;
  text-align: left; font-size: 0.68rem; font-weight: 600;
  color: var(--t2); text-transform: uppercase; letter-spacing: .8px;
  border-bottom: 1px solid var(--border);
}}
tbody td {{ padding: 11px 16px; border-bottom: 1px solid var(--border); }}
tbody tr:last-child td {{ border-bottom: none; }}
tbody tr:hover td {{ background: #f8fafc; }}
.cname {{ font-weight: 600; }}
.csym {{ font-size: 0.7rem; color: var(--t2); margin-left: 5px; }}
.num {{ font-variant-numeric: tabular-nums; }}
.t2 {{ color: var(--t2); }}
.pos {{ color: var(--buy); font-weight: 500; }}
.neg {{ color: var(--sell); font-weight: 500; }}
footer {{ text-align: center; color: var(--t2); font-size: 0.7rem; border-top: 1px solid var(--border); padding-top: 16px; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="header-icon">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
    </div>
    <div>
      <div class="header-title">Crypto ETL Pipeline</div>
      <div class="header-sub">Last run: {run_time}</div>
    </div>
  </div>
  <div class="status-badge">
    <div class="sdot"></div>
    Completed
  </div>
</div>

<div class="wrap">

  <div class="cards">
    <div class="card card-a">
      <div class="clabel">Records Loaded</div>
      <div class="cvalue" style="color:var(--accent)">{total_records}</div>
      <div class="csub">Coins in snapshot</div>
    </div>
    <div class="card card-b">
      <div class="clabel">Top Gainer 24h</div>
      <div class="cvalue" style="color:var(--buy)">{top_gainer['symbol'].upper()}</div>
      <div class="csub">+{top_gainer['price_change_percentage_24h']:.2f}%</div>
    </div>
    <div class="card card-c">
      <div class="clabel">Top Loser 24h</div>
      <div class="cvalue" style="color:var(--sell)">{top_loser['symbol'].upper()}</div>
      <div class="csub">{top_loser['price_change_percentage_24h']:.2f}%</div>
    </div>
    <div class="card card-d">
      <div class="clabel">Avg Market Cap</div>
      <div class="cvalue" style="color:#f59e0b">${avg_mcap_b:.1f}B</div>
      <div class="csub">Across all coins</div>
    </div>
  </div>

  <div class="stitle">ETL Pipeline Status</div>
  <div class="flow-section">
    <div class="flow">
      <div class="flow-step">
        <div class="flow-step-status"></div>
        <div class="flow-step-icon">⬇</div>
        <div class="flow-step-name">Extract</div>
        <div class="flow-step-sub">CoinGecko API</div>
      </div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">
        <div class="flow-step-status"></div>
        <div class="flow-step-icon">⚙</div>
        <div class="flow-step-name">Transform</div>
        <div class="flow-step-sub">pandas · feature eng.</div>
      </div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">
        <div class="flow-step-status"></div>
        <div class="flow-step-icon">💾</div>
        <div class="flow-step-name">Load</div>
        <div class="flow-step-sub">SQLite database</div>
      </div>
    </div>
  </div>

  <div class="stitle">Market Overview</div>
  <div class="charts-row">
    <div class="chart-card">
      <div class="chart-title">Market Cap Ranking (Billion USD)</div>
      <div class="chart-wrap"><canvas id="mcChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">24h Price Change (%)</div>
      <div class="chart-wrap"><canvas id="chChart"></canvas></div>
    </div>
  </div>

  <div class="stitle">Top 10 by Market Cap</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>#</th><th>Asset</th><th>Price</th><th>24h %</th><th>Market Cap</th></tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <footer>Generated {now_utc} &nbsp;&middot;&nbsp; Data: CoinGecko &nbsp;&middot;&nbsp; Not financial advice.</footer>
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
        if (!a) return 'rgba(99,102,241,0.7)';
        var g = chart.ctx.createLinearGradient(a.left, 0, a.right, 0);
        g.addColorStop(0, 'rgba(99,102,241,0.2)');
        g.addColorStop(1, 'rgba(99,102,241,0.85)');
        return g;
      }},
      borderRadius: 4, borderSkipped: false
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: function(i) {{ return ' $' + i.raw + 'B'; }} }} }} }},
    scales: {{
      x: {{ grid: {{ color: 'rgba(226,232,240,0.8)' }}, ticks: {{ color: '#64748b', font: {{ size: 10 }} }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ color: '#1e293b', font: {{ size: 11, weight: '600' }} }} }}
    }}
  }}
}});

new Chart(document.getElementById('chChart'), {{
  type: 'bar',
  data: {{
    labels: chLabels,
    datasets: [{{
      data: chValues,
      backgroundColor: chColors,
      borderRadius: 4, borderSkipped: false
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: function(i) {{ var s = i.raw > 0 ? '+' : ''; return ' ' + s + i.raw + '%'; }} }} }} }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color: '#1e293b', font: {{ size: 10, weight: '600' }} }} }},
      y: {{
        grid: {{ color: 'rgba(226,232,240,0.8)' }},
        ticks: {{ color: '#64748b', font: {{ size: 10 }}, callback: function(v) {{ return v + '%'; }} }},
        afterDataLimits: function(axis) {{ var m = Math.max(Math.abs(axis.min), Math.abs(axis.max)) * 1.1; axis.min = -m; axis.max = m; }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

    path = "reports/etl_dashboard.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML dashboard saved: {path}")
    return path


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
