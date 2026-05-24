from __future__ import annotations
"""
AlpacaBot Streamlit Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
設計原則：本檔案不呼叫任何外部 API（Alpaca / yfinance / requests）。
所有資料均來自 reports/ 目錄內由 GitHub Actions 預先生成的 JSON 報告。
因此 Dashboard 可部署至 Streamlit Community Cloud，隨時可用。
"""
import json
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ── 路徑設定（相容本機與 Streamlit Cloud）─────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# 資料讀取來自獨立模組（可單獨測試，不依賴 Streamlit context）
from src.dashboard.data import (
    get_account_ids,
    get_available_dates,
    get_all_account_nav_history,
    load_report_json,
)


# ═══════════════════════════════════════════════════════════════════════════
# 頁面設定
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="AlpacaBot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.disclaimer{background:#fef9c3;border:1px solid #fde68a;border-radius:8px;
            padding:12px;font-size:.8rem;color:#92400e;margin-top:8px;}
.section-head{font-size:.75rem;font-weight:600;color:#94a3b8;
              text-transform:uppercase;letter-spacing:.08em;margin-bottom:.5rem;}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# 側欄
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🤖 AlpacaBot")
    st.caption("全自動美股投資系統")
    st.divider()

    account_ids = get_account_ids()
    selected_account = st.selectbox("📁 帳戶", account_ids)

    available_dates = get_available_dates(selected_account)
    selected_date = st.selectbox(
        "📅 報告日期",
        available_dates if available_dates else ["（尚無報告）"],
    )

    st.divider()
    st.markdown("**📊 圖表設定**")
    show_qqq = st.checkbox("QQQ (NASDAQ 100)", value=True)
    show_spy = st.checkbox("SPY (S&P 500)", value=True)

    st.divider()
    st.markdown("""
<div class="disclaimer">
⚠️ 本 Dashboard 及所有顯示內容，<br>
均僅供資訊整理與研究參考，<br>
<b>不構成任何投資建議。</b><br>
投資有風險，請謹慎評估。
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# 載入報告
# ═══════════════════════════════════════════════════════════════════════════

report = None
if available_dates:
    report = load_report_json(selected_account, selected_date)

if not report:
    st.title("🤖 AlpacaBot Dashboard")
    st.info(
        "📭 **尚無報告資料。**\n\n"
        "請執行 `DRY_RUN=true python3 main.py` 產生第一份報告，"
        "或等待 GitHub Actions 自動執行後重新整理頁面。"
    )
    st.stop()

# 取出常用欄位
s      = report["account_summary"]
top10  = report.get("top10_today", [])
pos    = report.get("positions", [])
trades = report.get("trades_executed", [])
bench  = report.get("benchmark", {})
wl     = report.get("watchlist", {})
# benchmark_nav_history 由 GitHub Actions 預先存入 JSON，不需即時呼叫 API
bm_hist = report.get("benchmark_nav_history", {})
nav_history = report.get("nav_history", [])

# ═══════════════════════════════════════════════════════════════════════════
# 標題
# ═══════════════════════════════════════════════════════════════════════════

col_title, col_meta = st.columns([3, 1])
with col_title:
    st.title("🤖 AlpacaBot Dashboard")
with col_meta:
    st.caption(f"帳戶：**{selected_account}**")
    st.caption(f"策略：`{report.get('strategy_id', '—')}`")
    st.caption(f"報告：**{report['date']}**")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# KPI 卡片
# ═══════════════════════════════════════════════════════════════════════════

c1, c2, c3, c4 = st.columns(4)
pnl_delta_color = "normal" if s["daily_pnl"] >= 0 else "inverse"

c1.metric("💰 總 NAV",      f"${s['nav']:,.2f}")
c2.metric(
    "📈 今日損益",
    f"${s['daily_pnl']:+,.2f}",
    f"{s['daily_pnl_pct']:+.2f}%",
    delta_color=pnl_delta_color,
)
c3.metric("🏦 現金水位",    f"${s['cash']:,.0f}",  f"{s['cash_pct']:.1f}%")
c4.metric(
    "📉 當前回撤",
    f"{s['drawdown_pct']:.2f}%",
    f"最大 {s['max_drawdown_pct']:.2f}%",
    delta_color="inverse",
)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# NAV 折線圖（資料完全來自 JSON，零 API 呼叫）
# ═══════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-head">📊 NAV 歷史 vs 大盤（資料來自預計算 JSON）</p>',
            unsafe_allow_html=True)

nav_df = pd.DataFrame(nav_history) if nav_history else pd.DataFrame()
fig = go.Figure()

if not nav_df.empty and "nav" in nav_df.columns:
    base = nav_df["nav"].iloc[0]
    nav_df["pct"] = (nav_df["nav"] - base) / base * 100
    fig.add_trace(go.Scatter(
        x=nav_df["date"], y=nav_df["pct"],
        name="我的 NAV",
        line=dict(color="#6366f1", width=2.5),
        hovertemplate="%{y:.2f}%<extra>我的 NAV</extra>",
    ))

# QQQ / SPY 資料直接從 report JSON 讀，不呼叫 yfinance
for sym, label, color in [("QQQ", "QQQ (NASDAQ)", "#f59e0b"),
                           ("SPY", "SPY (S&P500)", "#10b981")]:
    show = show_qqq if sym == "QQQ" else show_spy
    if show and bm_hist.get(sym):
        bm_df = pd.DataFrame(bm_hist[sym])
        if not bm_df.empty and "value" in bm_df.columns:
            bm_df["pct"] = bm_df["value"] - 100
            fig.add_trace(go.Scatter(
                x=bm_df["date"], y=bm_df["pct"],
                name=label,
                line=dict(color=color, width=1.5, dash="dot"),
                hovertemplate=f"%{{y:.2f}}%<extra>{label}</extra>",
            ))

fig.update_layout(
    yaxis_title="累積報酬 (%)", xaxis_title="",
    hovermode="x unified", height=300,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=10, b=0),
)
fig.add_hline(y=0, line_dash="solid", line_color="#e2e8f0")
st.plotly_chart(fig, use_container_width=True)

# ── 回撤圖 ────────────────────────────────────────────────────────────────
with st.expander("📉 回撤圖"):
    if nav_df.empty:
        st.info("尚無 NAV 歷史資料")
    else:
        navs = nav_df["nav"].tolist()
        peak, drawdowns = navs[0], []
        for n in navs:
            peak = max(peak, n)
            drawdowns.append((n - peak) / peak * 100)

        dd_df = pd.DataFrame({"date": nav_df["date"], "drawdown": drawdowns})
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=dd_df["date"], y=dd_df["drawdown"],
            fill="tozeroy", name="我的回撤",
            line=dict(color="#ef4444"), fillcolor="rgba(239,68,68,0.15)",
        ))
        # 基準回撤
        for sym, label, color in [("QQQ", "QQQ", "#f59e0b"), ("SPY", "SPY", "#10b981")]:
            show = show_qqq if sym == "QQQ" else show_spy
            if show and bm_hist.get(sym):
                bm_df = pd.DataFrame(bm_hist[sym])
                if not bm_df.empty and "value" in bm_df.columns:
                    vals = bm_df["value"].tolist()
                    pk, bm_dd = vals[0], []
                    for v in vals:
                        pk = max(pk, v)
                        bm_dd.append((v - pk) / pk * 100)
                    fig2.add_trace(go.Scatter(
                        x=bm_df["date"], y=bm_dd,
                        name=label,
                        line=dict(color=color, width=1, dash="dot"),
                    ))
        fig2.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0),
                           yaxis_title="回撤 (%)", hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# 持倉表格
# ═══════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-head">📋 持倉明細</p>', unsafe_allow_html=True)

if pos:
    pos_df = pd.DataFrame(pos)
    display_cols = {
        "symbol": "股票", "qty": "股數",
        "avg_entry_price": "均價($)", "current_price": "現價($)",
        "market_value": "市值($)", "weight_pct": "權重%",
        "unrealized_pnl": "未實現損益",
        "unrealized_pnl_pct": "損益%",
        "perf_1d_pct": "1日%", "perf_1w_pct": "1週%", "perf_1m_pct": "1月%",
        "pe_ratio": "P/E",
    }
    existing = [c for c in display_cols if c in pos_df.columns]
    pos_df = pos_df[existing].rename(columns=display_cols)

    def color_num(val):
        try:
            v = float(val)
            return "color: #16a34a" if v >= 0 else "color: #dc2626"
        except Exception:
            return ""

    pct_cols = [c for c in ["損益%", "1日%", "1週%", "1月%"] if c in pos_df.columns]
    styled = pos_df.style.map(color_num, subset=pct_cols)
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("目前無持倉")

# ═══════════════════════════════════════════════════════════════════════════
# 今日交易
# ═══════════════════════════════════════════════════════════════════════════

if trades:
    st.divider()
    st.markdown('<p class="section-head">🔔 今日交易</p>', unsafe_allow_html=True)
    for t in trades:
        icon = "🟢" if t.get("action") == "BUY" else "🔴"
        status = f"（{t.get('status', '')}）" if t.get("status") else ""
        st.write(f"{icon} **{t.get('action')}** {t.get('symbol')} × {t.get('qty')} 股 {status}")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# NASDAQ 前 10 & 大盤比較
# ═══════════════════════════════════════════════════════════════════════════

col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown('<p class="section-head">🏆 今日 NASDAQ 前 10</p>', unsafe_allow_html=True)
    if top10:
        t10 = pd.DataFrame(top10)[["rank", "symbol", "price", "market_cap_B"]]
        t10.columns = ["排名", "股票", "現價($)", "市值(B$)"]
        held = {p["symbol"] for p in pos}

        def highlight_held(row):
            return ["background-color:#f0fdf4" if row["股票"] in held else "" for _ in row]

        st.dataframe(
            t10.style.apply(highlight_held, axis=1),
            use_container_width=True, hide_index=True,
        )
        st.caption("🟩 綠底 = 目前持倉中")
    else:
        st.info("前 10 資料尚未載入")

with col_r:
    st.markdown('<p class="section-head">📈 與大盤比較</p>', unsafe_allow_html=True)
    rows = [{"指數": "我的帳戶",
             "今日%": s["daily_pnl_pct"], "1週%": "—", "1月%": "—"}]
    for sym, label in [("QQQ", "QQQ (NASDAQ)"), ("SPY", "SPY (S&P500)")]:
        b = bench.get(sym, {})
        rows.append({"指數": label,
                     "今日%": b.get("1d", 0), "1週%": b.get("1w", 0), "1月%": b.get("1m", 0)})
    b_df = pd.DataFrame(rows)

    def color_bench(val):
        try:
            return "color: #16a34a" if float(val) >= 0 else "color: #dc2626"
        except Exception:
            return ""

    num_cols = [c for c in ["今日%", "1週%", "1月%"] if c in b_df.columns]
    st.dataframe(
        b_df.style.applymap(color_bench, subset=num_cols),
        use_container_width=True, hide_index=True,
    )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# 關注股票（三大類別，從 JSON 讀取）
# ═══════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-head">🔎 關注股票</p>', unsafe_allow_html=True)
cat_labels = {"ai_tech": "🤖 AI 科技", "semicon": "💾 半導體", "growth": "🚀 成長股"}

if wl:
    wl_cols = st.columns(len(wl))
    for idx, (cat, items) in enumerate(wl.items()):
        with wl_cols[idx]:
            st.markdown(f"**{cat_labels.get(cat, cat)}**")
            if items:
                wl_df = pd.DataFrame(items).rename(
                    columns={"symbol": "股票", "perf_1d_pct": "今日%"}
                )
                cols_avail = [c for c in ["股票", "今日%"] if c in wl_df.columns]
                st.dataframe(
                    wl_df[cols_avail].style.applymap(color_num, subset=["今日%"] if "今日%" in cols_avail else []),
                    use_container_width=True, hide_index=True,
                )
else:
    st.info("關注股資料尚未載入（等待 GitHub Actions 執行後更新）")

# ═══════════════════════════════════════════════════════════════════════════
# 免責聲明
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="disclaimer">
⚠️ 本 Dashboard 及所有顯示內容，均僅供資訊整理與研究參考，不構成任何投資建議。<br>
股票投資具有風險，過去績效不代表未來報酬，投資前請謹慎評估個人風險承受能力。<br>
資料來源：Alpaca Markets API / yfinance（由 GitHub Actions 每日更新存入 JSON）
</div>""", unsafe_allow_html=True)
