"""AlpacaBot Streamlit Dashboard"""
import json
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 路徑設定
ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from src.report.model import load_report, load_nav_history, HISTORY_INDEX_PATH, REPORTS_DIR
from src.data.benchmark import fetch_benchmark_nav_history

st.set_page_config(
    page_title="AlpacaBot Dashboard",
    page_icon="🤖",
    layout="wide",
)

# ── 樣式 ─────────────────────────────────────────────
st.markdown("""
<style>
.metric-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;
             padding:16px;text-align:center;}
.metric-val{font-size:1.6rem;font-weight:700;}
.metric-lbl{font-size:.75rem;color:#94a3b8;margin-top:4px;}
.disclaimer{background:#fef9c3;border:1px solid #fde68a;border-radius:8px;
            padding:12px;font-size:.8rem;color:#92400e;margin-top:8px;}
</style>""", unsafe_allow_html=True)


# ── 側欄：帳戶 & 日期選擇 ───────────────────────────
st.sidebar.title("🤖 AlpacaBot")
st.sidebar.markdown("---")

accounts_path = ROOT / "accounts" / "accounts_index.json"
account_ids = ["account_A"]
if accounts_path.exists():
    data = json.loads(accounts_path.read_text())
    account_ids = [a["account_id"] for a in data["accounts"] if a.get("enabled")]

selected_account = st.sidebar.selectbox("帳戶", account_ids)

# 可用日期清單
available_dates = []
if HISTORY_INDEX_PATH.exists():
    index = json.loads(HISTORY_INDEX_PATH.read_text())
    available_dates = sorted(
        {r["date"] for r in index.get("reports", []) if r["account_id"] == selected_account},
        reverse=True
    )

selected_date = st.sidebar.selectbox("報告日期", available_dates or ["（尚無報告）"])

st.sidebar.markdown("---")
show_qqq = st.sidebar.checkbox("顯示 QQQ (NASDAQ)", value=True)
show_spy = st.sidebar.checkbox("顯示 SPY (S&P500)", value=True)

st.sidebar.markdown("""
<div class="disclaimer">
⚠️ 本系統僅供資訊整理與研究參考，不構成任何投資建議。<br>投資有風險，請謹慎評估。
</div>""", unsafe_allow_html=True)

# ── 載入報告 ─────────────────────────────────────────
report = None
if available_dates:
    report = load_report(selected_account, selected_date)

if not report:
    st.title("🤖 AlpacaBot Dashboard")
    st.info("📭 尚無報告資料。請執行 `python main.py` 產生第一份報告。")
    st.stop()

s = report["account_summary"]
top10 = report.get("top10_today", [])
positions = report.get("positions", [])
trades = report.get("trades_executed", [])
bench = report.get("benchmark", {})
nav_history = report.get("nav_history", [])
watchlist = report.get("watchlist", {})

# ── 標題 ─────────────────────────────────────────────
st.title(f"🤖 AlpacaBot Dashboard")
st.markdown(f"**帳戶：** {selected_account} ｜ **策略：** {report.get('strategy_id')} ｜ **日期：** {report['date']}")

# ── KPI 卡片 ─────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
pnl_color = "normal" if s["daily_pnl"] >= 0 else "inverse"
c1.metric("💰 總 NAV", f"${s['nav']:,.2f}")
c2.metric("📈 今日損益",
          f"${s['daily_pnl']:+,.2f}",
          f"{s['daily_pnl_pct']:+.2f}%",
          delta_color=pnl_color)
c3.metric("🏦 現金水位", f"${s['cash']:,.0f}", f"{s['cash_pct']:.1f}%")
c4.metric("📉 當前回撤", f"{s['drawdown_pct']:.2f}%",
          f"最大 {s['max_drawdown_pct']:.2f}%", delta_color="inverse")

st.markdown("---")

# ── NAV 歷史折線圖 ───────────────────────────────────
st.subheader("📊 NAV 歷史 vs 大盤")

nav_df = pd.DataFrame(nav_history)
fig = go.Figure()

if not nav_df.empty:
    base_nav = nav_df["nav"].iloc[0]
    nav_df["pct"] = (nav_df["nav"] - base_nav) / base_nav * 100
    fig.add_trace(go.Scatter(
        x=nav_df["date"], y=nav_df["pct"],
        name="我的 NAV", line=dict(color="#6366f1", width=2.5),
        hovertemplate="%{y:.2f}%<extra>我的 NAV</extra>"
    ))

if show_qqq or show_spy:
    with st.spinner("載入基準資料..."):
        bm_hist = fetch_benchmark_nav_history(days=len(nav_df) + 10 if not nav_df.empty else 90)
    if show_qqq and bm_hist.get("QQQ"):
        bm_df = pd.DataFrame(bm_hist["QQQ"])
        bm_df["pct"] = bm_df["value"] - 100
        fig.add_trace(go.Scatter(
            x=bm_df["date"], y=bm_df["pct"],
            name="QQQ (NASDAQ)", line=dict(color="#f59e0b", width=1.5, dash="dot"),
            hovertemplate="%{y:.2f}%<extra>QQQ</extra>"
        ))
    if show_spy and bm_hist.get("SPY"):
        bm_df = pd.DataFrame(bm_hist["SPY"])
        bm_df["pct"] = bm_df["value"] - 100
        fig.add_trace(go.Scatter(
            x=bm_df["date"], y=bm_df["pct"],
            name="SPY (S&P500)", line=dict(color="#10b981", width=1.5, dash="dash"),
            hovertemplate="%{y:.2f}%<extra>SPY</extra>"
        ))

fig.update_layout(
    yaxis_title="累積報酬 (%)", xaxis_title="",
    hovermode="x unified", height=320,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=10, b=0),
)
fig.add_hline(y=0, line_dash="solid", line_color="#e2e8f0")
st.plotly_chart(fig, use_container_width=True)

# ── 回撤圖 ───────────────────────────────────────────
with st.expander("📉 回撤圖"):
    if nav_df.empty:
        st.info("尚無資料")
    else:
        navs = nav_df["nav"].tolist()
        drawdowns = []
        peak = navs[0]
        for n in navs:
            peak = max(peak, n)
            drawdowns.append((n - peak) / peak * 100)
        dd_df = pd.DataFrame({"date": nav_df["date"], "drawdown": drawdowns})
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=dd_df["date"], y=dd_df["drawdown"],
            fill="tozeroy", name="回撤",
            line=dict(color="#ef4444"), fillcolor="rgba(239,68,68,0.15)"
        ))
        fig2.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0),
                           yaxis_title="回撤 (%)")
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── 持倉表格 ─────────────────────────────────────────
st.subheader("📋 持倉明細")

if positions:
    pos_df = pd.DataFrame(positions)[
        ["symbol", "qty", "avg_entry_price", "current_price",
         "market_value", "weight_pct", "unrealized_pnl",
         "unrealized_pnl_pct", "perf_1d_pct", "perf_1w_pct",
         "perf_1m_pct", "pe_ratio"]
    ].rename(columns={
        "symbol": "股票", "qty": "股數",
        "avg_entry_price": "均價", "current_price": "現價",
        "market_value": "市值", "weight_pct": "權重%",
        "unrealized_pnl": "未實現損益", "unrealized_pnl_pct": "損益%",
        "perf_1d_pct": "1日%", "perf_1w_pct": "1週%",
        "perf_1m_pct": "1月%", "pe_ratio": "P/E",
    })

    def color_pnl(val):
        try:
            v = float(val)
            return "color: #16a34a" if v >= 0 else "color: #dc2626"
        except Exception:
            return ""

    styled = pos_df.style.applymap(color_pnl, subset=["損益%", "1日%", "1週%", "1月%"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("目前無持倉")

# ── 今日交易 ──────────────────────────────────────────
if trades:
    st.subheader("🔔 今日交易")
    for t in trades:
        icon = "🟢" if t.get("action") == "BUY" else "🔴"
        st.write(f"{icon} **{t.get('action')}** {t.get('symbol')} × {t.get('qty')} 股")

st.markdown("---")

# ── NASDAQ 前 10 ──────────────────────────────────────
col_l, col_r = st.columns([1, 1])

with col_l:
    st.subheader("🏆 今日 NASDAQ 前 10")
    if top10:
        t10_df = pd.DataFrame(top10)[["rank", "symbol", "price", "market_cap_B"]]
        t10_df.columns = ["排名", "股票", "現價", "市值(B)"]
        held = {p["symbol"] for p in positions}
        def highlight_held(row):
            return ["background-color: #f0fdf4" if row["股票"] in held else "" for _ in row]
        st.dataframe(t10_df.style.apply(highlight_held, axis=1),
                     use_container_width=True, hide_index=True)
        st.caption("綠底 = 目前持倉中")

with col_r:
    st.subheader("📈 大盤比較")
    bench_rows = []
    if bench:
        bench_rows.append({"指數": "QQQ (NASDAQ)",
                           "今日%": bench.get("QQQ", {}).get("1d", 0),
                           "1週%":  bench.get("QQQ", {}).get("1w", 0),
                           "1月%":  bench.get("QQQ", {}).get("1m", 0)})
        bench_rows.append({"指數": "SPY (S&P500)",
                           "今日%": bench.get("SPY", {}).get("1d", 0),
                           "1週%":  bench.get("SPY", {}).get("1w", 0),
                           "1月%":  bench.get("SPY", {}).get("1m", 0)})
    bench_rows.append({"指數": "我的帳戶",
                       "今日%": s["daily_pnl_pct"],
                       "1週%": 0, "1月%": 0})
    if bench_rows:
        b_df = pd.DataFrame(bench_rows)
        styled_b = b_df.style.applymap(color_pnl, subset=["今日%", "1週%", "1月%"])
        st.dataframe(styled_b, use_container_width=True, hide_index=True)

st.markdown("---")

# ── 關注股票 ──────────────────────────────────────────
st.subheader("🔎 關注股票")
cat_labels = {"ai_tech": "🤖 AI 科技", "semicon": "💾 半導體", "growth": "🚀 成長股"}

if watchlist:
    for cat, items in watchlist.items():
        st.markdown(f"**{cat_labels.get(cat, cat)}**")
        wl_df = pd.DataFrame(items)
        if not wl_df.empty and "perf_1d_pct" in wl_df.columns:
            wl_df = wl_df.rename(columns={"symbol": "股票", "perf_1d_pct": "今日%"})
            st.dataframe(
                wl_df.style.applymap(color_pnl, subset=["今日%"]),
                use_container_width=True, hide_index=True
            )
else:
    st.info("關注股票資料尚未載入")

# ── 免責聲明 ──────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
⚠️ 本 Dashboard 及所有顯示內容，均僅供資訊整理與研究參考，不構成任何投資建議。
股票投資具有風險，過去績效不代表未來報酬，投資前請謹慎評估個人風險承受能力。
</div>""", unsafe_allow_html=True)
