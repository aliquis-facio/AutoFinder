from __future__ import annotations

from typing import Any, Dict, List, Tuple
from word_entry import WordEntry


class Formatter:
    # Anki tag 매핑(한글 품사 기준)
    tag_dict: Dict[str, str] = {
        "숙어": "Idiom(숙어)",
        "다의어": "Polysemy(다의어)",
        "접두사": "Prefix(접두사)",
        "명사": "Noun(명사)",
        "대명사": "Pronoun(대명사)",
        "동사": "Verb(동사)",
        "형용사": "Adjective(형용사)",
        "부사": "Adverb(부사)",
        "전치사": "Preposition",
        "접속사": "Conjunction(접속사)",
        "한정사": "Determiner(한정사)",
        "감탄사": "Intergection/Exclamation(감탄사)",
        "수사": "Numeral(수사)",
        "관사": "Article(관사)",
    }

    # Parser 결과에서 part_of_speech가 영문으로 들어오는 케이스 대응
    pos_en_to_ko: Dict[str, str] = {
        "Noun": "명사",
        "Pronoun": "대명사",
        "Verb": "동사",
        "Adjective": "형용사",
        "Adverb": "부사",
        "Preposition": "전치사",
        "Conjunction": "접속사",
        "Determiner": "한정사",
        "Interjection": "감탄사",
        "Exclamation": "감탄사",
        "Numeral": "수사",
        "Article": "관사",
    }

    def __init__(self, data: Dict[str, Any], include_variants_in_meaning: bool = True) -> None:
        self._raw: Dict[str, Any] = data
        self.include_variants_in_meaning = include_variants_in_meaning

        self.word: str = str(data.get("word", "") or "").strip()
        if not self.word:
            raise ValueError("Formatter: input JSON에 'word'가 비어 있습니다.")

    # -------------------------
    # 내부 유틸
    # -------------------------
    def _as_list(self, v: Any) -> List[Any]:
        return v if isinstance(v, list) else []

    def _as_str(self, v: Any) -> str:
        return v if isinstance(v, str) else (str(v) if v is not None else "")

    def _join_br(self, lines: List[str]) -> str:
        cleaned: List[str] = []
        for x in lines:
            s = (x or "").strip()
            if s:
                cleaned.append(s)
        return "<br>".join(cleaned)

    def _norm_pos(self, pos: str) -> str:
        pos = (pos or "").strip()
        if not pos:
            return ""
        return self.pos_en_to_ko.get(pos, pos)

    # -------------------------
    # pronounce
    # -------------------------
    def _format_pronounce(self) -> str:
        prons = self._as_list(self._raw.get("pronunciations"))
        parts: List[str] = []

        for p in prons:
            if not isinstance(p, dict):
                continue
            region = self._as_str(p.get("region_label", "")).strip()
            ipa = self._as_str(p.get("ipa_text", "")).strip()

            if region and ipa:
                parts.append(f"{region} {ipa}")
            elif ipa:
                parts.append(ipa)
            elif region:
                parts.append(region)

        return " / ".join([x for x in parts if x])
