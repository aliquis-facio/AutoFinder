# -*- coding: utf-8 -*-

from string import ascii_letters
import time
import os
from automatic_search import AutomaticSearch
from string_format import Format4Anki


class AnkiTui:
    def __init__(self) -> None:
        self.file_name = f'{time.localtime().tm_year}-{time.localtime().tm_mon}-{time.localtime().tm_mday}-Engword.txt'
        self.file_path = 'C:\\Users\\jeony\\OneDrive\\바탕 화면'

        self.start = True
        self.finish = False

        self.input_words = set()
        self.error_words = []
        self.commands_dic = {'!quit': 'quit entering', '!re': 'remove lastest word and retype new word', '!show': 'Show all you entered',
                             '!del': 'delete word if it exsist', '!find': 'find word', '!help': 'show all commands and how to use'}
        self.commands = list(self.commands_dic.keys())
        self.special_characters = [' ', '-', '\n', '!']

    def file_write(self, string_lst):
        mode = 'wt' if not os.path.isfile(
            f'{self.file_path}\\{self.file_name}') else 'at'

        with open(f'{self.file_path}\\{self.file_name}', mode, encoding='utf-8') as f:
            for i in range(len(string_lst)):
                if i == len(string_lst) - 1:
                    f.write(f'"{string_lst[i]}"\n')
                else:
                    f.write(f'"{string_lst[i]}"\t')
                print(string_lst[i])
                print()
            f.close()

    def show_(self, parse_lst):
        # show -> show all words
        if self.input_words:
            print('---words---')
            for word in sorted(self.input_words):
                print(word, end=', ')
            print('------')
        else:
            print('---none---')

    def del_(self, parse_lst):
        # del word
        # del word1 word2 word3 ...
        # Do you wanna delete this/these word(s)? y/n
        # 지웠다/없어서 못 지웠다
        pass

    def find_(self, parse_lst):
        # find word
        # find word1 word2
        # answer -> y/n
        pass

    def re_(self, parse_lst):
        # remove the lastest word
        pass

    def quit_(self, parse_lst):
        self.start = False
        self.finish = True

    def help_(self, parse_lst):
        # help -> all
        # help (command) -> command
        print('\n---commands list---')
        for command, introduce in sorted(self.commands_dic.items()):
            print(f'{command}: {introduce}')
        print('------')

    def user_input(self):
        pass

    def ouput(self):
        if self.input_words:
            for word in self.input_words.copy():
                ChromeDriver = AutomaticSearch()
                ChromeDriver.set_word(word)
                word_lst = ChromeDriver.get_word()

                if type(word_lst) == str:  # 오류 발생 시
                    self.error_words.append(word_lst)
                else:
                    formatter = Format4Anki(word_lst)
                    formatter.replace_broken_char()
                    string_lst = [f'{word}\n{formatter.format_pronounce()}',
                                  formatter.format_meaning(), formatter.format_tag()]

                    self.file_write(string_lst)

                self.input_words.remove(word)

            if self.error_words:
                print('You should re-do about these ones:')
                for obj in self.error_words:
                    print(obj)

    def main(self):
        print('This Program is searching for Korean meaning of English word.\n')

        while self.start:
            reset = False

            intro_msg = 'Enter the English word\n(If you want to quit then pls enter the \'!quit\'.)\n-> '
            print(intro_msg, end='')
            input_word = input().strip()

            if input_word.startswith('!'):
                parse_lst = input_word.split()

                for command in self.commands:
                    if parse_lst[0] == command:
                        getattr(self, command[1:] + '_')(parse_lst)
                        break
                else:  # 명령어를 잘못 입력했을 경우
                    print(f'You may enter wrong command: {input_word}')

            if self.finish == True:
                print('finish')
                break

            for char in input_word:
                if not ((char in ascii_letters) or (char in self.special_characters)):
                    print("pls enter the English word\n")
                    reset = True
                    break

            if reset:
                continue

            self.input_words.add(input_word)
            print()

        self.ouput()


if __name__ == '__main__':
    anki_tui = AnkiTui()
    anki_tui.main()
