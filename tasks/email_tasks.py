import smtplib
from email.message import EmailMessage
from celery import current_app
from core.config import settings


@current_app.task(bind=True, max_retries=3)
def send_email_task(self, to_email: str, subject: str, body: str):
    """
    Send email asynchronously with Celery.
    Retries up to 3 times on failure.
    """
    # Skip email sending in testing mode or with placeholder credentials
    if settings.TESTING or settings.SMTP_PASSWORD == "your-gmail-app-password":
        print(f"DEBUG: Email would be sent to {to_email}")
        print(f"DEBUG: Subject: {subject}")
        print(f"DEBUG: Body: {body}")
        return {"status": "debug", "message": "Email skipped in debug mode"}
    
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
        
        return {"status": "sent", "to": to_email, "subject": subject}
    
    except Exception as exc:
        if settings.DEBUG:
            print(f"Failed to send email: {exc}")
            print(f"Email content: To: {to_email}, Subject: {subject}, Body: {body}")
            return {"status": "failed", "error": str(exc), "debug": True}
        
        # Retry with exponential backoff
        countdown = min(2 ** self.request.retries, 60)  # Max 60 seconds
        raise self.retry(exc=exc, countdown=countdown)
