from dataclasses import dataclass
from urllib.parse import urlparse
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

@dataclass
class PageResult:
    url: str
    title: str
    text: str

class BrowserTool:
    def __init__(self, headless=True):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=headless)
        self.page = self.browser.new_page(
            viewport={"width":1440,"height":900},
            user_agent="AutonomousResearchAgent/1.0"
        )

    @staticmethod
    def _validate_url(url):
        p = urlparse(url)
        if p.scheme not in {"http","https"} or not p.netloc:
            raise ValueError("Only valid http/https URLs are allowed.")

    def navigate(self, url):
        self._validate_url(url)
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(800)
        except PlaywrightTimeoutError:
            pass
        return self.extract_text()

    def click(self, selector):
        self.page.locator(selector).first.click(timeout=10000)
        self.page.wait_for_timeout(500)

    def extract_text(self, max_chars=16000):
        title = self.page.title()
        text = self.page.locator("body").inner_text(timeout=10000)
        text = re.sub(r"\s+", " ", text).strip()
        return PageResult(self.page.url, title, text[:max_chars])

    def close(self):
        self.browser.close()
        self._pw.stop()
