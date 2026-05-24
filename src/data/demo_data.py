from __future__ import annotations
"""
DEMO_MODE 假資料產生器
━━━━━━━━━━━━━━━━━━━━━━
當 DEMO_MODE=true 時使用，完全不需要 Alpaca API Key。
讓 GitHub Actions 在未設定 Secrets 的情況下也能跑通整個流程，
產生真實格式的報告 JSON 供 Streamlit Dashboard 展示。
"""
import random
from datetime import date, timedelta
from src.data.market_data import StockData

# ── 假股票價格（接近真實的靜態數值）──────────────────────────────────────
DEMO_PRICES = {
    "AAPL": 192.35, "MSFT": 415.20, "NVDA": 875.00, "GOOGL": 178.50,
    "AMZN": 185.90, "META": 512.30, "AVGO": 1680.00, "TSM": 168.40,
    "V":    278.50, "MA":   468.20, "ORCL": 138.90, "CRM":  310.50,
    "ADBE": 480.10, "CSCO":  53.40, "INTC":  30.20, "QCOM": 168.80,
    "TXN":  195.60, "NOW":  780.30, "NFLX": 645.20, "UBER":  78.50,
    "SNOW": 148.30, "PLTR":  24.50, "AMD":  156.70, "IBM":  191.30,
    "ASML": 810.40,
}

DEMO_SHARES = {
    "AAPL": 15_204_137_000, "MSFT": 7_433_000_000, "NVDA": 24_440_000_000,
    "GOOGL":  5_949_000_000, "AMZN": 10_525_000_000, "META":  2_560_000_000,
    "TSM":    5_180_000_000, "ASML":    394_000_000, "AVGO":  4_680_000_000,
    "V":      2_060_000_000, "MA":      924_000_000, "ORCL":  2_750_000_000,
    "CRM":      968_000_000, "ADBE":    435_000_000, "CSCO":  4_040_000_000,
    "INTC":   4_260_000_000, "QCOM":  1_120_000_000, "TXN":     908_000_000,
    "NOW":      204_000_000, "NFLX":    431_000_000, "UBER":  2_140_000_000,
    "SNOW":     330_000_000, "PLTR":  2_100_000_000, "AMD":   1_617_000_000,
    "IBM":      906_000_000,
}


def demo_client():
    """回傳一個模擬 AlpacaClient，所有方法回傳假資料"""
    from unittest.mock import MagicMock
    client = MagicMock()

    # is_trading_day
    client.is_trading_day.return_value = True

    # get_account
    client.get_account.return_value = {
        "equity": "102345.67",
        "cash": "1023.45",
        "portfolio_value": "102345.67",
    }

    # get_positions — 模擬已有前 5 檔持倉
    top5 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
    client.get_positions.return_value = [
        {
            "symbol": sym,
            "qty": str(int(10000 / DEMO_PRICES[sym])),
            "avg_entry_price": str(round(DEMO_PRICES[sym] * 0.96, 2)),
            "current_price": str(DEMO_PRICES[sym]),
            "market_value": str(round(int(10000 / DEMO_PRICES[sym]) * DEMO_PRICES[sym], 2)),
        }
        for sym in top5
    ]

    # get_latest_bars
    def _mock_bars(symbols):
        return {s: DEMO_PRICES[s] for s in symbols if s in DEMO_PRICES}
    client.get_latest_bars.side_effect = _mock_bars

    # submit_order — 回傳假 order_id
    import uuid
    client.submit_order.return_value = {"id": str(uuid.uuid4()), "status": "filled"}
    client.wait_for_fills.return_value = {}

    return client


def demo_top10() -> list[StockData]:
    """回傳 demo 用的前 10 檔 StockData"""
    stocks = []
    for sym, price in DEMO_PRICES.items():
        shares = DEMO_SHARES.get(sym, 1_000_000_000)
        mc = price * shares
        stocks.append(StockData(
            symbol=sym, price=price,
            shares_outstanding=shares,
            market_cap=mc, market_cap_B=round(mc / 1e9, 1),
        ))
    stocks.sort(key=lambda s: s.market_cap, reverse=True)
    for i, s in enumerate(stocks):
        s.rank = i + 1
    return stocks[:10]


def demo_benchmark_performance() -> dict:
    return {
        "QQQ": {"1d": 0.95, "1w": 2.10, "1m": 3.20, "price": 445.0},
        "SPY": {"1d": 0.70, "1w": 1.50, "1m": 2.10, "price": 525.0},
    }


def demo_benchmark_nav_history(days: int = 60) -> dict:
    """產生 QQQ/SPY 模擬 NAV 歷史（隨機遊走，起始值 100）"""
    random.seed(42)
    result = {}
    for sym, drift, vol in [("QQQ", 0.0004, 0.008), ("SPY", 0.0003, 0.006)]:
        val, history = 100.0, []
        for i in range(days):
            d = date.today() - timedelta(days=days - i)
            val *= (1 + drift + random.gauss(0, vol))
            history.append({"date": d.isoformat(), "value": round(val, 2)})
        result[sym] = history
    return result


def demo_pe_ratios(symbols: list[str]) -> dict:
    base = {"AAPL": 28.5, "MSFT": 35.2, "NVDA": 65.0, "GOOGL": 22.1,
            "AMZN": 45.0, "META": 24.3, "AVGO": 32.1, "TSM": 18.5,
            "V": 30.2, "MA": 33.8}
    return {s: base.get(s, "N/A") for s in symbols}


def demo_performance(symbols: list[str]) -> dict:
    random.seed(123)
    return {
        s: {
            "1d": round(random.gauss(0.5, 1.2), 2),
            "1w": round(random.gauss(1.2, 2.5), 2),
            "1m": round(random.gauss(3.0, 5.0), 2),
        }
        for s in symbols
    }
