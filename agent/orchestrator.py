"""
Autonomous Job Seeker Agent Orchestrator.
Orchestrates notification harvesting, LLM matching, database tracking, and browser applications.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.settings import settings
from config.candidate_profile import CANDIDATE
from core.db import get_db, JobApplicationRecord, ApplicationStatus
from core.llm_matcher import matcher, MatchEvaluation
from harvesters.gmail_harvester import gmail_harvester, ExtractedJobLead
from harvesters.browser_gmail_harvester import BrowserGmailHarvester
from applicators.browser_manager import browser_manager
from applicators.linkedin_apply import LinkedInApplyHandler
from applicators.naukri_apply import NaukriApplyHandler
from applicators.ats_apply import ATSApplyHandler

logger = logging.getLogger("JobSeekerOrchestrator")

class JobSeekerOrchestrator:
    def __init__(self):
        self.db = get_db()

    def run_pipeline(self, max_leads: int = 10, dry_run: bool = False) -> Dict[str, Any]:
        """
        Runs the end-to-end agentic workflow:
        1. Harvest leads from Gmail notifications (Naukri + LinkedIn).
        2. Deduplicate against database.
        3. Match and score against Poorna's resume with LLM.
        4. Execute browser application (if score qualifies and dry_run=False).
        5. Persist telemetry and results.
        """
        logger.info(f"Starting Job Seeker Agent Run (DryRun={dry_run}, MaxLeads={max_leads})...")
        summary = {
            "harvested_count": 0,
            "new_leads_count": 0,
            "qualified_count": 0,
            "applied_count": 0,
            "skipped_count": 0,
            "results": []
        }

        # Step 1: Harvest Leads (Browser or IMAP)
        page = None
        leads: List[ExtractedJobLead] = []

        if settings.HARVESTER_MODE.upper() == "BROWSER":
            try:
                page = browser_manager.start()
                browser_harvester = BrowserGmailHarvester(page)
                leads = browser_harvester.fetch_job_leads_from_browser(max_emails=max_leads)
            except Exception as e:
                logger.error(f"Browser Gmail harvesting error: {e}. Falling back to standard harvester.")

        if not leads and settings.HARVESTER_MODE.upper() == "IMAP":
            leads = gmail_harvester.fetch_job_leads(max_emails=max_leads)

        summary["harvested_count"] = len(leads)
        if not leads:
            logger.info("No matching job leads found in current notification batch.")
            return summary

        logger.info(f"Harvested {len(leads)} genuine job leads. Evaluating with LLM...")

        for lead in leads:
            # Step 2: Deduplication Check
            existing = self.db.query(JobApplicationRecord).filter(
                JobApplicationRecord.job_url == lead.url
            ).first()

            if existing:
                logger.info(f"Skipping already processed lead: {lead.title} ({lead.url})")
                continue

            summary["new_leads_count"] += 1

            # Step 3: LLM Evaluation
            evaluation = matcher.evaluate_job(
                job_title=lead.title,
                company=lead.company,
                jd_text=lead.snippet or lead.title
            )

            is_qualified = evaluation.match_score >= settings.MATCH_SCORE_THRESHOLD
            if is_qualified:
                summary["qualified_count"] += 1
            else:
                summary["skipped_count"] += 1

            # Create DB Record
            record = JobApplicationRecord(
                source=lead.source,
                job_title=lead.title,
                company_name=lead.company,
                job_url=lead.url,
                job_description=lead.snippet,
                match_score=float(evaluation.match_score),
                match_fit_category=evaluation.fit_category,
                match_rationale=evaluation.reasoning,
                matched_skills=", ".join(evaluation.skills_matched),
                missing_skills=", ".join(evaluation.skills_missing),
                tailored_pitch=evaluation.tailored_pitch,
                status=ApplicationStatus.QUALIFIED.value if is_qualified else ApplicationStatus.SKIPPED_LOW_SCORE.value
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)

            lead_result = {
                "id": record.id,
                "title": lead.title,
                "company": lead.company,
                "url": lead.url,
                "score": evaluation.match_score,
                "category": evaluation.fit_category,
                "status": record.status,
                "message": ""
            }

            # Step 4: Application Execution (if qualified and not dry_run)
            from core.licensing import licensing
            lic_status = licensing.get_license_status()

            if is_qualified and not dry_run:
                if not lic_status["can_apply"]:
                    logger.warning("Free application limit reached (10/10). Upgrade to Pro required.")
                    record.status = "LICENSE_LIMIT_REACHED"
                    record.error_message = "Free tier limit of 10 applications reached. Upgrade to CareerPilot Pro to unlock unlimited applications."
                    self.db.commit()
                    lead_result["status"] = record.status
                    lead_result["message"] = record.error_message
                    summary["results"].append(lead_result)
                    continue

                try:
                    if not page:
                        page = browser_manager.start()

                    apply_result = self._dispatch_applicator(page, lead, evaluation)
                    
                    record.status = apply_result.get("status", record.status)
                    record.screenshot_path = apply_result.get("screenshot", "")
                    record.error_message = apply_result.get("message", "")
                    if record.status in ["APPLIED", "PENDING_REVIEW"]:
                        record.applied_at = datetime.utcnow()
                        summary["applied_count"] += 1

                    self.db.commit()
                    lead_result["status"] = record.status
                    lead_result["message"] = apply_result.get("message", "")

                except Exception as e:
                    logger.error(f"Error applying to {lead.url}: {e}")
                    record.status = ApplicationStatus.FAILED.value
                    record.error_message = str(e)
                    self.db.commit()
                    lead_result["status"] = "FAILED"
                    lead_result["message"] = str(e)

            summary["results"].append(lead_result)

        # Teardown browser if opened
        if page:
            browser_manager.close()

        logger.info(f"Agent Run complete! Processed {len(summary['results'])} jobs. Applied: {summary['applied_count']}")
        return summary

    def _dispatch_applicator(self, page, lead: ExtractedJobLead, evaluation: Optional[MatchEvaluation] = None) -> Dict[str, Any]:
        """Dispatches job URL to appropriate portal handler."""
        url = lead.url.lower()
        if "linkedin.com" in url:
            handler = LinkedInApplyHandler(page)
            return handler.inspect_and_apply(lead, existing_evaluation=evaluation)
        elif "naukri.com" in url:
            handler = NaukriApplyHandler(page)
            return handler.inspect_and_apply(lead.url, existing_evaluation=evaluation)
        else:
            handler = ATSApplyHandler(page)
            return handler.inspect_and_apply(lead.url)

orchestrator = JobSeekerOrchestrator()

