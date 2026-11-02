"""
External ATS / Company Career Portal Application Handler.
Navigates to external company portals (Workday, Greenhouse, Lever, Taleo, Ashby, SmartRecruiters, custom),
auto-populates candidate details, attaches resume, and completes or stages application.
"""
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from config.settings import settings
from config.candidate_profile import CANDIDATE

logger = logging.getLogger("ATSApply")

class ATSApplyHandler:
    def __init__(self, page: Page):
        self.page = page

    def inspect_and_apply(self, career_url: str) -> Dict[str, Any]:
        """
        Navigates to the external organization career website, detects the ATS type,
        auto-fills fields, attaches Poorna's resume, and submits or stages for review.
        """
        result = {
            "url": career_url,
            "title": "",
            "company": "",
            "status": "FAILED",
            "message": "",
            "screenshot": ""
        }

        try:
            logger.info(f"Navigating to External Career Site: {career_url}")
            if self.page.url != career_url and not any(ats in self.page.url for ats in ["greenhouse", "lever", "workday", "smartrecruiters", "taleo"]):
                self.page.goto(career_url, wait_until="domcontentloaded", timeout=40000)
            
            self.page.wait_for_timeout(3500)

            current_url = self.page.url.lower()
            logger.info(f"Arrived at organization career portal: {self.page.url}")

            # Check for initial "Apply" / "Apply Now" button on company job page
            self._click_initial_apply_button()

            # Detect ATS architecture
            if "greenhouse.io" in current_url:
                return self._handle_greenhouse(result)
            elif "lever.co" in current_url:
                return self._handle_lever(result)
            elif "myworkdayjobs.com" in current_url or "workday" in current_url:
                return self._handle_workday(result)
            elif "smartrecruiters.com" in current_url:
                return self._handle_smartrecruiters(result)
            else:
                return self._handle_generic_career_form(result)

        except Exception as e:
            logger.error(f"Error automating external career portal: {e}")
            result["status"] = "FAILED"
            result["message"] = str(e)

        return result

    def _click_initial_apply_button(self):
        """Clicks 'Apply' or 'Apply Now' if landing on a job description page before the form."""
        apply_selectors = [
            "a[href*='#apply']",
            "a:has-text('Apply for this job')",
            "button:has-text('Apply for this job')",
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "button:has-text('Apply')",
            "[data-automation-id='applyButton']"
        ]
        for sel in apply_selectors:
            try:
                btn = self.page.query_selector(sel)
                if btn and btn.is_visible():
                    logger.info(f"Clicking initial apply trigger: {sel}")
                    btn.click()
                    self.page.wait_for_timeout(2500)
                    break
            except Exception:
                pass

    def _handle_greenhouse(self, result: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling Greenhouse ATS portal...")
        first_name, *last_name = CANDIDATE.full_name.split()
        last = " ".join(last_name) if last_name else first_name

        self._fill_if_exists("input#first_name, input[name*='first_name']", first_name)
        self._fill_if_exists("input#last_name, input[name*='last_name']", last)
        self._fill_if_exists("input#email, input[name*='email']", CANDIDATE.email)
        self._fill_if_exists("input#phone, input[name*='phone']", CANDIDATE.phone)

        # Upload resume
        self._attach_resume("input[type='file']")

        # Links
        self._fill_if_exists("input[autocomplete*='url'], input[id*='portfolio']", CANDIDATE.portfolio_url)
        self._fill_if_exists("input[id*='github']", CANDIDATE.github_url)
        self._fill_if_exists("input[id*='linkedin']", CANDIDATE.linkedin_url or CANDIDATE.portfolio_url)

        from applicators.browser_manager import browser_manager
        result["screenshot"] = browser_manager.capture_screenshot("greenhouse_filled")
        
        # Check auto submit
        submit_btn = self.page.query_selector("button#submit_app, input[type='submit']")
        if settings.AUTO_SUBMIT and submit_btn and submit_btn.is_visible():
            submit_btn.click()
            self.page.wait_for_timeout(3000)
            result["status"] = "APPLIED"
            result["message"] = "Submitted application on Greenhouse!"
        else:
            result["status"] = "PENDING_REVIEW"
            result["message"] = "Greenhouse application pre-filled with resume. Staged for 1-click review."

        return result

    def _handle_lever(self, result: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling Lever ATS portal...")
        self._fill_if_exists("input[name='name']", CANDIDATE.full_name)
        self._fill_if_exists("input[name='email']", CANDIDATE.email)
        self._fill_if_exists("input[name='phone']", CANDIDATE.phone)
        self._fill_if_exists("input[name='org']", CANDIDATE.current_company)
        self._fill_if_exists("input[name='urls[LinkedIn]']", CANDIDATE.portfolio_url)
        self._fill_if_exists("input[name='urls[GitHub]']", CANDIDATE.github_url)
        self._fill_if_exists("input[name='urls[Portfolio]']", CANDIDATE.portfolio_url)

        self._attach_resume("input[type='file']")

        from applicators.browser_manager import browser_manager
        result["screenshot"] = browser_manager.capture_screenshot("lever_filled")

        submit_btn = self.page.query_selector("button#btn-submit, button:has-text('Submit Application')")
        if settings.AUTO_SUBMIT and submit_btn and submit_btn.is_visible():
            submit_btn.click()
            self.page.wait_for_timeout(3000)
            result["status"] = "APPLIED"
            result["message"] = "Submitted application on Lever!"
        else:
            result["status"] = "PENDING_REVIEW"
            result["message"] = "Lever application pre-filled with resume. Staged for review."

        return result

    def _handle_workday(self, result: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling Workday career portal...")
        
        # Check for 'Autofill with Resume' or 'Apply Manually'
        autofill_btn = self.page.query_selector("[data-automation-id='autofillWithResume'], button:has-text('Autofill with Resume')")
        apply_manually_btn = self.page.query_selector("[data-automation-id='applyManually'], button:has-text('Apply Manually')")

        if autofill_btn and autofill_btn.is_visible():
            logger.info("Found 'Autofill with Resume' on Workday. Clicking and uploading PDF...")
            autofill_btn.click()
            self.page.wait_for_timeout(2000)
            self._attach_resume("input[type='file']")
        elif apply_manually_btn and apply_manually_btn.is_visible():
            logger.info("Clicking 'Apply Manually' on Workday...")
            apply_manually_btn.click()
            self.page.wait_for_timeout(2000)

        # Fill common Workday inputs
        first_name, *last_name = CANDIDATE.full_name.split()
        last = " ".join(last_name) if last_name else first_name

        self._fill_if_exists("[data-automation-id='legalNameSection_firstName'], input[id*='firstName']", first_name)
        self._fill_if_exists("[data-automation-id='legalNameSection_lastName'], input[id*='lastName']", last)
        self._fill_if_exists("[data-automation-id='email'], input[id*='email']", CANDIDATE.email)
        self._fill_if_exists("[data-automation-id='phone-number'], input[id*='phone']", CANDIDATE.phone)

        self._attach_resume("input[type='file']")

        from applicators.browser_manager import browser_manager
        result["screenshot"] = browser_manager.capture_screenshot("workday_filled")
        result["status"] = "PENDING_REVIEW"
        result["message"] = "Workday application navigated and pre-populated. Staged for 1-click review."
        return result

    def _handle_smartrecruiters(self, result: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling SmartRecruiters portal...")
        first_name, *last_name = CANDIDATE.full_name.split()
        last = " ".join(last_name) if last_name else first_name

        self._fill_if_exists("input#first-name-input", first_name)
        self._fill_if_exists("input#last-name-input", last)
        self._fill_if_exists("input#email-input", CANDIDATE.email)
        self._fill_if_exists("input#phone-number-input", CANDIDATE.phone)

        self._attach_resume("input[type='file']")

        from applicators.browser_manager import browser_manager
        result["screenshot"] = browser_manager.capture_screenshot("smartrecruiters_filled")
        result["status"] = "PENDING_REVIEW"
        result["message"] = "SmartRecruiters form filled with resume. Staged for review."
        return result

    def _handle_generic_career_form(self, result: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Handling generic organization career form...")
        first_name, *last_name = CANDIDATE.full_name.split()
        last = " ".join(last_name) if last_name else first_name

        # Fill Name fields
        self._fill_if_exists("input[name*='first_name'], input[id*='first_name'], input[name*='fname']", first_name)
        self._fill_if_exists("input[name*='last_name'], input[id*='last_name'], input[name*='lname']", last)
        self._fill_if_exists("input[name*='full_name'], input[id*='full_name'], input[name='name']", CANDIDATE.full_name)

        # Email & Phone
        self._fill_if_exists("input[type='email'], input[name*='email'], input[id*='email']", CANDIDATE.email)
        self._fill_if_exists("input[type='tel'], input[name*='phone'], input[id*='phone']", CANDIDATE.phone)

        # Company / Role
        self._fill_if_exists("input[name*='company'], input[id*='company']", CANDIDATE.current_company)
        self._fill_if_exists("input[name*='title'], input[id*='title']", CANDIDATE.current_title)

        # URLs
        self._fill_if_exists("input[name*='linkedin'], input[id*='linkedin']", CANDIDATE.portfolio_url)
        self._fill_if_exists("input[name*='github'], input[id*='github']", CANDIDATE.github_url)
        self._fill_if_exists("input[name*='portfolio'], input[id*='portfolio'], input[name*='website']", CANDIDATE.portfolio_url)

        # Resume upload
        self._attach_resume("input[type='file']")

        from applicators.browser_manager import browser_manager
        result["screenshot"] = browser_manager.capture_screenshot("generic_career_filled")
        result["status"] = "PENDING_REVIEW"
        result["message"] = "Organization career page form pre-filled with candidate data and resume. Staged for review."
        return result

    def _fill_if_exists(self, selector: str, value: str):
        try:
            el = self.page.query_selector(selector)
            if el and not el.input_value():
                el.fill(value)
        except Exception:
            pass

    def _attach_resume(self, selector: str):
        try:
            file_input = self.page.query_selector(selector)
            resume_file = Path(settings.RESUME_PATH)
            if file_input and resume_file.exists():
                file_input.set_input_files(str(resume_file.resolve()))
                logger.info(f"Attached candidate resume: {resume_file.name}")
        except Exception as e:
            logger.debug(f"Resume attach notice: {e}")
