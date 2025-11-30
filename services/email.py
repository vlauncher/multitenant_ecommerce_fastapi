import os
from core.config import settings

# Try to import Celery task, fallback to direct execution if not available
try:
    from tasks.email_tasks import send_email_task
    USE_CELERY = True
except ImportError:
    USE_CELERY = False

from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape


# Jinja2 environment for email templates
_templates_env = Environment(
    loader=FileSystemLoader(searchpath=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")),
    autoescape=select_autoescape(["html", "xml", "txt"]),
)

def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Send email using Celery if available, otherwise send directly.
    This function returns immediately and doesn't block the request when using Celery.
    """
    if USE_CELERY:
        try:
            send_email_task.delay(to_email, subject, body)
            print("✓ Email task queued to Celery")
            return
        except Exception as e:
            if settings.DEBUG:
                print(f"Celery not available, falling back to direct email sending: {e}")
            else:
                # In production, we might want to fail or retry
                pass
    
    # Fallback: send email directly (synchronously)
    _send_email_direct(to_email, subject, body)


def render_template(template_path: str, context: Dict[str, Any]) -> str:
    """Render a text template from templates/ directory with provided context."""
    template = _templates_env.get_template(template_path)
    return template.render(**context)


def send_templated_email(to_email: str, subject: str, template_path: str, context: Dict[str, Any]) -> None:
    """Render a template and send email via existing send_email path."""
    body = render_template(template_path, context)
    send_email(to_email, subject, body)


def _send_email_direct(to_email: str, subject: str, body: str) -> None:
    """Direct email sending fallback"""
    import smtplib
    from email.message import EmailMessage
    
    # Only skip email sending with placeholder credentials
    if settings.SMTP_PASSWORD == "your-gmail-app-password":
        print(f"DEBUG: Email would be sent to {to_email}")
        print(f"DEBUG: Subject: {subject}")
        print(f"DEBUG: Body: {body}")
        print("DEBUG: Configure real SMTP credentials to send actual emails")
        return
    
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ Email sent successfully to {to_email}")
    except Exception as e:
        if settings.DEBUG:
            print(f"Failed to send email: {e}")
            print(f"Email content: To: {to_email}, Subject: {subject}, Body: {body}")
        else:
            # In production, you might want to log this error
            print(f"Email sending failed: {e}")
