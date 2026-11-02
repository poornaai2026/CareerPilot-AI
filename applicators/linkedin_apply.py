"""
LinkedIn Job Application Handler.
Detects BOTH 'Easy Apply' (in-app modal) and standard 'Apply' (company website redirect).
Fills forms, attaches Poorna's resume, and submits or stages for 1-click review.
"""
import time
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from config.settings import settings
from config.candidate_profile import CANDIDATE
from core.llm_matcher import matcher, MatchEvaluation
from harvesters.gmail_harvester import ExtractedJobLead

logger = logging.getLogger("LinkedInApply")

class LinkedInApplyHandler:
    def __init__(self, page: Page):
        self.page = page

    def inspect_and_apply(self, lead_or_url: Any, existing_evaluation: Optional[MatchEvaluation] = None) -> Dict[str, Any]:
        """
        Navigates to a LinkedIn job URL, extracts details, and handles BOTH
        'Easy Apply' and standard 'Apply' (external company website).
        """
        if isinstance(lead_or_url, str):
            job_url = lead_or_url
            lead_title = ""
            lead_company = ""
            lead_snippet = ""
        else:
            job_url = getattr(lead_or_url, "url", str(lead_or_url))
            lead_title = getattr(lead_or_url, "title", "")
            lead_company = getattr(lead_or_url, "company", "")
            lead_snippet = getattr(lead_or_url, "snippet", "")

        result = {
            "url": job_url,
            "title": lead_title,
            "company": lead_company,
            "status": "FAILED",
            "match_score": existing_evaluation.match_score if existing_evaluation else 0,
            "fit_category": existing_evaluation.fit_category if existing_evaluation else "UNKNOWN",
            "message": "",
            "screenshot": ""
        }

        try:
            logger.info(f"Navigating to LinkedIn Job: {job_url}")
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=25000)
            self.page.wait_for_timeout(2500)

            # Wait for main page container
            try:
                self.page.wait_for_selector("h1, .jobs-description, .job-details, .jobs-unified-top-card", timeout=6000)
            except Exception:
                pass

            # Extract Title (with fallback to lead_title)
            title_el = self.page.query_selector(
                "h1.t-24, h1[class*='job-title'], h1, .job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title"
            )
            title = title_el.inner_text().strip() if title_el and len(title_el.inner_text().strip()) > 3 else lead_title
            
            # Extract Company (with fallback to lead_company)
            comp_el = self.page.query_selector(
                ".job-details-jobs-unified-top-card__company-name a, .job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name, a[href*='/company/']"
            )
            company = comp_el.inner_text().strip() if comp_el and len(comp_el.inner_text().strip()) > 2 else lead_company

            # Extract Full Job Description
            jd_el = self.page.query_selector(
                "#job-details, .jobs-description__content, .jobs-box__html-content, article.jobs-description__container"
            )
            jd_text = jd_el.inner_text().strip() if jd_el else ""

            result["title"] = title
            result["company"] = company

            # If we don't have an evaluation, evaluate now
            if not existing_evaluation or (len(jd_text) > 200 and existing_evaluation.match_score == 0):
                evaluation: MatchEvaluation = matcher.evaluate_job(title, company, jd_text or lead_snippet or title)
                result["match_score"] = evaluation.match_score
                result["fit_category"] = evaluation.fit_category
            else:
                evaluation = existing_evaluation

            logger.info(f"Job Fit: [{title} @ {company}] -> Score: {evaluation.match_score}% ({evaluation.fit_category})")

            # Check Threshold
            if evaluation.match_score < settings.MATCH_SCORE_THRESHOLD:
                result["status"] = "SKIPPED_LOW_SCORE"
                result["message"] = f"Match score {evaluation.match_score}% below threshold ({settings.MATCH_SCORE_THRESHOLD}%)."
                logger.info(f"Skipping: score {evaluation.match_score}% < threshold {settings.MATCH_SCORE_THRESHOLD}%.")
                return result

            # Detect Apply Action: 'EASY_APPLY' vs 'EXTERNAL_APPLY'
            action_type, apply_btn = self._find_apply_action()

            # Case 1: Easy Apply (In-page modal)
            if action_type == "EASY_APPLY":
                logger.info("Found 'Easy Apply' button! Initiating in-page application flow...")
                apply_btn.click()
                self.page.wait_for_timeout(2000)

                app_completed = self._handle_easy_apply_dialog(evaluation)
                
                from applicators.browser_manager import browser_manager
                result["screenshot"] = browser_manager.capture_screenshot("linkedin_easy_applied")

                if app_completed:
                    result["status"] = "APPLIED" if settings.AUTO_SUBMIT else "PENDING_REVIEW"
                    result["message"] = "Submitted successfully via Easy Apply!" if settings.AUTO_SUBMIT else "Easy Apply pre-filled and staged for review."
                else:
                    result["status"] = "PENDING_REVIEW"
                    result["message"] = "Encountered custom questionnaire. Pre-filled standard fields and staged for review."
                return result

            # Case 2: Standard Apply (Redirect to company career site)
            elif action_type == "EXTERNAL_APPLY":
                logger.info("Found standard 'Apply' button (Company Career Website). Following link...")
                initial_page_count = len(self.page.context.pages)

                # Check if button itself has an href
                direct_href = apply_btn.get_attribute("href")

                # Click the Apply button
                apply_btn.click()
                self.page.wait_for_timeout(2000)

                # Check if LinkedIn popped up a confirmation dialog
                self._handle_linkedin_external_redirect_modal()

                # Determine external page
                external_page = None
                if len(self.page.context.pages) > initial_page_count:
                    external_page = self.page.context.pages[-1]
                elif direct_href and not direct_href.startswith("#"):
                    # Open direct href if not opened automatically
                    external_page = self.page.context.new_page()
                    external_page.goto(direct_href, wait_until="domcontentloaded")
                else:
                    external_page = self.page

                if external_page:
                    # Wait for redirect from LinkedIn intermediate link to employer website
                    for _ in range(12):
                        curr_url = external_page.url.lower()
                        if "linkedin.com" not in curr_url and "about:blank" not in curr_url:
                            break
                        external_page.wait_for_timeout(1000)

                    try:
                        external_page.wait_for_load_state("domcontentloaded", timeout=15000)
                    except Exception:
                        pass

                    logger.info(f"Successfully arrived at company website: {external_page.url}")
                    from applicators.ats_apply import ATSApplyHandler
                    ats_handler = ATSApplyHandler(external_page)
                    ats_res = ats_handler.inspect_and_apply(external_page.url)
                    result["status"] = ats_res.get("status", "PENDING_REVIEW")
                    result["message"] = ats_res.get("message", f"Navigated to company career site: {external_page.url}")
                    result["screenshot"] = ats_res.get("screenshot", "")
                    return result
                else:
                    result["status"] = "EXTERNAL_APPLY_REQUIRED"
                    result["message"] = "Clicked Apply, redirecting to company site."
                    return result

            # Case 3: No Apply button found (Already Applied or Closed)
            else:
                already_applied = self.page.query_selector(".artdeco-inline-feedback--success, :has-text('Application submitted'), :has-text('Applied')")
                if already_applied and already_applied.is_visible():
                    logger.info("Job was already applied previously.")
                    result["status"] = "ALREADY_APPLIED"
                    result["message"] = "Job already applied previously on LinkedIn."
                else:
                    logger.info("Apply button not visible (may be closed or expired).")
                    result["status"] = "NOT_FOUND"
                    result["message"] = "No active Apply or Easy Apply button visible."
                return result

        except Exception as e:
            logger.error(f"Error handling LinkedIn job: {e}")
            result["status"] = "FAILED"
            result["message"] = str(e)

        return result

    def _find_apply_action(self) -> Tuple[Optional[str], Optional[Any]]:
        """
        Detects BOTH 'Easy Apply' and standard 'Apply' buttons on LinkedIn.
        Returns: ('EASY_APPLY', element) or ('EXTERNAL_APPLY', element) or (None, None)
        """
        selectors = [
            "button.jobs-apply-button",
            "a.jobs-apply-button",
            ".jobs-apply-button--top-card button",
            ".jobs-apply-button--top-card a",
            ".jobs-s-apply button",
            ".jobs-s-apply a",
            "button[aria-label*='Apply']",
            "a[aria-label*='Apply']",
            "button:has-text('Easy Apply')",
            "button:has-text('Apply on company')",
            "button:has-text('Apply')",
            "a:has-text('Apply')"
        ]

        # 1. Check for 'Easy Apply' first
        for sel in selectors:
            try:
                for el in self.page.query_selector_all(sel):
                    if el.is_visible():
                        text = el.inner_text().strip().lower()
                        aria = (el.get_attribute("aria-label") or "").lower()
                        if "easy apply" in text or "easy apply" in aria:
                            return "EASY_APPLY", el
            except Exception:
                pass

        # 2. Check for standard 'Apply' / 'Apply on company website' (External Apply)
        for sel in selectors:
            try:
                for el in self.page.query_selector_all(sel):
                    if el.is_visible():
                        text = el.inner_text().strip().lower()
                        aria = (el.get_attribute("aria-label") or "").lower()
                        if any(neg in text for neg in ["applied", "save", "share", "dismiss", "follow"]):
                            continue
                        if "apply" in text or "apply" in aria:
                            return "EXTERNAL_APPLY", el
            except Exception:
                pass

        return None, None

    def _handle_linkedin_external_redirect_modal(self):
        """Clicks 'Continue' or 'Proceed' if LinkedIn shows an external redirect confirmation dialog."""
        modal_selectors = [
            "div[role='dialog'] button:has-text('Continue')",
            "div[role='dialog'] a:has-text('Continue')",
            "div[role='dialog'] button:has-text('Proceed')",
            "div[role='dialog'] a:has-text('Proceed')",
            "button:has-text('Continue to application')",
            "a:has-text('Continue to application')",
            "button:has-text('Apply on company website')",
            "a:has-text('Apply on company website')",
            "button[data-easy-apply-next-button]"
        ]
        for sel in modal_selectors:
            try:
                btn = self.page.query_selector(sel)
                if btn and btn.is_visible():
                    logger.info(f"Clicking external redirect modal confirmation: {sel}")
                    btn.click()
                    self.page.wait_for_timeout(2000)
                    break
            except Exception:
                pass

    def _handle_easy_apply_dialog(self, evaluation: MatchEvaluation, max_steps: int = 6) -> bool:
        """Navigates through the Easy Apply modal dialog steps."""
        for step in range(max_steps):
            self.page.wait_for_timeout(1500)

            # Fill phone number if empty
            phone_inputs = self.page.query_selector_all("input[id*='phoneNumber'], input[name*='phoneNumber']")
            for pin in phone_inputs:
                if not pin.input_value():
                    pin.fill(CANDIDATE.phone)

            # Handle resume upload if required
            file_inputs = self.page.query_selector_all("input[type='file']")
            resume_path = Path(settings.RESUME_PATH)
            if file_inputs and resume_path.exists():
                try:
                    file_inputs[0].set_input_files(str(resume_path.resolve()))
                    logger.info("Attached candidate resume PDF.")
                except Exception as e:
                    logger.debug(f"File upload note: {e}")

            # Answer common questions
            self._answer_form_questions(evaluation)

            # Look for Next, Review, or Submit buttons
            next_btn = self.page.query_selector("button:has-text('Next'), button[data-easy-apply-next-button]")
            review_btn = self.page.query_selector("button:has-text('Review')")
            submit_btn = self.page.query_selector("button:has-text('Submit application')")

            if submit_btn and submit_btn.is_visible():
                if settings.AUTO_SUBMIT:
                    logger.info("Clicking 'Submit application' button...")
                    submit_btn.click()
                    self.page.wait_for_timeout(2000)
                    return True
                else:
                    logger.info("AUTO_SUBMIT is False. Preserving application at final Review screen.")
                    return True

            if review_btn and review_btn.is_visible():
                review_btn.click()
                continue

            if next_btn and next_btn.is_visible():
                next_btn.click()
                continue

            break

        return False

    def _answer_form_questions(self, evaluation: MatchEvaluation):
        """Answers standard numeric and text screening inputs."""
        inputs = self.page.query_selector_all(".fb-dash-form-element, .jobs-easy-apply-form-element")
        for item in inputs:
            label_el = item.query_selector("label")
            label_text = label_el.inner_text().lower() if label_el else ""
            
            input_box = item.query_selector("input[type='text'], input[type='number']")
            if not input_box or input_box.input_value():
                continue

            val_to_enter = None
            if "years" in label_text or "experience" in label_text:
                if "python" in label_text:
                    val_to_enter = "8"
                elif "genai" in label_text or "llm" in label_text or "ai" in label_text:
                    val_to_enter = "3"
                elif "playwright" in label_text:
                    val_to_enter = "4"
                elif "selenium" in label_text or "automation" in label_text:
                    val_to_enter = "10"
                else:
                    val_to_enter = "12"
            elif "notice" in label_text:
                val_to_enter = "30"
            elif "ctc" in label_text or "salary" in label_text:
                val_to_enter = "Negotiable"

            if val_to_enter:
                try:
                    input_box.fill(val_to_enter)
                except Exception:
                    pass
