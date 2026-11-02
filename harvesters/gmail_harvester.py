"""
Gmail Job Notification Harvester.
Reads incoming job notification emails from Naukri, LinkedIn, and recruiters via IMAP.
Extracts direct job URLs, company names, and preliminary descriptions.
"""
import email
from email.header import decode_header
import imaplib
import logging
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

from config.settings import settings
from core.db import get_db, JobApplicationRecord, ApplicationStatus

logger = logging.getLogger("GmailHarvester")

class ExtractedJobLead:
    def __init__(self, title: str, company: str, url: str, source: str, snippet: str = ""):
        self.title = title
        self.company = company
        self.url = url
        self.source = source
        self.snippet = snippet

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "source": self.source,
            "snippet": self.snippet
        }

class GmailHarvester:
    def __init__(self):
        self.user = settings.GMAIL_USER
        self.password = settings.GMAIL_APP_PASSWORD
        self.imap_server = "imap.gmail.com"

    def is_configured(self) -> bool:
        return bool(self.user and self.password and "your_" not in self.password.lower())

    def fetch_job_leads(self, max_emails: int = 25) -> List[ExtractedJobLead]:
        """
        Connects to Gmail via IMAP, searches for job notification emails,
        and extracts job URLs and metadata.
        """
        if not self.is_configured():
            logger.warning(
                "Gmail credentials not configured in .env. Returning sample demonstration leads."
            )
            return self._get_sample_leads()

        leads: List[ExtractedJobLead] = []
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.user, self.password)
            mail.select("inbox")

            # Search queries for Naukri and LinkedIn notifications
            search_queries = [
                '(FROM "naukri.com")',
                '(FROM "linkedin.com")',
                '(SUBJECT "job" OR SUBJECT "opening" OR SUBJECT "opportunity")'
            ]

            msg_ids = set()
            for query in search_queries:
                try:
                    status, data = mail.search(None, query)
                    if status == "OK" and data[0]:
                        ids = data[0].split()
                        # Get the latest message IDs
                        msg_ids.update(ids[-max_emails:])
                except Exception as e:
                    logger.debug(f"Search query '{query}' failed: {e}")

            logger.info(f"Found {len(msg_ids)} relevant notification emails in Gmail.")

            # Process most recent emails first
            sorted_ids = sorted(list(msg_ids), key=lambda x: int(x), reverse=True)[:max_emails]

            for msg_id in sorted_ids:
                try:
                    status, data = mail.fetch(msg_id, "(RFC822)")
                    if status != "OK":
                        continue
                    
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    subject = self._decode_str(msg.get("Subject", ""))
                    sender = self._decode_str(msg.get("From", ""))
                    body_html, body_text = self._extract_body(msg)

                    source = "GMAIL_UNKNOWN"
                    if "naukri" in sender.lower() or "naukri" in subject.lower():
                        source = "GMAIL_NAUKRI"
                    elif "linkedin" in sender.lower() or "linkedin" in subject.lower():
                        source = "GMAIL_LINKEDIN"

                    # Parse job links from email body
                    extracted = self._extract_leads_from_content(
                        subject=subject,
                        sender=sender,
                        body_html=body_html,
                        body_text=body_text,
                        source=source
                    )
                    leads.extend(extracted)
                except Exception as e:
                    logger.error(f"Error parsing email ID {msg_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to connect or fetch from Gmail: {e}")
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except Exception:
                    pass

        # Deduplicate leads by URL
        seen_urls = set()
        unique_leads = []
        for lead in leads:
            clean_url = lead.url.split("?")[0].strip()
            if clean_url and clean_url not in seen_urls:
                seen_urls.add(clean_url)
                unique_leads.append(lead)

        return unique_leads

    def _extract_leads_from_content(
        self, subject: str, sender: str, body_html: str, body_text: str, source: str
    ) -> List[ExtractedJobLead]:
        leads = []
        content = body_html or body_text

        if not content:
            return leads

        soup = BeautifulSoup(content, "html.parser")
        links = soup.find_all("a", href=True)

        for a in links:
            href = a["href"].strip()
            link_text = a.get_text(strip=True)

            # Detect LinkedIn Job URLs
            if "linkedin.com/jobs/view/" in href or "linkedin.com/comm/jobs/view/" in href:
                title = link_text or subject
                company = self._infer_company(subject, link_text)
                leads.append(ExtractedJobLead(
                    title=self._clean_title(title),
                    company=company,
                    url=href,
                    source="GMAIL_LINKEDIN",
                    snippet=subject
                ))

            # Detect Naukri Job URLs
            elif "naukri.com/job-listings-" in href or "naukri.com/jobs/" in href:
                title = link_text or subject
                company = self._infer_company(subject, link_text)
                leads.append(ExtractedJobLead(
                    title=self._clean_title(title),
                    company=company,
                    url=href,
                    source="GMAIL_NAUKRI",
                    snippet=subject
                ))

            # Detect Direct ATS URLs (Greenhouse, Lever, Workday)
            elif any(ats in href for ats in ["greenhouse.io", "lever.co", "myworkdayjobs.com", "smartrecruiters.com"]):
                leads.append(ExtractedJobLead(
                    title=self._clean_title(link_text or subject),
                    company=self._infer_company(subject, link_text),
                    url=href,
                    source="GMAIL_DIRECT_ATS",
                    snippet=subject
                ))

        return leads

    def _decode_str(self, s: str) -> str:
        if not s:
            return ""
        decoded = ""
        try:
            parts = decode_header(s)
            for text, charset in parts:
                if isinstance(text, bytes):
                    decoded += text.decode(charset or "utf-8", errors="ignore")
                else:
                    decoded += str(text)
        except Exception:
            return str(s)
        return decoded

    def _extract_body(self, msg) -> tuple[str, str]:
        html = ""
        text = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if "attachment" not in cdispo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_decoded = payload.decode(charset, errors="ignore")
                        if ctype == "text/html":
                            html += body_decoded
                        elif ctype == "text/plain":
                            text += body_decoded
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="ignore")
        return html, text

    def _infer_company(self, subject: str, link_text: str) -> str:
        # Check patterns like "Job opening at [Company]" or "[Company] is hiring"
        match = re.search(r'at\s+([A-Za-z0-9\s&]+?)(?:\s+in|\s+for|\.|$|\!)', subject, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'([A-Za-z0-9\s&]+?)\s+is hiring', subject, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Unknown Company"

    def _clean_title(self, raw_title: str) -> str:
        title = re.sub(r'\s+', ' ', raw_title).strip()
        if len(title) > 80:
            return title[:77] + "..."
        return title or "Lead Quality & GenAI Engineer"

    def _get_sample_leads(self) -> List[ExtractedJobLead]:
        """Provides realistic mock leads so the system can be verified instantly."""
        return [
            ExtractedJobLead(
                title="Senior GenAI / Agentic AI Engineer",
                company="Anthropic Ecosystem Partner",
                url="https://www.linkedin.com/jobs/view/sample-genai-lead-101",
                source="GMAIL_LINKEDIN",
                snippet="Looking for 10+ years experienced lead with LangGraph, Python, FastAPI, and MCP integration."
            ),
            ExtractedJobLead(
                title="Lead QA Automation Architect (Python + Playwright)",
                company="Global FinTech Innovations",
                url="https://www.naukri.com/job-listings-sample-lead-102",
                source="GMAIL_NAUKRI",
                snippet="Lead automation framework modernization from Java/Selenium to Python/Playwright with CI/CD."
            ),
            ExtractedJobLead(
                title="AI Quality Engineering & Evaluation Lead",
                company="HealthTech Enterprise Labs",
                url="https://boards.greenhouse.io/samplecompany/jobs/103",
                source="GMAIL_DIRECT_ATS",
                snippet="Architect LLM evaluation gates using Ragas/DeepEval, automated test generation, and guardrails."
            )
        ]

gmail_harvester = GmailHarvester()

