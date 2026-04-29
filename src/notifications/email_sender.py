"""Email notification sender using SendGrid."""

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from jinja2 import Environment, FileSystemLoader

from src.utils.config import get_api_key
from src.utils.logging import get_logger

log = get_logger(__name__)

def send_email(briefing: dict, config: dict) -> bool:
    """Send HTML email briefing via SendGrid."""
    api_key = get_api_key("SENDGRID_API_KEY")
    if not api_key:
        log.warning("sendgrid_no_api_key")
        return False
        
    to_email = config.get("to")
    if not to_email:
        log.error("sendgrid_no_to_address")
        return False
        
    run_type = briefing.get("run_type", "morning")
    subject = f"📊 Stock Portfolio {run_type.capitalize()} Briefing"
    
    # Render HTML template
    try:
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(f"{run_type}_briefing.html")
        html_content = template.render(**briefing)
    except Exception as e:
        log.error("email_template_error", error=str(e))
        return False
        
    message = Mail(
        from_email="briefing@portfolio-agent.com",
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        log.info("email_sent", status_code=response.status_code)
        return True
    except Exception as e:
        log.error("email_send_error", error=str(e))
        return False
