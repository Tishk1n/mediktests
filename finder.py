import re

import requests
from bs4 import BeautifulSoup

test = 'крушины'


def get_link(question):
    try:
        params = {"q": question + " site:tests-exam.ru"}
        session = requests.Session()
        session.headers.update({'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"})
        url = 'https://www.google.com/search'
        response = session.get(url=url, params=params)
        soup = BeautifulSoup(response.text, 'html.parser')
        url = []
        link = soup.find('a',
                         attrs={'href':
                                re.compile("https://www.tests-exam.ru")})

        link = str(link['href']).replace(
            "/url?q=", "").replace(
            "%3D", "=").replace(
            "%3F", "?").replace(
            "%26", "&")
        return link
    except Exception as ex:
        print(ex)
        # with open('test.txt', 'a', encoding='utf-8') as file:
        #     print(soup.prettify, file=file)
        print("Результат поиска не найден, надо чинить:(")
        print(response.status_code)
        return None


def get_answer(link):
    try:
        response = requests.get(url=link)
        soup = BeautifulSoup(response.text, "html.parser")
        ans = soup.find(id='prav_id')
        return ans.get_text()
    except Exception as ex:
        print(ex)
        print("Ответ на странице не найден, надо чинить:(")
        return None


if __name__ == '__main__':
    while True:
        test = input()
        url = get_link(test)
        print(get_answer(url))
