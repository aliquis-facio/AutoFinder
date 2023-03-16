# -*- coding: utf-8 -*-

import time
import os
from WebDriver import Crawling
from StringManage import Formatter
from typing import List, Dict, Set


class AnkiTui:
    def __init__(self) -> None:
        self.file_name: str = f"{time.localtime().tm_year}-{time.localtime().tm_mon}-{time.localtime().tm_mday}-Engword.txt"
        self.file_path: str = "C:\\Users\\jeony\\Desktop"

        self.input_words: Set[str] = set()
        self.error_words: List[str] = []

        self.commands_info: Dict[str, str] = {"!quit": "quit entering"}
        self.commands: List[str] = list(self.commands_info.keys())

        self.special_characters: List[str] = [" ", "-", "\n", "!"]

        self.finish: bool = None

        self.driver = self.formatter = None

    def file_write(self, words_data: List[Dict]):
        mode = "wt" if not os.path.isfile(
            f"{self.file_path}\\{self.file_name}") else "at"

        with open(f"{self.file_path}\\{self.file_name}", mode, encoding="utf-8") as f:
            for word_data in words_data:
                for i in range(len(word_data["tag"])):
                    word_data["tag"][i] = ("#" + word_data["tag"][i])
                tag: str = " ".join(word_data["tag"])

                f.write(word_data["word"] + "<br>")
                f.write(word_data["pronounce"] + "\t")
                f.write(word_data["meaning"] + "\t")
                f.write(tag + "\n")

            f.close()

    def ouput(self):
        if self.input_words:
            ChromeDriver = Crawling()
            word_data_lst = []

            for i, input_word in enumerate(self.input_words.copy()):
                try:
                    print(f"progress: {i + 1} / {len(self.input_words)}")
                    ChromeDriver.set_word(input_word)
                    extracted_word_lst = ChromeDriver.search_word()

                    for extracted_word in extracted_word_lst:
                        formatter = Formatter(extracted_word)
                        word_data: Dict[str, any] = formatter.return_data()
                        word_data_lst.append(word_data)

                        # print(f"curr word: {word_data}\n")
                        print(f"word: {word_data['word']}")
                        print(f"pronounce: {word_data['pronounce']}")
                        meaning: str = word_data['meaning'].replace(
                            '<br>', '\n').strip()
                        print(f"meaning: {meaning}")
                        print(f"tag: {word_data['tag']}\n")

                except Exception as e:
                    self.error_words.append(input_word)
                    print(f"curr word: {input_word} -> {type(e)}\n")

            ChromeDriver.driver_close()
            self.file_write(word_data_lst)

            if self.error_words:
                print("--- error words ---")
                for error_word in self.error_words:
                    print(error_word)

    def quit_(self, parse_lst: List[str]):
        self.finish = True

    def main(self):
        # print("This Program is searching for Korean meaning of English word.\n")

        while not self.finish:
            intro_msg = "Enter the English word\n(If you want to quit then pls enter the \"!quit\".)\n-> "
            input_word = input(intro_msg).strip()
            print()

            if input_word.startswith("!"):
                parse_lst = input_word.split()

                for command in self.commands:
                    if parse_lst[0] == command:
                        getattr(self, command[1:] + "_")(parse_lst)
                        break
                else:
                    print(f"You may enter wrong command: {input_word}")
            else:
                if input_word:
                    self.input_words.add(input_word)

        self.ouput()


if __name__ == "__main__":
    anki_tui = AnkiTui()
    anki_tui.main()
