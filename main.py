import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from finder import get_answer, get_link

load_dotenv()

url = os.getenv("URL")
PATH = os.getenv("PATH")
login = os.getenv("LOGIN")
password = os.getenv("PASSWORD")


def start_new(driver):
    element = WebDriverWait(driver=driver, timeout=10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "dijitButtonContents")))
    element.click()
    start_button = WebDriverWait(driver=driver, timeout=5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "extraSpace")))
    start_button.click()
    first_question = WebDriverWait(driver=driver, timeout=5).until(
        EC.presence_of_element_located(
            (By.XPATH, "span[@text()='Перейти к первому вопросу']")))
    first_question.click()


def continue_old(driver):
    original_window = driver.current_window_handle
    arrow = WebDriverWait(driver=driver, timeout=3).until(
        EC.presence_of_element_located((By.CLASS_NAME,
                                        "fa-arrow-circle-right")))
    arrow.click()
    for window_handle in driver.window_handles:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break


def auth(driver):
    email_input = driver.find_element("id", "username")
    email_input.clear()
    email_input.send_keys(login)
    password_input = driver.find_element("id", "password")
    password_input.clear()
    password_input.send_keys(password)


def find_question(driver):
    question = WebDriverWait(driver=driver, timeout=7).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "p")))
    return question


def find_answer(driver, right_ans):
    driver.find_element(By.XPATH, 
                        f'//p[contains(text(), "{right_ans}")]/ancestor::tr/td[@class="options  xforms-enabled"]'
                        ).click()


try:
    driver = webdriver.Chrome(PATH)
    driver.get(url=url)
    auth(driver)
    time.sleep(2)
    login_button = driver.find_element(By.CLASS_NAME, "login-button").click()
    command = input()
    if command == 'new':
        start_new(driver)
    elif command == 'continue':
        continue_old(driver)
    for i in range(80):
        data = find_question(driver)
        data = [d.text for d in data]
        link = get_link(data[0])
        right_ans = get_answer(link)
        print(right_ans)
        print(data)
        if right_ans in data:
            find_answer(driver, right_ans)
            driver.find_element(By.XPATH, '//span[text()="Далее"]').click()
        else:
            driver.find_element(By.XPATH, '//span[text()="Далее"]').click()
        time.sleep(2)

    time.sleep(10)
except Exception as ex:
    print(ex)
finally:
    driver.close()
    driver.quit()
