from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException, TimeoutException, ElementClickInterceptedException
from time import sleep


class AutomaticSearch:
    DRIVER_PATH = 'C:\\Users\\jeony\\OneDrive\\바탕 화면\\Python\\Anki_proj\\chromedriver.exe'

    def __init__(self) -> None:
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('headless')
        self.driver = webdriver.Chrome(self.DRIVER_PATH, options=self.options)
        self.word = ''
        self.wait_time = 2  # sec

    def set_word(self, word):
        self.word = word

    def get_word(self):
        try:
            self.driver.get(url='https://en.dict.naver.com/#/main')

            search_box = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, 'query')))
            search_box.send_keys(self.word)
            search_box.send_keys(Keys.RETURN)

            objs = WebDriverWait(self.driver, self.wait_time).until(EC.presence_of_all_elements_located(
                (By.XPATH, '/html/body/div[2]/div[2]/div[1]/div[3]/div/div[1]/div[1]/a/strong')))
            objs[0].click()

            pronounce_area = WebDriverWait(self.driver, self.wait_time).until(EC.presence_of_all_elements_located(
                (By.CLASS_NAME, 'entry_pronounce')))
            pronounce = pronounce_area[0].text

            mean_area = WebDriverWait(self.driver, self.wait_time).until(EC.presence_of_all_elements_located(
                (By.CLASS_NAME, 'mean_tray')))
            meaning = mean_area[0].text

            example_sentence_area = WebDriverWait(self.driver, self.wait_time).until(EC.presence_of_all_elements_located(
                (By.XPATH, '//*[@id="searchPage_example"]/div/div[1]')))
            example_sentence = example_sentence_area[0].text

            lst = [self.word, pronounce, meaning, example_sentence]
            return lst

        except Exception as e:
            print(f'{self.word} -> {type(e)}')
            return self.word

        finally:
            sleep(2)
            self.driver.close()


if __name__ == '__main__':
    input_word = 'photocopier'
    ChromeDriver = AutomaticSearch()
    ChromeDriver.set_word(input_word)
    word_lst = ChromeDriver.get_word()
    print(word_lst)
