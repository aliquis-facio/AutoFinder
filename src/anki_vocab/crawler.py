from __future__ import annotations

import logging, re, time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

# BeautifulSoup
from bs4 import BeautifulSoup as bs
from bs4.element import Tag

# 크롬 드라이버 기본 모듈
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException # type: ignore
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 크롬 드라이버 자동 업데이트를 위한 모듈
from webdriver_manager.chrome import ChromeDriverManager


logger = logging.getLogger(__name__)


class CrawlerError(RuntimeError):
    """Crawler domain error (optional raise depending on config)."""


@dataclass
class CrawlerConfig:
    base_url: str = "https://en.dict.naver.com"
    main_url: str = "https://en.dict.naver.com/#/main"
    wait_time: int = 8
    headless: bool = True
    page_load_timeout: int = 20
    raise_on_error: bool = False


class NaverDictSel:
    SEARCH_INPUT = (By.NAME, "query")
    LEVEL_ALL = (By.CSS_SELECTOR, "#level_all")

    REVISION_ENTRY = (By.ID, "revisionSearchPage_entry")
    SEARCH_ENTRY = (By.CSS_SELECTOR, "#searchPage_entry > div")

    CONTENT = (By.CSS_SELECTOR, "#content")
    MEAN_GROUPS = (By.CSS_SELECTOR, "#allMeanGroups")

    # 상세 페이지 "더보기" 버튼
    MORE_BTNS = (
        By.CSS_SELECTOR,
        "dl.entry_conjugation_list a.btn_more, dl.entry_conjugation a.btn_more",
    )


class SeleniumHelper:
    def __init__(self, driver: WebDriver, wait_time: int) -> None:
        self.driver = driver
        self.wait_time = wait_time
    
    def wait_presence(self, locator) -> WebElement:
        return WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located(locator)
        )
    
    def wait_clickable(self, locator) -> WebElement:
        return WebDriverWait(self.driver, self.wait_time).until(
            EC.element_to_be_clickable(locator)
        )

    def safe_click(self, locator) -> bool:
        try:
            el = self.wait_clickable(locator)
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except TimeoutException:
            return False
        except WebDriverException:
            return False

    def get_inner_html(self, locator) -> str | None:
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
    

class Crawler:
    def __init__(self, config: Optional[CrawlerConfig] = None) -> None:
        self.config = config or CrawlerConfig()

        # 크롬 드라이버 옵션 설정
        self.driver_options: Options = Options()
        # 브라우저 꺼짐 방지 옵션
        self.driver_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # 크롬 드라이버가 조작하는 브라우저 안 보임 설정
        if self.config.headless:
            # 크롬 최신 계열 권장. 구버전 호환 필요 시 "--headless"로 바꿔도 됨.
            self.driver_options.add_argument("--headless=new")
            self.driver_options.add_argument("--disable-gpu")

        # 안정성 옵션(환경별로 도움이 됨)
        self.driver_options.add_argument("--no-sandbox")
        self.driver_options.add_argument("--disable-dev-shm-usage")

        # 크롬 드라이버 최신 버전 설정
        self.service: Service = Service(ChromeDriverManager().install())

        # 크롬 드라이버 실행
        self.driver: WebDriver = webdriver.Chrome(
            service=self.service,
            options=self.driver_options,
        )
        self.driver.set_page_load_timeout(self.config.page_load_timeout)

        self._sx = SeleniumHelper(self.driver, self.config.wait_time)

    # Context Manager
    def __enter__(self) -> "Crawler":
        return self
    
    def __exit__(self, exc_type, exc, tb) -> None:
        self.driver_close()
    
    def _normalize_query(self, word: str) -> str:
        if word is None:
            return ""
        if not isinstance(word, str):
            raise TypeError(f"word must be str, got {type(word)}")
        q = word.strip()
        if not q:
            return ""
        # 연속 공백 정리: "look   up" -> "look up"
        q = re.sub(r"\s+", " ", q)
        return q

    def _get_href(self, a_tag: Tag | None) -> str:
        if not a_tag:
            return ""

        raw_href = a_tag.get("href")
        href: str = ""
        if isinstance(raw_href, list):
            href = " ".join(raw_href).strip()
        elif isinstance(raw_href, str):
            href = raw_href.strip()

        if not href:
            return ""
        
        # 이미 절대 URL이면 그대로
        if href.startswith("http://") or href.startswith("https://"):
            return href

        # 네이버 사전은 보통 '#/entry/...' 또는 '/...' 형태가 나올 수 있음
        if href.startswith("#/"):
            return f"https://en.dict.naver.com/{href}"
        if href.startswith("/"):
            return f"https://en.dict.naver.com{href}"

        # 기타 상대경로 방어
        return f"https://en.dict.naver.com/{href}"
    
    def _open_search_main(self) -> None:
        self.driver.get(self.config.main_url)
        self._sx.wait_document_complete()
    
    def _submit_query(self, locator, q: str) -> None:
        search_box: WebElement = self._sx.wait_presence(locator)
        search_box.clear()
        search_box.send_keys(q)
        search_box.send_keys(Keys.RETURN)

    def _select_level_all(self) -> None:
        clicked = self._sx.safe_click(NaverDictSel.LEVEL_ALL)
        if clicked:
            time.sleep(0.1)
    
    def _collect_revision_link(self) -> List[str]:
        html = self._sx.get_inner_html(NaverDictSel.REVISION_ENTRY)
        if not html:
            return []
        
        soup: bs = bs(html, "html.parser")
        a_tag: Tag | None = soup.select_one("div > div.row > div.origin > a")
        href: str = self._get_href(a_tag) if a_tag != None else ""

        return [href] if href else []
    
    def _collect_search_entry_links(self) -> List[str]:
        """
        일반 검색 결과에서 링크들을 추출.
        - 기존 코드의 select_one 반복(항상 첫 번째만 가져오는 문제) 제거
        - 동음이의어 sup.num이 있으면 번호별로 하나씩 우선 수집
        """
        html = self._sx.get_inner_html(NaverDictSel.SEARCH_ENTRY)
        if not html:
            return []

        soup = bs(html, "html.parser")

        # 결과 row 단위로 수집
        rows = soup.select("div.row")
        if not rows:
            return []

        by_homonym: dict[int, str] = {}
        ordered_links: List[str] = []

        for row in rows:
            a_tag = row.select_one("div.origin > a.link") or row.select_one("div.origin > a")
            href = self._get_href(a_tag)
            if not href:
                continue

            sup = a_tag.select_one("sup.num") if a_tag else None
            if sup:
                t = sup.get_text(strip=True)
                if t.isdigit():
                    n = int(t)
                    if n not in by_homonym:
                        by_homonym[n] = href
                    continue

            # sup이 없거나 숫자가 아니면 appearance order로 누적
            ordered_links.append(href)

        # 동음이의어가 있으면 (1,2,3...) 순서로 정렬해서 반환
        if by_homonym:
            return [by_homonym[k] for k in sorted(by_homonym.keys())]

        # 동음이의어 정보가 없으면, 최소 1개는 반환(기존 의도 유지)
        return ordered_links[:1] if ordered_links else []
    
    def _dedup_links(self, links: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for x in links:
            if not x:
                continue
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    def _expand_all_more(self) -> None:
        btns = self._sx.find_elements(*NaverDictSel.MORE_BTNS)
        for b in btns:
            try:
                if b.is_displayed() and b.is_enabled():
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                    self.driver.execute_script("arguments[0].click();", b)
                    time.sleep(0.15)
            except WebDriverException:
                continue

    def _fetch_entry_content_html(self, entry_link: str) -> Optional[str]:
        try:
            self.driver.get(entry_link)
        except WebDriverException as e:
            logger.warning("driver.get failed: %s", e)
            return None

        # 뜻/콘텐츠 영역 대기(둘 중 하나라도 뜨면 계속 진행)
        try:
            self._sx.wait_presence(NaverDictSel.MEAN_GROUPS)
        except TimeoutException:
            pass

        try:
            self._sx.wait_presence(NaverDictSel.CONTENT)
        except TimeoutException:
            return None

        # 필요 시 “더보기” 펼치기
        self._expand_all_more()

        res_html = self._sx.get_inner_html(NaverDictSel.CONTENT)
        if not res_html:
            return None

        soup = bs(res_html, "html.parser")
        return soup.prettify()

    def _back_to_search_page(self, q: str) -> None:
        url = f"{self.config.base_url}/#/search?range=all&query={quote(q)}"
        try:
            self.driver.get(url)
            # SPA 특성상 readyState만으로 부족할 수 있으나, 여기서는 최소 안정장치로 유지
            self._sx.wait_document_complete()
        except WebDriverException:
            pass

    def search_from_naver(self, word: str) -> List[str]:
        q = self._normalize_query(word)
        if q == "":
            return []

        try:
            self._open_search_main()
            self._submit_query(NaverDictSel.SEARCH_INPUT, q)
            self._select_level_all()

            links: List[str] = []
            links.extend(self._collect_revision_link())
            links.extend(self._collect_search_entry_links())
            entry_links = self._dedup_links(links)

            logger.info("query=%r entry_links=%d", q, len(entry_links))

            if not entry_links:
                return []

            html_lst: List[str] = []
            for link in entry_links:
                html = self._fetch_entry_content_html(link)
                if html:
                    html_lst.append(html)
                self._back_to_search_page(q)

            logger.info("query=%r html_count=%d", q, len(html_lst))
            return html_lst

        except Exception as e:
            # 유지보수 관점: 기본은 [] 반환(기존 동작과 유사), 필요 시 raise_on_error로 전환
            logger.exception("crawl failed: query=%r err=%s", q, e)
            if self.config.raise_on_error:
                raise CrawlerError(f"crawl failed for query={q!r}") from e
            return []

    def driver_close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    c = Crawler()

    res = c.search_from_naver("word")
    print(res)