# -*- coding: utf-8 -*-

import re
from typing import List, Dict, Tuple, Any
from WebDriver import Crawling


class Formatter:
    parts_of_speech: List[str] = ["명사", "대명사", "동사", "형용사", "부사",
                                  "전치사", "접속사", "한정사", "감탄사", "수사", "관계사"]
    sub_parts_of_speech: Dict[str, str] = {"가산명사": "명사", "불가산명사": "명사",
                                           "계사": "동사", "자동사": "동사", "타동사": "동사", "조동사": "동사",
                                           "관사": "한정사", "양화사": "한정사", "소유격": "한정사"}
    relation_lst: List[str] = ["문형", "유의어", "반의어", "참고어",
                               "상호참조", "Help", "약어", "부가설명", "전문용어", "줄임말"]
    broken_char_in_utf8: Dict[str, str] = {"∙": "/", "ˌ": ", ", "ˈ": "\""}

    def __init__(self, word_data: Tuple[List[str], List[str], Dict[str, bool]]) -> None:
        # parameter: ([영단어, 의미], [품사], {'isIdiom': bool, 'isPolysemy': bool, 'isError': bool})
        if not word_data[2]["isError"]:
            self.word: str = word_data[0][0]
            if not word_data[2]["isIdiom"]:
                self.pronounce: str = word_data[0][1]
            self.meaning: str = word_data[0][1] if word_data[
                2]["isIdiom"] else word_data[0][2]
            self.optional_data: Dict[str, bool] = word_data[2]
            self.tag: List[str] = word_data[1]
        else:
            raise Exception

    def replace_broken_char(self):
        pass

    def is_ordering(self, string: str) -> bool:
        if len(string) >= 2:
            i: int = string.find(".")
            return True if (0 < i <= 2) and (string[i - 1].isnumeric() or string[i - 1].encode().isalpha()) else False
        else:
            return False

    def is_additional_meaning(self, string: str) -> bool:
        if string.encode().isalpha():
            return False

        if string in self.relation_lst:
            return False

        for part in self.parts_of_speech:
            if string.startswith(part):
                return False

        for sub_part in self.sub_parts_of_speech.keys():
            if string.startswith(sub_part):
                return False

        return True

    def delete_punctuation_marks(self, string: str) -> str:
        return re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z]", "", string)

    def format_pronounce(self):
        # copy self.pronounce to text_lst
        text_lst: List[str] = self.pronounce.split('\n')
        size: int = len(text_lst)

        # modify self.pronounce using formatted text_lst
        self.pronounce = ""
        for i in range(size - 1):
            if text_lst[i]:
                self.pronounce += (text_lst[i] + "<br>")
        self.pronounce += text_lst[-1]
        self.pronounce.strip()

    def format_meaning(self):
        # copy self.meaning to text_lst
        text_lst: List[str] = self.meaning.split('\n')
        size: int = len(text_lst)

        # formatting text_lst
        for i in range(size - 1):
            if len(text_lst[i + 1]) <= 1:
                continue

            if self.is_ordering(text_lst[i + 1]):
                if text_lst[i + 1][:2] == "1." and i != 0:
                    text_lst[i] = f"<br>{text_lst[i]}"

                if i + 2 < size and not self.is_ordering(text_lst[i + 2]):
                    string = self.delete_punctuation_marks(text_lst[i + 2])
                    if self.is_additional_meaning(string):
                        text_lst[i +
                                 1] = f"{text_lst[i + 1]} // {text_lst[i + 2]}"
                        text_lst[i + 2] = ""

            elif text_lst[i + 1] in self.relation_lst:
                if i + 2 < size:
                    text_lst[i + 1] = f"{text_lst[i + 1]}: {text_lst[i + 2]}"
                    text_lst[i + 2] = ""

        # modify self.meaning using formatted text_lst
        self.meaning = ""
        for i in range(size - 1):
            if text_lst[i]:
                self.meaning += (text_lst[i] + "<br>")
        self.meaning += text_lst[-1]
        self.meaning.strip()

    def format_tag(self):
        for i in range(len(self.tag)):
            self.tag[i] = self.tag[i].strip()
            if self.tag[i] in self.sub_parts_of_speech:
                self.tag[i] = self.sub_parts_of_speech[self.tag[i]]

        self.tag = list(set(self.tag))
        if "" in self.tag:
            self.tag.remove("")

        for k, v in self.optional_data.items():
            if v and not (len(self.tag) > 0 and k == "isIdiom"):
                self.tag.append(k[2:])

    def return_data(self) -> Dict[str, Any]:
        if not self.optional_data["isIdiom"]:
            self.format_pronounce()
        self.format_meaning()
        self.format_tag()

        if self.optional_data["isIdiom"]:
            return {"word": self.word, "pronounce": "", "meaning": self.meaning, "tag": self.tag}
        else:
            return {"word": self.word, "pronounce": self.pronounce, "meaning": self.meaning, "tag": self.tag}


if __name__ == "__main__":
    input_word_lst = [
        "intermittently",
        "put down",
        "prior to",
        "pan",
        "as well as",
    ]

    ChromeDriver = Crawling()
    fomatter = None

    for input_word in input_word_lst:
        ChromeDriver.set_word(input_word)
        extracted_word_lst = ChromeDriver.search_word()

        for extracted_word in extracted_word_lst:
            formatter = Formatter(extracted_word)
            formatter.format_meaning()
            formatter.format_tag()

            print("--- --- ---\n{}\n{}\ntag: {}\n".format(formatter.word.replace("<br>", "\n"),
                  formatter.meaning.replace("<br>", "\n"), ", ".join(formatter.tag)))

    ChromeDriver.driver_close()
