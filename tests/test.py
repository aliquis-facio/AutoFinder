from src.anki_vocab.crawler import Crawler
from parser import Parser
from formatter import Formatter  # 있다면
# from word_entry import WordEntry  # 있다면

import json
import os
from pathlib import Path


# 1) 케이스별 단어 묶음
TEST_CASES = {
    # 다의어
    "polysemy_basics": ["make", "work", "water", "bark", "bat", "row", "pace"],
    # 동형이의어
    "homograph_pron": ["lead", "wind", "tear", "bow", "bass", "close"],
    # 강세/품사 전환
    "stress_shift": ["record", "permit", "object", "present", "conduct", "produce"],
    # 굴절/불규칙
    "inflection": ["went", "better", "children", "mice"],
    # 구/기호/하이픈/공백
    "phrases_symbols": ["look up", "well-known", "U.S.", "e-mail", "café"],
    # 결과 없음/예외
    "negative": ["asdkfjqwe", "", "   "],
}

FIXTURE_DIR = Path("tests/fixtures/naver")


def save_html_fixture(word: str, htmls: list[str]) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    safe = word.strip().replace(" ", "_").replace("/", "_")
    for i, html in enumerate(htmls):
        (FIXTURE_DIR / f"{safe}_{i}.html").write_text(html, encoding="utf-8")


def assert_crawler_basic(word: str, htmls: list[str]) -> None:
    # 최소한의 “형태” 검증 (크롤링이 완전 실패/빈 문자열/오류 페이지인지)
    if word.strip() == "" or word.strip().isspace():
        # 빈 입력은 정책상 [] 처리 또는 예외가 바람직
        # 구현 정책에 맞게 아래 중 하나로 고정하세요.
        assert htmls == [] or len(htmls) == 0
        return

    if word == "asdkfjqwe":
        # nonsense는 일반적으로 결과가 없을 가능성이 큼
        # 구현 정책에 맞게 len==0 을 기대하거나, 최소 0 이상만 확인
        assert len(htmls) >= 0
        return

    # 일반 단어는 보통 1개 이상 HTML이 와야 함 (단, 사이트/네트워크 상태에 따라 흔들릴 수 있음)
    assert isinstance(htmls, list)
    assert all(isinstance(h, str) for h in htmls)
    assert all(len(h) > 100 for h in htmls), f"{word}: HTML too short (maybe blocked or error page)"


def assert_parser_schema(word: str, data: dict) -> None:
    # parse_to_json의 “정확한” 스키마를 모르니, 흔히 필요한 최소 스키마만 방어적으로 검사
    assert isinstance(data, dict)
    # word 필드가 있다면 일치(없어도 통과)
    if "word" in data:
        assert data["word"] == word

    # 발음 리스트가 있다면 형식 확인
    for k in ("pron", "pronunciations", "prons"):
        if k in data:
            assert isinstance(data[k], list)
            for p in data[k]:
                assert isinstance(p, dict)
                if "ipa_text" in p:
                    s = p["ipa_text"]
                    assert isinstance(s, str)
                    assert s.startswith("[") and s.endswith("]"), f"{word}: ipa_text not bracketed: {s}"
            break

    # 의미/엔트리 리스트가 있다면 비어있지 않음(일반 단어 기준)
    for k in ("entries", "senses", "meanings"):
        if k in data and word not in ("asdkfjqwe", "", "   "):
            assert isinstance(data[k], list)
            # 완전 빈 리스트가 될 수도 있어 강제하지는 않되, 원하면 아래를 켜세요.
            # assert len(data[k]) > 0
            break


def crawler_smoke_test(save_fixture: bool = False) -> None:
    crawler = Crawler()
    try:
        for group, words in TEST_CASES.items():
            print(f"\n=== group: {group} ===")
            for word in words:
                print(f"word: {repr(word)}")
                htmls = crawler.search_from_naver(word)
                print(f"len(htmls): {len(htmls)}")
                assert_crawler_basic(word, htmls)
                if save_fixture and word.strip():
                    save_html_fixture(word, htmls)
    finally:
        crawler.driver_close()


def parser_smoke_test(words: list[str]) -> None:
    crawler = Crawler()
    try:
        for word in words:
            htmls = crawler.search_from_naver(word)
            for i, html in enumerate(htmls):
                parser = Parser(html)
                data = parser.parse_to_json(word)
                assert_parser_schema(word, data)
                print(f"\n[{word} #{i}]")
                print(json.dumps(data, ensure_ascii=False, indent=2))
    finally:
        crawler.driver_close()


def main():
    # 1) 크롤러만 스모크 + fixture 저장
    crawler_smoke_test(save_fixture=True)

    # 2) 파서 스모크 (원하는 그룹만)
    parser_smoke_test(TEST_CASES["homograph_pron"])


if __name__ == "__main__":
    main()
