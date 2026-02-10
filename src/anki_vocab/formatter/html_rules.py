from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


# 제거할 key
SKIP_KEYS: Set[str] = {"sense_no"}

# key -> 태그 오버라이드(없으면 span)
TAG_OVERRIDES: Dict[str, str] = {
    "part_of_speech": "p",
    "part_speech": "div",
    "examples": "div",
    "en": "p",
    "ko": "p",
}

# key가 list일 때 ol 구조로 렌더링할 key
OL_KEYS: Set[str] = {"senses"}

# ol의 li class 매핑
OL_ITEM_CLASS: Dict[str, str] = {
    "senses": "sense_item",
}


@dataclass(frozen=True)
class ListRule:
    # mode:
    # - "wrap": 각 item을 (tag, class)로 감싼다
    # - "raw": item wrapper 없이 inner만 concat
    mode: str
    item_tag: str = "span"
    item_class: str = "__item"


# parent_key(list의 부모 key) -> list 처리 규칙
LIST_ITEM_RULES: Dict[str, ListRule] = {
    "entries": ListRule(mode="wrap", item_tag="div", item_class="entry_item"),
    "part_speech": ListRule(mode="wrap", item_tag="span", item_class="part_speech_item"),
    "examples": ListRule(mode="raw"),
}
