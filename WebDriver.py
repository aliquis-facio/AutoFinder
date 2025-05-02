# -*- coding: utf-8 -*-

import time
import os
from typing import List, Dict, Set, Any
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup as bs

# --- Crawling Class ---
class Crawling:
    def __init__(self) -> None:
        self.word: str = ""
        self.driver_options = Options()
        self.driver_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.driver_options.add_argument("headless")
        self.wait_time: int = 5

        self.driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), options=self.driver_options)
        self.driver.implicitly_wait(self.wait_time)
        self.driver.get(url="https://en.dict.naver.com/#/main")

    def set_word(self, word: str) -> None:
        self.word = word.lower()

    def get_raw_data(self, searched_word_elem, searched_word_text: str) -> Dict[str, Any]:
        data = {
            "word": searched_word_text,
            "pronounce": "",
            "meaning": "",
            "parts_of_speech": [],
            "is_idiom": " " in searched_word_text.strip(),
            "is_polysemy": False,
            "is_error": True
        }
        try:
            WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable(searched_word_elem)).click()

            if not data["is_idiom"]:
                try:
                    pronounce_elem = WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "pronounce_area")))
                    data["pronounce"] = pronounce_elem.text
                except TimeoutException:
                    data["pronounce"] = ""

            meaning_elem = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.CLASS_NAME, "mean_tray")))
            data["meaning"] = meaning_elem.text

            parts_of_speech_elem = self.driver.find_elements(By.CLASS_NAME, "part_speech")
            for elem in parts_of_speech_elem:
                data["parts_of_speech"].extend([t.strip() for t in elem.text.split(",")])

            data["is_error"] = False
        except Exception as e:
            print(f"[ERROR] get_raw_data(): {type(e)} - {e}")
        finally:
            self.driver.back()
            return data

    def search_word(self) -> List[Dict[str, Any]]:
        word_data_list: List[Dict[str, Any]] = []

        search_box = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((By.NAME, "query")))
        search_box.clear()
        search_box.send_keys(self.word)
        search_box.send_keys(Keys.RETURN)

        i = 0
        while True:
            try:
                search_page_entry = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.ID, "searchPage_entry")))
                searched_word_elems = search_page_entry.find_elements(By.CLASS_NAME, "row")

                if i >= len(searched_word_elems):
                    break

                curr_elem = searched_word_elems[i].find_element(By.TAG_NAME, 'a')
                curr_text = curr_elem.text

                sup_num = searched_word_elems[i].find_elements(By.TAG_NAME, "sup")
                is_polysemy = len(sup_num) > 0 and sup_num[0].text.strip() != ""

                xpath = f"//*[@id='searchPage_entry']/div/div[{i + 1}]/div[1]/a"
                elem = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.XPATH, xpath)))

                data = self.get_raw_data(elem, curr_text)
                data["is_polysemy"] = is_polysemy or i > 0
                word_data_list.append(data)

                i += 1
            except Exception:
                break

        if not word_data_list:
            raise Exception("No word data found")

        return word_data_list

    def driver_close(self):
        self.driver.quit()


if __name__ == "__main__":
    ChromeDriver = Crawling()
    input_word_lst = [
        "rumor",
    ]

    for input_word in input_word_lst:
        ChromeDriver.set_word(input_word)
        extracted_word_lst = ChromeDriver.search_word()

        for extracted_word in extracted_word_lst:
            print(extracted_word)
        print()

    ChromeDriver.driver_close()
