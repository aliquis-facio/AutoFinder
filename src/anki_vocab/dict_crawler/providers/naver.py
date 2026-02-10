"""
Docstring for anki_vocab.dict_crawler.providers.naver

역할
- 네이버 영어사전 전용 Provider
- 검색 -> 링크 수집 -> 상세 HTML 추출을 수행하고 EntryDocument 리스트를 반환
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup as bs
from bs4.element import Tag

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException  # type: ignore
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from webdriver_manager.chrome import ChromeDriverManager

from ..models import EntryDocument, Locator
from ..selenium_helper import SeleniumHelper


logger = logging.getLogger(__name__)


@dataclass
class NaverProviderConfig:
    base_url: str = "https://en.dict.naver.com"
    main_url: str = "https://en.dict.naver.com/#/main"
    wait_time: int = 8
    headless: bool = True
    page_load_timeout: int = 20


class NaverSel:
    SEARCH_INPUT: Locator = (By.NAME, "query")
    LEVEL_ALL: Locator = (By.CSS_SELECTOR, "#level_all")

    REVISION_ENTRY: Locator = (By.ID, "revisionSearchPage_entry")
    SEARCH_ENTRY: Locator = (By.CSS_SELECTOR, "#searchPage_entry > div")

    CONTENT: Locator = (By.CSS_SELECTOR, "#content")
    MEAN_GROUPS: Locator = (By.CSS_SELECTOR, "#allMeanGroups")

    # 상세 페이지 "더보기" 버튼
    MORE_BTNS: tuple[str, str] = (
        By.CSS_SELECTOR,
        "dl.entry_conjugation_list a.btn_more, dl.entry_conjugation a.btn_more",
    )


class NaverDictProvider:
    source = "naver"

    def __init__(self, config: Optional[NaverProviderConfig] = None) -> None:
        self.config = config or NaverProviderConfig()
        self.driver: Optional[WebDriver] = None
        self._sx: Optional[SeleniumHelper] = None

    # lifecycle
    def __enter__(self) -> "NaverDictProvider":
        if self.driver is not None:
            return self

        opts = Options()
        opts.add_experimental_option("excludeSwitches", ["enable-logging"])

        if self.config.headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")

        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.set_page_load_timeout(self.config.page_load_timeout)

        self._sx = SeleniumHelper(self.driver, self.config.wait_time)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.driver = None
        self._sx = None

    # internals
    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _normalize_query(self, word: str) -> str:
        if word is None:
            return ""
        if not isinstance(word, str):
            raise TypeError(f"query must be str, got {type(word)}")
        return re.sub(r"\s+", " ", word.strip())

    def _get_href(self, a_tag: Tag | None) -> str:
        if not a_tag:
            return ""

        raw_href = a_tag.get("href")
        href = ""
        if isinstance(raw_href, list):
            href = " ".join(raw_href).strip()
        elif isinstance(raw_href, str):
            href = raw_href.strip()

        if not href:
            return ""

        if href.startswith("http://") or href.startswith("https://"):
            return href

        base = self.config.base_url.rstrip("/")
        if href.startswith("#/"):
            return f"{base}/{href}"
        if href.startswith("/"):
            return f"{base}{href}"
        return f"{base}/{href}"

    def _open_main(self) -> None:
        assert self.driver and self._sx
        self.driver.get(self.config.main_url)
        self._sx.wait_document_complete()

    def _submit_query(self, q: str) -> None:
        assert self._sx
        box = self._sx.wait_presence(NaverSel.SEARCH_INPUT)
        box.clear()
        box.send_keys(q)
        box.send_keys(Keys.RETURN)

    def _select_level_all(self) -> None:
        assert self._sx
        if self._sx.safe_click(NaverSel.LEVEL_ALL):
            time.sleep(0.1)

    def _collect_revision_link(self) -> List[str]:
        assert self._sx
        html = self._sx.get_inner_html(NaverSel.REVISION_ENTRY)
        if not html:
            return []
        soup = bs(html, "html.parser")
        a = soup.select_one("div > div.row > div.origin > a")
        href = self._get_href(a)
        return [href] if href else []

    def _collect_search_entry_links(self) -> List[str]:
        assert self._sx
        html = self._sx.get_inner_html(NaverSel.SEARCH_ENTRY)
        if not html:
            return []

        soup = bs(html, "html.parser")
        rows = soup.select("div.row")
        if not rows:
            return []

        by_homonym: dict[int, str] = {}
        ordered: List[str] = []

        for row in rows:
            a_tag = row.select_one("div.origin > a.link") or row.select_one("div.origin > a")
            if not a_tag:
                continue

            href = self._get_href(a_tag)
            if not href:
                continue

            sup = a_tag.select_one("sup.num")
            if sup:
                t = sup.get_text(strip=True)
                if t.isdigit():
                    n = int(t)
                    if n not in by_homonym:
                        by_homonym[n] = href
                    continue

            ordered.append(href)

        if by_homonym:
            return [by_homonym[k] for k in sorted(by_homonym.keys())]
        return ordered[:1] if ordered else []

    def _dedup(self, links: List[str]) -> List[str]:
        out: List[str] = []
        seen = set()
        for x in links:
            if not x or x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    def _expand_more(self) -> None:
        assert self.driver and self._sx
        btns = self._sx.find_elements(*NaverSel.MORE_BTNS)
        for b in btns:
            try:
                if b.is_displayed() and b.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                    self.driver.execute_script("arguments[0].click();", b)
                    time.sleep(0.15)
            except WebDriverException:
                continue

    def _fetch_entry_html(self, entry_url: str) -> Optional[str]:
        assert self.driver and self._sx
        try:
            self.driver.get(entry_url)
        except WebDriverException as e:
            logger.warning("[naver] driver.get failed: %s", e)
            return None

        try:
            self._sx.wait_presence(NaverSel.MEAN_GROUPS)
        except TimeoutException:
            pass

        try:
            self._sx.wait_presence(NaverSel.CONTENT)
        except TimeoutException:
            return None

        self._expand_more()

        inner = self._sx.get_inner_html(NaverSel.CONTENT)
        if not inner:
            return None

        return bs(inner, "html.parser").prettify()

    def _back_to_search(self, q: str) -> None:
        assert self.driver and self._sx
        url = f"{self.config.base_url}/#/search?range=all&query={quote(q)}"
        try:
            self.driver.get(url)
            self._sx.wait_document_complete()
        except WebDriverException:
            pass

    # public
    def search(self, query: str) -> List[EntryDocument]:
        q = self._normalize_query(query)
        if not q:
            return []

        if self.driver is None or self._sx is None:
            self.__enter__()

        assert self.driver and self._sx

        try:
            self._open_main()
            self._submit_query(q)
            self._select_level_all()

            links: List[str] = []
            links.extend(self._collect_revision_link())
            links.extend(self._collect_search_entry_links())
            entry_links = self._dedup(links)

            logger.info("[naver] query=%r entry_links=%d", q, len(entry_links))
            if not entry_links:
                return []

            docs: List[EntryDocument] = []
            for url in entry_links:
                html = self._fetch_entry_html(url)
                if html:
                    docs.append(
                        EntryDocument(
                            source=self.source,
                            query=q,
                            entry_url=url,
                            html=html,
                            fetched_at_iso=self._now_iso(),
                            status="ok",
                        )
                    )
                self._back_to_search(q)

            return docs

        except Exception as e:
            logger.exception("[naver] search failed: %s", e)
            return []
