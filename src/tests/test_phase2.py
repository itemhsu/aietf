from __future__ import annotations
"""Phase 2 測試 — 市場資料、選股、P/E、基準"""
import pytest
import responses as rsps
from unittest.mock import patch, MagicMock
from src.data.market_data import (
    fetch_prices, calculate_market_caps, rank_stocks,
    SHARES_OUTSTANDING, StockData
)
from src.data.pe_ratio import fetch_pe_ratios
from src.data.benchmark import fetch_benchmark_performance
from src.data.alpaca_client import AlpacaClient
from src.engine.selector import select_top_stocks

BASE_URL = "https://paper-api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"

MOCK_BARS = {
    "bars": {
        "AAPL": {"c": 192.35},
        "MSFT": {"c": 415.20},
        "NVDA": {"c": 875.00},
        "GOOGL": {"c": 178.50},
        "AMZN": {"c": 185.90},
    }
}


@rsps.activate
def test_fetch_prices_batch():
    rsps.add(rsps.GET, f"{DATA_URL}/v2/stocks/bars/latest",
             json=MOCK_BARS, status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    prices = fetch_prices(list(MOCK_BARS["bars"].keys()), client)
    assert len(prices) == 5
    assert prices["AAPL"] == 192.35


@rsps.activate
def test_market_cap_calc():
    prices = {"AAPL": 192.35, "MSFT": 415.20}
    caps = calculate_market_caps(prices)
    assert "AAPL" in caps
    expected = 192.35 * SHARES_OUTSTANDING["AAPL"]
    assert abs(caps["AAPL"] - expected) < 1


@rsps.activate
def test_top10_selection_marketcap():
    rsps.add(rsps.GET, f"{DATA_URL}/v2/stocks/bars/latest",
             json=MOCK_BARS, status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    strategy = {
        "universe": {"symbols": list(MOCK_BARS["bars"].keys()), "min_market_cap_B": 0},
        "selection": {"method": "market_cap", "top_n": 3},
        "allocation": {},
    }
    top = select_top_stocks(strategy, client)
    assert len(top) == 3
    # 應依市值由大至小
    caps = [s.market_cap for s in top]
    assert caps == sorted(caps, reverse=True)


def test_top10_no_duplicate():
    prices = {"AAPL": 192.0, "MSFT": 415.0, "NVDA": 875.0}
    ranked = rank_stocks(prices, method="market_cap", top_n=3)
    symbols = [s.symbol for s in ranked]
    assert len(symbols) == len(set(symbols))


def test_ranking_order():
    prices = {"AAPL": 192.0, "MSFT": 415.0, "NVDA": 875.0}
    ranked = rank_stocks(prices, method="market_cap", top_n=3)
    caps = [s.market_cap for s in ranked]
    assert caps[0] >= caps[1] >= caps[2]


@patch("yfinance.Ticker")
def test_pe_ratio_positive(mock_ticker):
    mock_ticker.return_value.info = {"trailingPE": 28.5}
    result = fetch_pe_ratios(["AAPL"])
    assert result["AAPL"] == 28.5


@patch("yfinance.Ticker")
def test_pe_ratio_na_on_missing(mock_ticker):
    mock_ticker.return_value.info = {}
    result = fetch_pe_ratios(["XYZ"])
    assert result["XYZ"] == "N/A"


@patch("yfinance.Ticker")
def test_benchmark_qqq_spy(mock_ticker):
    import pandas as pd
    import numpy as np
    mock_hist = pd.DataFrame(
        {"Close": [450.0 + i for i in range(30)]},
        index=pd.date_range("2026-04-01", periods=30)
    )
    mock_ticker.return_value.history.return_value = mock_hist
    result = fetch_benchmark_performance()
    assert "QQQ" in result
    assert "SPY" in result
    assert "1d" in result["QQQ"]
    assert "1w" in result["QQQ"]


@rsps.activate
def test_missing_price_handling():
    """無報價的股票應被排除"""
    rsps.add(rsps.GET, f"{DATA_URL}/v2/stocks/bars/latest",
             json={"bars": {"AAPL": {"c": 192.0}}}, status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    prices = fetch_prices(["AAPL", "FAKESYM"], client)
    assert "AAPL" in prices
    assert "FAKESYM" not in prices


@rsps.activate
def test_watchlist_prices():
    all_syms = ["NVDA", "MSFT", "GOOGL", "META", "AMZN",
                "TSM", "ASML", "AVGO", "AMD", "QCOM",
                "NFLX", "UBER", "SNOW", "PLTR", "CRM"]
    bars = {"bars": {s: {"c": 100.0 + i} for i, s in enumerate(all_syms)}}
    rsps.add(rsps.GET, f"{DATA_URL}/v2/stocks/bars/latest",
             json=bars, status=200)
    client = AlpacaClient("key", "secret", BASE_URL)
    prices = fetch_prices(all_syms, client)
    assert len(prices) == len(all_syms)
