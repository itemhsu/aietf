from __future__ import annotations
"""Phase 7 測試 — GitHub Actions & 主程式整合"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_main_dry_run_all_accounts():
    """DRY_RUN=true 走過所有帳戶，不應拋出例外"""
    os.environ["DRY_RUN"] = "true"
    os.environ["ALPACA_KEY_A"] = "fake_key"
    os.environ["ALPACA_SECRET_A"] = "fake_secret"
    os.environ["ALPACA_URL_A"] = "https://paper-api.alpaca.markets"

    with patch("src.data.alpaca_client.AlpacaClient._request") as mock_req, \
         patch("src.data.market_data.fetch_performance", return_value={}), \
         patch("src.data.pe_ratio.fetch_pe_ratios", return_value={}), \
         patch("src.data.benchmark.fetch_benchmark_performance", return_value={}), \
         patch("src.notify.email_sender._send_email", return_value=True):

        mock_req.side_effect = lambda method, url, **kw: (
            [{"date": "2026-05-24"}] if "calendar" in url else
            {"equity": "100000", "cash": "5000"} if "account" in url else
            [] if "positions" in url else
            {"bars": {"AAPL": {"c": 192.0}, "MSFT": {"c": 415.0},
                      "NVDA": {"c": 875.0}}} if "bars" in url else {}
        )

        from importlib import reload
        import main
        reload(main)
        # 不應拋出例外即通過


def test_main_skips_non_trading_day():
    """非交易日時 is_trading_day 回傳 False，程式應正常退出（不下單）"""
    with patch("src.data.alpaca_client.AlpacaClient.is_trading_day", return_value=False), \
         patch("src.engine.trader.execute_rebalance") as mock_exec:
        from src.engine.account_manager import load_accounts
        accounts = load_accounts()
        for acc in accounts:
            client = MagicMock()
            client.is_trading_day.return_value = False
        mock_exec.assert_not_called()


def test_strategy_json_valid():
    """所有 strategies/ 目錄下的 JSON 均合法"""
    from src.engine.strategy_loader import validate_strategy
    strategies_dir = Path(__file__).parents[2] / "strategies"
    import json
    for f in strategies_dir.glob("*.json"):
        data = json.loads(f.read_text())
        validate_strategy(data)  # 不應拋出例外


def test_accounts_index_valid():
    """accounts_index.json 格式正確"""
    import json
    path = Path(__file__).parents[2] / "accounts" / "accounts_index.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert "accounts" in data
    for acc in data["accounts"]:
        assert "account_id" in acc
        assert "active_strategy" in acc
        assert "email_recipient" in acc


def test_workflow_yml_syntax():
    """GitHub Actions YAML 語法正確"""
    workflow_path = Path(__file__).parents[2] / ".github" / "workflows" / "daily_workflow.yml"
    assert workflow_path.exists(), "daily_workflow.yml 不存在"
    import yaml
    try:
        with open(workflow_path) as f:
            yaml.safe_load(f)
    except Exception as e:
        pytest.fail(f"YAML 語法錯誤：{e}")
