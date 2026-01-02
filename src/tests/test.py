from anki_vocab.crawler import Crawler
from anki_vocab.parser import Parser
from anki_vocab.formatter import Formatter
from anki_vocab.file_handler import FileHandler, FileHandlerConfig
import json, os

# 1) 케이스별 단어 묶음
TEST_CASES = {
    "homograph_pron": ["lead", "wind", "tear", "bow", "bass", "close", "do"],
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

    with FileHandler("output/anki_notes.tsv") as fh:
        for idx, words in enumerate(TEST_CASES.values()):
            print(f"{idx+1}번째 묶음")
            for i, word in enumerate(words):
                print(f"{i+1}/{len(words)}, {word}")
                htmls = crawler.search_from_naver(word)
                is_homonym = len(htmls) >= 2

                for idx, html in enumerate(htmls, start=1):
                    parser.set_html(html)
                    data = parser.parse_to_json(word)
                    # print(json.dumps(data, ensure_ascii=False, indent=2))
                    formatter.set_data(data)

                    pronunciation = formatter.format_pronunciation(join_with="")
                    print(pronunciation)
                    conjugation = formatter.format_conjugation(join_with="")
                    print(conjugation)
                    meaning = formatter.format_meaning(join_with="")
                    print(repr(meaning))  # 여기에 \n 이 없으면, prettify가 만든 개행임
                    print(formatter.pretty_html(meaning))  # 여기 출력은 prettify 때문에 줄바꿈이 생김

                    tags = formatter.format_tag()
                    print(tags)

                    fh.write_note(
                        word=word,
                        pronunciation=pronunciation,
                        conjugation=conjugation,
                        meaning=meaning,
                        tags=tags,
                        homonym_no=(idx if is_homonym else None),
                    )


if __name__ == "__main__":
    test()