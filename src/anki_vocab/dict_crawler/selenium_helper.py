"""
Docstring for anki_vocab.dict_crawler.selenium_helper

역할
- Selenium에서 반복되는 대기/클릭/HTML 추출을 한 곳에 모아 표준화
- 사이트별 Provider는 여기 유틸을 사용해 코드 중복을 줄임
"""

from __future__ import annotations

from typing import List, Optional

from selenium.common.exceptions import TimeoutException, WebDriverException  # type: ignore
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .models import Locator


class SeleniumHelper:
    def __init__(self, driver: WebDriver, wait_time: int) -> None:
        self.driver = driver
        self.wait_time = wait_time

    def wait_presence(self, locator: Locator) -> WebElement:
        return WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located(locator)
        )

    def wait_clickable(self, locator: Locator) -> WebElement:
        return WebDriverWait(self.driver, self.wait_time).until(
            EC.element_to_be_clickable(locator)
        )

    def safe_click(self, locator: Locator) -> bool:
        try:
            el = self.wait_clickable(locator)
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except (TimeoutException, WebDriverException):
            return False

    def get_inner_html(self, locator: Locator) -> Optional[str]:
        try:
            el = self.wait_presence(locator)
            return el.get_attribute("innerHTML")
        except TimeoutException:
            return None

    def wait_document_complete(self) -> None:
        WebDriverWait(self.driver, self.wait_time).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def find_elements(self, by: str, value: str) -> List[WebElement]:
        try:
            return self.driver.find_elements(by, value)
        except WebDriverException:
            return []
