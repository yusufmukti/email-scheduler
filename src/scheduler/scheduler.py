"""
Scheduling logic for the Email Scheduler app.
"""

import threading
import time
import logging
from typing import Any, Callable
from datetime import datetime
from src.email.email_utils import send_email_gmail_api

# Configure logging
logging.basicConfig(level=logging.INFO)

def schedule_email_job(job: Any, get_token_func: Callable[[Any], str]) -> None:
    """Start a background thread to send emails on the chosen schedule, starting from the selected date."""
    now = datetime.now()
    start_date = job.start_date
    # Ensure both are datetime for subtraction
    if isinstance(start_date, datetime):
        delay = (start_date - now).total_seconds()
    else:
        # fallback for legacy data
        delay = (datetime.combine(start_date, datetime.min.time()) - now).total_seconds()
    interval_map = {
        'hourly': 3600,
        'daily': 86400,
        'weekly': 604800,
        'monthly': 2628000,
        'three_monthly': 7884000,
        'yearly': 31536000
    }
    interval = interval_map.get(job.schedule_option)
    # If one-time and scheduled in the past, do not schedule
    if not interval and delay < 0:
        return
    # For recurring jobs, if scheduled in the past, calculate next occurrence in the future
    if interval and delay < 0:
        missed = int(abs(delay) // interval) + 1
        delay = delay + missed * interval
        if delay < 0:
            return
    def job_func():
        token = get_token_func(job)
        if not token:
            return
        ok, err = send_email_gmail_api(token, job.to_address, job.subject, job.message)
        if not ok:
            logging.error(f"Failed to send email: {err}")
    def schedule_with_delay():
        time.sleep(delay)
        if interval:
            while True:
                job_func()
                time.sleep(interval)
        else:
            job_func()
    t = threading.Thread(target=schedule_with_delay, daemon=True)
    t.start()
