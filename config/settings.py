"""
Configuration Settings for the Job Seeker Agent
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # LLM Settings (OpenRouter & Gemini)
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API Key")
    OPENROUTER_MODEL: str = Field(default="google/gemini-2.5-flash", description="OpenRouter model name")
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter API Base URL")
    OPENROUTER_MAX_TOKENS: int = Field(default=1500, description="Max tokens per evaluation request")

    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key (optional alternative)")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    
    # Gmail Harvester Settings
    HARVESTER_MODE: str = Field(default="BROWSER", description="'BROWSER' to read via Chrome, or 'IMAP' via app password")
    GMAIL_USER: str = Field(default="poorna.ai.2026@gmail.com", description="Gmail address to monitor")
    GMAIL_MAX_AGE_DAYS: int = Field(default=3, description="Only search for job alerts from the past N days (e.g. 3 days)")
    GMAIL_APP_PASSWORD: str = Field(default="", description="16-character Google App Password for IMAP")
    GMAIL_SEARCH_QUERY: str = Field(
        default='(from:naukri OR from:linkedin OR from:recruiter) (subject:"job" OR subject:"opening" OR subject:"alert" OR subject:"opportunity")',
        description="IMAP search criteria"
    )
    
    # Autonomous Application Modes
    AUTO_SUBMIT: bool = Field(default=False, description="If False, stops at review screen. If True, clicks final submit.")
    MATCH_SCORE_THRESHOLD: int = Field(default=75, description="Minimum match percentage (0-100) to apply")
    DAILY_APPLICATION_LIMIT: int = Field(default=25, description="Max applications per day to protect account reputation")
    
    # Browser & Stealth Configuration
    BROWSER_HEADLESS: bool = Field(default=False, description="Run browser in non-headless mode to allow human inspection")
    BROWSER_USER_DATA_DIR: str = Field(default=str(BASE_DIR / "chrome_debug_profile"), description="Persistent browser session directory")
    CHROME_CDP_URL: str = Field(default="", description="Optional Chrome DevTools port (e.g. http://127.0.0.1:9222) to attach to existing Chrome")
    
    # Candidate Resume & Assets
    RESUME_PATH: str = Field(default=str(BASE_DIR / "resumes" / "Poorna_Chandra_Rao_Resume.pdf"), description="Path to candidate resume PDF for ATS uploads")
    
    # Database
    DATABASE_URL: str = Field(default=f"sqlite:///{BASE_DIR / 'job_seeker.db'}", description="SQLite connection string")
    
    # Web Review Dashboard & Commercial
    DASHBOARD_PORT: int = Field(default=8000, description="Local dashboard web port")
    CHECKOUT_URL: str = Field(default="", description="Product checkout page URL")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
