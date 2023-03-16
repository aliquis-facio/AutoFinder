# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from typing import List, Dict, Tuple
from webdriver_manager.chrome import ChromeDriverManager
import chromedriver_autoinstaller
import os
import shutil


class Crawling:
    def chromedriver_update(self):  # this solution had not been needed anymore
        chrome_ver = chromedriver_autoinstaller.get_chrome_version().split('.')[
            0]
        curr_lst = os.listdir(os.getcwd())
        driver_folder_lst = []

        # find out every folders including chromedriver
        for obj in curr_lst:
            path = os.path.join(os.getcwd(), obj)
            if os.path.isdir(path):
                if "chromedriver.exe" in os.listdir(obj):
                    driver_folder_lst.append(obj)

        old_version = list(set(driver_folder_lst) - set([chrome_ver]))

        # remove old version
        for obj in old_version:
            path = os.path.join(os.getcwd(), obj)
            shutil.rmtree(path)

        # install the lastest version driver
        if not chrome_ver in curr_lst:
            chromedriver_autoinstaller.install(True)

        return os.path.join(os.getcwd(), chrome_ver)

    def __init__(self) -> None:
        # initial target word
        self.word: str = ""

        try:
            # driver's options
            self.driver_options = Options()
            self.driver_options.add_experimental_option(
                "excludeSwitches", ["enable-logging"])
            self.driver_options.add_argument("headless")
            self.wait_time: int = 5  # sec

            # initialize the lastest driver
            self.driver = webdriver.Chrome(service=Service(
                ChromeDriverManager().install()), options=self.driver_options)
            self.driver.implicitly_wait(self.wait_time)

            # set intial page
            self.driver.get(url="https://en.dict.naver.com/#/main")
        except SessionNotCreatedException as e:
            print(
                f"Chrome version may not be the latest version. Please update Chrome and try again.")
            print(type(e))
        except Exception as e:
            print("Please try again later")
            print(type(e))

    def set_word(self, word: str):
        self.word = word.lower()

    def get_raw_data(self, searched_word_elem, searched_word_text: str) -> Tuple[List[str], List[str], Dict[str, bool]]:
        word_data: List[str] = [searched_word_text]

        isIdiom: bool = False
        text_lst: List[str] = searched_word_text.split()
        for round_bracket in ('(', ')'):
            if round_bracket not in text_lst:
                for i, text in enumerate(text_lst):
                    if i > 0 and text.isalpha():
                        isIdiom = True
                        break

        type_dict = dict()
        type_dict.setdefault("isIdiom", isIdiom)

        parts_of_speech_text_lst: List[str] = []

        try:
            WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable(searched_word_elem)).click()

            if not isIdiom:
                try:
                    WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "pronounce_area")))
                    pronounce_elem = WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "pronounce_area")))
                    pronounce_text: str = pronounce_elem.text
                except TimeoutException:
                    # not exist html class "pronounce_area"
                    pronounce_text: str = ""
                finally:
                    word_data.append(pronounce_text)

            meaning_elem = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.CLASS_NAME, "mean_tray")))
            meaning_text: str = meaning_elem.text

            parts_of_speech_elem = self.driver.find_elements(
                By.CLASS_NAME, "part_speech")
            for elem in parts_of_speech_elem:
                text_lst = elem.text.split(",")
                for text in text_lst:
                    parts_of_speech_text_lst.append(text.strip())

            word_data.append(meaning_text)
            # word_data.append(parts_of_speech_text_lst)
        except Exception as e:
            print(f"exception occured in Crawling.getword function: {type(e)}")
        finally:
            self.driver.back()
            # word_data contatin [searched_word_text, (pronounce_text), (meaning_text)]
            return (word_data, parts_of_speech_text_lst, type_dict)

    def search_word(self) -> Tuple[List[str], List[str], Dict[str, bool]]:
        # ouput: ([영단어, 의미], [품사], {'isIdiom': bool, 'isPolysemy': bool, 'isError': bool})
        word_data_lst: List[str] = []

        # enter the word in search box
        search_box = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((By.NAME, "query")))
        search_box.clear()
        search_box.send_keys(self.word)
        search_box.send_keys(Keys.RETURN)

        isPolysemy: bool = True
        i: int = 0
        while (isPolysemy):
            # find words in a result page after searching
            search_page_entry = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "searchPage_entry")))
            searched_word_elems = search_page_entry.find_elements(
                By.CLASS_NAME, "row")

            # check the finding word is a polsemy(word with multiple meanings) or containing a sub-entry
            if (i < len(searched_word_elems)):
                curr_elem_text: str = searched_word_elems[i].text[:searched_word_elems[i].text.find(
                    '\n')]

                for j in range(len(self.word)):
                    # if curr elem text is not equal with self.word
                    if self.word[j] != curr_elem_text[j]:
                        break
                else:  # if curr elem text is equal with self.word
                    # if sup class "num" is existed: curr searched word is polsemy(word with multiple meanings)
                    sup_num = searched_word_elems[i].find_elements(
                        By.TAG_NAME, "sup")

                    isPolysemy = True if ((i < len(sup_num)) and
                                          (sup_num[0].text.strip() != "")) else False

                    curr_xpath: str = "//*[@id= \"searchPage_entry\"]/div/div[" + \
                        str(i + 1) + "]/div[1]/a"

                    curr_elem = WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.XPATH, curr_xpath)))

                    if curr_elem:
                        data = self.get_raw_data(curr_elem, curr_elem_text)
                        data[2]["isPolysemy"] = isPolysemy or i > 0
                        data[2]["isError"] = False
                        word_data_lst.append(data)

                i += 1
            else:
                break

        if len(word_data_lst) == 0:
            raise Exception

        return word_data_lst

    def driver_close(self):
        # self.driver.close() # close this browser
        self.driver.quit()  # close every browser


if __name__ == "__main__":
    ChromeDriver = Crawling()
    input_word_lst = [
        # "intermittently",
        # "put down",
        # "prior to",
        # "pan",
        # "as well as",
        # "rumor",
        # "utilize",
        # "stress out",
        # "briskness",
        # "unlimit",
        # "artifact",
        # "apart from",
        "inquire",
    ]

    for input_word in input_word_lst:
        ChromeDriver.set_word(input_word)
        extracted_word_lst = ChromeDriver.search_word()

        for extracted_word in extracted_word_lst:
            print(extracted_word)
        print()

    ChromeDriver.driver_close()
