from __future__ import annotations
"""市場資料模組 — 股價、市值計算、動能計算"""
import logging
import yfinance as yf
from dataclasses import dataclass, field
from typing import Optional
from src.data.alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)

# 各股流通股數（每季更新，單位：股）
SHARES_OUTSTANDING = {
    "AAPL":  15_204_137_000, "MSFT":   7_433_000_000, "NVDA":  24_440_000_000,
    "GOOGL":  5_949_000_000, "AMZN":  10_525_000_000, "META":   2_560_000_000,
    "TSM":    5_180_000_000, "ASML":     394_000_000, "AVGO":   4_680_000_000,
    "AMD":    1_617_000_000, "ORCL":   2_750_000_000, "CRM":      968_000_000,
    "ADBE":     435_000_000, "CSCO":   4_040_000_000, "INTC":   4_260_000_000,
    "QCOM":   1_120_000_000, "TXN":      908_000_000, "NOW":      204_000_000,
    "V":      2_060_000_000, "MA":       924_000_000, "IBM":      906_000_000,
    "NFLX":     431_000_000, "UBER":   2_140_000_000, "SNOW":     330_000_000,
    "PLTR":   2_100_000_000,
}


@dataclass
class StockData:
    symbol: str
    price: float = 0.0
    shares_outstanding: int = 0
    market_cap: float = 0.0
    market_cap_B: float = 0.0
    momentum_20d: float = 0.0
    rank: int = 0
    perf_1d_pct: float = 0.0
    perf_1w_pct: float = 0.0
    perf_1m_pct: float = 0.0


def fetch_prices(symbols: list[str], client: AlpacaClient) -> dict[str, float]:
    """透過 Alpaca 批次取得最新收盤價"""
    try:
        prices = client.get_latest_bars(symbols)
        missing = [s for s in symbols if s not in prices or prices[s] == 0]
        if missing:
            logger.warning(f"以下股票無法取得報價，排除：{missing}")
        return {s: p for s, p in prices.items() if p > 0}
    except Exception as e:
        logger.error(f"取得股價失敗：{e}")
        return {}


def calculate_market_caps(prices: dict[str, float]) -> dict[str, float]:
    caps = {}
    for sym, price in prices.items():
        shares = SHARES_OUTSTANDING.get(sym, 0)
        if shares > 0:
            caps[sym] = price * shares
    return caps


def calculate_momentum(symbols: list[str], days: int = 20) -> dict[str, float]:
    """計算過去 N 日漲幅（動能）"""
    result = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period=f"{days + 5}d")
            if len(hist) >= days:
                old_price = hist["Close"].iloc[-days]
                new_price = hist["Close"].iloc[-1]
                result[sym] = (new_price - old_price) / old_price * 100
            else:
                result[sym] = 0.0
        except Exception as e:
            logger.warning(f"{sym} 動能計算失敗：{e}")
            result[sym] = 0.0
    return result


def fetch_performance(symbols: list[str]) -> dict[str, dict]:
    """取得個股 1d/1w/1m 報酬"""
    result = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="35d")
            if len(hist) < 2:
                result[sym] = {"1d": 0.0, "1w": 0.0, "1m": 0.0}
                continue
            now = hist["Close"].iloc[-1]
            d1  = hist["Close"].iloc[-2] if len(hist) >= 2 else now
            d5  = hist["Close"].iloc[-6] if len(hist) >= 6 else now
            d21 = hist["Close"].iloc[-22] if len(hist) >= 22 else now
            result[sym] = {
                "1d": round((now - d1)  / d1  * 100, 2),
                "1w": round((now - d5)  / d5  * 100, 2),
                "1m": round((now - d21) / d21 * 100, 2),
            }
        except Exception as e:
            logger.warning(f"{sym} 績效計算失敗：{e}")
            result[sym] = {"1d": 0.0, "1w": 0.0, "1m": 0.0}
    return result


def rank_stocks(prices: dict[str, float], method: str = "market_cap",
                top_n: int = 10) -> list[StockData]:
    """依策略方法排名並回傳前 N 檔"""
    stocks = []
    momentum = {}
    if method == "momentum":
        momentum = calculate_momentum(list(prices.keys()))

    for sym, price in prices.items():
        shares = SHARES_OUTSTANDING.get(sym, 0)
        mc = price * shares if shares > 0 else 0
        sd = StockData(
            symbol=sym,
            price=price,
            shares_outstanding=shares,
            market_cap=mc,
            market_cap_B=round(mc / 1e9, 1),
            momentum_20d=momentum.get(sym, 0.0),
        )
        stocks.append(sd)

    key_fn = (lambda s: s.momentum_20d) if method == "momentum" \
             else (lambda s: s.market_cap)
    stocks.sort(key=key_fn, reverse=True)

    for i, s in enumerate(stocks):
        s.rank = i + 1

    return stocks[:top_n]
