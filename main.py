"""
AlpacaBot 主程式入口
━━━━━━━━━━━━━━━━━━━
執行環境：GitHub Actions（不支援也不需要本機 .env）
環境變數由 GitHub Secrets 注入。

執行模式：
  DEMO_MODE=true   — 使用模擬資料，不需要任何 API Key（用於測試流程）
  DRY_RUN=true     — 有真實 API Key，計算但不下單
  DRY_RUN=false    — 實際下單（需 Live Key + 充足資金）
"""
import os
import sys
import logging
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("alpacabot.main")

# ── 模式旗標 ──────────────────────────────────────────────────────────────
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
DRY_RUN   = os.environ.get("DRY_RUN",   "true").lower()  == "true"

from src.engine.account_manager import load_accounts
from src.engine.selector import select_top_stocks
from src.engine.rebalancer import calculate_rebalance, should_rebalance
from src.engine.trader import execute_rebalance
from src.report.model import (
    build_report, save_report, load_nav_history, REPORTS_DIR
)
from src.report.view_email import render_email_html, save_email_html
from src.notify.email_sender import send_daily_report
from src.notify.trade_alert import make_notifier


def run_account_demo(account) -> bool:
    """DEMO_MODE：使用假資料走完整個流程，不呼叫任何 API"""
    from src.data.demo_data import (
        demo_client, demo_top10, demo_benchmark_performance,
        demo_benchmark_nav_history, demo_pe_ratios, demo_performance,
        DEMO_PRICES,
    )
    logger.info("▶ DEMO_MODE — 使用模擬資料")

    strategy  = account.strategy()
    client    = demo_client()
    top10     = demo_top10()
    positions = client.get_positions.return_value

    # 模擬帳戶數值
    alpaca_account = client.get_account.return_value
    nav   = float(alpaca_account["equity"])
    cash  = float(alpaca_account["cash"])

    # 計算再平衡（DRY_RUN，不實際下單）
    current_positions = [
        {
            "symbol": p["symbol"],
            "qty": float(p["qty"]),
            "avg_entry_price": float(p["avg_entry_price"]),
            "current_price": float(p["current_price"]),
            "market_value": float(p["market_value"]),
        }
        for p in positions
    ]
    orders = calculate_rebalance(current_positions, top10, nav, cash, strategy)
    trades = execute_rebalance(client, orders, dry_run=True)

    # 用 mock patch 替換 build_report 的外部呼叫
    import unittest.mock as mock
    history = load_nav_history(account.account_id)
    prev_nav = history[-1]["nav"] if history else None

    with mock.patch("src.report.model.fetch_performance",
                    side_effect=demo_performance), \
         mock.patch("src.report.model.fetch_pe_ratios",
                    side_effect=demo_pe_ratios), \
         mock.patch("src.report.model.fetch_benchmark_performance",
                    return_value=demo_benchmark_performance()), \
         mock.patch("src.report.model.fetch_benchmark_nav_history",
                    return_value=demo_benchmark_nav_history()):

        report = build_report(
            account_id=account.account_id,
            strategy=strategy,
            alpaca_account=alpaca_account,
            positions=current_positions,
            top10=top10,
            trades=trades,
            prev_nav=prev_nav,
        )

    report["email_recipient"] = account.email_recipient
    report_path  = save_report(report)
    today_dir    = REPORTS_DIR / date.today().isoformat()
    email_html   = render_email_html(report)
    save_email_html(report, today_dir)
    send_daily_report(report, email_html)

    logger.info(f"[DEMO] 帳戶 {account.account_id} 完成 ✓ — 報告：{report_path}")
    return True


def run_account_live(account) -> bool:
    """REAL_MODE：使用真實 Alpaca API"""
    client   = account.client()
    strategy = account.strategy()

    # 確認交易日
    if not client.is_trading_day():
        logger.info("今日非交易日，跳過")
        return True

    # 帳戶狀態
    alpaca_account = client.get_account()
    nav  = float(alpaca_account.get("equity", 0))
    cash = float(alpaca_account.get("cash",   0))
    logger.info(f"NAV: ${nav:,.2f}  現金: ${cash:,.2f}")

    # 持倉
    raw_positions = client.get_positions()
    positions = [
        {
            "symbol": p.get("symbol"),
            "qty": float(p.get("qty", 0)),
            "avg_entry_price": float(p.get("avg_entry_price", 0)),
            "current_price": float(p.get("current_price", 0)),
            "market_value": float(p.get("market_value", 0)),
        }
        for p in raw_positions
    ]

    # 選股
    top10 = select_top_stocks(strategy, client)
    if not top10:
        logger.error("選股失敗，中止")
        return False

    # 再平衡
    history  = load_nav_history(account.account_id)
    prev_nav = history[-1]["nav"] if history else None
    rebal_needed, rebal_reason = should_rebalance(strategy, cash, nav, None)
    rebal_needed = rebal_needed or (len(positions) == 0)

    trades = []
    if rebal_needed:
        logger.info(f"觸發再平衡：{rebal_reason or '首次建倉'}")
        orders   = calculate_rebalance(positions, top10, nav, cash, strategy)
        notifier = make_notifier(account.account_id, account.email_recipient)
        trades   = execute_rebalance(client, orders, dry_run=DRY_RUN,
                                     notify_fn=notifier)
        if not DRY_RUN:
            alpaca_account = client.get_account()
            positions = [
                {
                    "symbol": p.get("symbol"),
                    "qty": float(p.get("qty", 0)),
                    "avg_entry_price": float(p.get("avg_entry_price", 0)),
                    "current_price": float(p.get("current_price", 0)),
                    "market_value": float(p.get("market_value", 0)),
                }
                for p in client.get_positions()
            ]
    else:
        logger.info("無需再平衡（在容忍帶內）")

    # 生成報告
    report = build_report(
        account_id=account.account_id,
        strategy=strategy,
        alpaca_account=alpaca_account,
        positions=positions,
        top10=top10,
        trades=trades,
        prev_nav=prev_nav,
    )
    report["email_recipient"] = account.email_recipient

    report_path = save_report(report)
    today_dir   = REPORTS_DIR / date.today().isoformat()
    email_html  = render_email_html(report)
    save_email_html(report, today_dir)
    send_daily_report(report, email_html)

    logger.info(f"帳戶 {account.account_id} 完成 ✓")
    return True


def main():
    account_filter = os.environ.get("ACCOUNT_FILTER", "")
    accounts = load_accounts(account_filter)

    mode = "DEMO" if DEMO_MODE else ("DRY_RUN" if DRY_RUN else "LIVE")
    logger.info(f"AlpacaBot 啟動  模式={mode}  帳戶數={len(accounts)}")

    if not accounts:
        logger.warning("沒有啟用的帳戶，結束")
        return

    success = 0
    for account in accounts:
        logger.info(f"{'='*50}")
        logger.info(f"帳戶：{account.account_id} ({account.display_name})")
        logger.info(f"策略：{account.active_strategy}  模式：{mode}")
        try:
            ok = run_account_demo(account) if DEMO_MODE \
                 else run_account_live(account)
            if ok:
                success += 1
        except Exception as e:
            logger.error(f"帳戶 {account.account_id} 失敗：{e}", exc_info=True)

    logger.info(f"完成：{success}/{len(accounts)} 帳戶成功")


if __name__ == "__main__":
    main()
