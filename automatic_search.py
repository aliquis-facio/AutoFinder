from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException, TimeoutException, ElementClickInterceptedException
from time import sleep


class AutomaticSearch:
    def __init__(self) -> None:
        self.options = webdriver.ChromeOptions()
        self.options.add_experimental_option(
            "excludeSwitches", ["enable-logging"])
        # self.options.add_argument('headless')
        self.wait_time = 3  # sec

        self.word = ''

        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(), options=self.options)
        self.driver.implicitly_wait(3)

        self.driver.get(url='https://en.dict.naver.com/#/main')

    def set_word(self, word):
        self.word = word

    def get_word(self):
        try:
            # 검색창에 영단어 입력
            search_box = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, 'query')))
            search_box.send_keys(self.word)
            search_box.send_keys(Keys.RETURN)

            # 검색 후 결과창에 있는 영단어들
            search_page_entry = self.driver.find_element(
                By.ID, 'searchPage_entry')
            display_words = search_page_entry.find_elements(
                By.CLASS_NAME, 'row')

            # 이 단어가 다의어인지 확인할 것
            # sup class 'num'이 존재하는 경우: 다의어
            # 다의어인 경우,
            # 하나씩 접속해서 단어의 한글 뜻 text를 챙기고 이전 페이지로 돌아가야 함.
            # pronounce, mean, example sentence
            for display_word in display_words:
                obj = display_word.find_element(By.TAG_NAME, 'strong')
                obj_text = display_word.text
                print(obj_text)
                print(obj)

            pronounce = ''
            meaning = ''
            example_sentence = ''
            lst = [self.word, pronounce, meaning, example_sentence]
            return lst

        except Exception as e:
            print(f'{self.word} -> {type(e)}')
            return self.word

        finally:
            sleep(2)
            self.driver.close()


if __name__ == '__main__':
    input_word = 'row'
    ChromeDriver = AutomaticSearch()
    ChromeDriver.set_word(input_word)
    word_lst = ChromeDriver.get_word()
    print(word_lst)
