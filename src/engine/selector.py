from __future__ import annotations
"""選股模組 — 依策略 JSON 選出目標股票"""
import logging
from src.data.alpaca_client import AlpacaClient
from src.data.market_data import fetch_prices, rank_stocks, StockData

logger = logging.getLogger(__name__)


def select_top_stocks(strategy: dict, client: AlpacaClient) -> list[StockData]:
    """
    依策略選出前 N 檔股票。
    strategy 為已載入的 JSON 策略 dict。
    """
    symbols: list[str] = strategy["universe"]["symbols"]
    method: str = strategy["selection"]["method"]
    top_n: int = strategy["selection"]["top_n"]
    min_cap_B: float = strategy["universe"].get("min_market_cap_B", 0)

    prices = fetch_prices(symbols, client)
    if not prices:
        logger.error("無法取得任何股票價格")
        return []

    ranked = rank_stocks(prices, method=method, top_n=len(prices))

    # 依最低市值篩選
    if min_cap_B > 0:
        ranked = [s for s in ranked if s.market_cap_B >= min_cap_B]

    result = ranked[:top_n]
    logger.info(f"選股完成（{method}）：{[s.symbol for s in result]}")
    return result


def get_watchlist_prices(strategy: dict, client: AlpacaClient) -> dict:
    """取得策略 watchlist_categories 中各股的最新報價"""
    categories = strategy.get("watchlist_categories", {})
    all_symbols = []
    for syms in categories.values():
        all_symbols.extend(syms)

    prices = fetch_prices(list(set(all_symbols)), client)
    result = {}
    for cat, syms in categories.items():
        result[cat] = [
            {"symbol": s, "price": prices.get(s, 0.0)}
            for s in syms
        ]
    return result
