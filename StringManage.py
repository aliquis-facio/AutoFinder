# -*- coding: utf-8 -*-

from string import ascii_letters
from typing import List, Dict, Tuple
from WebDriver import Crawling


class Formatter:
    parts_of_speech: List[str] = ["명사", "대명사", "동사", "형용사", "부사",
                                  "전치사", "접속사", "한정사", "감탄사", "수사", "관계사"]
    relation_lst: List[str] = ["문형", "유의어", "반의어", "참고어",
                               "상호참조", "Help", "약어", "부가설명", "전문용어"]
    ignored: List[str] = ["VN"]
    # about_pronounce: List[str] = ["발음듣기", "반복듣기"]
    broken_char_in_utf8: Dict[str, str] = {"∙": "/", "ˌ": ", ", "ˈ": "\""}

    def __init__(self, word_data: Tuple[List[str], Dict[str, bool]]) -> None:
        if not word_data[1]["isError"]:
            self.word: str = word_data[0][0]
            if not word_data[1]["isIdiom"]:
                self.pronounce: str = word_data[0][1]
            self.meaning: str = word_data[0][1] if word_data[
                1]["isIdiom"] else word_data[0][2]
            self.tag: Dict[str, bool] = word_data[1]
        else:
            raise Exception

    def replace_broken_char(self):
        pass

    def format_pronounce(self):
        pass

    def format_meaning(self):
        for i in range(len(self.meaning)):
            idx = self.meaning[i].find(' ')

            if (self.meaning[i] in self.parts_of_speech) and (i != 0):  # ex) 명사
                if i + 1 < len(self.meaning):
                    if self.meaning[i + 1].startswith("1. "):
                        for word_class in self.parts_of_speech:
                            if (word_class in self.meaning[i]):
                                self.meaning[i] = '\n' + \
                                    self.meaning[i]
                                break

            elif (self.meaning[i][idx - 1:idx] == "."):  # ex) 7. U // 일
                if i + 1 < len(self.meaning):
                    idx = self.meaning[i + 1].find(' ')

                    if (self.meaning[i + 1][idx - 1:idx] != ".") and not(self.meaning[i + 1] in self.relation_lst) and not(self.meaning[i + 1] in self.parts_of_speech):

                        temp_string = self.meaning[i + 1]
                        # for ignore_char in self.ignore_lst:
                        #     temp_string = temp_string.replace(ignore_char, "")

                        for char in ascii_letters:
                            if char in temp_string:
                                break
                        else:
                            self.meaning[i] = f"{self.meaning[i]} // {self.meaning[i + 1]}"
                            self.meaning[i + 1] = ""

            elif self.meaning[i - 1] in self.relation_lst:  # ex) 문형: sth ~
                for obj in self.relation_lst:
                    if self.meaning[i - 1] == obj:
                        self.meaning[i] = f"{obj}: {self.meaning[i]}"
                        break
                self.meaning[i - 1] = ""

        temp_lst = []
        for i in range(len(self.meaning)):
            if self.meaning[i]:
                temp_lst.append(self.meaning[i])

        string = ""
        for i in range(len(temp_lst)):
            if i == len(temp_lst) - 1:
                string += temp_lst[i]
            else:
                string += (temp_lst[i] + '\n')

        return string

    def format_meaning(self):
        text_lst = self.meaning.split('\n')

        for i, text in enumerate(text_lst):
            print(text)
            if (text[0].isnumeric() and text[1] == ".") or (text[0].isalpha() and text[1] == "."):
                if text[0] == '1':
                    text_lst[i - 1] = '\n' + text_lst[i - 1]

        self.meaning = '\n'.join(text_lst)

    def format_tag(self):
        for i in range(len(self.meaning)):
            for word_class in self.parts_of_speech:
                if (word_class in self.meaning[i]) and (self.meaning[i + 1].startswith("1. ")):
                    # 명사와 대명사 구분
                    if word_class == "명사" and len(self.meaning[i]) != 3:
                        continue
                    self.tag_lst.append(f"#{word_class}")
                    break

        string = ""
        for i in range(len(self.tag_lst)):
            if i == len(self.tag_lst) - 1:
                string += self.tag_lst[i]
            else:
                string += (self.tag_lst[i] + ' ')
        return string


if __name__ == "__main__":
    input_word_lst = ["center", "bow", "curb",
                      "apple", "row", "vow", "in order to", "treat"]
    input_word_lst = ["center", "bow"]

    ChromeDriver = Crawling()
    fomatter = None

    for input_word in input_word_lst:
        ChromeDriver.set_word(input_word)
        extracted_word_lst = ChromeDriver.search_word()

        try:
            for extracted_word in extracted_word_lst:
                formatter = Formatter(extracted_word)
                formatter.format_meaning()
                print(f"\n\n{formatter.meaning}")
        except Exception as e:
            print(type(e))
        # print(f"--- after formatting ---")
        # print(formatter.format_pronounce())
        # print(formatter.format_tag())

        # print("\n\n")

    ChromeDriver.driver_close()
