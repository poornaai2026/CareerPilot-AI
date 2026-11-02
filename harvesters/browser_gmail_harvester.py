"""
Browser-based Gmail Job Notification Harvester.
High-recall notification scanner that parses multi-job digest emails (like LinkedIn Job Alerts)
and extracts every individual job opportunity with its specific title, company, and application link.
"""
import time
import logging
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from config.settings import settings
from harvesters.gmail_harvester import ExtractedJobLead
from harvesters.notification_classifier import classifier

logger = logging.getLogger("BrowserGmailHarvester")

class BrowserGmailHarvester:
    def __init__(self, page: Page):
        self.page = page

    def fetch_job_leads_from_browser(self, max_emails: int = 20) -> List[ExtractedJobLead]:
        """
        Scans Gmail inbox for all LinkedIn and Naukri job alert emails,
        extracts every individual job posting inside multi-job digest emails,
        and returns clean job leads.
        """
        leads: List[ExtractedJobLead] = []

        try:
            logger.info("Opening Gmail inbox in Chrome: https://mail.google.com/mail/u/0/#inbox")
            self.page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="domcontentloaded", timeout=45000)
            self.page.wait_for_timeout(2500)

            # Check if user needs to log in
            if "signin" in self.page.url or "accounts.google.com" in self.page.url:
                logger.warning(
                    "Gmail is not logged in! Please run 'python main.py login' to sign in once."
                )
                return leads

            # Navigate directly to Gmail search URL (avoids autocomplete dropdown intercept)
            import urllib.parse
            days = settings.GMAIL_MAX_AGE_DAYS
            query = f'from:(linkedin OR naukri) newer_than:{days}d'
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://mail.google.com/mail/u/0/#search/{encoded_query}"
            logger.info(f"Navigating directly to Gmail search: '{query}'...")
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
            self.page.wait_for_timeout(3500)

            # Wait for email rows
            try:
                self.page.wait_for_selector("tr.zA", timeout=8000)
            except Exception:
                logger.info("No notification email rows found matching query.")

            email_rows = self.page.query_selector_all("tr.zA")
            logger.info(f"Detected {len(email_rows)} emails from LinkedIn and Naukri.")

            if not email_rows:
                return leads

            # Scan up to 50 rows in inbox to find ALL relevant job alert emails
            verified_job_emails = []
            for idx, row in enumerate(email_rows[:50]):
                subject_el = row.query_selector("span.bqe, span.bog")
                subject = subject_el.inner_text().strip() if subject_el else "Job Alert"

                sender_el = row.query_selector("span.bA4, span[email]")
                sender = sender_el.inner_text().strip() if sender_el else ""

                snippet_el = row.query_selector("span.y2")
                snippet = snippet_el.inner_text().strip() if snippet_el else ""

                date_el = row.query_selector("td.xW.xY span[title], td.xW.xY")
                date_str = date_el.get_attribute("title") if (date_el and date_el.get_attribute("title")) else (date_el.inner_text().strip() if date_el else "")

                # Intelligent Classification
                is_job_alert, reason = classifier.classify_notification(sender, subject, snippet)

                if not is_job_alert:
                    continue

                source = "GMAIL_NAUKRI" if "naukri" in f"{sender} {subject}".lower() else "GMAIL_LINKEDIN"

                verified_job_emails.append({
                    "index": idx,
                    "subject": subject,
                    "sender": sender,
                    "source": source,
                    "snippet": snippet,
                    "date": date_str
                })

                if len(verified_job_emails) >= max_emails:
                    break

            logger.info(f"Targeting {len(verified_job_emails)} verified job alert emails to extract opportunities.")

            # Process each verified job email
            for item in verified_job_emails:
                idx = item["index"]
                subject = item["subject"]
                source = item["source"]
                date_str = item["date"]
                snippet = item["snippet"]

                try:
                    # Always ensure we are on the search page
                    if "#search" not in self.page.url:
                        self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                        self.page.wait_for_selector("tr.zA", timeout=8000)
                        self.page.wait_for_timeout(1000)

                    current_rows = self.page.query_selector_all("tr.zA")
                    if idx >= len(current_rows):
                        continue
                    
                    row = current_rows[idx]
                    logger.info(f"Opening Job Email: [{date_str or 'Recent'}] '{subject}'")

                    # Click on subject or sender element to open email, avoiding checkbox
                    clickable = row.query_selector("span.bog, span.bqe, div.y6, span[email]") or row
                    clickable.click()
                    self.page.wait_for_timeout(2000)

                    # Extract body HTML
                    body_el = None
                    try:
                        self.page.wait_for_selector("div.a3s.aiL, div.ii.gt", timeout=6000)
                        body_el = self.page.query_selector("div.a3s.aiL, div.ii.gt")
                    except Exception:
                        body_el = self.page.query_selector("div.a3s.aiL, div.ii.gt")

                    if body_el:
                        body_html = body_el.inner_html()
                        extracted = self._parse_email_html(body_html, subject, source, snippet)
                        leads.extend(extracted)
                        logger.info(f"Extracted {len(extracted)} distinct job links from '{subject}'.")

                    # Direct return to search results for next email
                    self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    self.page.wait_for_selector("tr.zA", timeout=8000)
                    self.page.wait_for_timeout(1000)

                except Exception as e:
                    logger.debug(f"Error reading email '{subject}': {e}")
                    self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    self.page.wait_for_timeout(1500)

        except Exception as e:
            logger.error(f"Error accessing Gmail via browser: {e}")

        # Deduplicate leads by URL
        seen_urls = set()
        unique_leads = []
        for lead in leads:
            # Clean URL to standard base
            clean_url = lead.url.split("?")[0].strip()
            if clean_url and clean_url not in seen_urls:
                seen_urls.add(clean_url)
                unique_leads.append(lead)

        logger.info(f"Successfully harvested {len(unique_leads)} distinct job opportunities from emails.")
        return unique_leads

    def _parse_email_html(self, html: str, subject: str, default_source: str, snippet: str = "") -> List[ExtractedJobLead]:
        leads = []
        soup = BeautifulSoup(html, "html.parser")

        ignore_terms = [
            "unsubscribe", "privacy", "terms", "help", "support",
            "google.com/accounts", "play.google.com", "apps.apple.com", "facebook.com",
            "twitter.com", "notifications", "communication-preferences", "view all", "manage alerts"
        ]

        # 1. Parse LinkedIn Job Cards in Digest Emails
        # LinkedIn emails organize each job posting in table rows/cards
        job_links = soup.find_all("a", href=re.compile(r"linkedin\.com/(comm/)?jobs/(view|\?)", re.IGNORECASE))
        if not job_links:
            job_links = soup.find_all("a", href=re.compile(r"linkedin\.com/.*jobs", re.IGNORECASE))
        
        for a in job_links:
            href = a["href"].strip()
            text = a.get_text(strip=True)
            
            # Skip image wrapper links without text if sibling has title
            if any(ign in href.lower() for ign in ignore_terms):
                continue

            # Find card container (table or div)
            card = a.find_parent("table") or a.find_parent("tr") or a.find_parent("div")
            card_text = card.get_text(separator=" | ", strip=True) if card else ""

            # Extract Title
            job_title = text
            if not job_title or len(job_title) < 4 or job_title.lower() in ["view", "see job", "apply", "apply now"]:
                # Try finding text from card
                parts = [p.strip() for p in card_text.split("|") if len(p.strip()) > 4]
                job_title = parts[0] if parts else subject

            # Extract Company
            company = "Company from LinkedIn Alert"
            if card:
                # Look for company link inside the same card
                comp_link = card.find("a", href=re.compile(r"linkedin\.com/(comm/)?company/", re.IGNORECASE))
                if comp_link and comp_link.get_text(strip=True):
                    company = comp_link.get_text(strip=True)
                else:
                    # In LinkedIn digest: "Job Title | Company Name | Location"
                    parts = [p.strip() for p in card_text.split("|") if len(p.strip()) > 2]
                    for idx, p in enumerate(parts):
                        if p == job_title and idx + 1 < len(parts):
                            company = parts[idx + 1]
                            break

            leads.append(ExtractedJobLead(
                title=self._clean_title(job_title),
                company=company,
                url=href,
                source="GMAIL_LINKEDIN",
                snippet=card_text or snippet or subject
            ))

        # 2. Parse Naukri Job Alerts
        naukri_links = soup.find_all("a", href=re.compile(r"(naukri\.com/(job-listings|jobs|customjob|jd)|email\.naukri\.com)", re.IGNORECASE))
        for a in naukri_links:
            href = a["href"].strip()
            text = a.get_text(strip=True)
            if any(ign in href.lower() for ign in ignore_terms):
                continue

            card = a.find_parent("table") or a.find_parent("tr")
            card_text = card.get_text(separator=" | ", strip=True) if card else ""

            title = text if (text and len(text) > 5 and "apply" not in text.lower()) else subject
            comp = self._infer_company(subject, card_text)

            leads.append(ExtractedJobLead(
                title=self._clean_title(title),
                company=comp,
                url=href,
                source="GMAIL_NAUKRI",
                snippet=card_text or snippet or subject
            ))

        # 3. Direct ATS links in email body (Greenhouse, Lever, Workday)
        ats_links = soup.find_all("a", href=re.compile(r"(greenhouse\.io|lever\.co|myworkdayjobs\.com|smartrecruiters\.com)", re.IGNORECASE))
        for a in ats_links:
            href = a["href"].strip()
            text = a.get_text(strip=True)
            title = text if len(text) > 5 else subject
            leads.append(ExtractedJobLead(
                title=self._clean_title(title),
                company=self._infer_company(subject, text),
                url=href,
                source="GMAIL_DIRECT_ATS",
                snippet=snippet or subject
            ))

        return leads

    def _infer_company(self, subject: str, snippet: str = "") -> str:
        # Pattern: Global Technologies Senior Network Tools... -> Global Technologies
        match = re.search(r'^([A-Za-z0-9\s&]{2,30}?)\s+(?:Senior|Lead|Software|QA|Engineer|Architect|Network|Python)', subject, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'Job\s*\|\s*([A-Za-z0-9\s&]+?)\s*[-–]', subject, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'at\s+([A-Za-z0-9\s&]+?)(?:\s+in|\s+for|\.|$|\!)', subject, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Company from Job Alert"

    def _clean_title(self, raw: str) -> str:
        clean = re.sub(r'^(Job\s*\|\s*|Apply\s*:\s*|New\s+job\s+alert\s*:\s*)', '', raw, flags=re.IGNORECASE).strip()
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) > 80:
            return clean[:77] + "..."
        return clean or "Senior GenAI / Automation Engineer"
