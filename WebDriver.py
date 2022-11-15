from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from typing import List
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
            # self.driver_options.add_argument("headless")
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
        self.word = word

    def get_word(self, searched_word_elem, searched_word_text: str) -> List[str]:
        WebDriverWait(self.driver, self.wait_time).until(
            EC.element_to_be_clickable(searched_word_elem)).click()

        try:  # can't extract meaning of idiom
            pronounce_elem = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pronounce_area")))
            pronounce_text: str = pronounce_elem.text

            meaning_elem = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.CLASS_NAME, "mean_tray")))
            meaning_text: str = meaning_elem.text

            word_data: List[str] = [searched_word_text,
                                    pronounce_text, meaning_text]

            return word_data
        except:
            return [searched_word_text]
        finally:
            self.driver.back()

    def search_word(self) -> List[str]:
        word_data_lst: List[str] = []

        # enter the word in search box
        search_box = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((By.NAME, "query")))
        search_box.clear()
        search_box.send_keys(self.word)
        search_box.send_keys(Keys.RETURN)

        try:
            isPolsemy: bool = True
            i: int = 0
            while(isPolsemy):
                # find words in a result page after searching
                search_page_entry = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.ID, "searchPage_entry")))
                searched_word_elems = search_page_entry.find_elements(
                    By.CLASS_NAME, "row")

                # check the finding word is a polsemy(word with multiple meanings) or containing a sub-entry
                if (len(searched_word_elems) > i):
                    curr_elem_text: str = searched_word_elems[i].text[:searched_word_elems[i].text.find(
                        '\n')]

                    for j in range(len(self.word)):
                        # self.word is not equal curr_elem_text
                        if self.word[j] != curr_elem_text[j]:
                            break
                    else:
                        # if sup class "num" is existed: polsemy(word with multiple meanings)
                        sup_num = searched_word_elems[i].find_elements(
                            By.TAG_NAME, "sup")

                        isPolsemy = True if (len(sup_num) > 0) and (
                            sup_num[0].text.strip() != "") else False

                        curr_xpath: str = "//*[@id= \"searchPage_entry\"]/div/div[" + \
                            str(i + 1) + "]/div[1]/a"

                        curr_elem = WebDriverWait(self.driver, self.wait_time).until(
                            EC.presence_of_element_located((By.XPATH, curr_xpath)))

                        if curr_elem:
                            word_data_lst.append(
                                self.get_word(curr_elem, curr_elem_text))

                    i += 1
                else:
                    break

            return word_data_lst

        except Exception as e:
            print(
                f"occured error in \'{self.word}\': {type(e)}")
            return [self.word]

    def driver_close(self):
        # self.driver.close() # close this browser
        self.driver.quit()  # close every browser


if __name__ == "__main__":
    # pororo 같이 검색어는 나오지만, pororo 단독으로 있지 않은 경우, 리스트가 공란으로 나옴.
    # adsjfdakfj와 같이 검색이 안되는 경우, 오류가 발생하고, 단어를 리스트로 반환함.
    ChromeDriver = Crawling()
    input_word_lst = ["row", "center", "vow", "in order to",
                      "curb", "pororo", "adsjaljdfh"]
    input_word_lst = ["in order to"]
    for input_word in input_word_lst:
        ChromeDriver.set_word(input_word)
        extracted_word_lst = ChromeDriver.search_word()
        for extracted_word in extracted_word_lst:
            if type(extracted_word) == list:
                for text in extracted_word:
                    print(text)
            else:
                print(extracted_word)
            print()

    ChromeDriver.driver_close()
