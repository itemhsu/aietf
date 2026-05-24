"""
AlpacaBot 主程式入口
- GitHub Actions 每日呼叫
- 依序走過所有帳戶，執行選股→再平衡→報告→通知
"""
import os
import sys
import logging
from datetime import date
from pathlib import Path

# 確保 src 在路徑中
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("alpacabot.main")

from src.engine.account_manager import load_accounts
from src.engine.selector import select_top_stocks, get_watchlist_prices
from src.engine.rebalancer import calculate_rebalance, should_rebalance
from src.engine.trader import execute_rebalance
from src.data.benchmark import fetch_benchmark_performance
from src.data.market_data import fetch_performance
from src.report.model import build_report, save_report, load_nav_history, REPORTS_DIR
from src.report.view_email import render_email_html, save_email_html
from src.notify.email_sender import send_daily_report
from src.notify.trade_alert import make_notifier


def run_account(account, dry_run: bool) -> bool:
    """執行單一帳戶的完整流程"""
    logger.info(f"{'='*50}")
    logger.info(f"帳戶：{account.account_id} ({account.display_name})")
    logger.info(f"策略：{account.active_strategy}")
    logger.info(f"DRY_RUN：{dry_run}")

    client = account.client()
    strategy = account.strategy()

    # Step 1：確認交易日
    if not client.is_trading_day():
        logger.info("今日非交易日，跳過")
        return True

    # Step 2：取得帳戶狀態
    alpaca_account = client.get_account()
    nav = float(alpaca_account.get("equity", 0))
    cash = float(alpaca_account.get("cash", 0))
    logger.info(f"NAV: ${nav:,.2f}  現金: ${cash:,.2f}")

    # Step 3：取得持倉
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

    # Step 4：選股
    top10 = select_top_stocks(strategy, client)
    if not top10:
        logger.error("選股失敗，中止")
        return False

    # Step 5：判斷是否再平衡
    history = load_nav_history(account.account_id)
    prev_nav = history[-1]["nav"] if history else None
    rebal_needed, rebal_reason = should_rebalance(strategy, cash, nav, None)
    rebal_needed = rebal_needed or (len(positions) == 0)  # 首次建倉

    trades = []
    if rebal_needed:
        logger.info(f"觸發再平衡：{rebal_reason or '首次建倉'}")
        orders = calculate_rebalance(positions, top10, nav, cash, strategy)
        notifier = make_notifier(account.account_id, account.email_recipient)
        trades = execute_rebalance(client, orders, dry_run=dry_run, notify_fn=notifier)

        # 再平衡後重新取得帳戶狀態
        if not dry_run:
            alpaca_account = client.get_account()
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
    else:
        logger.info("無需再平衡（在容忍帶內）")

    # Step 6：生成報告
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
    today_dir = REPORTS_DIR / date.today().isoformat()
    email_html = render_email_html(report)
    save_email_html(report, today_dir)

    # Step 7：發送 Email
    send_daily_report(report, email_html)

    logger.info(f"帳戶 {account.account_id} 完成 ✓")
    return True


def main():
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    account_filter = os.environ.get("ACCOUNT_FILTER", "")

    logger.info("AlpacaBot 啟動")
    logger.info(f"DRY_RUN={dry_run}, ACCOUNT_FILTER='{account_filter}'")

    accounts = load_accounts(account_filter)
    if not accounts:
        logger.warning("沒有啟用的帳戶，結束")
        return

    success_count = 0
    for account in accounts:
        try:
            ok = run_account(account, dry_run=dry_run)
            if ok:
                success_count += 1
        except Exception as e:
            logger.error(f"帳戶 {account.account_id} 發生錯誤：{e}", exc_info=True)

    logger.info(f"完成：{success_count}/{len(accounts)} 帳戶成功")


if __name__ == "__main__":
    main()
