from __future__ import annotations

from anki_vocab.word_entry import WordEntry
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional, Set
import html
import re


class Formatter:
    _class_re = re.compile(r"[^a-zA-Z0-9_-]+")

    # Anki tag 매핑(한글 품사 기준)
    tag_dict: Dict[str, str] = {
        "숙어": "Idiom(숙어)",
        "동음이의어": "Homonym(동음이의어)",
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

    def __init__(self, include_variants_in_meaning: bool = True) -> None:
        self.include_variants_in_meaning = include_variants_in_meaning
        self._raw: Dict[str, Any] = {}
        self.word: str = ""

    def set_data(self, data: Dict[str, Any]) -> None:
        self._raw = data or {}
        self.word = str(self._raw.get("word", "") or "").strip()
        if not self.word:
            raise ValueError("Formatter: input JSON에 'word'가 비어 있습니다.")

    def _ensure_ready(self) -> None:
        if not self.word:
            raise RuntimeError("Formatter: set_data()가 호출되지 않았습니다.")

    # util
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
    
    def _safe_class(self, name: str) -> str:
        # class로 쓰기 애매한 문자는 '_'로 치환
        return self._class_re.sub("_", name).strip("_") or "_"

    def _format_node(
        self,
        obj: Any,
        *,
        join_with: str,
        item_wrap_class: Optional[str],
        ol_keys: Set[str],
        ol_item_class: str,
    ) -> str:
        # dict: key를 class로 하는 span (단, ol_keys는 ol로)
        if isinstance(obj, dict):
            parts: List[str] = []
            for k, v in obj.items():
                key_raw = str(k)
                key_cls = html.escape(self._safe_class(key_raw), quote=True)

                # part_of_speech 영문 → 한글 정규화
                if key_raw == "part_of_speech" and isinstance(v, str):
                    v = self._norm_pos_text(v)

                # senses: <ol class="senses"><li class="sense">...</li>...</ol>
                if key_raw in ol_keys and isinstance(v, list):
                    lis: List[str] = []
                    for x in v:
                        inner = self._format_node(
                            x,
                            join_with=join_with,
                            item_wrap_class=item_wrap_class,
                            ol_keys=ol_keys,
                            ol_item_class=ol_item_class,
                        )
                        if inner.strip():
                            li_cls = html.escape(self._safe_class(ol_item_class), quote=True)
                            lis.append(f'<li class="{li_cls}">{inner}</li>')
                    parts.append(f'<ol class="{key_cls}">' + "".join(lis) + "</ol>")
                    continue

                # 기본: <span class="{key}">...</span>
                inner = self._format_node(
                    v,
                    join_with=join_with,
                    item_wrap_class=item_wrap_class,
                    ol_keys=ol_keys,
                    ol_item_class=ol_item_class,
                )
                parts.append(f'<span class="{key_cls}">{inner}</span>')

            return join_with.join([p for p in parts if p])

        # list: 각 원소 렌더 후 join (필요 시 __item 래핑)
        if isinstance(obj, list):
            items: List[str] = []
            for x in obj:
                inner = self._format_node(
                    x,
                    join_with=join_with,
                    item_wrap_class=item_wrap_class,
                    ol_keys=ol_keys,
                    ol_item_class=ol_item_class,
                )
                if not inner.strip():
                    continue

                if item_wrap_class:
                    cls = html.escape(self._safe_class(item_wrap_class), quote=True)
                    items.append(f'<span class="{cls}">{inner}</span>')
                else:
                    items.append(inner)

            return join_with.join(items)

        # scalar
        s = "" if obj is None else str(obj)
        return html.escape(s)
    
    def _norm_pos_text(self, s: str) -> str:
        """
        "Noun" -> "명사"
        "Verb (made, made[meɪd])" -> "동사 (made, made[meɪd])"
        """
        s = (s or "").strip()
        if not s:
            return ""

        # 1) 완전 일치
        if s in self.pos_en_to_ko:
            return self.pos_en_to_ko[s]

        # 2) 접두어 치환 (Verb ( ... ), Noun: ... 등)
        for en, ko in self.pos_en_to_ko.items():
            if s.startswith(en):
                # en 다음이 공백/괄호/구분자/끝이면 POS로 간주
                nxt = s[len(en):len(en) + 1]
                if nxt in ("", " ", "(", ":", "-", "·", "∙"):
                    return ko + s[len(en):]
        return s

    def _pos_head_ko(self, pos_raw: str) -> str:
        """
        part_of_speech에서 '첫 토큰(품사)'만 뽑아 한글로 정규화.
        예)
        "Noun" -> "명사"
        "Verb (made, made[meɪd])" -> "동사"
        "동사" -> "동사"
        """
        s = (pos_raw or "").strip()
        if not s:
            return ""

        head = re.split(r"\s|\(", s, 1)[0].strip()
        return self.pos_en_to_ko.get(head, head)
    
    def pretty_html(self, html_text: str, *, parser: str = "html.parser") -> str:
        """
        HTML을 보기 좋게 들여쓰기/줄바꿈해서 반환.
        주의: prettify()는 self-closing 처리(<br/> 등)나 공백을 일부 바꿀 수 있음.
        """
        soup = BeautifulSoup(html_text, parser)
        return soup.prettify()

    def format_pronunciation(self, join_with: str = "<br>",) -> str:
        prons = self._as_list(self._raw.get("pronunciations"))
        parts: List[str] = []

        for p in prons:
            if not isinstance(p, dict):
                continue
            region = self._as_str(p.get("region_label", "")).strip()
            ipa = self._as_str(p.get("ipa_text", "")).strip()
            ipa = ipa.replace("|", "'") # 강세 표기 변환

            if region and ipa:
                parts.append(f"{region} {ipa}")
            elif ipa:
                parts.append(ipa)
            elif region:
                parts.append(region)

        return join_with.join([x for x in parts if x])

    def format_meaning(
        self,
        *,
        join_with: str = "<br>",
        item_wrap_class: Optional[str] = "__item",
        ol_keys: Set[str] = {"senses"},
        ol_item_class: str = "sense",
    ) -> str:
        """
        meaning은 보통 entries 아래를 렌더링하는 게 자연스러우니,
        기본은 {"entries": self._raw.get("entries", [])} 를 루트로 잡음.
        """
        entries = self._raw.get("entries", [])
        return self._format_node(
            {"entries": entries},
            join_with=join_with,
            item_wrap_class=item_wrap_class,
            ol_keys=ol_keys,
            ol_item_class=ol_item_class,
        )

    def format_tag(self) -> str:
        tags: Set[str] = set()

        # entries의 part_of_speech 기반 품사 태그
        entries = self._as_list(self._raw.get("entries"))

        for e in entries:
            if not isinstance(e, dict):
                continue
            pos_raw = self._as_str(e.get("part_of_speech", "")).strip()
            pos_ko = self._pos_head_ko(pos_raw)

            if pos_ko in self.tag_dict:
                tags.add(self.tag_dict[pos_ko])

        # 숙어(다단어 표현)
        if " " in self.word:
            tags.add(self.tag_dict["숙어"])

        # 접두사(예: anti- 형태) 또는 별도 플래그가 있는 경우
        if self.word.endswith("-") or bool(self._raw.get("is_prefix")):
            tags.add(self.tag_dict["접두사"])

        # 동음이의어(Homonym): crawler entry link가 2개 이상
        entry_links = self._as_list(self._raw.get("entry_links"))
        if len(entry_links) >= 2:
            tags.add(self.tag_dict["동음이의어"])

        # Anki 태그는 공백으로 구분되는 1줄 문자열
        return " ".join(sorted(tags))