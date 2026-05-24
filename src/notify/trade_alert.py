from __future__ import annotations
"""即時交易通知模組"""
import logging
from src.notify.email_sender import send_trade_alert

logger = logging.getLogger(__name__)


def make_notifier(account_id: str, recipient: str):
    """回傳一個通知函式，供 trader.execute_rebalance 呼叫"""
    def notify(message: str):
        full_msg = f"[{account_id}] {message}"
        logger.info(f"交易通知：{full_msg}")
        send_trade_alert(recipient, full_msg)
    return notify
