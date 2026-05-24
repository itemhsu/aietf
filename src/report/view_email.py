from __future__ import annotations
"""Email View — 從 report model JSON 渲染 HTML Email（不呼叫任何 API）"""
from pathlib import Path
from datetime import datetime


def render_email_html(report: dict) -> str:
    """將 report model dict 轉換為 HTML Email 字串"""
    s = report["account_summary"]
    top10 = report.get("top10_today", [])
    positions = report.get("positions", [])
    trades = report.get("trades_executed", [])
    watchlist = report.get("watchlist", {})
    bench = report.get("benchmark", {})

    pnl_color = "#16a34a" if s["daily_pnl"] >= 0 else "#dc2626"
    pnl_sign = "+" if s["daily_pnl"] >= 0 else ""

    def pos_neg(v, suffix="%"):
        if v >= 0:
            return f'<span style="color:#16a34a">+{v:.2f}{suffix}</span>'
        return f'<span style="color:#dc2626">{v:.2f}{suffix}</span>'

    # 持倉列
    pos_rows = ""
    for p in sorted(positions, key=lambda x: x["market_value"], reverse=True):
        pos_rows += f"""
        <tr>
          <td><b>{p['symbol']}</b></td>
          <td>{p['qty']}</td>
          <td>${p['current_price']:,.2f}</td>
          <td>${p['market_value']:,.0f}</td>
          <td>{p['weight_pct']:.1f}%</td>
          <td>{pos_neg(p['perf_1d_pct'])}</td>
          <td>{pos_neg(p['perf_1w_pct'])}</td>
          <td>{pos_neg(p['perf_1m_pct'])}</td>
          <td>{p['pe_ratio']}</td>
        </tr>"""

    # 前10名列
    top10_rows = "".join(
        f"<tr><td>#{s['rank']}</td><td><b>{s['symbol']}</b></td>"
        f"<td>${s['price']:,.2f}</td><td>${s['market_cap_B']:,.0f}B</td></tr>"
        for s in top10
    )

    # 交易記錄
    trade_text = "無交易" if not trades else ""
    for t in trades:
        icon = "🟢" if t.get("action") == "BUY" else "🔴"
        trade_text += f"{icon} {t.get('action')} {t.get('symbol')} × {t.get('qty')} 股<br>"

    # 關注股
    wl_sections = ""
    cat_names = {"ai_tech": "🤖 AI 科技", "semicon": "💾 半導體", "growth": "🚀 成長股"}
    for cat, items in watchlist.items():
        cat_label = cat_names.get(cat, cat)
        cells = " ".join(
            f"<td style='padding:4px 10px;border-radius:6px;"
            f"background:{'#dcfce7' if i.get('perf_1d_pct', 0) >= 0 else '#fee2e2'}'>"
            f"<b>{i['symbol']}</b><br>"
            f"<span style='color:{'#16a34a' if i.get('perf_1d_pct', 0) >= 0 else '#dc2626'}'>"
            f"{'+' if i.get('perf_1d_pct', 0) >= 0 else ''}{i.get('perf_1d_pct', 0):.2f}%</span>"
            f"</td>"
            for i in items
        )
        wl_sections += f"<tr><td style='padding:8px 0;color:#64748b'>{cat_label}</td></tr>"
        wl_sections += f"<tr><td><table><tr>{cells}</tr></table></td></tr>"

    qqq = bench.get("QQQ", {})
    spy = bench.get("SPY", {})

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body{{font-family:'Segoe UI',sans-serif;background:#f1f5f9;margin:0;padding:20px;}}
  .card{{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #e2e8f0;}}
  h1{{color:#0f172a;font-size:1.3rem;margin:0 0 4px;}}
  .sub{{color:#64748b;font-size:.85rem;}}
  .kpi{{display:inline-block;margin:8px 16px 8px 0;}}
  .kpi-val{{font-size:1.5rem;font-weight:700;}}
  .kpi-lbl{{font-size:.75rem;color:#94a3b8;}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem;}}
  th{{background:#f8fafc;padding:8px;text-align:left;color:#64748b;border-bottom:1px solid #e2e8f0;}}
  td{{padding:7px 8px;border-bottom:1px solid #f1f5f9;}}
  .disclaimer{{font-size:.75rem;color:#94a3b8;background:#f8fafc;border-radius:8px;padding:12px;margin-top:16px;}}
</style>
</head><body>

<div class="card">
  <h1>📊 AlpacaBot 日報 — {report['date']}</h1>
  <div class="sub">帳戶：{report['account_id']} ｜ 策略：{report['strategy_id']}</div>
  <div style="margin-top:12px;">
    <div class="kpi"><div class="kpi-val">${s['nav']:,.2f}</div><div class="kpi-lbl">總 NAV</div></div>
    <div class="kpi"><div class="kpi-val" style="color:{pnl_color}">{pnl_sign}{s['daily_pnl']:,.2f} ({pnl_sign}{s['daily_pnl_pct']:.2f}%)</div><div class="kpi-lbl">今日損益</div></div>
    <div class="kpi"><div class="kpi-val">${s['cash']:,.0f} ({s['cash_pct']:.1f}%)</div><div class="kpi-lbl">現金水位</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#dc2626">{s['drawdown_pct']:.2f}%</div><div class="kpi-lbl">當前回撤</div></div>
  </div>
</div>

<div class="card">
  <h2 style="font-size:1rem;margin:0 0 12px;">📋 持倉明細</h2>
  <table>
    <tr><th>股票</th><th>股數</th><th>現價</th><th>市值</th><th>權重</th><th>1日%</th><th>1週%</th><th>1月%</th><th>P/E</th></tr>
    {pos_rows}
  </table>
</div>

<div class="card">
  <h2 style="font-size:1rem;margin:0 0 12px;">🏆 今日執行交易</h2>
  <div style="font-size:.9rem;line-height:1.8;">{trade_text}</div>
</div>

<div class="card">
  <h2 style="font-size:1rem;margin:0 0 12px;">🥇 NASDAQ 市值前 10</h2>
  <table>
    <tr><th>排名</th><th>股票</th><th>現價</th><th>市值</th></tr>
    {top10_rows}
  </table>
</div>

<div class="card">
  <h2 style="font-size:1rem;margin:0 0 12px;">🔎 關注股票</h2>
  <table>{wl_sections}</table>
</div>

<div class="card">
  <h2 style="font-size:1rem;margin:0 0 12px;">📈 與大盤比較（今日）</h2>
  <table>
    <tr><th></th><th>1日</th><th>1週</th><th>1月</th></tr>
    <tr><td><b>我的帳戶</b></td><td>{pos_neg(s['daily_pnl_pct'])}</td><td>—</td><td>—</td></tr>
    <tr><td><b>QQQ (NASDAQ)</b></td><td>{pos_neg(qqq.get('1d',0))}</td><td>{pos_neg(qqq.get('1w',0))}</td><td>{pos_neg(qqq.get('1m',0))}</td></tr>
    <tr><td><b>SPY (S&P500)</b></td><td>{pos_neg(spy.get('1d',0))}</td><td>{pos_neg(spy.get('1w',0))}</td><td>{pos_neg(spy.get('1m',0))}</td></tr>
  </table>
</div>

<div class="disclaimer">
  {report.get('disclaimer', '⚠️ 本報告僅供資訊整理與研究參考，不構成任何投資建議。')}<br>
  Generated by AlpacaBot · {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>

</body></html>"""
    return html


def save_email_html(report: dict, output_dir: Path) -> Path:
    html = render_email_html(report)
    path = output_dir / f"email_{report['account_id']}.html"
    path.write_text(html, encoding="utf-8")
    return path
