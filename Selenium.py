from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
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
        self.word = ""

        try:
            # driver's options
            self.driver_options = Options()
            self.driver_options.add_experimental_option(
                "excludeSwitches", ["enable-logging"])
            # self.driver_options.add_argument("headless")
            self.wait_time = 5  # sec

            # initialize the lastest driver
            self.driver = webdriver.Chrome(service=Service(
                ChromeDriverManager().install()), options=self.driver_options)
            self.driver.implicitly_wait(self.wait_time)

            # set intial page
            self.driver.get(url="https://en.dict.naver.com/#/main")
        except SessionNotCreatedException:
            print(
                f'Chrome version may not be the latest version. Please update Chrome and try again.')
            print(type(SessionNotCreatedException))

    def set_word(self, word):
        self.word = word

    def get_word(self, searched_word_elem):
        my_ignored_exceptions = (StaleElementReferenceException)
        WebDriverWait(self.driver, self.wait_time, ignored_exceptions=my_ignored_exceptions).until(
            EC.element_to_be_clickable(searched_word_elem)).click()
        sleep(2)
        self.driver.back()

    def test(self):
        # enter the word in search box
        search_box = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((By.NAME, "query")))
        search_box.clear()
        search_box.send_keys(self.word)
        search_box.send_keys(Keys.RETURN)

        isPolsemy = True
        i = 0
        while(isPolsemy):
            # find words in a result page after searching
            search_page_entry = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "searchPage_entry")))
            searched_word_elems = search_page_entry.find_elements(
                By.CLASS_NAME, "row")

            if (len(searched_word_elems) > i):
                curr_elem_text = searched_word_elems[i].text[:searched_word_elems[i].text.find(
                    '\n')]

                for j in range(len(self.word)):
                    if self.word[j] != curr_elem_text[j]:
                        break
                else:
                    sup_num = searched_word_elems[i].find_elements(
                        By.TAG_NAME, "sup")

                    isPolsemy = True if (len(sup_num) > 0) and (
                        sup_num[0].text.strip() != "") else False

                    curr_xpath = "//*[@id= \"searchPage_entry\"]/div/div[" + \
                        str(i + 1) + "]/div[1]/a"
                    print(f"xpath: {curr_xpath}")
                    curr_elem = WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.XPATH, curr_xpath)))
                    if curr_elem:
                        print(f"if current element exist: {curr_elem}")
                        self.get_word(curr_elem)
                i += 1
            else:
                break

    def search_word(self):
        try:
            # enter the word in search box
            search_box = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, "query")))
            search_box.clear()
            search_box.send_keys(self.word)
            search_box.send_keys(Keys.RETURN)

            # find words in a result page after searching
            search_page_entry = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, "searchPage_entry")))
            searched_word_elems = search_page_entry.find_elements(
                By.CLASS_NAME, "row")

            # check the finding word is a polsemy(word with multiple meanings) or containing a sub-entry
            # if sup class "num" is existed: polsemy(word with multiple meanings)
            isPolsemy = None
            for i, searched_word_elem in enumerate(searched_word_elems):
                curr_elem_text = searched_word_elem.text[:searched_word_elem.text.find(
                    '\n')]
                print(f"current element's text: {curr_elem_text}")

                for j in range(len(self.word)):
                    if self.word[j] != curr_elem_text[j]:
                        break
                else:  # curr elem(word) is same start spelled with searched word(sub entry is not cared)
                    sup_num = searched_word_elem.find_elements(
                        By.TAG_NAME, "sup")

                    if (len(sup_num) > 0) and (sup_num[0].text.strip() != ""):
                        # curr elem(word) is polsemy(word with multiple meanings)
                        isPolsemy = True
                        curr_xpath = "//*[@id= \"searchPage_entry\"]/div/div[" + \
                            str(i + 1) + "]/div[1]/a"
                        print(f"sup num: {sup_num[0].text.strip()}")
                        print(f"xpath: {curr_xpath}")
                    else:
                        isPolsemy = False
                        curr_xpath = "//*[@id= \"searchPage_entry\"]/div/div[1]/div[1]/a"
                        print(f"xpath: {curr_xpath}")

                    curr_elem = WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.XPATH, curr_xpath)))

                    if curr_elem:
                        print(f"if current element exist: {curr_elem}")
                        self.get_word(curr_elem)

                    if not isPolsemy:
                        break

            pronounce = ""
            meaning = ""
            example_sentence = ""
            lst = [self.word, pronounce, meaning, example_sentence]

            return lst

        except Exception as e:
            print(
                f"occured error in \'{self.word}: {curr_elem_text}\': {type(e)}")
            return self.word

        finally:
            sleep(2)

    def driver_close(self):
        # self.driver.close() # close this browser
        self.driver.quit()  # close every browser


if __name__ == "__main__":
    ChromeDriver = Crawling()

    input_word = "row"
    ChromeDriver.set_word(input_word)
    # word_lst = ChromeDriver.search_word()
    ChromeDriver.test()

    # input_word = "center"
    # ChromeDriver.set_word(input_word)
    # word_lst = ChromeDriver.search_word()
    # print(word_lst)

    ChromeDriver.driver_close()
