from __future__ import annotations
"""策略 JSON 載入與驗證"""
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["strategy_id", "name", "universe", "selection", "allocation", "rebalance"]
STRATEGIES_DIR = Path(__file__).parents[2] / "strategies"


def load_strategy(strategy_id: str) -> dict:
    """依 strategy_id 載入對應的 JSON 策略"""
    path = STRATEGIES_DIR / f"{strategy_id}.json"
    if not path.exists():
        # 嘗試模糊搜尋
        for f in STRATEGIES_DIR.glob("*.json"):
            data = json.loads(f.read_text())
            if data.get("strategy_id") == strategy_id:
                path = f
                break
        else:
            raise FileNotFoundError(f"找不到策略：{strategy_id}")

    strategy = json.loads(path.read_text(encoding="utf-8"))
    validate_strategy(strategy)
    logger.info(f"策略載入成功：{strategy_id}")
    return strategy


def validate_strategy(strategy: dict) -> None:
    """驗證策略 JSON 必填欄位"""
    missing = [f for f in REQUIRED_FIELDS if f not in strategy]
    if missing:
        raise ValueError(f"策略 JSON 缺少必填欄位：{missing}")
    if "top_n" not in strategy["selection"]:
        raise ValueError("策略 selection 需包含 top_n")
    if "weight_per_stock" not in strategy["allocation"]:
        raise ValueError("策略 allocation 需包含 weight_per_stock")


def list_strategies() -> list[str]:
    """列出所有可用策略"""
    result = []
    for f in STRATEGIES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            result.append(data.get("strategy_id", f.stem))
        except Exception:
            pass
    return result
