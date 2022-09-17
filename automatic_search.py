from re import search
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
        self.word = ''

        self.options = webdriver.ChromeOptions()
        self.options.add_experimental_option(
            "excludeSwitches", ["enable-logging"])
        # self.options.add_argument('headless')
        self.wait_time = 5  # sec

        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(), options=self.options)
        self.driver.implicitly_wait(3)

        self.driver.get(url='https://en.dict.naver.com/#/main')

    def set_word(self, word):
        self.word = word

    def text_extract(self, web_element):
        # pronoce, meaning, example sentence의 text를 추출한다. + word class(품사)
        word_class = []
        pronounce = ''
        meaning = ''
        ex_sentence = ''
        pass

    def get_word(self):
        try:
            # 검색창에 영단어 입력
            search_box = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, 'query')))
            search_box.send_keys(self.word)
            search_box.send_keys(Keys.RETURN)

            # 검색 후 결과창에 있는 영단어들
            search_page_entry = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.ID, 'searchPage_entry')))
            display_words = search_page_entry.find_elements(
                By.CLASS_NAME, 'row')

            # sup class 'num'이 존재하는 경우: 다의어
            # 다의어인 경우,
            # 하나씩 접속해서 단어의 한글 뜻 text를 챙기고 이전 페이지로 돌아가야 함.
            for display_word in display_words:
                # display_word가 검색한 단어인지 확인하기
                # center (centre) 또는 a (an)과 같은 경우에는 어떻게 할 것인가?
                # -> () 안에 들어오는 단어가 검색한 단어의 부표제어인지 확인하면 된다 -> 굳이 부표제어인지 확인하지 않아도 self.word의 단어 길이까지 display_word가 같다면 통과할 수 있게끔 하자.
                obj = WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'strong')))
                obj_text = display_word.text
                obj_text = obj_text[:obj_text.find('\n')]

                for i in range(len(self.word)):
                    if self.word[i] != obj_text[i]:
                        break
                else:
                    # 22.09.17 click 부분부터 진행
                    WebDriverWait(self.driver, self.wait_time).until(
                        EC.element_to_be_clickable(obj)).click()
                    # self.text_extract(obj)
                    print(obj_text)
                # 검색한 단어가 다의어인지 확인하기
                # 다의어가 아닐 경우에는 첫 번째 단어만 확인하면 되지 않을까?
                # print(obj_text)

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
    input_word = 'center'
    ChromeDriver = AutomaticSearch()
    ChromeDriver.set_word(input_word)
    word_lst = ChromeDriver.get_word()
    print(word_lst)
