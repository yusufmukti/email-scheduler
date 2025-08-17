"""
Database models and job persistence for the Email Scheduler app.
"""

import os
import logging
from typing import Optional
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)

Base = declarative_base()

class ScheduledJob(Base):
    """SQLAlchemy model for a scheduled email job."""
    __tablename__ = 'scheduled_jobs'
    id = Column(String, primary_key=True)
    user_email = Column(String, nullable=False)
    to_address = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    schedule_option = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)  # Google OAuth refresh token
    attachments = Column(Text, nullable=True)  # Comma-separated file paths

DB_PATH = os.environ.get('DB_PATH', 'sqlite:///jobs.db')
engine = create_engine(DB_PATH)
Session = sessionmaker(bind=engine)

# Create tables if not exist
def init_db() -> None:
    """Create all database tables if they do not exist."""
    Base.metadata.create_all(engine)
