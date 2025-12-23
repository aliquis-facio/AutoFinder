# 크롬 드라이버 기본 모듈
from selenium import webdriver
from selenium.common.exceptions import * # type: ignore
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver

# 크롬 드라이버 자동 업데이트를 위한 모듈
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webelement import WebElement

# BeautifulSoup
from bs4 import BeautifulSoup as bs
from bs4.element import Tag

# 기타
from typing import List
from urllib.parse import quote
import re


class Crawler:
    def __init__(self) -> None:
        # 크롬 드라이버 옵션 설정
        self.driver_options: Options = Options()
        # 1. 브라우저 꺼짐 방지 옵션
        self.driver_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        # 2. 크롬 드라이버가 조작하는 브라우저 안 보임 설정
        # self.driver_options.add_argument("headless")
        # 3. 크롬 드라이버 대기 시간
        self.wait_time: int = 5  # sec
        # 4. 크롬 드라이버 최신 버전 설정
        self.service: Service = Service(ChromeDriverManager().install())

        # 크롬 드라이버 실행
        self.driver: WebDriver = webdriver.Chrome(service=self.service, options=self.driver_options)

    def _wait_document_complete(self) -> None:
        """
        Docstring for _wait_document_complete
        
        :param self: selenium driver
        전체 문서 로딩이 완료될 때까지 대기
        """
        
        WebDriverWait(self.driver, self.wait_time).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def _get_href(self, a_tag: Tag | None) -> str:
        href: str = ""
        if a_tag:
            raw_href = a_tag.get("href")
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
            return "https://en.dict.naver.com/" + href
        if href.startswith("/"):
            return "https://en.dict.naver.com" + href

        # 기타 상대경로 방어
        return "https://en.dict.naver.com/" + href
    
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
    
    def search_from_naver(self, word: str) -> List[str]:
        """
        Docstring for search_from_naver
        
        :param self: selenium driver
        :param word: 검색할 단어
        :type word: str
        :return: html 배열
        :rtype: List[str]
        """
        q: str = self._normalize_query(word)
        if q == "":
            # 빈 입력은 Selenium을 타면 안 됨
            return []

        # return 값 초기화
        html_lst: List[str] = []

        # 웹페이지 해당 주소로 이동
        self.driver.get(url="https://en.dict.naver.com/#/main")

        # 검색
        search_box: WebElement = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((By.NAME, "query"))
        )
        search_box.clear()
        search_box.send_keys(q)
        search_box.send_keys(Keys.RETURN)

        # 레벨: 초급, 중급, 전체 -> 전체 선택
        try:
            level_all: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#level_all"))
            )
            level_all.click()
        except:
            pass
        
        # 링크 배열 초기화
        entry_links: List[str] = []

        # 메인 검색 결과(revisionSearchPage_entry)에서 링크 1개 추출
        try:
            revision_el: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "revisionSearchPage_entry"))
            )

            revision_html: str | None = revision_el.get_attribute("innerHTML")
            if revision_html:
                revision_soup: bs = bs(revision_html, "html.parser")
                a_tag: Tag | None = revision_soup.select_one("div > div.row > div.origin > a")
                href: str = self._get_href(a_tag)
                if href:
                    entry_links.append(href)
        except:
            pass
        
        # 일반 검색 결과(searchPage_entry)에서 링크들 추출
        try:
            # BeautifulSoup으로 component_keyword 내부 HTML 가져와서 sup(동음이의어 번호) 파싱
            component_keyword: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#searchPage_entry > div"))
            )
            entry_html: str | None = component_keyword.get_attribute("innerHTML")

            if entry_html:
                entry_soup = bs(entry_html, "html.parser")

                # sup 기반 동음이의어 개수 계산
                sup_tags = entry_soup.select("div.row > div.origin > a > sup.num")
                homonym_numbers = set()
                for sup in sup_tags:
                    num_text = sup.get_text(strip=True)
                    if num_text.isdigit():
                        homonym_numbers.add(int(num_text))

                # 메인 검색 결과 내용이 없는 경우 최소 하나의 링크는 가져올 수 있도록 설정
                loop: int = len(homonym_numbers) if len(entry_links) > 0 else 1
                for i in range(loop):
                    a_tag = entry_soup.select_one("div.row > div.origin > a.link")
                    if not a_tag:
                        continue

                    href = self._get_href(a_tag)
                    if href:
                        entry_links.append(href)
        except TimeoutException:
            return []
        except Exception:
            pass
        
        # 중복 제거(순서 유지)
        dedup: List[str] = []
        seen = set()
        for link in entry_links:
            if link not in seen:
                seen.add(link)
                dedup.append(link)
        entry_links = dedup

        if not entry_links:
            return []
        
        # 각 엔트리 상세 페이지로 이동해서 #content HTML 추출
        # print(f"len(entry_links): {len(entry_links)}") # 디버깅용
        for entry_link in entry_links:
            # 상세 페이지로 이동
            self.driver.get(entry_link)

            # 뜻 영역 대기
            try:
                WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#allMeanGroups"))
                )
            except:
                pass

            try:
                content: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#content"))
                )
                
                res_html = content.get_attribute("innerHTML")
                if res_html:
                    soup: bs = bs(res_html, "html.parser")
                    html_lst.append(soup.prettify())
            except:
                pass
            
            # 추출 후 검색 페이지로 복귀
            self.driver.get("https://en.dict.naver.com/#/search?range=all&query=" + q)
            self._wait_document_complete()
        
        return html_lst

    def driver_close(self) -> None:
        self.driver.quit() # close every browser
