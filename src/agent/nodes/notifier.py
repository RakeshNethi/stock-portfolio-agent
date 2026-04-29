"""Notification dispatcher node.

Sends the generated briefing via configured channels
(email, Telegram). Phase 1 outputs to console.
"""

from __future__ import annotations

import json
from datetime import datetime

from src.agent.state import AgentState
from src.utils.config import load_settings
from src.utils.logging import get_logger

log = get_logger(__name__)


def _format_console_briefing(briefing: dict) -> str:
    """Format briefing data as a readable console output."""
    lines = [
        "",
        "━" * 60,
        f"📊 {briefing.get('run_type', 'DAILY').upper()} BRIEFING — {briefing.get('generated_at', '')[:10]}",
        "━" * 60,
        "",
    ]

    # Market overview
    overview = briefing.get("market_overview", "")
    if overview:
        lines.append("🌍 MARKET OVERVIEW")
        lines.append(overview)
        lines.append("")

    # Stock table
    stock_table = briefing.get("stock_table", [])
    if stock_table:
        lines.append("📈 YOUR PORTFOLIO")
        lines.append(f"{'Ticker':<8} {'Price':>10} {'Change':>8} {'Signal':<12} {'Note'}")
        lines.append("─" * 60)
        for row in stock_table:
            ticker = row.get("ticker", "")
            price = row.get("price", 0)
            change = row.get("change_percent", 0)
            signal = row.get("signal", "hold")
            note = row.get("one_liner", "")
            lines.append(f"{ticker:<8} ${price:>9.2f} {change:>+7.1f}% {signal:<12} {note}")
        lines.append("")

    # Alerts
    alerts = briefing.get("alerts", [])
    if alerts:
        lines.append("⚡ KEY ALERTS")
        for i, alert in enumerate(alerts, 1):
            level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(
                alert.get("level", "info"), "ℹ️"
            )
            lines.append(f"  {i}. {level_emoji} {alert.get('title', '')}")
            lines.append(f"     {alert.get('detail', '')}")
        lines.append("")

    # Recommendations
    recs = briefing.get("recommendations", [])
    if recs:
        lines.append("💡 RECOMMENDATIONS")
        for rec in recs:
            signal_emoji = {"buy": "🟢", "strong_buy": "🟢", "sell": "🔴",
                           "strong_sell": "🔴", "hold": "🟡"}.get(
                rec.get("signal", "hold"), "🟡"
            )
            lines.append(f"  {signal_emoji} {rec.get('ticker', '')}: {rec.get('rationale', '')}")
            levels = rec.get("key_levels", {})
            if levels:
                level_str = ", ".join(f"{k}: ${v:.2f}" for k, v in levels.items())
                lines.append(f"     Key levels: {level_str}")
        lines.append("")

    # Narrative
    narrative = briefing.get("narrative", "")
    if narrative:
        lines.append("📝 FULL BRIEFING")
        lines.append(narrative)
        lines.append("")

    lines.append("━" * 60)
    return "\n".join(lines)


def send_notifications(state: AgentState) -> dict:
    """Send the briefing via configured notification channels.

    Phase 1: Prints to console.
    Phase 3: Will send via SendGrid email and Telegram bot.

    Args:
        state: Agent state with briefing generated.

    Returns:
        State update with audit log entry.
    """
    briefing = state.get("briefing", {})
    settings = load_settings()
    notification_config = settings.get("notifications", {})

    log.info("send_notifications_start")

    # Always output to console
    formatted = _format_console_briefing(briefing)
    print(formatted)

    channels_sent = ["console"]

    if notification_config.get("email", {}).get("enabled", False):
        from src.notifications.email_sender import send_email
        if send_email(briefing, notification_config["email"]):
            channels_sent.append("email")

    if notification_config.get("telegram", {}).get("enabled", False):
        from src.notifications.telegram_bot import send_telegram
        if send_telegram(briefing, notification_config["telegram"]):
            channels_sent.append("telegram")

    log.info("send_notifications_complete", channels=channels_sent)

    return {
        "audit_log": [
            {
                "timestamp": datetime.now().isoformat(),
                "agent": "Notifier",
                "action": "send_notifications",
                "detail": f"Sent via: {', '.join(channels_sent)}",
            }
        ],
    }
