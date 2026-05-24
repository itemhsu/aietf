from __future__ import annotations
"""Phase 3 測試 — 再平衡邏輯"""
import pytest
import math
from src.engine.rebalancer import calculate_rebalance, should_rebalance, RebalanceOrder
from src.data.market_data import StockData


def make_stock(symbol, price, rank=1):
    shares = 1_000_000_000
    return StockData(symbol=symbol, price=price, shares_outstanding=shares,
                     market_cap=price * shares, market_cap_B=price, rank=rank)


STRATEGY = {
    "allocation": {"weight_per_stock": 0.10, "share_type": "integer_only", "cash_buffer_pct": 0.01},
    "rebalance": {"tolerance_pct": 0.02, "on_new_capital": True,
                  "new_capital_threshold_pct": 0.05, "monthly_first_day": True},
}

TOP10 = [make_stock(f"S{i}", 100.0, i+1) for i in range(10)]
NAV = 100_000.0


def test_rebalance_integer_shares_only():
    orders = calculate_rebalance([], TOP10, NAV, NAV, STRATEGY)
    for o in orders:
        assert isinstance(o.qty, int), f"{o.symbol} qty 不是整數"


def test_first_run_all_cash():
    orders = calculate_rebalance([], TOP10, NAV, NAV, STRATEGY)
    buy_orders = [o for o in orders if o.action == "BUY"]
    assert len(buy_orders) == 10


def test_rebalance_exit_top10():
    positions = [{"symbol": "OLD1", "qty": 50, "current_price": 100.0, "market_value": 5000}]
    orders = calculate_rebalance(positions, TOP10, NAV, 5000.0, STRATEGY)
    sell = [o for o in orders if o.action == "SELL" and o.symbol == "OLD1"]
    assert len(sell) == 1
    assert sell[0].qty == 50


def test_rebalance_new_entrant():
    positions = [{"symbol": "S0", "qty": 100, "current_price": 100.0, "market_value": 10000}]
    orders = calculate_rebalance(positions, TOP10, NAV, 90000.0, STRATEGY)
    buy_new = [o for o in orders if o.action == "BUY" and o.symbol != "S0"]
    assert len(buy_new) >= 9


def test_rebalance_no_change_within_tolerance():
    """所有持股在容忍帶內 → 買賣數量接近 0"""
    positions = [
        {"symbol": f"S{i}", "qty": 100, "current_price": 100.0, "market_value": 10000}
        for i in range(10)
    ]
    orders = calculate_rebalance(positions, TOP10, NAV, 0.0, STRATEGY)
    meaningful = [o for o in orders if o.value >= 1.0]
    assert len(meaningful) == 0


def test_sell_before_buy():
    positions = [{"symbol": "OLD1", "qty": 50, "current_price": 100.0, "market_value": 5000}]
    orders = calculate_rebalance(positions, TOP10, NAV, 50000.0, STRATEGY)
    if len(orders) >= 2:
        sell_idx = next((i for i, o in enumerate(orders) if o.action == "SELL"), None)
        buy_idx  = next((i for i, o in enumerate(orders) if o.action == "BUY"),  None)
        if sell_idx is not None and buy_idx is not None:
            assert sell_idx < buy_idx


def test_equal_weight_10pct():
    orders = calculate_rebalance([], TOP10, NAV, NAV, STRATEGY)
    for o in orders:
        if o.action == "BUY":
            weight = o.value / NAV
            assert 0.05 <= weight <= 0.15, f"{o.symbol} 權重 {weight:.2%} 超出合理範圍"


def test_cash_buffer_maintained():
    orders = calculate_rebalance([], TOP10, NAV, NAV, STRATEGY)
    total_buy = sum(o.value for o in orders if o.action == "BUY")
    assert total_buy <= NAV * (1 - STRATEGY["allocation"]["cash_buffer_pct"])


def test_minimum_order_value():
    orders = calculate_rebalance([], TOP10, NAV, NAV, STRATEGY)
    for o in orders:
        assert o.value >= 1.0, f"{o.symbol} 訂單金額 {o.value} < $1"


def test_multi_account_independent():
    """兩帳戶各自計算不影響彼此"""
    orders_a = calculate_rebalance([], TOP10[:10], NAV, NAV, STRATEGY)
    orders_b = calculate_rebalance([], TOP10[:10], NAV * 2, NAV * 2, STRATEGY)
    total_a = sum(o.value for o in orders_a if o.action == "BUY")
    total_b = sum(o.value for o in orders_b if o.action == "BUY")
    assert abs(total_b - total_a * 2) / total_a < 0.05  # B 約為 A 的 2 倍


def test_rebalance_new_capital():
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("src.engine.rebalancer.date",
                   type("D", (), {"today": staticmethod(lambda: type("d", (), {"day": 15})())}))
        triggered, reason = should_rebalance(STRATEGY, 6000.0, 100000.0, None)
    assert triggered
    assert "new_capital" in reason


def test_monthly_rebalance_trigger():
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("src.engine.rebalancer.date",
                   type("D", (), {"today": staticmethod(lambda: type("d", (), {"day": 1})())}))
        triggered, reason = should_rebalance(STRATEGY, 100.0, 100000.0, None)
    assert triggered
    assert reason == "monthly_rebalance"
