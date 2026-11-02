"""
Smart Notification Classifier.
Inspects email headers (sender, subject, snippet) directly from the Gmail inbox list
BEFORE clicking or opening the email, ensuring only genuine job alerts for Poorna are opened.
"""
import re
import logging
from typing import Tuple, Dict, Any

from config.candidate_profile import CANDIDATE

logger = logging.getLogger("NotificationClassifier")

class NotificationClassifier:
    # 1. Non-job patterns to immediately reject without opening
    REJECT_PATTERNS = [
        r"security alert",
        r"google account",
        r"verify your",
        r"verification code",
        r"new device",
        r"password reset",
        r"interview has been scheduled",
        r"interview-candidate",
        r"waiting for the interviewer",
        r"invitation to interview",
        r"invitation to connect",
        r"accepted your invitation",
        r"viewed your profile",
        r"who's viewed your profile",
        r"who viewed your profile",
        r"trying to reach you",
        r"application viewed",
        r"receipt",
        r"invoice",
        r"statement",
        r"billing update"
    ]

    # 2. Positive job notification signals
    JOB_SIGNALS = [
        r"\bjob\b",
        r"\bhiring\b",
        r"\bopening\b",
        r"\brequirement\b",
        r"\bopportunity\b",
        r"\bvacanc",
        r"\brecommended job",
        r"\bjobs matching\b",
        r"\bnew job alert\b",
        r"\bcareer opportunity\b",
        r"\bengineer\b",
        r"\barchitect\b",
        r"\blead\b",
        r"\bimmediate joiners\b"
    ]

    # 3. Candidate's relevant technical domains
    RELEVANT_DOMAINS = [
        "qa", "test", "automation", "sdet", "genai", "ai", "agentic",
        "quality", "playwright", "selenium", "python", "architect",
        "lead", "engineer", "framework", "llm", "rag", "eval",
        "network", "tools", "backend", "developer", "cloud"
    ]

    @classmethod
    def classify_notification(cls, sender: str, subject: str, snippet: str = "") -> Tuple[bool, str]:
        """
        Classifies an email from the inbox preview without opening it.
        Returns: (is_valid_job_alert: bool, reason: str)
        """
        combined_text = f"{sender} {subject} {snippet}".lower()
        subject_lower = subject.lower()

        # Step 1: Reject security, social, and non-job noise
        for pattern in cls.REJECT_PATTERNS:
            if re.search(pattern, combined_text):
                if "interview" in pattern:
                    return False, "Interview Schedule / Interviewer Alert (Preserved for candidate)"
                elif "security" in pattern or "verify" in pattern or "google account" in pattern:
                    return False, "Account Security / Verification Notice"
                else:
                    return False, f"Social/Marketing update ({pattern})"

        # Step 2: Check for Job Alert signals
        has_job_signal = False
        for signal in cls.JOB_SIGNALS:
            if re.search(signal, combined_text):
                has_job_signal = True
                break

        if not has_job_signal and not any(kw in subject_lower for kw in ["job", "lead", "engineer", "architect", "sdet", "qa", "developer"]):
            return False, "No job alert keywords detected"

        # Step 3: Check domain relevance against Poorna's skillset
        domain_matches = [kw for kw in cls.RELEVANT_DOMAINS if re.search(r'\b' + re.escape(kw) + r'\b', combined_text)]
        if not domain_matches:
            # Check if sender is a recognized job alert sender
            if any(snd in sender.lower() for snd in ["naukri", "linkedin", "foundit", "indeed"]):
                return True, "Job notification from job board (general match)"
            return False, "Job alert not aligned with Poorna's technical domains"

        return True, f"Relevant job alert (Matched domains: {', '.join(domain_matches[:4])})"

classifier = NotificationClassifier()

