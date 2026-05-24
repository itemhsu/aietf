from __future__ import annotations
"""Alpaca API 封裝 — 所有對 Alpaca 的 HTTP 呼叫集中於此"""
import os
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

DATA_URL = "https://data.alpaca.markets"


class AuthenticationError(Exception):
    pass


class AlpacaClient:
    def __init__(self, api_key: str, secret_key: str, base_url: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Content-Type": "application/json",
        })

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """發送 HTTP 請求，含指數退避重試"""
        for attempt in range(3):
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code == 401:
                raise AuthenticationError("Alpaca API 認證失敗，請確認 API Key")
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limit，等待 {wait}s 後重試")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 2 ** attempt
                logger.warning(f"Server error {resp.status_code}，等待 {wait}s 重試")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json() if resp.text else {}
        raise RuntimeError(f"API 呼叫失敗：{url}")

    def get_account(self) -> dict:
        return self._request("GET", f"{self.base_url}/v2/account")

    def get_positions(self) -> list:
        return self._request("GET", f"{self.base_url}/v2/positions")

    def get_calendar(self, start: str, end: str) -> list:
        return self._request("GET", f"{self.base_url}/v2/calendar",
                             params={"start": start, "end": end})

    def is_trading_day(self, date: Optional[str] = None) -> bool:
        from datetime import date as dt_date
        d = date or dt_date.today().isoformat()
        cal = self.get_calendar(d, d)
        return len(cal) > 0

    def get_latest_bars(self, symbols: list[str]) -> dict:
        """批次取得最新收盤價"""
        result = {}
        chunk_size = 100
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            data = self._request(
                "GET", f"{DATA_URL}/v2/stocks/bars/latest",
                params={"symbols": ",".join(chunk), "feed": "iex"}
            )
            for sym, bar_data in data.get("bars", {}).items():
                result[sym] = bar_data.get("c", 0.0)   # 收盤價
        return result

    def get_historical_bars(self, symbol: str, timeframe: str = "1Day",
                             limit: int = 30) -> list:
        """取得歷史 K 線"""
        data = self._request(
            "GET", f"{DATA_URL}/v2/stocks/{symbol}/bars",
            params={"timeframe": timeframe, "limit": limit, "feed": "iex"}
        )
        return data.get("bars", [])

    def submit_order(self, symbol: str, qty: int, side: str,
                     time_in_force: str = "day") -> dict:
        payload = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "market",
            "time_in_force": time_in_force,
        }
        return self._request("POST", f"{self.base_url}/v2/orders", json=payload)

    def get_order(self, order_id: str) -> dict:
        return self._request("GET", f"{self.base_url}/v2/orders/{order_id}")

    def cancel_all_orders(self):
        self._request("DELETE", f"{self.base_url}/v2/orders")

    def wait_for_fills(self, order_ids: list[str], timeout: int = 60,
                       poll_interval: int = 5) -> dict:
        filled = {}
        deadline = time.time() + timeout
        pending = list(order_ids)
        while pending and time.time() < deadline:
            for oid in list(pending):
                order = self.get_order(oid)
                if order.get("status") in ("filled", "canceled", "expired"):
                    filled[oid] = order
                    pending.remove(oid)
            if pending:
                time.sleep(poll_interval)
        return filled


def client_from_env(key_env: str, secret_env: str, url_env: str) -> AlpacaClient:
    """從環境變數建立 AlpacaClient"""
    key = os.environ.get(key_env, "")
    secret = os.environ.get(secret_env, "")
    url = os.environ.get(url_env, "https://paper-api.alpaca.markets")
    return AlpacaClient(api_key=key, secret_key=secret, base_url=url)
