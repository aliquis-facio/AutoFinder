# tests/test_parser_unit.py
import json
from pathlib import Path
from anki_vocab.parser import Parser


FIXTURE_DIR = Path("tests/fixtures/naver")
EXPECTED_DIR = Path("tests/expected")

def load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def test_norm_ipa_basic():
    # private 메서드라도 “정규화 규칙”은 회귀가 중요하니 고정 테스트 권장
    p = Parser("<html></html>")
    assert p._norm_ipa("[ ɪnˈkwaɪə(r) ]") == "[ɪnˈkwaɪə(r)]"

def test_parse_enquire_snapshot():
    html = load_text(FIXTURE_DIR / "enquire_0.html")
    data = Parser(html).parse_to_json("enquire")

    # 1) 스키마 최소 검증
    assert isinstance(data, dict)

    # 2) 스냅샷(골든 파일) 비교: 파서 결과가 바뀌면 이 테스트가 잡아줌
    expected = load_json(EXPECTED_DIR / "enquire_0.json")
    assert data == expected

def test_parse_lead_has_multiple_entries():
    html = load_text(FIXTURE_DIR / "lead_0.html")
    data = Parser(html).parse_to_json("lead")

    # 아래 키 이름은 실제 스키마에 맞춰 조정
    entries = data.get("entries") or data.get("senses") or data.get("meanings") or []
    assert isinstance(entries, list)
    assert len(entries) >= 1
