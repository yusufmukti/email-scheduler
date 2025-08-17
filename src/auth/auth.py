"""
Authentication and Google OAuth logic for the Email Scheduler app.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from flask_dance.contrib.google import make_google_blueprint, google
from flask import session

# Configure logging
logging.basicConfig(level=logging.INFO)


load_dotenv()

"""
This module provides the Google OAuth blueprint for authentication in the Email Scheduler app.
"""

blueprint = make_google_blueprint(
    client_id=os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"
    ],
    redirect_to="index",
    offline=True,
    reprompt_consent=True
)

