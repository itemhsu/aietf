from __future__ import annotations
"""交易執行模組 — 透過 Alpaca 執行再平衡訂單"""
import logging
from src.data.alpaca_client import AlpacaClient
from src.engine.rebalancer import RebalanceOrder

logger = logging.getLogger(__name__)


def execute_rebalance(
    client: AlpacaClient,
    orders: list[RebalanceOrder],
    dry_run: bool = True,
    notify_fn=None,
) -> list[dict]:
    """
    執行再平衡：先賣後買。
    dry_run=True 只印出不下單。
    notify_fn：有交易完成時呼叫的通知函式。
    """
    if not orders:
        logger.info("沒有需要執行的訂單")
        return []

    executed = []
    sell_orders = [o for o in orders if o.action == "SELL"]
    buy_orders  = [o for o in orders if o.action == "BUY"]

    # --- 賣出 ---
    sell_ids = []
    for order in sell_orders:
        if dry_run:
            logger.info(f"[DRY_RUN] SELL {order.symbol} × {order.qty} @ ${order.price:.2f}")
            executed.append({"symbol": order.symbol, "action": "SELL",
                             "qty": order.qty, "status": "dry_run"})
        else:
            try:
                resp = client.submit_order(order.symbol, order.qty, "sell")
                sell_ids.append(resp["id"])
                logger.info(f"SELL {order.symbol} × {order.qty} 已送出")
                executed.append({"symbol": order.symbol, "action": "SELL",
                                 "qty": order.qty, "order_id": resp["id"],
                                 "status": "submitted"})
                if notify_fn:
                    notify_fn(f"🔴 賣出 {order.symbol} × {order.qty} 股")
            except Exception as e:
                logger.error(f"SELL {order.symbol} 失敗：{e}")

    # 等待賣單成交
    if sell_ids and not dry_run:
        client.wait_for_fills(sell_ids)

    # --- 買入 ---
    buy_ids = []
    for order in buy_orders:
        if dry_run:
            logger.info(f"[DRY_RUN] BUY  {order.symbol} × {order.qty} @ ${order.price:.2f}")
            executed.append({"symbol": order.symbol, "action": "BUY",
                             "qty": order.qty, "status": "dry_run"})
        else:
            try:
                resp = client.submit_order(order.symbol, order.qty, "buy")
                buy_ids.append(resp["id"])
                logger.info(f"BUY  {order.symbol} × {order.qty} 已送出")
                executed.append({"symbol": order.symbol, "action": "BUY",
                                 "qty": order.qty, "order_id": resp["id"],
                                 "status": "submitted"})
                if notify_fn:
                    notify_fn(f"🟢 買入 {order.symbol} × {order.qty} 股")
            except Exception as e:
                logger.error(f"BUY {order.symbol} 失敗：{e}")

    if buy_ids and not dry_run:
        client.wait_for_fills(buy_ids)

    return executed
