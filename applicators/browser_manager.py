"""
Browser Session Manager with Anti-Detection and Persistent Session Support.
Supports:
1. Chrome DevTools Protocol (CDP) connection to your active real Chrome browser.
2. Standalone persistent browser context with Playwright Stealth.
"""
import os
import logging
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
try:
    from playwright_stealth import Stealth
except ImportError:
    Stealth = None

from config.settings import settings

logger = logging.getLogger("BrowserManager")

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_cdp = False
        
        # Ensure screenshot and browser profile dirs exist
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        self.user_data_dir = Path(settings.BROWSER_USER_DATA_DIR)
        self.user_data_dir.mkdir(exist_ok=True)

    def start(self) -> Page:
        """Starts or connects to the browser session."""
        if self.page and not self.page.is_closed():
            return self.page

        self.playwright = sync_playwright().start()

        # Mode 1: Connect to active real Chrome via CDP (Zero-bot-risk)
        if settings.CHROME_CDP_URL:
            try:
                logger.info(f"Connecting to Chrome via CDP endpoint: {settings.CHROME_CDP_URL}...")
                self.browser = self.playwright.chromium.connect_over_cdp(settings.CHROME_CDP_URL)
                self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
                self.page = self.context.new_page()
                self.is_cdp = True
                logger.info("Successfully connected to existing Chrome session via CDP!")
                return self.page
            except Exception as e:
                logger.warning(f"Could not connect via CDP ({e}). Falling back to persistent browser context.")

        # Mode 2: Persistent browser context with stealth
        logger.info(f"Launching persistent browser context at '{self.user_data_dir}' (Headless={settings.BROWSER_HEADLESS})...")
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=settings.BROWSER_HEADLESS,
            channel="chrome", # Try installed Chrome first, fallback to Chromium
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--start-maximized"
            ],
            viewport=None,
            ignore_default_args=["--enable-automation"]
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        
        # Apply anti-detection stealth
        if Stealth:
            try:
                stealth = Stealth()
                stealth.apply_stealth_sync(self.page)
            except Exception as e:
                logger.debug(f"Stealth injection notice: {e}")

        logger.info("Browser session initialized.")
        return self.page

    def capture_screenshot(self, name_prefix: str = "app_review") -> str:
        """Saves a screenshot of the current page for review/audit."""
        if not self.page:
            return ""
        timestamp = Path(f"{name_prefix}_{os.getpid()}_{int(self.page.evaluate('Date.now()'))}.png")
        out_path = self.screenshots_dir / timestamp
        try:
            self.page.screenshot(path=str(out_path), full_page=False)
            return str(out_path)
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return ""

    def close(self):
        """Clean up browser resources."""
        try:
            if self.context and not self.is_cdp:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.debug(f"Error during browser teardown: {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None

browser_manager = BrowserManager()
