# AutoFinder (anki_vocab)
네이버 사전 결과를 크롤링/파싱하여 **Anki 가져오기용 TSV(탭 구분) 파일**을 생성하는 파이프라인 프로젝트입니다.

- 데이터 흐름: `Crawler -> Parser -> Formatter -> FileHandler`
- 출력 필드: `word`, `pronunciation`, `meaning`, `tags`
- **동음이의어**는 `윗첨자 숫자(¹²³ …)`로 구분합니다.

---

## 1) 주요 기능
- **단어 검색 자동화**: Selenium 기반으로 네이버 사전(또는 해당 검색 페이지) 결과 HTML을 수집
- **구조화 파싱**: 수집한 HTML을 JSON 형태로 정규화(단어/발음/의미/품사 등)
- **Anki 친화 포맷팅**
  - 발음/의미/태그를 Anki 필드에 넣기 좋은 형태로 변환
  - 의미(meaning)는 HTML 형태로 정리(Anki에서 “HTML 허용” 권장)
  - 한글 품사 기반 **Anki Tag 매핑**(예: `명사 -> Noun(명사)` 등)
- **TSV 파일 생성**: 최종 결과물을 **탭(\t) 구분 텍스트**로 저장하여 Anki에서 바로 Import 가능

---

## 2) 전체 파이프라인 개요
아래 테스트 함수 형태의 흐름을 표준 파이프라인으로 확장합니다.

1. **Crawler**
   - 입력 단어로 검색 페이지 접근
   - 결과(동음이의어/표제어 변형 등)별 HTML 수집

2. **Parser**
   - HTML에서 필요한 정보(발음/의미/품사/동음이의어 구분 등)를 추출
   - `parse_to_json(word)` 형태로 표준 JSON 반환

3. **Formatter**
   - JSON을 Anki 카드 필드에 맞게 가공
   - `format_pronunciation()`, `format_meaning()`, `format_tag()` 등 제공
   - (정책) **pos에서 불규칙 활용 추출은 하지 않음**

4. **FileHandler**
   - 여러 결과물을 모아 TSV로 저장
   - 컬럼: `word`, `pronunciation`, `meaning`, `tags`

---

## 3) 프로젝트 구조

```text
.  
├─ README.md  
├─ .gitignore  
├─ pyproject.toml              # (권장) 없으면 requirements.txt로 시작해도 됨  
├─ pytest.ini                  # tests/가 아니라 루트로 이동 권장  
├─ src/  
│  └─ anki_vocab/              # 패키지명(원하는 이름으로 변경 가능)  
│     ├─ __init__.py  
│     ├─ crawler.py  
│     ├─ parser.py  
│     ├─ formatter.py  
│     ├─ file_handler.py  
│     ├─ tui.py                # CLI/TUI 진입점이면 cli.py로 바꿔도 좋음  
│     └─ word_entry.py  
└─ tests/  
   ├─ conftest.py              # 공용 fixture, 헬퍼  
   ├─ fixtures/  
   │  └─ html/  
   │     └─ naver/             # 크롤링 결과 HTML 샘플 보관  
   ├─ expected/  
   │  ├─ parser/               # parser 기대 JSON  
   │  └─ formatter/            # formatter 기대 출력(텍스트/CSV 등)  
   ├─ unit/  
   │  ├─ test_parser.py  
   │  └─ test_formatter.py  
   └─ integration/  
      └─ test_crawler.py       # selenium/네트워크 의존  
```

---

## 4) 설치 및 실행 환경

### 필수

* Python 3.11+ 권장
* Google Chrome (Selenium 구동)
* ChromeDriver는 `webdriver_manager` 사용을 권장(자동 매칭)

### 의존성(대표)

* `selenium`
* `webdriver-manager`
* `beautifulsoup4`
* `pytest` (테스트용)

예시 설치:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 5) 사용 방법(Quick Start)

### 5.1 단어 리스트 준비

예:

```python
input_words = ["enquire", "make", "work", "water", "pace", "bark", "bat", "row"]
```

### 5.2 실행 예시(main.py)

아래는 권장 실행 흐름(개념 예시)입니다. 실제 클래스/메서드 시그니처는 프로젝트 코드에 맞게 조정하세요.

```python
from anki_vocab.crawler import Crawler
from anki_vocab.parser import Parser
from anki_vocab.formatter import Formatter
from anki_vocab.file_handler import FileHandler

def run(words: list[str], out_path: str) -> None:
    crawler = Crawler()
    parser = Parser()
    formatter = Formatter()
    writer = FileHandler(out_path)

    try:
        for word in words:
            htmls = crawler.search_from_naver(word)

            for html in htmls:
                parser.set_html(html)
                data = parser.parse_to_json(word)

                formatter.set_data(data)

                row = {
                    "word": formatter.format_word(),                  # 동음이의어면 윗첨자 포함
                    "pronunciation": formatter.format_pronunciation(),
                    "meaning": formatter.format_meaning(),            # HTML 문자열
                    "tags": formatter.format_tag(),                   # 공백 구분 태그 문자열 등
                }
                writer.append(row)

        writer.flush()
    finally:
        crawler.driver_close()

if __name__ == "__main__":
    run(
        words=["enquire", "make", "work"],
        out_path="output/anki_vocab.tsv"
    )
```

---

## 6) 출력 포맷(TSV)

* **탭(\t) 구분**
* 필드 순서: `word`, `pronunciation`, `meaning`, `tags`

예시(가독성을 위해 `\t`를 표기):

```text
enquire\t/ɪnˈkwaɪə(r)/\t<div>...</div>\tVerb(동사)
row²\t/roʊ/\t<div>...</div>\tNoun(명사)
```

### 동음이의어 표기 규칙

* 동일 표제어의 다중 엔트리는 `word¹`, `word²` … 형태로 출력
* Anki에서 “서로 다른 카드”로 인식되도록 **단어 필드 자체에 윗첨자**를 포함시키는 방식을 기본으로 합니다.

---

## 7) Anki Import 가이드

1. Anki에서 새 노트 타입(또는 기존 노트 타입)에 필드 4개 생성

   * `word`
   * `pronunciation`
   * `meaning`
   * `tags`
2. 가져오기(Import) 시 옵션

   * 구분자: **Tab**
   * “HTML 허용(Allow HTML)” 활성화 권장 (`meaning`에 HTML이 들어갈 수 있음)
3. 태그 적용

   * `tags` 필드를 “태그로 처리”하거나, 카드 템플릿에서 별도 표시하도록 선택

---

## 8) 테스트

pytest 기반 단위 테스트를 권장합니다.

```bash
pytest -q
```

테스트 포인트 예시:

* `Formatter`의 태그 매핑/HTML 정리/동음이의어 윗첨자 처리
* `Parser`의 특정 HTML 케이스(동음이의어/품사/발음 누락/다의어)
* `Crawler`의 입력 검증 및 예외 처리(빈 문자열, 공백, 특수문자 등)

---

## 9) 주의사항 및 제한

* 크롤링은 대상 사이트의 정책/로봇 배제 표준/서비스 약관을 준수해야 합니다.
* HTML 구조 변경 시 Parser가 깨질 수 있습니다. (변경에 강한 파싱 로직/회귀 테스트 권장)
* 과도한 요청은 차단/캡차/법적 이슈로 이어질 수 있으니 **요청 빈도 제한(딜레이/캐싱)**을 권장합니다.

---

## 10) 로드맵

* [ ] CLI 지원 (`--input words.txt --out output.tsv`)
* [ ] 캐시(동일 단어 재조회 방지)
* [ ] 재시도/백오프 및 네트워크/캡차 예외 처리
* [ ] 의미 정리 템플릿 고도화(예문/동의어/반의어 선택 출력)
* [ ] Anki 노트 타입/필드 자동 체크(가이드 문서 강화)
* [ ] 사용자가 둘 이상이면? -> 스레드 적용?
* [ ] 다른 필드 구조를 사용한다면?
* [ ] 불규칙 변화(go, child)는 본래 형태를 고를 수 있도록
* [ ] 다른 사전을 이용하고 싶다면?

---

## 11) 라이선스 / 디스클레이머

본 프로젝트는 학습 및 개인 생산성 목적의 자동화를 목표로 합니다. 데이터 출처의 권리 및 이용 조건을 확인하고 준수하세요.

<!-- selenium 같은 크롤러를 코딩할 때는 봇으로 동작하는 크롬이랑 내가 만지는 크롬이랑 페이지 화면이 다를 수 있으니까 꼭 확인하면서 코딩하기!!! -->