from __future__ import annotations
"""報告 Model — 生成 JSON 報告資料（不涉及任何樣式/展示邏輯）"""
import json
import logging
from datetime import datetime, date
from pathlib import Path
from src.data.market_data import StockData, fetch_performance
from src.data.pe_ratio import fetch_pe_ratios
from src.data.benchmark import fetch_benchmark_performance, fetch_benchmark_nav_history
from src.engine.rebalancer import RebalanceOrder

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parents[2] / "reports"
HISTORY_INDEX_PATH = REPORTS_DIR / "history_index.json"


def build_report(
    account_id: str,
    strategy: dict,
    alpaca_account: dict,
    positions: list[dict],
    top10: list[StockData],
    trades: list[dict],
    prev_nav: float | None = None,
) -> dict:
    """建構完整的報告 model dict"""
    today = date.today().isoformat()
    nav = float(alpaca_account.get("equity", 0))
    cash = float(alpaca_account.get("cash", 0))

    daily_pnl = nav - prev_nav if prev_nav else 0.0
    daily_pnl_pct = daily_pnl / prev_nav * 100 if prev_nav else 0.0

    # 持倉績效與 P/E
    pos_symbols = [p["symbol"] for p in positions]
    perfs = fetch_performance(pos_symbols) if pos_symbols else {}
    pes = fetch_pe_ratios(pos_symbols) if pos_symbols else {}
    benchmark = fetch_benchmark_performance()

    enriched_positions = []
    for pos in positions:
        sym = pos["symbol"]
        qty = float(pos.get("qty", 0))
        avg = float(pos.get("avg_entry_price", 0))
        cur = float(pos.get("current_price", 0))
        mv = qty * cur
        upnl = mv - qty * avg
        upnl_pct = upnl / (qty * avg) * 100 if avg > 0 else 0
        perf = perfs.get(sym, {})
        enriched_positions.append({
            "symbol": sym,
            "qty": int(qty),
            "avg_entry_price": round(avg, 2),
            "current_price": round(cur, 2),
            "market_value": round(mv, 2),
            "weight_pct": round(mv / nav * 100, 2) if nav > 0 else 0,
            "unrealized_pnl": round(upnl, 2),
            "unrealized_pnl_pct": round(upnl_pct, 2),
            "pe_ratio": pes.get(sym, "N/A"),
            "perf_1d_pct": perf.get("1d", 0.0),
            "perf_1w_pct": perf.get("1w", 0.0),
            "perf_1m_pct": perf.get("1m", 0.0),
        })

    # 計算回撤（從歷史高點）
    history = load_nav_history(account_id)
    all_navs = [h["nav"] for h in history] + [nav]
    max_nav = max(all_navs) if all_navs else nav
    drawdown_pct = (nav - max_nav) / max_nav * 100 if max_nav > 0 else 0
    all_drawdowns = []
    peak = all_navs[0]
    for n in all_navs:
        peak = max(peak, n)
        all_drawdowns.append((n - peak) / peak * 100)
    max_drawdown_pct = min(all_drawdowns) if all_drawdowns else 0

    # 關注股表
    watchlist = {}
    wl_categories = strategy.get("watchlist_categories", {})
    for cat, syms in wl_categories.items():
        w_perfs = fetch_performance(syms)
        watchlist[cat] = [
            {"symbol": s, "perf_1d_pct": w_perfs.get(s, {}).get("1d", 0.0)}
            for s in syms
        ]

    report = {
        "report_id": f"{today}_{account_id}",
        "account_id": account_id,
        "strategy_id": strategy["strategy_id"],
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "account_summary": {
            "nav": round(nav, 2),
            "cash": round(cash, 2),
            "cash_pct": round(cash / nav * 100, 2) if nav > 0 else 0,
            "equity": round(nav - cash, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
        },
        "positions": enriched_positions,
        "top10_today": [
            {"rank": s.rank, "symbol": s.symbol,
             "market_cap_B": s.market_cap_B, "price": round(s.price, 2)}
            for s in top10
        ],
        "trades_executed": trades,
        "benchmark": {
            "QQQ": benchmark.get("QQQ", {}),
            "SPY": benchmark.get("SPY", {}),
        },
        "nav_history": history + [{"date": today, "nav": round(nav, 2)}],
        "watchlist": watchlist,
        "disclaimer": "⚠️ 本報告僅供資訊整理與研究參考，不構成任何投資建議。",
    }
    return report


def save_report(report: dict) -> Path:
    """儲存報告 JSON 至 reports/YYYY-MM-DD/"""
    today = report["date"]
    account_id = report["account_id"]
    report_dir = REPORTS_DIR / today
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"model_{account_id}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"報告已儲存：{path}")
    _update_history_index(report, path)
    return path


def load_report(account_id: str, report_date: str) -> dict | None:
    """載入指定日期的歷史報告"""
    path = REPORTS_DIR / report_date / f"model_{account_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_nav_history(account_id: str, max_days: int = 90) -> list[dict]:
    """從 history_index.json 載入 NAV 歷史"""
    if not HISTORY_INDEX_PATH.exists():
        return []
    index = json.loads(HISTORY_INDEX_PATH.read_text(encoding="utf-8"))
    records = [r for r in index.get("reports", []) if r["account_id"] == account_id]
    records.sort(key=lambda r: r["date"])
    return [{"date": r["date"], "nav": r["nav"]} for r in records[-max_days:]]


def _update_history_index(report: dict, path: Path):
    """更新歷史索引"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if HISTORY_INDEX_PATH.exists():
        index = json.loads(HISTORY_INDEX_PATH.read_text(encoding="utf-8"))
    else:
        index = {"last_updated": "", "reports": []}

    entry = {
        "date": report["date"],
        "account_id": report["account_id"],
        "path": str(path.relative_to(REPORTS_DIR.parent)),
        "nav": report["account_summary"]["nav"],
    }
    # 若同日期已存在則覆蓋
    index["reports"] = [
        r for r in index["reports"]
        if not (r["date"] == entry["date"] and r["account_id"] == entry["account_id"])
    ]
    index["reports"].append(entry)
    index["last_updated"] = report["date"]
    HISTORY_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
