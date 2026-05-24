from __future__ import annotations
"""基準指數資料模組 — QQQ（NASDAQ）和 SPY（S&P500）"""
import logging
import yfinance as yf

logger = logging.getLogger(__name__)

BENCHMARKS = {"QQQ": "NASDAQ 100", "SPY": "S&P 500"}


def fetch_benchmark_performance() -> dict:
    """取得 QQQ、SPY 的 1d/1w/1m 報酬"""
    result = {}
    for sym in BENCHMARKS:
        try:
            hist = yf.Ticker(sym).history(period="35d")
            if len(hist) < 2:
                result[sym] = {"1d": 0.0, "1w": 0.0, "1m": 0.0}
                continue
            now = hist["Close"].iloc[-1]
            d1  = hist["Close"].iloc[-2]
            d5  = hist["Close"].iloc[-6] if len(hist) >= 6 else now
            d21 = hist["Close"].iloc[-22] if len(hist) >= 22 else now
            result[sym] = {
                "1d": round((now - d1)  / d1  * 100, 2),
                "1w": round((now - d5)  / d5  * 100, 2),
                "1m": round((now - d21) / d21 * 100, 2),
                "price": round(float(now), 2),
            }
        except Exception as e:
            logger.warning(f"{sym} 基準資料取得失敗：{e}")
            result[sym] = {"1d": 0.0, "1w": 0.0, "1m": 0.0, "price": 0.0}
    return result


def fetch_benchmark_nav_history(days: int = 90) -> dict[str, list]:
    """取得 QQQ/SPY 歷史 NAV（用於 Dashboard 折線圖比對）"""
    result = {}
    for sym in BENCHMARKS:
        try:
            hist = yf.Ticker(sym).history(period=f"{days + 5}d")
            if hist.empty:
                result[sym] = []
                continue
            base = hist["Close"].iloc[0]
            result[sym] = [
                {
                    "date": str(idx.date()),
                    "value": round(float(close) / float(base) * 100, 2),
                }
                for idx, close in zip(hist.index, hist["Close"])
            ]
        except Exception as e:
            logger.warning(f"{sym} 歷史資料取得失敗：{e}")
            result[sym] = []
    return result
