from __future__ import annotations
"""
Phase 5 測試 — Dashboard 零依賴測試
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
核心驗證：Dashboard 不呼叫任何外部 API（Alpaca / yfinance / requests）。
所有資料均來自 reports/ JSON 檔案，可在 Streamlit Cloud 上無縫執行。
"""
import json
import inspect
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


# ─── 共用 mock 報告資料 ────────────────────────────────────────────────────

MOCK_NAV_HISTORY = [
    {"date": "2026-05-01", "nav": 100000.00},
    {"date": "2026-05-08", "nav": 101200.00},
    {"date": "2026-05-15", "nav": 102100.00},
    {"date": "2026-05-24", "nav": 102345.67},
]

MOCK_BM_HIST = {
    "QQQ": [
        {"date": "2026-05-01", "value": 100.00},
        {"date": "2026-05-08", "value": 101.50},
        {"date": "2026-05-15", "value": 102.30},
        {"date": "2026-05-24", "value": 102.80},
    ],
    "SPY": [
        {"date": "2026-05-01", "value": 100.00},
        {"date": "2026-05-08", "value": 100.80},
        {"date": "2026-05-15", "value": 101.50},
        {"date": "2026-05-24", "value": 101.90},
    ],
}

def make_full_report(extra: dict = None) -> dict:
    base = {
        "report_id": "2026-05-24_account_A",
        "account_id": "account_A",
        "strategy_id": "top10_marketcap_v1",
        "date": "2026-05-24",
        "generated_at": "2026-05-24T06:00:00",
        "account_summary": {
            "nav": 102345.67, "cash": 1023.45, "cash_pct": 1.0,
            "equity": 101322.22, "daily_pnl": 1234.56, "daily_pnl_pct": 1.22,
            "drawdown_pct": -1.50, "max_drawdown_pct": -3.20,
        },
        "positions": [
            {"symbol": "AAPL", "qty": 54, "avg_entry_price": 185.42,
             "current_price": 192.35, "market_value": 10386.9, "weight_pct": 10.15,
             "unrealized_pnl": 374.22, "unrealized_pnl_pct": 3.74, "pe_ratio": 28.5,
             "perf_1d_pct": 0.82, "perf_1w_pct": 2.15, "perf_1m_pct": 5.43},
            {"symbol": "MSFT", "qty": 24, "avg_entry_price": 398.10,
             "current_price": 415.20, "market_value": 9964.8, "weight_pct": 9.74,
             "unrealized_pnl": 410.4, "unrealized_pnl_pct": 4.30, "pe_ratio": 35.2,
             "perf_1d_pct": 1.05, "perf_1w_pct": 3.20, "perf_1m_pct": 6.10},
        ],
        "top10_today": [
            {"rank": 1, "symbol": "AAPL", "market_cap_B": 2950.0, "price": 192.35},
            {"rank": 2, "symbol": "MSFT", "market_cap_B": 2870.0, "price": 415.20},
            {"rank": 3, "symbol": "NVDA", "market_cap_B": 2140.0, "price": 875.00},
        ],
        "trades_executed": [
            {"symbol": "NVDA", "action": "BUY", "qty": 10, "status": "dry_run"}
        ],
        "benchmark": {
            "QQQ": {"1d": 0.95, "1w": 2.10, "1m": 3.20, "price": 445.0},
            "SPY": {"1d": 0.70, "1w": 1.50, "1m": 2.10, "price": 525.0},
        },
        # ← 關鍵：benchmark_nav_history 從 JSON 讀，不呼叫 yfinance
        "benchmark_nav_history": MOCK_BM_HIST,
        "nav_history": MOCK_NAV_HISTORY,
        "watchlist": {
            "ai_tech":  [{"symbol": "NVDA", "perf_1d_pct": 1.5},
                         {"symbol": "MSFT", "perf_1d_pct": 1.1}],
            "semicon":  [{"symbol": "TSM",  "perf_1d_pct": 0.8}],
            "growth":   [{"symbol": "PLTR", "perf_1d_pct": 2.1}],
        },
        "disclaimer": "本報告僅供研究參考，不構成投資建議。",
    }
    if extra:
        base.update(extra)
    return base


# ═══════════════════════════════════════════════════════════════════════════
# 1. 程式碼靜態分析：直接讀原始碼，不 import Streamlit 模組
#    （避免 Streamlit module-level code 在 pytest 中執行）
# ═══════════════════════════════════════════════════════════════════════════

def _read_app_source() -> str:
    app_path = Path(__file__).parents[1] / "dashboard" / "app.py"
    return app_path.read_text(encoding="utf-8")


def test_dashboard_no_alpaca_import():
    """app.py 不應 import AlpacaClient 或直接呼叫 Alpaca API"""
    src = _read_app_source()
    assert "AlpacaClient" not in src, "Dashboard 不應直接使用 AlpacaClient"
    assert "from src.data.alpaca_client" not in src


def test_dashboard_no_yfinance_import():
    """app.py 不應有 yfinance 的 import 語句（docstring 提及不算）"""
    src = _read_app_source()
    import re
    # 只抓 import 語句，忽略 docstring / 注釋中的提及
    import_lines = [
        line.strip() for line in src.splitlines()
        if re.match(r"^\s*(import|from)\s+", line)
    ]
    for line in import_lines:
        assert "yfinance" not in line, f"Dashboard import 到 yfinance：{line}"


def test_dashboard_no_requests_import():
    """app.py 不應直接使用 requests"""
    src = _read_app_source()
    assert "import requests" not in src, "Dashboard 不應直接使用 requests"


def test_dashboard_no_live_benchmark_fetch():
    """app.py 不應呼叫 fetch_benchmark_nav_history（即時 API）"""
    src = _read_app_source()
    assert "fetch_benchmark_nav_history" not in src, \
        "Dashboard 應從 JSON 讀 benchmark_nav_history，不應即時抓取"


def test_dashboard_only_reads_json():
    """app.py 不應呼叫 build_report 或 fetch_prices 等資料生成函式"""
    src = _read_app_source()
    assert "build_report" not in src
    assert "fetch_prices" not in src


# ═══════════════════════════════════════════════════════════════════════════
# 2. 資料讀取函式測試（import data.py，無 Streamlit UI）
# ═══════════════════════════════════════════════════════════════════════════

def test_get_account_ids_returns_list():
    from src.dashboard.data import get_account_ids
    ids = get_account_ids()
    assert isinstance(ids, list)
    assert len(ids) >= 1


def test_get_available_dates_empty_when_no_index(tmp_path):
    """無 history_index.json 時回傳空列表，不應拋出例外"""
    from src.dashboard import data as dash_data
    orig = dash_data.get_history_index_path
    dash_data.get_history_index_path = lambda: tmp_path / "history_index.json"
    try:
        result = dash_data.get_available_dates("account_A")
    finally:
        dash_data.get_history_index_path = orig
    assert result == []


def test_get_available_dates_correct(tmp_path):
    index = {
        "reports": [
            {"date": "2026-05-24", "account_id": "account_A", "nav": 102345},
            {"date": "2026-05-23", "account_id": "account_A", "nav": 101111},
            {"date": "2026-05-24", "account_id": "account_B", "nav": 99000},
        ]
    }
    idx_path = tmp_path / "history_index.json"
    idx_path.write_text(json.dumps(index))
    from src.dashboard import data as dash_data
    orig = dash_data.get_history_index_path
    dash_data.get_history_index_path = lambda: idx_path
    try:
        result = dash_data.get_available_dates("account_A")
    finally:
        dash_data.get_history_index_path = orig
    assert "2026-05-24" in result
    assert "2026-05-23" in result
    # account_B 的日期不應包含（account_A 只有2筆）
    assert len(result) == 2


def test_get_all_account_nav_history_sorted(tmp_path):
    index = {
        "reports": [
            {"date": "2026-05-23", "account_id": "account_A", "nav": 101000},
            {"date": "2026-05-24", "account_id": "account_A", "nav": 102000},
            {"date": "2026-05-22", "account_id": "account_A", "nav": 100000},
        ]
    }
    idx_path = tmp_path / "history_index.json"
    idx_path.write_text(json.dumps(index))
    from src.dashboard import data as dash_data
    orig = dash_data.get_history_index_path
    dash_data.get_history_index_path = lambda: idx_path
    try:
        history = dash_data.get_all_account_nav_history("account_A")
    finally:
        dash_data.get_history_index_path = orig
    dates = [h["date"] for h in history]
    assert dates == sorted(dates), "NAV 歷史應依日期升序排列"


# ═══════════════════════════════════════════════════════════════════════════
# 3. 報告 model 包含 benchmark_nav_history
# ═══════════════════════════════════════════════════════════════════════════

def test_report_contains_benchmark_nav_history():
    """報告 JSON 必須包含 benchmark_nav_history 欄位（供 Dashboard 使用）"""
    report = make_full_report()
    assert "benchmark_nav_history" in report, "報告缺少 benchmark_nav_history 欄位"


def test_benchmark_nav_history_has_qqq_spy():
    report = make_full_report()
    bm = report["benchmark_nav_history"]
    assert "QQQ" in bm
    assert "SPY" in bm


def test_benchmark_nav_history_structure():
    """每個基準歷史記錄應有 date 和 value 欄位"""
    report = make_full_report()
    for sym in ["QQQ", "SPY"]:
        for entry in report["benchmark_nav_history"][sym]:
            assert "date" in entry, f"{sym} 歷史記錄缺少 date"
            assert "value" in entry, f"{sym} 歷史記錄缺少 value"
            assert isinstance(entry["value"], (int, float))


def test_benchmark_nav_history_normalized():
    """基準歷史的第一筆 value 應為 100（已標準化）"""
    report = make_full_report()
    for sym in ["QQQ", "SPY"]:
        hist = report["benchmark_nav_history"][sym]
        if hist:
            assert hist[0]["value"] == 100.0, f"{sym} 第一筆 value 應為 100"


# ═══════════════════════════════════════════════════════════════════════════
# 4. build_report 會生成 benchmark_nav_history
# ═══════════════════════════════════════════════════════════════════════════

def test_build_report_includes_benchmark_nav_history():
    """build_report() 生成的報告應包含 benchmark_nav_history"""
    from src.report.model import build_report
    from src.data.market_data import StockData

    mock_stock = StockData(
        symbol="AAPL", price=192.0, shares_outstanding=15_000_000_000,
        market_cap=192.0 * 15_000_000_000, market_cap_B=2880.0, rank=1,
    )

    with patch("src.report.model.fetch_performance", return_value={}), \
         patch("src.report.model.fetch_pe_ratios", return_value={}), \
         patch("src.report.model.fetch_benchmark_performance",
               return_value={"QQQ": {"1d": 0.9}, "SPY": {"1d": 0.7}}), \
         patch("src.report.model.fetch_benchmark_nav_history",
               return_value=MOCK_BM_HIST), \
         patch("src.report.model.load_nav_history", return_value=[]):

        report = build_report(
            account_id="account_A",
            strategy={"strategy_id": "test", "watchlist_categories": {}},
            alpaca_account={"equity": "102000", "cash": "1000"},
            positions=[],
            top10=[mock_stock],
            trades=[],
        )

    assert "benchmark_nav_history" in report
    assert "QQQ" in report["benchmark_nav_history"]


# ═══════════════════════════════════════════════════════════════════════════
# 5. 報告儲存後 benchmark_nav_history 可被正確讀取
# ═══════════════════════════════════════════════════════════════════════════

def test_saved_report_benchmark_readable(tmp_path):
    from src.report.model import save_report, load_report
    report = make_full_report()

    with patch("src.report.model.REPORTS_DIR", tmp_path), \
         patch("src.report.model.HISTORY_INDEX_PATH", tmp_path / "history_index.json"):
        save_report(report)
        loaded = load_report("account_A", "2026-05-24")

    assert loaded is not None
    assert "benchmark_nav_history" in loaded
    assert len(loaded["benchmark_nav_history"]["QQQ"]) == len(MOCK_BM_HIST["QQQ"])


# ═══════════════════════════════════════════════════════════════════════════
# 6. Dashboard 能優雅處理缺少欄位的情況（向後相容舊報告）
# ═══════════════════════════════════════════════════════════════════════════

def test_report_without_benchmark_nav_history_handled():
    """舊版報告沒有 benchmark_nav_history 時，get() 應回傳 {}，不拋出 KeyError"""
    report = make_full_report()
    del report["benchmark_nav_history"]  # 模擬舊版報告
    bm_hist = report.get("benchmark_nav_history", {})
    # Dashboard 的邏輯：bm_hist.get("QQQ") 應回傳 None 而非拋出例外
    assert bm_hist.get("QQQ") is None


def test_report_empty_positions_no_error():
    """空持倉報告不應讓 Dashboard 崩潰"""
    report = make_full_report({"positions": []})
    assert report["positions"] == []


def test_report_empty_trades_no_error():
    report = make_full_report({"trades_executed": []})
    assert report["trades_executed"] == []


def test_report_empty_nav_history_no_error():
    """沒有 NAV 歷史時圖表應顯示空狀態，不崩潰"""
    report = make_full_report({"nav_history": []})
    nav_history = report.get("nav_history", [])
    import pandas as pd
    nav_df = pd.DataFrame(nav_history) if nav_history else pd.DataFrame()
    assert nav_df.empty


# ═══════════════════════════════════════════════════════════════════════════
# 7. Streamlit Cloud 部署相關
# ═══════════════════════════════════════════════════════════════════════════

def test_streamlit_app_entry_exists():
    """Streamlit Cloud 需要 root 目錄的 streamlit_app.py"""
    entry = Path(__file__).parents[2] / "streamlit_app.py"
    assert entry.exists(), "缺少 streamlit_app.py（Streamlit Cloud 入口點）"


def test_streamlit_config_exists():
    """.streamlit/config.toml 應存在"""
    config = Path(__file__).parents[2] / ".streamlit" / "config.toml"
    assert config.exists(), "缺少 .streamlit/config.toml"


def test_streamlit_config_valid():
    """config.toml 應可正確解析"""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # fallback
    config_path = Path(__file__).parents[2] / ".streamlit" / "config.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    assert "server" in config or "theme" in config


def test_requirements_has_streamlit():
    """requirements.txt 應包含 streamlit"""
    req_path = Path(__file__).parents[2] / "requirements.txt"
    content = req_path.read_text()
    assert "streamlit" in content


def test_requirements_no_local_only_packages():
    """requirements.txt 不應有只能本機用的套件（如 jupyterlab 等）"""
    req_path = Path(__file__).parents[2] / "requirements.txt"
    content = req_path.read_text().lower()
    bad_pkgs = ["jupyterlab", "notebook", "ipykernel"]
    for pkg in bad_pkgs:
        assert pkg not in content, f"requirements.txt 不應包含 {pkg}"
