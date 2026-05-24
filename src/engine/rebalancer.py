from __future__ import annotations
"""再平衡計算模組 — 計算買賣指令（只買整數股）"""
import math
import logging
from dataclasses import dataclass
from datetime import date
from src.data.market_data import StockData

logger = logging.getLogger(__name__)

MIN_ORDER_VALUE = 1.0


@dataclass
class RebalanceOrder:
    symbol: str
    action: str        # "BUY" | "SELL"
    qty: int           # 整數股
    price: float
    value: float
    reason: str        # new_entrant | exit_top10 | weight_adjust | cash_deploy


def calculate_rebalance(
    current_positions: list[dict],
    top10: list[StockData],
    nav: float,
    available_cash: float,
    strategy: dict,
) -> list[RebalanceOrder]:
    """
    核心再平衡演算法。
    current_positions：[{"symbol":..., "qty":..., "current_price":...}, ...]
    """
    target_weight = strategy["allocation"]["weight_per_stock"]
    tolerance = strategy["rebalance"]["tolerance_pct"]
    cash_buffer = strategy["allocation"]["cash_buffer_pct"]
    target_value = nav * target_weight

    top10_symbols = {s.symbol for s in top10}
    price_map = {s.symbol: s.price for s in top10}
    current_map = {p["symbol"]: p for p in current_positions}

    orders: list[RebalanceOrder] = []

    # Step A：識別需賣出（不在前10名）
    for sym, pos in current_map.items():
        if sym not in top10_symbols:
            qty = int(pos.get("qty", 0))
            price = float(pos.get("current_price", 0))
            if qty > 0:
                orders.append(RebalanceOrder(
                    symbol=sym, action="SELL", qty=qty,
                    price=price, value=qty * price, reason="exit_top10"
                ))

    # Step B：估算賣出後可用現金
    sell_value = sum(o.value for o in orders if o.action == "SELL")
    cash_after_sell = available_cash + sell_value * 0.99  # 扣除滑點估算

    # Step C：容忍帶檢查 & 新進股票
    buy_orders: list[RebalanceOrder] = []
    for stock in top10:
        sym = stock.symbol
        price = stock.price
        if price <= 0:
            continue

        if sym not in current_map:
            # 新進前10：買入目標股數
            target_qty = math.floor(target_value / price)
            value = target_qty * price
            if target_qty > 0 and value >= MIN_ORDER_VALUE:
                buy_orders.append(RebalanceOrder(
                    symbol=sym, action="BUY", qty=target_qty,
                    price=price, value=value, reason="new_entrant"
                ))
        else:
            # 已持有：檢查容忍帶
            pos = current_map[sym]
            cur_value = float(pos.get("qty", 0)) * price
            cur_weight = cur_value / nav if nav > 0 else 0
            deviation = abs(cur_weight - target_weight)
            if deviation > tolerance:
                diff_value = target_value - cur_value
                diff_qty = math.floor(abs(diff_value) / price)
                if diff_qty > 0 and diff_qty * price >= MIN_ORDER_VALUE:
                    action = "BUY" if diff_value > 0 else "SELL"
                    buy_orders.append(RebalanceOrder(
                        symbol=sym, action=action, qty=diff_qty,
                        price=price, value=diff_qty * price, reason="weight_adjust"
                    ))

    # Step D：現金不足時按比例縮減買入數量
    total_buy_value = sum(o.value for o in buy_orders if o.action == "BUY")
    usable_cash = cash_after_sell * (1 - cash_buffer)
    if total_buy_value > usable_cash and total_buy_value > 0:
        ratio = usable_cash / total_buy_value
        scaled = []
        for o in buy_orders:
            if o.action == "BUY":
                new_qty = math.floor(o.qty * ratio)
                if new_qty > 0:
                    scaled.append(RebalanceOrder(
                        symbol=o.symbol, action="BUY", qty=new_qty,
                        price=o.price, value=new_qty * o.price, reason=o.reason
                    ))
            else:
                scaled.append(o)
        buy_orders = scaled

    orders.extend(buy_orders)

    # Step E：SELL 優先，BUY 在後
    orders.sort(key=lambda o: (0 if o.action == "SELL" else 1, o.symbol))
    logger.info(f"再平衡訂單：{len([o for o in orders if o.action=='SELL'])} 賣 / "
                f"{len([o for o in orders if o.action=='BUY'])} 買")
    return orders


def should_rebalance(strategy: dict, current_cash: float, nav: float,
                     last_rebalance_date: str | None) -> tuple[bool, str]:
    """判斷是否觸發再平衡"""
    today = date.today()
    threshold = strategy["rebalance"].get("new_capital_threshold_pct", 0.05)
    cash_pct = current_cash / nav if nav > 0 else 0

    if strategy["rebalance"].get("monthly_first_day") and today.day == 1:
        return True, "monthly_rebalance"
    if strategy["rebalance"].get("on_new_capital") and cash_pct > threshold:
        return True, f"new_capital({cash_pct:.1%})"
    return False, ""
