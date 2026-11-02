"""
Candidate Profile Configuration
Extracted from Poorna Chandra Rao J's Resume.
Used for JD matching, score calculation, and answering screening questions.
"""
from typing import Dict, List, Any
from pydantic import BaseModel, Field

class CandidateProfile(BaseModel):
    # Personal & Contact Information
    full_name: str = "Poorna Chandra Rao J"
    email: str = "poorna.ai.2026@gmail.com"
    phone: str = "+91-8143675811"
    city: str = "Hyderabad"
    state: str = "Telangana"
    country: str = "India"
    postal_code: str = "500081"
    portfolio_url: str = "https://qe-2-ai.vercel.app"
    github_url: str = "https://github.com/poornaai2026/QE2AI"
    linkedin_url: str = "" # Can be loaded from .env
    
    # Career Overview
    current_title: str = "Senior Quality & Gen AI Quality Engineer | Agentic AI & Test Automation"
    total_experience_years: float = 12.0
    genai_experience_years: float = 2.5
    automation_experience_years: float = 10.0
    current_company: str = "Publicis Sapient"
    current_client: str = "UHG / Optum"
    notice_period_days: int = 30
    
    # Education
    highest_degree: str = "Bachelor of Technology (B.Tech)"
    field_of_study: str = "Electronics & Instrumentation"
    university: str = "Acharya Nagarjuna University (Bapatla Engineering College)"
    
    # Target Roles
    target_job_titles: List[str] = [
        "GenAI Engineer",
        "Agentic AI Engineer",
        "AI Quality Engineer",
        "GenAI QE Engineer",
        "Lead Quality Engineer",
        "Senior Automation Architect",
        "Staff SDET",
        "Lead SDET",
        "Python AI Engineer",
        "Autonomous Agent Developer"
    ]
    
    # Target Locations
    preferred_locations: List[str] = [
        "Hyderabad",
        "Bengaluru",
        "Bangalore",
        "Remote",
        "Hybrid"
    ]
    
    # Core Skills Grouped by Category
    skills_taxonomy: Dict[str, List[str]] = {
        "GenAI & Agentic AI": [
            "LangGraph", "LangChain", "MCP (Model Context Protocol)", "FastMCP",
            "AI Agents", "Agentic AI", "RAG Systems", "LLM Applications",
            "Prompt Engineering", "LLM Evaluation", "Ragas", "Guardrails",
            "Vector Search", "ChromaDB", "FAISS", "Pinecone", "asyncio"
        ],
        "Backend & Engineering": [
            "Python 3.11", "FastAPI", "Pydantic V2", "RAG Pipelines", "LLM Integration",
            "Test Case Generation", "AI Quality Gates", "AI Validation", "Embeddings",
            "Retrieval Pipelines", "Redis Semantic Cache", "LangSmith"
        ],
        "Test Automation & Quality Engineering": [
            "Playwright", "Selenium WebDriver", "Appium", "Karate", "REST Assured",
            "TestNG", "Cucumber (BDD)", "pytest", "pytest-bdd", "Postman",
            "Newman", "Self-Healing Locators", "UI Automation", "API Automation"
        ],
        "DevOps & Cloud": [
            "Docker", "Kubernetes (K8s)", "GCP", "GitHub Actions", "Jenkins",
            "Bitbucket Pipelines", "CI/CD Optimization", "Linux", "Bash"
        ],
        "Databases & Tools": [
            "MySQL", "MongoDB", "PostgreSQL", "JIRA", "Confluence",
            "Salesforce Commerce Cloud (SFCC)", "BrowserStack"
        ]
    }
    
    # Default Answers for Typical Application Questionnaires
    screening_answers: Dict[str, str] = {
        "notice_period": "30 days (negotiable / serving notice)",
        "current_location": "Hyderabad, India",
        "preferred_location": "Hyderabad / Bengaluru / Remote",
        "relocation": "Yes, open to relocation or remote opportunities",
        "work_authorization": "Authorized to work in India (Citizen)",
        "years_experience_python": "8",
        "years_experience_automation": "12",
        "years_experience_playwright": "4",
        "years_experience_selenium": "10",
        "years_experience_genai": "2.5",
        "years_experience_langchain_langgraph": "2.5",
        "years_experience_fastapi": "3",
        "years_experience_devops_docker": "6",
        "salary_currency": "INR"
    }

# Instantiated candidate singleton
CANDIDATE = CandidateProfile()
