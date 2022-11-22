# -*- coding: utf-8 -*-

import re
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
            self.optional_data: Dict[str, bool] = word_data[1]
            self.tag: List[str] = None
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

    def kmp_search(self, txt: str, pat: str):
        M: int = len(pat)
        N: int = len(txt)

        lps: List[int] = [0] * M

        # preprocess the pattern
        self.compute_lps(pat, lps)

        i: int = 0  # idx for txt[]
        j: int = 0  # idx for pat[]

        while i < N:
            if pat[j] == txt[i]:  # 문자열이 같은 경우
                i += 1
                j += 1
            elif pat[j] != txt[i]:  # pattern을 찾지 못한 경우
                if j != 0:
                    j = lps[j - 1]  # 짧은 lps에 대해 재검사
                else:  # 일치하는 부분이 없음
                    i += 1

            if j == M:  # pattern을 찾은 경우
                j = lps[j - 1]

    def compute_lps(self, pat: str, lps: List[int]):
        leng: int = 0  # length of the previous longest prefix suffix

        i: int = 1  # always lps[0] == 0 -> while은 i == 1부터 시작함
        while i < len(pat):
            if pat[i] == pat[leng]:  # 이전 idx에서 같음
                leng += 1
                lps[i] = leng
                i += 1
            else:
                if leng != 0:  # 일치하지 않음
                    leng = lps[leng - 1]
                    # 이전 idx에서는 같았으므로 leng을 줄여서 다시 검사 -> i는 증가X
                else:  # 이전 idx에서도 같지 않음
                    lps[i] = 0
                    i += 1

    def format_meaning(self):
        text_lst = self.meaning.split('\n')

        # fix 1 ~ len(text_lst) and then modify to use enumerate
        for i in range(len(text_lst)):
            if (text_lst[i][0].isnumeric() and text_lst[i][1] == ".") or (text_lst[i][0].encode().isalpha() and text_lst[i][1] == "."):
                if text_lst[i][0] == "1" and i != 1:
                    text_lst[i - 1] = "\n" + text_lst[i - 1]
            else:
                erased_text = re.sub(
                    r"[^\uAC00-\uD7A30-9a-zA-Z\s]", "", text_lst[i])
                print(f"erased_text: {erased_text}")

                # if erased_text in self.relation_lst:
                #     if i + 1 < len(text_lst):
                #         text_lst[i] = f"{text_lst[i]}: {text_lst[i + 1]}"
                #         text_lst[i + 1] = ""

                if (not erased_text.encode().isalpha()) and (not erased_text in self.relation_lst):
                    if i - 1 > 0 and len(text_lst[i - 1]) >= 2:
                        print(f"text_lst[i - 1]: {text_lst[i - 1]}")
                        if (text_lst[i - 1][0].isnumeric() and text_lst[i - 1][1] == ".") or (text_lst[i - 1][0].encode().isalpha() and text_lst[i - 1][1] == "."):
                            if i + 1 < len(text_lst) and not text_lst[i + 1][0] == "1":
                                text_lst[i -
                                         1] = f"{text_lst[i - 1]} // {text_lst[i]}"
                                text_lst[i] = ""

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
            print(f"\n\n{formatter.word}\n{formatter.meaning}")

    ChromeDriver.driver_close()
