from __future__ import annotations
"""Email 發送模組 — 使用 Gmail SMTP"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

logger = logging.getLogger(__name__)


def send_daily_report(report: dict, html_content: str) -> bool:
    """發送日報 Email"""
    recipient = report.get("email_recipient") or os.environ.get("EMAIL_RECIPIENT", "")
    s = report["account_summary"]
    pnl_sign = "+" if s["daily_pnl"] >= 0 else ""
    subject = (
        f"📊 AlpacaBot 日報 {report['date']} | "
        f"NAV: ${s['nav']:,.0f} | "
        f"今日 {pnl_sign}{s['daily_pnl_pct']:.2f}%"
    )
    return _send_email(recipient, subject, html_content)


def send_trade_alert(recipient: str, message: str) -> bool:
    """發送即時交易通知"""
    subject = f"🔔 AlpacaBot 交易通知 {date.today()}"
    html = f"""<html><body style="font-family:sans-serif;padding:20px;">
    <h2>AlpacaBot 交易通知</h2>
    <p style="font-size:1.1rem;">{message}</p>
    <p style="color:#94a3b8;font-size:.8rem;">⚠️ 本通知僅供資訊參考，不構成投資建議。</p>
    </body></html>"""
    return _send_email(recipient, subject, html)


def _send_email(recipient: str, subject: str, html_body: str) -> bool:
    user = os.environ.get("EMAIL_USER", "")
    password = os.environ.get("EMAIL_PASS", "")

    if not user or not password:
        logger.warning("EMAIL_USER 或 EMAIL_PASS 未設定，跳過發送")
        return False
    if not recipient:
        logger.warning("收件人未設定，跳過發送")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, recipient, msg.as_string())
        logger.info(f"Email 已發送至 {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email 發送失敗：{e}")
        return False
