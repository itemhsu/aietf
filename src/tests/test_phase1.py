from __future__ import annotations
"""Phase 1 測試 — Alpaca 連線 & 多帳戶管理"""
import pytest
import responses as rsps
import json
from unittest.mock import patch, MagicMock
from src.data.alpaca_client import AlpacaClient, AuthenticationError, client_from_env
from src.engine.account_manager import load_accounts
from src.engine.strategy_loader import load_strategy, validate_strategy


BASE_URL = "https://paper-api.alpaca.markets"


# ─── AlpacaClient tests ────────────────────────────────────────────────────────

@rsps.activate
def test_alpaca_connection():
    rsps.add(rsps.GET, f"{BASE_URL}/v2/account",
             json={"equity": "100000", "cash": "5000"}, status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    account = client.get_account()
    assert "equity" in account


@rsps.activate
def test_get_account_nav():
    rsps.add(rsps.GET, f"{BASE_URL}/v2/account",
             json={"equity": "102345.67", "cash": "1234.00"}, status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    acc = client.get_account()
    nav = float(acc["equity"])
    assert nav > 0
    assert isinstance(nav, float)


@rsps.activate
def test_get_positions():
    rsps.add(rsps.GET, f"{BASE_URL}/v2/positions",
             json=[{"symbol": "AAPL", "qty": "10", "current_price": "192.5",
                    "avg_entry_price": "185.0", "market_value": "1925.0"}],
             status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    positions = client.get_positions()
    assert isinstance(positions, list)
    assert len(positions) == 1
    assert positions[0]["symbol"] == "AAPL"
    assert "qty" in positions[0]
    assert "current_price" in positions[0]


@rsps.activate
def test_is_trading_day_weekday():
    rsps.add(rsps.GET, f"{BASE_URL}/v2/calendar",
             json=[{"date": "2026-05-24", "open": "09:30", "close": "16:00"}],
             status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    assert client.is_trading_day("2026-05-24") is True


@rsps.activate
def test_is_trading_day_weekend():
    rsps.add(rsps.GET, f"{BASE_URL}/v2/calendar",
             json=[], status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    assert client.is_trading_day("2026-05-23") is False


@rsps.activate
def test_auth_error_raises():
    rsps.add(rsps.GET, f"{BASE_URL}/v2/account", status=401,
             json={"message": "Unauthorized"})
    client = AlpacaClient("bad_key", "bad_secret", BASE_URL)
    with pytest.raises(AuthenticationError):
        client.get_account()


@rsps.activate
def test_retry_on_429():
    rsps.add(rsps.GET, f"{BASE_URL}/v2/account", status=429, json={})
    rsps.add(rsps.GET, f"{BASE_URL}/v2/account", status=429, json={})
    rsps.add(rsps.GET, f"{BASE_URL}/v2/account",
             json={"equity": "100000"}, status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    with patch("time.sleep"):
        acc = client.get_account()
    assert "equity" in acc


# ─── 多帳戶載入 ────────────────────────────────────────────────────────────────

def test_multi_account_load():
    accounts = load_accounts()
    assert len(accounts) >= 1
    for acc in accounts:
        assert acc.account_id
        assert acc.active_strategy
        assert acc.email_recipient


def test_account_strategy_binding():
    accounts = load_accounts()
    acc_a = next((a for a in accounts if a.account_id == "account_A"), None)
    assert acc_a is not None
    assert acc_a.active_strategy == "top10_marketcap_v1"


# ─── 策略載入 ──────────────────────────────────────────────────────────────────

def test_strategy_load_valid():
    strategy = load_strategy("top10_marketcap_v1")
    assert strategy["strategy_id"] == "top10_marketcap_v1"
    assert "selection" in strategy
    assert "allocation" in strategy


def test_strategy_load_invalid():
    with pytest.raises(ValueError):
        validate_strategy({"strategy_id": "broken"})  # 缺少必填欄位
