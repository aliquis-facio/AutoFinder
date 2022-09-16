from selenium import webdriver

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import InvalidSessionIdException, TimeoutException, ElementClickInterceptedException
from time import sleep

URL = 'https://en.dict.naver.com/#/main'
options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Chrome(
    ChromeDriverManager().install(), options=options)

try:
    driver.get(url=URL)

    # element = WebDriverWait(driver, 5).until(
    #     EC.presence_of_element_located((By.NAME, 'query'))
    # )

    elem = driver.find_element('name', 'query')
    elem.send_keys('water')
    elem.send_keys(Keys.RETURN)
finally:
    driver.quit()
