"""
AI Resume Parser & Profile Generator.
Extracts text from any candidate's resume (PDF) and uses LLM to generate
a structured CandidateProfile JSON. Turns the agent into a universal multi-tenant platform.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pypdf import PdfReader

from config.settings import settings
from config.candidate_profile import CandidateProfile, CANDIDATE
from core.llm_matcher import matcher

logger = logging.getLogger("ResumeParser")
PROFILE_FILE = Path(__file__).resolve().parent.parent / "user_profile.json"

class AIResumeParser:
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extracts plain text from all pages of a PDF resume."""
        text = ""
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
        return text.strip()

    @classmethod
    def parse_and_save_profile(cls, pdf_path: str) -> CandidateProfile:
        """
        Extracts text from PDF and prompts LLM to generate structured CandidateProfile.
        Saves profile to user_profile.json and updates runtime candidate singleton.
        """
        raw_text = cls.extract_text_from_pdf(pdf_path)
        if not raw_text or len(raw_text) < 100:
            logger.warning("PDF text too short or empty. Retaining existing profile.")
            return cls.get_active_profile()

        prompt = f"""
You are an AI Executive Recruiter & Career Data Architect.
Extract the structured candidate profile from the resume text below:

RESUME TEXT:
{raw_text[:6000]}

TASK:
Convert this resume into a clean JSON adhering strictly to this schema:
{{
  "full_name": "Full Name",
  "email": "candidate.email@domain.com",
  "phone": "+91-XXXXXXXXXX",
  "city": "Current City",
  "state": "State",
  "country": "Country",
  "postal_code": "Postal Code",
  "portfolio_url": "https://portfolio-or-personal-site",
  "github_url": "https://github.com/username",
  "linkedin_url": "https://linkedin.com/in/username",
  "current_title": "Current Designation / Headline",
  "total_experience_years": 10.5,
  "current_company": "Current Employer",
  "current_client": "Current Client if any",
  "notice_period_days": 30,
  "highest_degree": "Degree name",
  "field_of_study": "Branch",
  "university": "College / University name",
  "target_job_titles": ["Title 1", "Title 2", "Title 3", "Title 4"],
  "preferred_locations": ["City 1", "City 2", "Remote"],
  "skills_taxonomy": {{
    "Primary Skills": ["Skill 1", "Skill 2"],
    "Tools & Frameworks": ["Tool 1", "Tool 2"],
    "Cloud & DevOps": ["Tool 1", "Tool 2"]
  }},
  "screening_answers": {{
    "notice_period": "30 days",
    "current_location": "City, Country",
    "preferred_location": "City / Remote",
    "relocation": "Yes",
    "work_authorization": "Authorized to work in India / Citizen",
    "years_experience_python": "8",
    "salary_currency": "INR"
  }}
}}

Output strictly valid JSON only. Do not add markdown backticks.
"""
        parsed_data = None
        if matcher.openrouter_client:
            try:
                res = matcher.openrouter_client.chat.completions.create(
                    model=settings.OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a precise data extractor. Return JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                import re
                clean = re.sub(r'^```json\s*', '', res.choices[0].message.content.strip())
                clean = re.sub(r'\s*```$', '', clean)
                parsed_data = json.loads(clean)
            except Exception as e:
                logger.error(f"OpenRouter parsing failed: {e}")

        if not parsed_data:
            logger.info("Using baseline candidate profile.")
            return cls.get_active_profile()

        # Save to user_profile.json
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=2)
            logger.info(f"Saved candidate profile to {PROFILE_FILE}")
            profile = CandidateProfile(**parsed_data)
            return profile
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return cls.get_active_profile()

    @classmethod
    def get_active_profile(cls) -> CandidateProfile:
        """Loads profile from user_profile.json if exists; otherwise defaults to CANDIDATE singleton."""
        if PROFILE_FILE.exists():
            try:
                with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return CandidateProfile(**data)
            except Exception as e:
                logger.debug(f"Could not load custom user_profile.json: {e}")
        return CANDIDATE

resume_parser = AIResumeParser()

