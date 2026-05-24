from __future__ import annotations
"""本益比（P/E Ratio）計算模組"""
import logging
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_pe_ratios(symbols: list[str]) -> dict[str, float | str]:
    """取得個股本益比，無資料時回傳 'N/A'"""
    result = {}
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            pe = info.get("trailingPE") or info.get("forwardPE")
            result[sym] = round(float(pe), 1) if pe else "N/A"
        except Exception as e:
            logger.warning(f"{sym} P/E 取得失敗：{e}")
            result[sym] = "N/A"
    return result
