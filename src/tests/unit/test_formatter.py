from anki_vocab.crawler import Crawler
from anki_vocab.parser import Parser
from anki_vocab.formatter import Formatter


def test_tag_mapping_basic():
    f = Formatter()
    assert f.tag_dict["명사"] == "Noun(명사)"
    assert f.tag_dict["동사"] == "Verb(동사)"

def test_tag_mapping_unknown_pos():
    f = Formatter()
    # 구현 정책 추천:
    # - unknown 품사는 "Other"로 보내거나
    # - 태그를 붙이지 않고 넘어가거나
    # 여기서는 “KeyError 나지 않게”를 목표로 예시 작성
    pos = "미정품사"
    tag = f.tag_dict.get(pos)
    assert tag is None
