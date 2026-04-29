"""LLM synthesizer node.

Takes all collected data and uses Gemini Flash to generate
a structured daily briefing with recommendations.
"""

from __future__ import annotations

import json
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agent.state import AgentState
from src.utils.config import get_api_key, load_settings
from src.utils.logging import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are a professional stock portfolio analyst assistant.
Synthesize market data, technical indicators, earnings, and news into a concise daily briefing.

GUIDELINES:
- Be concise but thorough (2-3 minute read).
- Lead with big movers and urgent alerts.
- Explain technical signals in plain English.
- Use emoji sparingly (🟢 🟡 🔴 ⚡ 📈 📉).
- Frame as "signals suggest" — NEVER give direct financial advice.

Return ONLY valid JSON with these fields:
{
  "market_overview": "2-3 sentence market summary",
  "portfolio_snapshot": {"total_value": 0, "day_change": 0, "day_change_percent": 0},
  "stock_table": [{"ticker": "", "price": 0, "change_percent": 0, "signal": "", "one_liner": ""}],
  "alerts": [{"ticker": "", "level": "info|warning|critical", "title": "", "detail": ""}],
  "recommendations": [{"ticker": "", "signal": "", "rationale": "", "key_levels": {}, "confidence": 0}],
  "news_digest": "summarized news",
  "narrative": "full 2-3 paragraph briefing"
}"""


def synthesize_briefing(state: AgentState) -> dict:
    """Generate the daily briefing using Gemini Flash."""
    run_type = state.get("run_type", "morning")
    log.info("synthesize_start", run_type=run_type)

    settings = load_settings()
    llm_config = settings.get("llm", {})

    context = {
        "run_type": run_type,
        "date": datetime.now().strftime("%A, %B %d, %Y"),
        "portfolio": state.get("portfolio", {}),
        "quotes": state.get("quotes", {}),
        "market_overview": state.get("market_overview", {}),
        "technical_signals": state.get("technical_signals", {}),
        "upcoming_earnings": state.get("upcoming_earnings", []),
        "recent_surprises": state.get("recent_surprises", []),
        "news_headlines": state.get("news_headlines", []),
        "sentiment_scores": state.get("sentiment_scores", {}),
    }

    user_prompt = f"Generate a {run_type.upper()} briefing:\n\n{json.dumps(context, indent=2, default=str)}\n\nReturn ONLY valid JSON."

    try:
        api_key = get_api_key("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model=llm_config.get("model", "gemini-2.0-flash"),
            temperature=llm_config.get("temperature", 0.3),
            max_output_tokens=llm_config.get("max_output_tokens", 4096),
            google_api_key=api_key,
        )

        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        text = response.content

        # Parse JSON from response (handle markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        briefing_data = json.loads(text.strip())
        log.info("synthesize_complete")

        return {
            "briefing": {"run_id": state.get("run_id", ""), "run_type": run_type,
                         "generated_at": datetime.now().isoformat(), **briefing_data},
            "recommendations": briefing_data.get("recommendations", []),
            "quality_score": 1.0,
            "audit_log": [{"timestamp": datetime.now().isoformat(), "agent": "Synthesizer",
                           "action": "generate_briefing", "detail": f"Generated {run_type} briefing"}],
        }

    except Exception as e:
        log.error("synthesize_error", error=str(e))
        return {
            "briefing": {"run_id": state.get("run_id", ""), "run_type": run_type,
                         "generated_at": datetime.now().isoformat(),
                         "narrative": f"Error: {e}", "error": True},
            "quality_score": 0.0,
            "audit_log": [{"timestamp": datetime.now().isoformat(), "agent": "Synthesizer",
                           "action": "generate_briefing_error", "detail": str(e)}],
        }
