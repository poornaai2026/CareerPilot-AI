"""
Database models and session management for Job Application tracking.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import enum

from config.settings import settings

Base = declarative_base()

class ApplicationStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    EVALUATING = "EVALUATING"
    QUALIFIED = "QUALIFIED"
    SKIPPED_LOW_SCORE = "SKIPPED_LOW_SCORE"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    ALREADY_APPLIED = "ALREADY_APPLIED"

class JobApplicationRecord(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False) # e.g. "GMAIL_NAUKRI", "GMAIL_LINKEDIN", "LINKEDIN_FEED", "DIRECT"
    job_id_external = Column(String(100), unique=True, index=True, nullable=True) # Unique ID or hash
    job_title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    job_url = Column(Text, nullable=False)
    job_description = Column(Text, nullable=True)
    
    # Match Assessment
    match_score = Column(Float, default=0.0)
    match_fit_category = Column(String(50), nullable=True) # STRONG, GOOD, PARTIAL, UNFIT
    match_rationale = Column(Text, nullable=True)
    matched_skills = Column(Text, nullable=True) # JSON or comma-separated
    missing_skills = Column(Text, nullable=True) # JSON or comma-separated
    tailored_pitch = Column(Text, nullable=True)
    
    # Application execution details
    application_portal = Column(String(50), nullable=True) # LINKEDIN_EASY_APPLY, NAUKRI_ONE_CLICK, EXTERNAL_ATS, etc.
    status = Column(String(50), default=ApplicationStatus.DISCOVERED.value)
    auto_submitted = Column(Boolean, default=False)
    screenshot_path = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    
    discovered_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        return db
    finally:
        pass
