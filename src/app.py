"""
Email Scheduler Web App (Modular Version)
-----------------------------------------
A modular Flask app for scheduling recurring emails with Google sign-in, using a database for job storage and clear separation of concerns.
"""


import os
import logging
from dotenv import load_dotenv
load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configure logging to write to both the console and a file
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logging.getLogger().addHandler(file_handler)

# Configure logging to write to the console
# logging.basicConfig(level=logging.INFO)

from flask import Flask, render_template, request, redirect, url_for, flash
from typing import List, Optional, Dict, Any
from flask_dance.contrib.google import google
from src.models.models import ScheduledJob, Session, init_db
from src.email.email_utils import hash_value, validate_email, validate_schedule_option
from src.scheduler.scheduler import schedule_email_job
from src.auth.auth import blueprint as google_blueprint
import uuid
from datetime import datetime


# Set correct template and static folder paths
app = Flask(
	__name__,
	template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
	static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'supersekrit')
app.register_blueprint(google_blueprint, url_prefix="/login")

init_db()

# Serve attachments for download

from flask import send_from_directory


# Use absolute path for attachments directory
@app.route('/attachments/<path:filename>')
def serve_attachment(filename: str):
	"""Serve an attachment file for download or inline viewing."""
	from flask import request
	as_attachment = request.args.get('download', '0') == '1'
	attachments_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'attachments')
	return send_from_directory(attachments_dir, filename, as_attachment=as_attachment)

# Helper to get jobs for the current user
def get_user_jobs(user_email: str) -> List[Any]:
	"""Retrieve all scheduled jobs for the given user email."""
	session = Session()
	jobs = session.query(ScheduledJob).filter_by(user_email=user_email).all()
	session.close()
	return jobs

# Edit scheduled email route
@app.route("/edit/<job_id>", methods=["GET", "POST"])
def edit(job_id: str):
	"""Edit a scheduled email job by job ID."""
	if not google.authorized:
		return redirect(url_for("google.login"))
	session = Session()
	job = session.query(ScheduledJob).filter_by(id=job_id).first()
	if not job:
		session.close()
		flash("Job not found.")
		return redirect(url_for("index"))
	if request.method == "POST":
		import json
		to_address_raw = request.form["to_address"].replace('\r\n', '\n').replace('\r', '\n')
		try:
			# Try to parse as JSON array from Tagify
			tagify_data = json.loads(to_address_raw)
			if isinstance(tagify_data, list) and all('value' in item for item in tagify_data):
				to_address = ','.join(item['value'] for item in tagify_data)
			else:
				to_address = to_address_raw
		except json.JSONDecodeError:
			to_address = to_address_raw
		# If another error occurs, let it propagate (fail fast)
		subject = request.form["subject"]
		message = request.form["message"]
		schedule_option = request.form["schedule_option"]
		start_date = request.form["start_date"]
		start_time = request.form["start_time"]
		# Input validation
		if not validate_schedule_option(schedule_option):
			flash('Invalid schedule option.')
			session.close()
			return redirect(url_for('edit', job_id=job_id))
		if not validate_email(to_address):
			flash('Invalid email address.')
			session.close()
			return redirect(url_for('edit', job_id=job_id))
		# Handle attachments
		attachment_files = request.files.getlist('attachments')
		attachment_paths = job.attachments.split(',') if job.attachments else []
		# Remove attachments marked for deletion
		remove_attachments = request.form.get('remove_attachments', '')
		if remove_attachments:
			remove_set = set([att.strip() for att in remove_attachments.split(',') if att.strip()])
			attachment_paths = [att for att in attachment_paths if att not in remove_set]
		for file in attachment_files:
			if file and file.filename:
				save_path = os.path.join('attachments', f"{job.id}_{file.filename}")
				file.save(save_path)
				attachment_paths.append(save_path)
		job.to_address = to_address
		job.subject = subject
		job.message = message
		job.schedule_option = schedule_option
		job.start_date = datetime.strptime(start_date + " " + start_time, "%Y-%m-%d %H:%M")
		job.attachments = ','.join(attachment_paths) if attachment_paths else None
		session.commit()
		session.close()
		flash('Scheduled email updated.')
		return redirect(url_for('index'))
	session.close()
	return render_template("edit.html", job=job)

@app.route("/send_now/<job_id>", methods=["POST"])
def send_now(job_id: str):
	"""Send the scheduled email immediately for the given job ID."""
	if not google.authorized:
		return redirect(url_for("google.login"))
	session = Session()
	job = session.query(ScheduledJob).filter_by(id=job_id).first()
	if not job:
		session.close()
		flash("Job not found.")
		return redirect(url_for("index"))
	# Use the current session's Google token for sending
	token_data = getattr(google, 'token', None)
	if not token_data or 'access_token' not in token_data:
		session.close()
		flash("Session error: No valid Google token in session. Please log in again.")
		return redirect(url_for("google.login"))
	token = token_data['access_token']
	refresh_token = token_data.get('refresh_token')
	from src.email.email_utils import send_email_gmail_api
	from datetime import datetime
	from src.email.email_utils import render_template_vars
	now = datetime.now()
	subject = render_template_vars(job.subject, now)
	message = render_template_vars(job.message, now)
	# Robustly parse and validate the to_address field (handle Tagify JSON and plain text, and all separators)
	import json, re
	to_address = None
	to_address_raw = job.to_address
	try:
		tagify_data = json.loads(to_address_raw)
		if isinstance(tagify_data, list) and all('value' in item for item in tagify_data):
			# Tagify JSON array
			address_list = [item['value'] for item in tagify_data]
		else:
			address_list = [to_address_raw]
	except json.JSONDecodeError:
		address_list = [to_address_raw] if to_address_raw else []
	# If another error occurs, let it propagate (fail fast)
	# Split all addresses on comma, semicolon, space, or newline
	split_addresses = []
	for addr in address_list:
		split_addresses.extend([a for a in re.split(r'[\s,;]+', addr) if a])
	# Remove duplicates and empty
	split_addresses = [a for a in dict.fromkeys(split_addresses) if a]
	to_address = ','.join(split_addresses)
	# Validate email(s)
	from src.email.email_utils import validate_email
	if not to_address or not validate_email(to_address):
		session.close()
		flash("Invalid or missing recipient email address.")
		return redirect(url_for("index"))
	# Pass attachment paths to send_email_gmail_api
	attachments = job.attachments.split(',') if job.attachments else []
	ok, err = send_email_gmail_api(token, to_address, subject, message, attachments=attachments, refresh_token=refresh_token)
	session.close()
	if ok:
		flash("Email sent immediately.")
		return redirect(url_for("index"))
	# If token expired and cannot be refreshed, log out user and redirect to login
	if err and "Token expired" in err:
		from flask import session as flask_session, make_response
		flask_session.clear()
		try:
			if hasattr(google, 'blueprint') and hasattr(google.blueprint, 'token'):
				google.blueprint.token = None
			if hasattr(google, 'token'):
				google.token = None
			if 'google_oauth_token' in flask_session:
				del flask_session['google_oauth_token']
		except Exception as e:
			print("Logout token clear error:", e)
		cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
		resp = make_response(redirect(url_for("google.login")))
		resp.set_cookie(key=cookie_name, value='', expires=0, path='/', httponly=True)
		flash("Session expired. Please log in again.")
		return resp
	flash(f"Failed to send email: {err}")
	return redirect(url_for("index"))

@app.route("/", methods=["GET"])
def index():
	"""Show the main page with the form and the user's scheduled jobs."""
	import sys
	from flask import session, request
	logging.debug("google.authorized: %s", google.authorized)
	logging.debug("google.token: %s", getattr(google, 'token', None))
	logging.debug("session keys: %s", list(session.keys()))
	logging.debug("session values: %s", {k: session[k] for k in session.keys()})
	logging.debug("session cookie: %s", request.cookies.get(app.config.get('SESSION_COOKIE_NAME', 'session')))
	"""Show the main page with the form and the user's scheduled jobs."""
	import sys
	from flask import session, request
	logging.debug("google.authorized: %s", google.authorized)
	logging.debug("google.token: %s", getattr(google, 'token', None))
	logging.debug("session keys: %s", list(session.keys()))
	logging.debug("session cookie: %s", request.cookies.get(app.config.get('SESSION_COOKIE_NAME', 'session')))
	if not google.authorized or not getattr(google, 'token', None):
		logging.warning("Not authorized or missing token after login. google.authorized: %s google.token: %s", google.authorized, getattr(google, 'token', None))
		# If user just logged in but no token, show error but do not clear session
		from flask import flash
		flash("Login failed: No valid token received from Google. Please try again or contact support.")
		return redirect(url_for("google.login"))
	resp = google.get("/oauth2/v2/userinfo")
	logging.debug("google.get userinfo status: %s", resp.status_code)
	logging.debug("google.get userinfo text: %s", resp.text)
	if not resp.ok:
		logging.warning("google.get userinfo failed: %s", resp.text)
		session.clear()
		from flask import flash, redirect, url_for
		flash("Session expired or permission revoked. Please log in again.")
		return redirect(url_for("google.login"))
	email = resp.json()["email"]
	jobs = get_user_jobs(email)
	import json
	# Calculate next run for each job
	def calc_next_run(job: Any) -> Any:
		"""Calculate the next scheduled run datetime for a job."""
		from datetime import datetime, timedelta, date
		now = datetime.now()
		start = job.start_date
		if isinstance(start, str):
			try:
				start = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
			except Exception:
				start = datetime.strptime(start, "%Y-%m-%d")
		# If first run is in the future
		if start > now:
			return start
		# Otherwise, calculate next occurrence
		option = job.schedule_option
		dt = start
		while dt <= now:
			if option == "hourly":
				dt += timedelta(hours=1)
			elif option == "daily":
				dt += timedelta(days=1)
			elif option == "weekly":
				dt += timedelta(weeks=1)
			elif option == "monthly":
				dt += timedelta(days=30)
			elif option == "three_monthly":
				dt += timedelta(days=90)
			elif option == "yearly":
				dt += timedelta(days=365)
			else:
				break
		return dt
	jobs_with_next = []
	for job in jobs:
		# Fix Tagify JSON for old jobs
		to_addr = job.to_address
		if to_addr and to_addr.strip().startswith('['):
			try:
				tagify_data = json.loads(to_addr)
				if isinstance(tagify_data, list) and all('value' in item for item in tagify_data):
					to_addr = ','.join(item['value'] for item in tagify_data)
			except json.JSONDecodeError:
				pass  # If not valid JSON, leave as is
			# If another error occurs, let it propagate (fail fast)
		job.to_address = to_addr
		next_run = calc_next_run(job)
		jobs_with_next.append({"job": job, "next_run": next_run})
	return render_template("index.html", email=email, jobs=jobs_with_next)

@app.route("/send", methods=["POST"])
def send():
	"""Handle form submission: schedule a new email job for the user."""
	if not google.authorized:
		return redirect(url_for("google.login"))
	import json
	to_address_raw = request.form["to_address"].replace('\r\n', '\n').replace('\r', '\n')
	try:
		tagify_data = json.loads(to_address_raw)
		if isinstance(tagify_data, list) and all('value' in item for item in tagify_data):
			to_address = ','.join(item['value'] for item in tagify_data)
		else:
			to_address = to_address_raw
	except Exception:
		to_address = to_address_raw
	subject = request.form["subject"]
	message = request.form["message"]
	schedule_option = request.form["schedule_option"]
	start_date = request.form["start_date"]
	start_time = request.form["start_time"]
	hash_addr = request.form.get('hash_addr')
	# Input validation
	if not validate_schedule_option(schedule_option):
		flash('Invalid schedule option.')
		return redirect(url_for('index'))
	if not hash_addr and not validate_email(to_address):
		flash('Invalid email address.')
		return redirect(url_for('index'))
	if hash_addr:
		to_address = hash_value(to_address)
	resp = google.get("/oauth2/v2/userinfo")
	email = resp.json()["email"]
	token = google.token["access_token"]
	refresh_token = google.token.get("refresh_token")
	job_id = str(uuid.uuid4())
	# Handle attachments
	attachment_files = request.files.getlist('attachments')
	attachment_paths = []
	for file in attachment_files:
		if file and file.filename:
			save_path = os.path.join('attachments', f"{job_id}_{file.filename}")
			file.save(save_path)
			attachment_paths.append(save_path)
	# Store job in database
	session = Session()
	# Combine start_date and start_time into a datetime
	start_dt = datetime.strptime(start_date + " " + start_time, "%Y-%m-%d %H:%M")
	job = ScheduledJob(
		id=job_id,
		user_email=email,
		to_address=to_address,
		subject=subject,
		message=message,
		schedule_option=schedule_option,
		start_date=start_dt,
		token=token,
		refresh_token=refresh_token,
		attachments=','.join(attachment_paths) if attachment_paths else None
	)
	session.add(job)
	session.commit()
	session.close()
	flash('Email scheduled!')
	return redirect(url_for('index'))

@app.route("/cancel/<job_id>", methods=["POST"])
def cancel(job_id: str):
	"""Cancel a scheduled job for the current user by unique job ID."""
	if not google.authorized:
		return redirect(url_for("google.login"))
	resp = google.get("/oauth2/v2/userinfo")
	email = resp.json()["email"]
	session = Session()
	job = session.query(ScheduledJob).filter_by(id=job_id, user_email=email).first()
	if job:
		session.delete(job)
		session.commit()
		flash('Scheduled email canceled.')
	session.close()
	return redirect(url_for('index'))

# Place the logout route after all other routes and app setup
@app.route("/logout", methods=["POST"])
def logout():
	"""Aggressive logout: clear session, all Flask-Dance tokens, and session cookie, then redirect to login."""
	from flask import session, make_response, redirect, url_for, flash, request
	# Clear Flask session
	session.clear()
	# Remove Flask-Dance OAuth token from all possible locations
	try:
		if hasattr(google, 'blueprint') and hasattr(google.blueprint, 'token'):
			google.blueprint.token = None
		if hasattr(google, 'token'):
			google.token = None
		if 'google_oauth_token' in session:
			del session['google_oauth_token']
	except Exception as e:
		logging.error("Logout token clear error: %s", e)
	# Remove session cookie
	cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
	resp = make_response(redirect(url_for("google.login")))
	resp.set_cookie(key=cookie_name, value='', expires=0, path='/', httponly=True)
	flash('You have been logged out.')
	return resp

def start_all_jobs():
	"""Load all jobs from database and start their schedulers when the app starts."""
	session = Session()
	jobs = session.query(ScheduledJob).all()
	for job in jobs:
		schedule_email_job(job, lambda j: j.token)
	session.close()

if __name__ == "__main__":
	logging.info("FLASK_SECRET_KEY: %s", app.secret_key)
	logging.info("SESSION_COOKIE_NAME: %s", app.config.get('SESSION_COOKIE_NAME', 'session'))
	logging.info("SESSION_COOKIE_SECURE: %s", app.config.get('SESSION_COOKIE_SECURE', False))
	start_all_jobs()	
	app.run(debug=True)
