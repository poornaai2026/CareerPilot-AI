"""
LLM Job Description Matcher and Screening Response Generator.
Supports:
1. OpenRouter (Claude 3.5, Gemini 2.0 Flash, GPT-4o, DeepSeek)
2. Google Gemini SDK (Direct)
3. Heuristic / Rule-based fallbacks
"""
import json
import logging
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from config.settings import settings
from config.candidate_profile import CANDIDATE, CandidateProfile

logger = logging.getLogger("LLMMatcher")

class MatchEvaluation(BaseModel):
    match_score: int = Field(description="Score between 0 and 100 representing fit")
    fit_category: str = Field(description="STRONG_MATCH, MODERATE_MATCH, or WEAK_MATCH")
    reasoning: str = Field(description="Detailed explanation of the score and suitability")
    skills_matched: List[str] = Field(default_factory=list, description="Skills present in both JD and candidate profile")
    skills_missing: List[str] = Field(default_factory=list, description="Important skills required by JD that candidate lacks")
    tailored_pitch: str = Field(description="2-3 sentence tailored elevator pitch for this specific role")
    screening_answers: Dict[str, str] = Field(default_factory=dict, description="Answers to custom application questions")


class LLMMatcher:
    def __init__(self):
        self.openrouter_key = settings.OPENROUTER_API_KEY
        self.openrouter_model = settings.OPENROUTER_MODEL
        self.openrouter_client = None

        self.gemini_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.gemini_client = None

        # 1. Initialize OpenRouter
        if self.openrouter_key and "sk-or-" in self.openrouter_key:
            try:
                import openai
                self.openrouter_client = openai.OpenAI(
                    base_url=settings.OPENROUTER_BASE_URL,
                    api_key=self.openrouter_key
                )
                logger.info(f"Initialized OpenRouter LLM client (Model: {self.openrouter_model})")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenRouter client: {e}")

        # 2. Fallback to Direct Gemini SDK if available
        if not self.openrouter_client and self.gemini_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_key)
                logger.info("Initialized Gemini client for JD matching.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    def evaluate_job(self, job_title: str, company: str, jd_text: str) -> MatchEvaluation:
        """
        Evaluates a job description against Poorna's profile.
        Prioritizes OpenRouter -> Gemini SDK -> Rule-based fallback.
        """
        if self.openrouter_client:
            try:
                return self._evaluate_with_openrouter(job_title, company, jd_text)
            except Exception as e:
                logger.error(f"OpenRouter evaluation error: {e}. Trying secondary options.")

        if self.gemini_client:
            try:
                return self._evaluate_with_gemini(job_title, company, jd_text)
            except Exception as e:
                logger.error(f"Gemini evaluation error: {e}. Falling back to rule-based evaluation.")

        return self._evaluate_rule_based(job_title, company, jd_text)

    def _build_prompt(self, job_title: str, company: str, jd_text: str) -> str:
        return f"""
You are an expert Executive Tech Recruiter and AI Talent Scout evaluating a candidate for a role.

CANDIDATE PROFILE:
Name: {CANDIDATE.full_name}
Current Title: {CANDIDATE.current_title}
Total Experience: {CANDIDATE.total_experience_years} years (10+ Enterprise Automation Architecture, 2.5+ GenAI & Agentic AI)
Current Company/Client: {CANDIDATE.current_company} / {CANDIDATE.current_client}
Portfolio: {CANDIDATE.portfolio_url}
GitHub: {CANDIDATE.github_url}
Location: {CANDIDATE.city}, {CANDIDATE.country}
Target Roles: {', '.join(CANDIDATE.target_job_titles)}
Key Skills Taxonomy:
{json.dumps(CANDIDATE.skills_taxonomy, indent=2)}

JOB DETAILS:
Title: {job_title}
Company: {company}
Job Description:
{jd_text[:4000]}

EVALUATION RULES:
1. Determine how well Poorna fits this position on a scale of 0 to 100 (match_score).
2. If the position is for GenAI, Agentic AI, AI Quality Engineer, SDET Lead, Test Automation Architect, Python Backend/Agent engineer, score high (78-98) based on skill overlap.
3. If it is completely irrelevant (e.g. Sales, HR, Graphic Design, PHP/Ruby intern, pure manual testing), score low (0-40).
4. Provide fit_category: "STRONG_MATCH" (>=80), "MODERATE_MATCH" (65-79), or "WEAK_MATCH" (<65).
5. Identify matching skills (skills_matched) and missing requirements (skills_missing).
6. Write a tailored 2-3 sentence elevator pitch highlighting Poorna's open-source QE2AI platform, LangGraph agentic frameworks, and enterprise Playwright automation leadership.
7. Provide screening_answers for standard questions: years of experience with Python (8), Automation (12), Playwright (4), GenAI (2.5), Notice period (30 days).

Return valid JSON adhering to:
{{
  "match_score": 85,
  "fit_category": "STRONG_MATCH",
  "reasoning": "...",
  "skills_matched": ["..."],
  "skills_missing": ["..."],
  "tailored_pitch": "...",
  "screening_answers": {{ ... }}
}}
"""

    def _evaluate_with_openrouter(self, job_title: str, company: str, jd_text: str) -> MatchEvaluation:
        prompt = self._build_prompt(job_title, company, jd_text)
        
        response = self.openrouter_client.chat.completions.create(
            model=self.openrouter_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise technical hiring evaluator. You MUST respond with strictly valid JSON matching the requested schema. Do not add markdown backticks."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=settings.OPENROUTER_MAX_TOKENS,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        clean_json = re.sub(r'^```json\s*', '', content.strip())
        clean_json = re.sub(r'\s*```$', '', clean_json)
        data = json.loads(clean_json)
        return MatchEvaluation(**data)

    def _evaluate_with_gemini(self, job_title: str, company: str, jd_text: str) -> MatchEvaluation:
        from google.genai import types
        prompt = self._build_prompt(job_title, company, jd_text)
        
        response = self.gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MatchEvaluation,
                temperature=0.2,
            )
        )
        data = json.loads(response.text)
        return MatchEvaluation(**data)

    def _evaluate_rule_based(self, job_title: str, company: str, jd_text: str) -> MatchEvaluation:
        """Deterministic rule-based matcher if API calls fail or offline."""
        text_lower = f"{job_title} {jd_text}".lower()
        core_keywords = [
            ("langgraph", 15), ("langchain", 10), ("agentic ai", 15), ("ai agent", 15),
            ("mcp", 12), ("rag", 10), ("ragas", 12), ("llm", 10), ("fastapi", 10),
            ("playwright", 12), ("selenium", 8), ("python", 10), ("automation lead", 10),
            ("sdet", 10), ("quality engineer", 8), ("docker", 5), ("ci/cd", 5), ("rest assured", 5)
        ]
        negative_keywords = ["freshers only", "internship only", "php developer", "angular developer", "sales executive"]
        
        score = 40
        matched = []
        missing = []
        
        title_lower = job_title.lower()
        if any(role.lower() in title_lower for role in CANDIDATE.target_job_titles):
            score += 20
        elif any(k in title_lower for k in ["qa", "test", "automation", "ai", "genai", "sdet", "engineer"]):
            score += 10
            
        for kw, weight in core_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                score += weight
                matched.append(kw)
            else:
                if weight >= 10:
                    missing.append(kw)
                    
        for neg in negative_keywords:
            if neg in text_lower:
                score -= 30
                
        final_score = max(5, min(98, score))
        if final_score >= 80:
            category = "STRONG_MATCH"
        elif final_score >= 65:
            category = "MODERATE_MATCH"
        else:
            category = "WEAK_MATCH"
            
        rationale = f"Evaluated via Skill Matrix. Matched core domains: {', '.join(matched[:6]) if matched else 'general tech'}."
        pitch = (
            f"With 12+ years of enterprise automation architecture and 2.5+ years pioneering GenAI Quality Engineering "
            f"(creator of open-source QE2AI, LangGraph test agents, and Playwright MCP frameworks at Publicis/Optum), "
            f"Poorna brings immediate impact to {company or 'your team'}."
        )
        
        return MatchEvaluation(
            match_score=final_score,
            fit_category=category,
            reasoning=rationale,
            skills_matched=matched,
            skills_missing=missing[:5],
            tailored_pitch=pitch,
            screening_answers=CANDIDATE.screening_answers
        )

# Global matcher instance
matcher = LLMMatcher()
