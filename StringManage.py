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
                               "상호참조", "Help", "약어", "부가설명", "전문용어"]
    broken_char_in_utf8: Dict[str, str] = {"∙": "/", "ˌ": ", ", "ˈ": "\""}

    def __init__(self, word_data: Tuple[List[str], Dict[str, bool]]) -> None:
        if not word_data[1]["isError"]:
            self.word: str = word_data[0][0]
            if not word_data[1]["isIdiom"]:
                self.pronounce: str = word_data[0][1]
            self.meaning: str = word_data[0][1] if word_data[
                1]["isIdiom"] else word_data[0][2]
            self.optional_data: Dict[str, bool] = word_data[1]
            self.tag: List[str] = []
        else:
            raise Exception

    def replace_broken_char(self):
        pass

    def is_ordering(self, string: str) -> bool:
        if len(string) >= 2:
            return True if (string[0].isnumeric() and string[1] == ".") or (string[0].encode().isalpha() and string[1] == ".") else False
        else:
            return False

    def is_additional_meaning(self, string: str) -> bool:
        return True if not (string.encode().isalpha() or (string in self.relation_lst) or (string in self.parts_of_speech) or (string in self.sub_parts_of_speech.keys())) else False

    def delete_punctuation_marks(self, string: str) -> str:
        return re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z]", "", string)

    def format_meaning(self):
        # copy self.meaning to text_lst
        text_lst: List[str] = self.meaning.split('\n')
        size: int = len(text_lst)

        # formatting text_lst
        for i in range(1, size - 1):
            if len(text_lst[i]) <= 1:
                continue

            if self.is_ordering(text_lst[i]):
                if text_lst[i][0] == "1" and i != 1:
                    text_lst[i - 1] = f"<br>{text_lst[i - 1]}"

                if not self.is_ordering(text_lst[i + 1]):
                    string = self.delete_punctuation_marks(text_lst[i + 1])
                    if self.is_additional_meaning(string):
                        text_lst[i] = f"{text_lst[i]} // {text_lst[i + 1]}"
                        text_lst[i + 1] = ""

            elif text_lst[i] in self.relation_lst:
                text_lst[i] = f"{text_lst[i]}: {text_lst[i + 1]}"
                text_lst[i + 1] = ""

        # modify self.meaning using formatted text_lst
        self.meaning = ""
        for i in range(size - 1):
            if text_lst[i]:
                self.meaning += (text_lst[i] + "<br>")
        self.meaning += text_lst[-1]

    def format_tag(self):
        # add from self.optional data
        for k, v in self.optional_data.items():
            if v:
                self.tag.append(k[2:])

        # add from self.meaning
        text_lst: List[str] = self.meaning.split("<br>")
        size: int = len(text_lst)

        for i in range(1, size - 1):
            if len(text_lst[i]) <= 1:
                continue

            if text_lst[i][0] == "1" and text_lst[i][1] == ".":
                for part in self.parts_of_speech:
                    if text_lst[i - 1].startswith(part):
                        self.tag.append(part)
                        break
                else:
                    for sub_part in self.sub_parts_of_speech.keys():
                        if text_lst[i - 1].startswith(sub_part):
                            self.tag.append(self.sub_parts_of_speech[sub_part])
                            break

        # delete overlapped elem
        self.tag = list(set(self.tag))

    def return_data(self) -> Dict[str, Any]:
        self.format_meaning()
        self.format_tag()

        if self.optional_data["isIdiom"]:
            return {"word": self.word, "pronounce": "", "meaning": self.meaning, "tag": self.tag}
        else:
            return {"word": self.word, "pronounce": self.pronounce, "meaning": self.meaning, "tag": self.tag}


if __name__ == "__main__":
    input_word_lst = ["center", "bow", "curb",
                      "apple", "row", "vow", "in order to", "treat"]

    ChromeDriver = Crawling()
    fomatter = None

    for input_word in input_word_lst:
        ChromeDriver.set_word(input_word)
        extracted_word_lst = ChromeDriver.search_word()

        # try:
        #     for extracted_word in extracted_word_lst:
        #         formatter = Formatter(extracted_word)
        #         formatter.format_meaning()
        #         print(f"\n\n{formatter.word}\n{formatter.meaning}")
        # except Exception as e:
        #     print(type(e))

        for extracted_word in extracted_word_lst:
            formatter = Formatter(extracted_word)
            formatter.format_meaning()
            formatter.format_tag()
            print(
                f"--- --- ---\n{formatter.word}\n{formatter.meaning}\n{formatter.tag}")

    ChromeDriver.driver_close()
