import requests
from bs4 import BeautifulSoup


def find_question(url):
    response = requests.get(url=url)
    soup = BeautifulSoup(response.text, 'html.parser')
    print(soup.prettify())


if __name__ == '__main__':
    find_question()
