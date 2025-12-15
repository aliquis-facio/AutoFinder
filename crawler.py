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
                # 혹시 리스트로 올 경우 대비
                href = " ".join(raw_href)
            elif isinstance(raw_href, str):
                href = raw_href.strip()
            else:
                href = ""

        if href:
            # 네이버 href는 '#/entry/...' 형태
            href = "https://en.dict.naver.com/" + href

        return href     
        
    def search_from_naver(self, word: str) -> List[str]:
        """
        Docstring for search_from_naver
        
        :param self: selenium driver
        :param word: 검색할 단어
        :type word: str
        :return: html 배열
        :rtype: List[str]
        """

        # return 값 초기화
        html_lst: List[str] = []

        # 웹페이지 해당 주소로 이동
        self.driver.get(url="https://en.dict.naver.com/#/main")

        # 검색
        search_box = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((By.NAME, "query"))
        )
        search_box.clear()
        search_box.send_keys(word)
        search_box.send_keys(Keys.RETURN)
        
        """
        최종 수정: 2025.11.26
        네이버 영어 사전 검색 결과 html 구조:
        revisionSearchPage_entry에 가장 유사도가 높은 단어와 함께 뜻이 포함되어 있음
        이 밑에 searchPage_entry에 동음이의어/다의어, 숙어 등 그 외 검색 결과가 존재
        """

        # 레벨: 초급, 중급, 전체 -> 전체 선택
        try:
            select_level_all_button: WebElement = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#level_all")
                )
            )
            select_level_all_button.click()
        except:
            pass
        
        # 파싱할 링크 배열 초기화
        entry_links: List[str] = []

        # 메인 검색 결과
        try:
            revisionSearchPage = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located(
                    (By.ID, "revisionSearchPage_entry")
                )
            )

            revisionSearchPage_entry = revisionSearchPage.get_attribute("innerHTML")
            if revisionSearchPage_entry:
                entry_soup: bs = bs(revisionSearchPage_entry, "html.parser")
                a_tag: Tag | None = entry_soup.select_one("div > div.row > div.origin > a")
                href: str = self._get_href(a_tag)
                if href:
                    entry_links.append(href)
        except:
            pass
        
        # BeautifulSoup으로 component_keyword 내부 HTML 가져와서 sup(동음이의어 번호) 파싱
        component_keyword: WebElement = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#searchPage_entry > div")
            )
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

            # 동음이의어 개수 or 1 개의 row에서 링크 추출
            for i in range(loop):
                a_tag = entry_soup.select_one("div.row > div.origin > a.link")
                if not a_tag:
                    continue

                href = self._get_href(a_tag)
                if href:
                    entry_links.append(href)

        # 각 엔트리 상세 페이지로 이동해서 #content HTML 추출
        print(f"len(entry_links): {len(entry_links)}")
        for entry_link in entry_links:
            # 상세 페이지로 이동
            self.driver.get(entry_link)

            # 뜻 영역이 뜰 때까지 대기
            try:
                mean_area: WebElement = WebDriverWait(self.driver, self.wait_time).until(
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
            self.driver.get("https://en.dict.naver.com/#/search?range=all&query=" + word)
            self._wait_document_complete()
        
        return html_lst

    def driver_close(self) -> None:
        self.driver.quit() # close every browser

if __name__ == "__main__":
    input_words = [
        "water",
        "pace",
        "inquire",
        "bark",
        "bat",
        "row",
    ]

    crawler = Crawler()
    
    for word in input_words:
        print(f"word: {word}")

        htmls = crawler.search_from_naver(word)
        print(f"len(htmls): {len(htmls)}")

    crawler.driver_close()