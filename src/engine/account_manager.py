from __future__ import annotations
"""多帳戶管理模組"""
import json
import os
import logging
from pathlib import Path
from dataclasses import dataclass
from src.data.alpaca_client import AlpacaClient, client_from_env
from src.engine.strategy_loader import load_strategy

logger = logging.getLogger(__name__)

ACCOUNTS_PATH = Path(__file__).parents[2] / "accounts" / "accounts_index.json"


@dataclass
class Account:
    account_id: str
    display_name: str
    alpaca_key_env: str
    alpaca_secret_env: str
    alpaca_base_url_env: str
    active_strategy: str
    email_recipient: str
    enabled: bool
    _client: AlpacaClient = None
    _strategy: dict = None

    def client(self) -> AlpacaClient:
        if self._client is None:
            self._client = client_from_env(
                self.alpaca_key_env, self.alpaca_secret_env, self.alpaca_base_url_env
            )
        return self._client

    def strategy(self) -> dict:
        if self._strategy is None:
            self._strategy = load_strategy(self.active_strategy)
        return self._strategy


def load_accounts(account_filter: str = "") -> list[Account]:
    """載入所有啟用的帳戶，可用 account_filter 指定單一帳戶"""
    data = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    accounts = []
    for item in data["accounts"]:
        if not item.get("enabled", True):
            continue
        if account_filter and item["account_id"] != account_filter:
            continue
        accounts.append(Account(
            account_id=item["account_id"],
            display_name=item["display_name"],
            alpaca_key_env=item["alpaca_key_env"],
            alpaca_secret_env=item["alpaca_secret_env"],
            alpaca_base_url_env=item["alpaca_base_url_env"],
            active_strategy=item["active_strategy"],
            email_recipient=item["email_recipient"],
            enabled=item["enabled"],
        ))
    logger.info(f"載入 {len(accounts)} 個帳戶")
    return accounts
