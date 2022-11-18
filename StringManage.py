from string import ascii_letters
from typing import List, Dict, Tuple
from WebDriver import Crawling


class Formatter:
    parts_of_speech: List[str] = ["명사", "대명사", "동사", "형용사", "부사",
                                  "전치사", "접속사", "한정사", "감탄사", "수사", "관계사"]
    other_lst: List[str] = ["문형", "유의어", "반의어", "참고어",
                            "상호참조", "Help", "약어", "부가설명", "전문용어"]
    ignored: List[str] = ["VN"]
    about_pronounce: List[str] = ["발음듣기", "반복듣기"]
    broken_char_in_utf8: Dict[str, str] = {"∙": "/", "ˌ": ", ", "ˈ": "\""}

    def __init__(self, word_data: Tuple[List[str], Dict[str, bool]]) -> None:
        print(word_data)
        if not word_data[1]["isError"]:
            self.word: str = word_data[0][0]
            if not word_data[1]["isIdiom"]:
                self.pronounce: str = word_data[0][1]
            self.meaning: str = word_data[0][1] if word_data[
                1]["isIdiom"] else word_data[0][2]
            self.tag: List[str] = None
        else:
            raise Exception

    def replace_broken_char(self):
        exam_lst = [self.word, self.pronounce, self.meaning]

        for exam_obj in exam_lst:
            print(exam_obj)
            # for text in exam_obj.split():
            #     print(text)
        #     for i in range(len(exam_obj)):
        #         for char in self.broken_char_in_utf8.keys():
        #             if char in exam_obj[i]:
        #                 exam_obj[i] = exam_obj[i].replace(
        #                     char, self.broken_char_in_utf8[char])

    def format_pronounce(self):
        for i in range(len(self.pronounce_lst)):
            if self.pronounce_lst[i].startswith("발음 "):
                self.pronounce_lst[i] = self.pronounce_lst[i][3:]

        string = '\n'.join(self.pronounce_lst)
        return string

    def format_meaning(self):
        for i in range(len(self.meaning_lst)):
            idx = self.meaning_lst[i].find(' ')

            if (self.meaning_lst[i] in self.parts_of_speech) and (i != 0):  # ex) 명사
                if i + 1 < len(self.meaning_lst):
                    if self.meaning_lst[i + 1].startswith("1. "):
                        for word_class in self.parts_of_speech:
                            if (word_class in self.meaning_lst[i]):
                                self.meaning_lst[i] = '\n' + \
                                    self.meaning_lst[i]
                                break

            elif (self.meaning_lst[i][idx - 1:idx] == "."):  # ex) 7. U // 일
                if i + 1 < len(self.meaning_lst):
                    idx = self.meaning_lst[i + 1].find(' ')

                    if (self.meaning_lst[i + 1][idx - 1:idx] != ".") and not(self.meaning_lst[i + 1] in self.other_lst) and not(self.meaning_lst[i + 1] in self.parts_of_speech):

                        temp_string = self.meaning_lst[i + 1]
                        # for ignore_char in self.ignore_lst:
                        #     temp_string = temp_string.replace(ignore_char, "")

                        for char in ascii_letters:
                            if char in temp_string:
                                break
                        else:
                            self.meaning_lst[i] = f"{self.meaning_lst[i]} // {self.meaning_lst[i + 1]}"
                            self.meaning_lst[i + 1] = ""

            elif self.meaning_lst[i - 1] in self.other_lst:  # ex) 문형: sth ~
                for obj in self.other_lst:
                    if self.meaning_lst[i - 1] == obj:
                        self.meaning_lst[i] = f"{obj}: {self.meaning_lst[i]}"
                        break
                self.meaning_lst[i - 1] = ""

        temp_lst = []
        for i in range(len(self.meaning_lst)):
            if self.meaning_lst[i]:
                temp_lst.append(self.meaning_lst[i])

        string = ""
        for i in range(len(temp_lst)):
            if i == len(temp_lst) - 1:
                string += temp_lst[i]
            else:
                string += (temp_lst[i] + '\n')

        return string

    def format_tag(self):
        for i in range(len(self.meaning_lst)):
            for word_class in self.parts_of_speech:
                if (word_class in self.meaning_lst[i]) and (self.meaning_lst[i + 1].startswith("1. ")):
                    # 명사와 대명사 구분
                    if word_class == "명사" and len(self.meaning_lst[i]) != 3:
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
    input_word_lst = ["row", "center", "vow", "bow",
                      "curb", "pororo", "adsjaljdfh"]

    ChromeDriver = Crawling()
    fomatter = None

    for input_word in input_word_lst:
        ChromeDriver.set_word(input_word)
        extracted_word = ChromeDriver.search_word()
        # print(extracted_word_lst, end="\n\n")

        try:
            formatter = Formatter(extracted_word)
            print("\nfix text")
            formatter.replace_broken_char()
        except Exception as e:
            print(type(e))
        # print(f"--- after formatting ---")
        # print(formatter.format_pronounce())
        # print(formatter.format_meaning())
        # print(formatter.format_tag())

        # print("\n\n")

    ChromeDriver.driver_close()
