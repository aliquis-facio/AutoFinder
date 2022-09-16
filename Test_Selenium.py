# import selenium
from selenium import webdriver
from selenium.webdriver import ActionChains

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

URL = 'https://en.dict.naver.com/#/main'

driver = webdriver.Chrome(executable_path='C:\\Users\\jeony\\OneDrive\\바탕 화면\\Python\\Anki_proj\\chromedriver')  # Windows

try:
    element = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'gLFyf'))
    )

    elem = driver.find_element_by_name('query')
    elem.send_keys('water')
    elem.send_keys(Keys.RETURN)
finally:
    driver.quit()
