from anki_vocab.crawler import Crawler
from anki_vocab.parser import Parser
from anki_vocab.formatter import Formatter
from anki_vocab.word_entry import WordEntry

import json
import os
from pathlib import Path


# 1) 케이스별 단어 묶음
TEST_CASES = {
    "homograph_pron": ["lead", "wind", "tear", "bow", "bass", "close"],
    "polysemy_basics": ["make", "work", "water", "bark", "bat", "row", "pace"],
    "stress_shift": ["record", "permit", "object", "present", "conduct", "produce"],
    "inflection": ["went", "better", "children", "mice"],
    "phrases_symbols": ["look up", "well-known", "U.S.", "e-mail", "café"],
    "negative": ["asdkfjqwe", "", "   "],
}

def test():
    crawler = Crawler()
    parser = Parser()
    formatter = Formatter()

    for case_name, words in TEST_CASES.items():
        for word in words:
            print(f"word: {word}")
            htmls = crawler.search_from_naver(word)

            for html in htmls:
                parser.set_html(html)
                data = parser.parse_to_json(word)
                # print(json.dumps(data, ensure_ascii=False, indent=3))
                
                formatter.set_data(data)
                print(formatter.format_pronunciation())
                print(formatter.pretty_html(formatter.format_meaning()))
                print(formatter.format_tag())

                input("waiting...")


if __name__ == "__main__":
    test()
