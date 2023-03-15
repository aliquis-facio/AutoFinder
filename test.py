import requests
from bs4 import BeautifulSoup

word = input("검색할 단어를 입력하세요: ")

url = f"https://en.dict.naver.com/#/search?query={word}"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# 뜻이 들어 있는 태그와 클래스 정보
meanings = soup.find_all("span", {"class": "mean"})

if meanings:
    print(f"{word}의 뜻:")
    for i, meaning in enumerate(meanings):
        print(f"{i+1}. {meaning.text}")
else:
    print(f"{word}에 대한 검색 결과가 없습니다.")
