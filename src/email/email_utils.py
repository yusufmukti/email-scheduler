"""
Email sending and validation utilities for the Email Scheduler app.
"""

import os
import base64
import hashlib
import re
import logging
from typing import Optional, Any, List
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)

load_dotenv()

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

def render_template_vars(text: str, now: Optional[Any] = None) -> str:
    """Replace {{time sent in ...}} and similar placeholders in text with formatted time."""
    import re
    from datetime import datetime
    if now is None:
        now = datetime.now()
    def repl(match):
        fmt = match.group(1).strip()
        # Replace custom codes with strftime codes
        fmt = (fmt.replace('DATETIME', '%A, %d %B %Y %H:%M')
               .replace('DDDD', '%A')
               .replace('YYYY', '%Y')
               .replace('YY', '%y')
               .replace('MMMM', '%B')
               .replace('MM', '%m')
               .replace('DD', '%d')
               .replace('HH', '%H')
               .replace('mm', '%M'))
        try:
            return now.strftime(fmt)
        except Exception:
            return match.group(0)
    return re.sub(r'\{\{([^}]+)\}\}', repl, text)

def hash_value(value: str) -> str:
    """Hash a string value using SHA-256 for privacy."""
    return hashlib.sha256(value.encode()).hexdigest()

def validate_email(email: str) -> bool:
    """Check if the email address or addresses (one per line) are valid."""
    emails = [e.strip() for e in email.replace(',', '\n').splitlines() if e.strip()]
    return all(EMAIL_REGEX.match(e) for e in emails)

def build_gmail_credentials(token: str, refresh_token: Optional[str] = None) -> Credentials:
    """Build a google.oauth2.credentials.Credentials object from the OAuth token and optional refresh token."""
    return Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    )

def send_email_gmail_api(token, to_address, subject, message, attachments=None, refresh_token=None):
    """Send an email using the Gmail API and the user's OAuth token. Supports multiple recipients. Automatically refreshes token if needed."""
    from google.auth.exceptions import RefreshError
    try:
        creds = build_gmail_credentials(token, refresh_token)
        service = build("gmail", "v1", credentials=creds)
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        import os
        mime_msg = MIMEMultipart()
        mime_msg.attach(MIMEText(message))
        # Support multiple recipients (one per line or comma)
        recipients = [e.strip() for e in to_address.replace(',', '\n').splitlines() if e.strip()]
        mime_msg["to"] = ', '.join(recipients)
        mime_msg["subject"] = subject
        # Attach files if present
        if attachments:
            for path in attachments:
                if not path:
                    continue
                try:
                    with open(path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(path)}")
                    mime_msg.attach(part)
                except Exception:
                    continue
        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
        send_result = service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()
        return True, None
    except RefreshError as refresh_err:
        return False, "Token expired and could not be refreshed. Please re-authenticate."
    except HttpError as error:
        return False, str(error)

def validate_schedule_option(option):
    """Return True if the schedule option is valid."""
    allowed_options = {"hourly", "daily", "weekly", "monthly", "three_monthly", "yearly"}
    return option in allowed_options
