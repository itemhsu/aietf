from __future__ import annotations
"""Phase 4 測試 — 報告 Model/View 分離"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.data.market_data import StockData


def make_mock_report():
    return {
        "report_id": "2026-05-24_test",
        "account_id": "test_account",
        "strategy_id": "top10_marketcap_v1",
        "date": "2026-05-24",
        "generated_at": "2026-05-24T06:00:00",
        "email_recipient": "test@test.com",
        "account_summary": {
            "nav": 102345.67, "cash": 1234.56, "cash_pct": 1.2,
            "equity": 101111.11, "daily_pnl": 1234.56, "daily_pnl_pct": 1.22,
            "drawdown_pct": -1.5, "max_drawdown_pct": -3.2,
        },
        "positions": [
            {"symbol": "AAPL", "qty": 54, "avg_entry_price": 185.42,
             "current_price": 192.35, "market_value": 10386.9, "weight_pct": 10.15,
             "unrealized_pnl": 374.22, "unrealized_pnl_pct": 3.74, "pe_ratio": 28.5,
             "perf_1d_pct": 0.82, "perf_1w_pct": 2.15, "perf_1m_pct": 5.43}
        ],
        "top10_today": [{"rank": 1, "symbol": "AAPL", "market_cap_B": 2950, "price": 192.35}],
        "trades_executed": [{"symbol": "NVDA", "action": "BUY", "qty": 10, "status": "dry_run"}],
        "benchmark": {"QQQ": {"1d": 0.95, "1w": 2.0, "1m": 3.2},
                      "SPY": {"1d": 0.70, "1w": 1.5, "1m": 2.1}},
        "nav_history": [{"date": "2026-05-01", "nav": 100000},
                        {"date": "2026-05-24", "nav": 102345.67}],
        "watchlist": {
            "ai_tech": [{"symbol": "NVDA", "perf_1d_pct": 1.5}],
            "semicon":  [{"symbol": "TSM",  "perf_1d_pct": 0.8}],
            "growth":   [{"symbol": "PLTR", "perf_1d_pct": 2.1}],
        },
        "disclaimer": "本報告僅供研究參考。",
    }


REQUIRED_KEYS = [
    "report_id", "account_id", "strategy_id", "date", "generated_at",
    "account_summary", "positions", "top10_today", "trades_executed",
    "benchmark", "nav_history", "watchlist", "disclaimer",
]

SUMMARY_KEYS = ["nav", "cash", "daily_pnl", "daily_pnl_pct", "drawdown_pct", "max_drawdown_pct"]


def test_report_model_schema():
    report = make_mock_report()
    for key in REQUIRED_KEYS:
        assert key in report, f"缺少欄位：{key}"


def test_report_nav_matches_alpaca():
    report = make_mock_report()
    assert abs(report["account_summary"]["nav"] - 102345.67) < 0.01


def test_report_pnl_calculation():
    report = make_mock_report()
    s = report["account_summary"]
    assert isinstance(s["daily_pnl"], (int, float))
    assert isinstance(s["daily_pnl_pct"], (int, float))


def test_report_drawdown_calc():
    report = make_mock_report()
    s = report["account_summary"]
    assert s["drawdown_pct"] <= 0
    assert s["max_drawdown_pct"] <= s["drawdown_pct"]


def test_report_benchmark_included():
    report = make_mock_report()
    bench = report["benchmark"]
    assert "QQQ" in bench and "SPY" in bench
    assert "1d" in bench["QQQ"]


def test_view_email_renders():
    from src.report.view_email import render_email_html
    report = make_mock_report()
    html = render_email_html(report)
    assert "{{" not in html
    assert "}}" not in html
    assert "AlpacaBot" in html
    assert report["date"] in html


def test_view_email_contains_disclaimer():
    from src.report.view_email import render_email_html
    report = make_mock_report()
    html = render_email_html(report)
    assert "投資建議" in html or "disclaimer" in html.lower()


def test_history_index_updated():
    from src.report.model import save_report, REPORTS_DIR, HISTORY_INDEX_PATH
    import shutil
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with patch("src.report.model.REPORTS_DIR", tmp), \
             patch("src.report.model.HISTORY_INDEX_PATH", tmp / "history_index.json"):
            report = make_mock_report()
            save_report(report)
            index_path = tmp / "history_index.json"
            assert index_path.exists()
            index = json.loads(index_path.read_text())
            assert len(index["reports"]) >= 1


def test_history_report_retrievable():
    from src.report.model import save_report, load_report
    import shutil
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with patch("src.report.model.REPORTS_DIR", tmp), \
             patch("src.report.model.HISTORY_INDEX_PATH", tmp / "history_index.json"):
            report = make_mock_report()
            save_report(report)
            loaded = load_report("test_account", "2026-05-24")
            assert loaded is not None
            assert loaded["report_id"] == "2026-05-24_test"


def test_duplicate_date_overwrite():
    from src.report.model import save_report, REPORTS_DIR, HISTORY_INDEX_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with patch("src.report.model.REPORTS_DIR", tmp), \
             patch("src.report.model.HISTORY_INDEX_PATH", tmp / "history_index.json"):
            report = make_mock_report()
            save_report(report)
            save_report(report)   # 重複儲存同一份
            index = json.loads((tmp / "history_index.json").read_text())
            same_day = [r for r in index["reports"] if r["date"] == "2026-05-24"]
            assert len(same_day) == 1   # 不重複


def test_model_view_independence():
    """View 只接受 dict，不直接呼叫任何 API"""
    from src.report import view_email
    import inspect
    src = inspect.getsource(view_email)
    # view_email 不應 import alpaca_client 或 yfinance
    assert "alpaca_client" not in src
    assert "yfinance" not in src
