"""
Scheduling logic for the Email Scheduler app.
"""
import threading
import time
from datetime import datetime
from email_utils import send_email_gmail_api

def schedule_email_job(job, get_token_func):
    """Start a background thread to send emails on the chosen schedule, starting from the selected date."""
    now = datetime.now()
    start_date = job.start_date
    delay = (start_date - now.date()).total_seconds()
    if delay < 0:
        delay = 0
    def job_func():
        token = get_token_func(job)
        if not token:
            return
        ok, err = send_email_gmail_api(token, job.to_address, job.subject, job.message)
        if not ok:
            print(f"Failed to send email: {err}")
    def schedule_with_delay():
        time.sleep(delay)
        interval_map = {
            'hourly': 3600,
            'daily': 86400,
            'weekly': 604800,
            'monthly': 2628000,
            'three_monthly': 7884000,
            'yearly': 31536000
        }
        interval = interval_map.get(job.schedule_option)
        if interval:
            while True:
                job_func()
                time.sleep(interval)
    t = threading.Thread(target=schedule_with_delay, daemon=True)
    t.start()
