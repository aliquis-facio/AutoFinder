# anki_vocab/dict_parser/models.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class PronItem(TypedDict, total=False):
    region_label: str
    ipa_text: str


class ParsedWord(TypedDict, total=False):
    word: str
    pronunciations: List[PronItem]
    conjugations: Dict[str, Any]          # 너가 쓰던 {"conjugation": [...]} 형태 유지
    entries: List[Dict[str, Any]]
    images: List[str]
    meta: Dict[str, Any]
    entry_links: List[str]               # Formatter.format_tag() 대비(선택)
