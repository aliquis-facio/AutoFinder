# -*- coding: utf-8 -*-

# others
from typing import List, Dict, Tuple, Set, Any, Optional
import time, os, re
from dataclasses import dataclass
from bs4 import BeautifulSoup as bs

from crawler import Crawler
from parser import Parser
from formatter import Formatter
from word_entry import WordEntry


class AnkiTui:
    """
    README.MD 에 적힌 요구사항을 만족하는 간단 TUI:

    1. 사용자로부터 여러 영단어 입력
    2. (현재는 네이버 영한 사전만 지원, 캠브리지는 확장 여지)
    3. Selenium 크롤링 → 단어/발음/뜻/예문/태그 추출
    4. 날짜 기반 파일(YYYYMMDD_영단어.txt)에 누적 저장
    """

    def __init__(self) -> None:
        today = time.strftime("%Y%m%d")
        self.file_name: str = f"{today}_영단어.txt"

        # 기본 저장 위치: 사용자 Desktop 이 있으면 Desktop, 아니면 현재 작업 디렉토리
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        self.file_path: str = desktop if os.path.isdir(desktop) else os.getcwd()

        self.input_words: Set[str] = set()
        self.error_words: List[str] = []

        # 간단 명령어 (!quit)
        self.commands_info: Dict[str, str] = {"!quit": "quit entering"}
        self.commands: List[str] = list(self.commands_info.keys())

        self.finish: bool = False

        # 현재는 네이버(영한)만 동작. 확장 시 이 값을 바꿔서 분기.
        self.dict_type: str = "naver"

    # --- 파일 관련 ---

    def file_write(self, words_data: List[WordEntry]) -> None:
        """
        README 의 포맷:
        영단어, 발음, 뜻, 예문, 태그

        - 구분자는 탭(\t)
        - 태그는 #tag1 #tag2 형식의 한 문자열로 합친다.
        """
        full_path = os.path.join(self.file_path, self.file_name)
        mode: str = "wt" if not os.path.isfile(full_path) else "at"

        with open(full_path, mode, encoding="utf-8") as f:
            for entry in words_data:
                tags_with_hash = [f"#{t}" for t in entry.tag]
                tag_str = " ".join(tags_with_hash)

                # 파일에는 <br> 로 줄바꿈을 표현 (한 줄 = 한 레코드)
                row = [
                    entry.word,
                    entry.pronounce,
                    entry.meaning,
                    # entry.example,
                    tag_str,
                ]
                f.write("\t".join(row) + "\n")

    # --- 크롤링 & 포맷팅 ---

    def output(self) -> None:
        if not self.input_words:
            print("입력된 단어가 없습니다.")
            return

        # 현재는 네이버 영한 사전만 구현
        chrome_driver = Crawler()
        word_entries: List[WordEntry] = []

        try:
            for i, input_word in enumerate(sorted(self.input_words), start=1):
                try:
                    print(f"[{i}/{len(self.input_words)}] 검색 중: {input_word}")
                    raw_list = chrome_driver.search_word(input_word, url=url)

                    for raw in raw_list:
                        entry = Formatter(raw).to_entry()
                        word_entries.append(entry)

                        # 콘솔에 간단 출력
                        print(f"word: {entry.word}")
                        print(f"pronounce: {entry.pronounce}")
                        meaning_text = entry.meaning.replace("<br>", "\n").strip()
                        if meaning_text:
                            print("meaning:")
                            print(meaning_text)
                        # example_text = entry.example.replace("<br>", "\n").strip()
                        # if example_text:
                        #     print("example:")
                        #     print(example_text)
                        print(f"tag: {entry.tag}\n")

                except Exception as e:
                    self.error_words.append(input_word)
                    print(f"[ERROR] {input_word} → {type(e).__name__}: {e}\n")

        finally:
            chrome_driver.driver_close()

        # 결과 파일로 저장
        if word_entries:
            self.file_write(word_entries)
            print(f"\n총 {len(word_entries)}개의 항목을 '{os.path.join(self.file_path, self.file_name)}' 에 저장했습니다.")

        # 에러난 단어들 출력
        if self.error_words:
            print("\n--- error words ---")
            for w in self.error_words:
                print(w)

    # --- 명령 처리 ---

    def quit_(self, parse_lst: List[str]) -> None:
        self.finish = True

    # --- 메인 루프 ---

    def main(self) -> None:
        # 사전 타입 선택 (현재는 안내 메시지만, 실제 동작은 네이버만)
        print("사전을 선택하세요.")
        print("1) 네이버 영한 사전 (기본)")
        print("2) 캠브리지 영영 사전 (미구현 - 선택 시에도 네이버로 검색합니다.)")

        choice = input("번호 입력 후 Enter: ").strip()
        if choice == "2":
            self.dict_type = "cambridge"
            print("※ 현재 구현은 네이버 영한 사전만 지원하므로, 캠브리지 선택 시에도 네이버로 검색합니다.\n")
        else:
            self.dict_type = "naver"
            print("네이버 영한 사전을 사용합니다.\n")

        while not self.finish:
            intro_msg = "영단어를 입력하세요 (종료: !quit)\n-> "
            input_word = input(intro_msg).strip()
            print()

            if not input_word:
                continue

            if input_word.startswith("!"):
                parse_lst = input_word.split()
                for command in self.commands:
                    if parse_lst[0] == command:
                        getattr(self, command[1:] + "_")(parse_lst)
                        break
                else:
                    print(f"알 수 없는 명령입니다: {input_word}")
            else:
                self.input_words.add(input_word)

        # 입력 종료 후 크롤링/파일 출력
        self.output()

if __name__ == "__main__":
    crawler = Crawler()
    res = crawler.search_from_naver("pace")
    for html in res:
        soup:bs = bs(html, 'html.parser')
        pretty_html = soup.prettify()
        print(pretty_html)
    crawler.driver_close()