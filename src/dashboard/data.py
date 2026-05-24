from __future__ import annotations
"""
Dashboard 資料讀取模組
━━━━━━━━━━━━━━━━━━━━━
⚡ 此模組不呼叫任何外部 API（Alpaca / yfinance / requests）。
⚡ 所有資料來自 reports/ 目錄的 JSON 報告（由 GitHub Actions 預先生成）。
⚡ 可被獨立 import 測試，不依賴 Streamlit Context。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def get_reports_dir() -> Path:
    return ROOT / "reports"


def get_history_index_path() -> Path:
    return get_reports_dir() / "history_index.json"


def get_account_ids() -> list[str]:
    """從 accounts_index.json 讀取啟用的帳戶列表"""
    path = ROOT / "accounts" / "accounts_index.json"
    if not path.exists():
        return ["account_A"]
    data = json.loads(path.read_text(encoding="utf-8"))
    return [a["account_id"] for a in data["accounts"] if a.get("enabled")]


def get_available_dates(account_id: str) -> list[str]:
    """回傳指定帳戶的所有可用報告日期（由新到舊）"""
    idx = get_history_index_path()
    if not idx.exists():
        return []
    index = json.loads(idx.read_text(encoding="utf-8"))
    dates = sorted(
        {r["date"] for r in index.get("reports", [])
         if r["account_id"] == account_id},
        reverse=True,
    )
    return dates


def get_all_account_nav_history(account_id: str) -> list[dict]:
    """回傳帳戶 NAV 歷史（依日期升序），資料來自 history_index.json"""
    idx = get_history_index_path()
    if not idx.exists():
        return []
    index = json.loads(idx.read_text(encoding="utf-8"))
    records = sorted(
        [r for r in index.get("reports", []) if r["account_id"] == account_id],
        key=lambda r: r["date"],
    )
    return [{"date": r["date"], "nav": r["nav"]} for r in records]


def load_report_json(account_id: str, report_date: str) -> dict | None:
    """載入指定帳戶與日期的報告 JSON，不存在時回傳 None"""
    path = get_reports_dir() / report_date / f"model_{account_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
