"""Telegram bot notification sender."""

import httpx
from src.utils.config import get_api_key
from src.utils.logging import get_logger

log = get_logger(__name__)

def send_telegram(briefing: dict, config: dict) -> bool:
    """Send briefing to Telegram chat."""
    bot_token = get_api_key("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        log.warning("telegram_no_bot_token")
        return False
        
    chat_id = config.get("chat_id")
    if not chat_id:
        log.error("telegram_no_chat_id")
        return False
        
    # Format message for Telegram
    run_type = briefing.get("run_type", "morning").upper()
    lines = [f"📊 *{run_type} BRIEFING*"]
    lines.append(f"_{briefing.get('market_overview', '')}_")
    
    for alert in briefing.get("alerts", []):
        emoji = "🔴" if alert.get("level") == "critical" else "🟡"
        lines.append(f"\n{emoji} *{alert.get('title')}*\n{alert.get('detail')}")
        
    lines.append(f"\n💡 *Recommendations*")
    for rec in briefing.get("recommendations", []):
        lines.append(f"• {rec.get('ticker')}: {rec.get('signal')} - {rec.get('rationale')}")
        
    text = "\n".join(lines)
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        log.info("telegram_sent")
        return True
    except Exception as e:
        log.error("telegram_send_error", error=str(e))
        return False
