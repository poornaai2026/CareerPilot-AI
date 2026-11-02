"""
Naukri Job Application Handler.
Extracts JD, matches against candidate profile, and performs 1-click apply.
"""
import time
import logging
from typing import Dict, Any, Optional
from playwright.sync_api import Page

from config.settings import settings
from config.candidate_profile import CANDIDATE
from core.llm_matcher import matcher, MatchEvaluation

logger = logging.getLogger("NaukriApply")

class NaukriApplyHandler:
    def __init__(self, page: Page):
        self.page = page

    def inspect_and_apply(self, job_url: str, existing_evaluation: Optional[MatchEvaluation] = None) -> Dict[str, Any]:
        """
        Navigates to a Naukri job URL, extracts JD, scores fit, and attempts application.
        """
        result = {
            "url": job_url,
            "title": "",
            "company": "",
            "status": "FAILED",
            "match_score": existing_evaluation.match_score if existing_evaluation else 0,
            "fit_category": existing_evaluation.fit_category if existing_evaluation else "UNKNOWN",
            "message": "",
            "screenshot": ""
        }

        try:
            logger.info(f"Navigating to Naukri Job: {job_url}")
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(2000)

            # Extract Title & Company
            title_el = self.page.query_selector("h1.styles_jd-header-title__rZwM1, h1")
            title = title_el.inner_text().strip() if title_el else "Unknown Role"

            comp_el = self.page.query_selector(".styles_jd-header-comp-name__MvqAI a, .styles_jd-header-comp-name__MvqAI")
            company = comp_el.inner_text().strip() if comp_el else "Unknown Company"

            # Extract Full JD
            jd_el = self.page.query_selector(".styles_job-desc-container__pvQvy, section.job-desc, .dang-inner-html")
            jd_text = jd_el.inner_text().strip() if jd_el else ""

            result["title"] = title
            result["company"] = company

            # Run LLM Match Evaluation if not already provided
            if not existing_evaluation:
                evaluation: MatchEvaluation = matcher.evaluate_job(title, company, jd_text)
                result["match_score"] = evaluation.match_score
                result["fit_category"] = evaluation.fit_category
            else:
                evaluation = existing_evaluation

            logger.info(f"Naukri Evaluated [{title} @ {company}]: Score = {evaluation.match_score} ({evaluation.fit_category})")

            # Check Threshold
            if evaluation.match_score < settings.MATCH_SCORE_THRESHOLD:
                result["status"] = "SKIPPED_LOW_SCORE"
                result["message"] = f"Match score {evaluation.match_score}% below threshold ({settings.MATCH_SCORE_THRESHOLD}%)."
                return result

            # Find Apply button
            apply_btn = self._find_apply_button()
            if not apply_btn:
                # Check if already applied
                already_applied = self.page.query_selector(".already-applied, :has-text('Already Applied')")
                if already_applied:
                    result["status"] = "ALREADY_APPLIED"
                    result["message"] = "Job already applied previously on Naukri."
                    return result
                result["status"] = "NOT_FOUND"
                result["message"] = "Apply button not visible (may require company site navigation)."
                return result

            btn_text = apply_btn.inner_text().strip().lower()

            # Check if it redirects externally
            if "company site" in btn_text:
                logger.info("Naukri job redirects to company career portal. Following link...")
                external_page = None
                try:
                    with self.page.context.expect_page(timeout=8000) as new_page_info:
                        apply_btn.click()
                    external_page = new_page_info.value
                except Exception:
                    apply_btn.click()
                    self.page.wait_for_timeout(3000)
                    external_page = self.page.context.pages[-1] if self.page.context.pages else self.page

                if external_page:
                    external_page.wait_for_load_state("domcontentloaded")
                    logger.info(f"Navigated to external company portal: {external_page.url}")
                    from applicators.ats_apply import ATSApplyHandler
                    ats_handler = ATSApplyHandler(external_page)
                    ats_res = ats_handler.inspect_and_apply(external_page.url)
                    result["status"] = ats_res.get("status", "PENDING_REVIEW")
                    result["message"] = ats_res.get("message", "Navigated and pre-filled on company portal.")
                    result["screenshot"] = ats_res.get("screenshot", "")
                    return result

                result["status"] = "EXTERNAL_APPLY_REQUIRED"
                result["message"] = "Redirects to external company career portal."
                return result

            # Click Apply
            logger.info("Clicking Naukri Apply button...")
            apply_btn.click()
            self.page.wait_for_timeout(2000)

            # Handle possible questionnaire or 'Apply without updating resume' modal
            self._handle_naukri_modals()

            # Capture proof screenshot
            from applicators.browser_manager import browser_manager
            screenshot_path = browser_manager.capture_screenshot("naukri_applied")
            result["screenshot"] = screenshot_path

            result["status"] = "APPLIED" if settings.AUTO_SUBMIT else "PENDING_REVIEW"
            result["message"] = "Application successfully submitted on Naukri!" if settings.AUTO_SUBMIT else "Staged for review on Naukri."

        except Exception as e:
            logger.error(f"Error applying on Naukri: {e}")
            result["status"] = "FAILED"
            result["message"] = str(e)

        return result

    def _find_apply_button(self):
        selectors = [
            "#apply-button",
            "button.apply-button",
            "button:has-text('Apply')",
            ".styles_apply-button-container__o_W_V button"
        ]
        for sel in selectors:
            btn = self.page.query_selector(sel)
            if btn and btn.is_visible():
                return btn
        return None

    def _handle_naukri_modals(self):
        """Dismisses update prompts or answers simple dropdowns."""
        # Check for 'Apply without update'
        bypass_btn = self.page.query_selector("button:has-text('Apply without'), button:has-text('Continue to apply')")
        if bypass_btn and bypass_btn.is_visible():
            bypass_btn.click()
            self.page.wait_for_timeout(1500)

