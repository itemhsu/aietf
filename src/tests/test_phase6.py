from __future__ import annotations
"""Phase 6 測試 — Email 通知"""
import pytest
from unittest.mock import patch, MagicMock


def make_mock_report():
    return {
        "report_id": "2026-05-24_test",
        "account_id": "test_account",
        "strategy_id": "top10_marketcap_v1",
        "date": "2026-05-24",
        "generated_at": "2026-05-24T06:00:00",
        "email_recipient": "test@test.com",
        "account_summary": {
            "nav": 102345.67, "cash": 1234.56, "cash_pct": 1.2,
            "equity": 101111.11, "daily_pnl": 1234.56, "daily_pnl_pct": 1.22,
            "drawdown_pct": -1.5, "max_drawdown_pct": -3.2,
        },
        "positions": [],
        "top10_today": [],
        "trades_executed": [],
        "benchmark": {"QQQ": {"1d": 0.95, "1w": 2.0, "1m": 3.2},
                      "SPY": {"1d": 0.70, "1w": 1.5, "1m": 2.1}},
        "nav_history": [],
        "watchlist": {},
        "disclaimer": "本報告僅供研究參考，不構成投資建議。",
    }


def test_email_renders_from_model():
    from src.report.view_email import render_email_html
    report = make_mock_report()
    html = render_email_html(report)
    assert len(html) > 100
    assert "2026-05-24" in html


def test_email_contains_disclaimer():
    from src.report.view_email import render_email_html
    report = make_mock_report()
    html = render_email_html(report)
    assert "投資建議" in html


def test_email_pnl_positive_green():
    from src.report.view_email import render_email_html
    report = make_mock_report()
    report["account_summary"]["daily_pnl"] = 500
    report["account_summary"]["daily_pnl_pct"] = 0.5
    html = render_email_html(report)
    assert "#16a34a" in html   # 綠色


def test_email_pnl_negative_red():
    from src.report.view_email import render_email_html
    report = make_mock_report()
    report["account_summary"]["daily_pnl"] = -500
    report["account_summary"]["daily_pnl_pct"] = -0.5
    html = render_email_html(report)
    assert "#dc2626" in html   # 紅色


@patch("smtplib.SMTP_SSL")
def test_email_send_mock(mock_smtp):
    import os
    from src.notify.email_sender import send_daily_report
    os.environ["EMAIL_USER"] = "test@gmail.com"
    os.environ["EMAIL_PASS"] = "testpass"

    mock_server = MagicMock()
    mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

    report = make_mock_report()
    from src.report.view_email import render_email_html
    result = send_daily_report(report, render_email_html(report))
    assert result is True


def test_trade_alert_on_buy():
    from src.notify.trade_alert import make_notifier
    with patch("src.notify.trade_alert.send_trade_alert") as mock_send:
        notifier = make_notifier("account_A", "test@test.com")
        notifier("🟢 買入 AAPL × 10 股")
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert "AAPL" in args[1]


def test_trade_alert_on_sell():
    from src.notify.trade_alert import make_notifier
    with patch("src.notify.trade_alert.send_trade_alert") as mock_send:
        notifier = make_notifier("account_A", "test@test.com")
        notifier("🔴 賣出 INTC × 50 股")
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert "INTC" in args[1]


def test_multi_account_separate_email():
    from src.notify.trade_alert import make_notifier
    with patch("src.notify.trade_alert.send_trade_alert") as mock_send:
        notifier_a = make_notifier("account_A", "a@test.com")
        notifier_b = make_notifier("account_B", "b@test.com")
        notifier_a("測試 A")
        notifier_b("測試 B")
        calls = mock_send.call_args_list
        recipients = [c[0][0] for c in calls]
        assert "a@test.com" in recipients
        assert "b@test.com" in recipients
