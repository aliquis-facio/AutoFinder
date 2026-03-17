from __future__ import annotations

from bs4 import BeautifulSoup
from typing import Any, Dict, List, Mapping, Set, Tuple
import html, re

from .html_renderer import HtmlRenderer


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

    _SUPERSCRIPT_DIGITS = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    }

    def __init__(self, include_variants_in_meaning: bool = True) -> None:
        self.include_variants_in_meaning = include_variants_in_meaning
        self._raw: Dict[str, Any] = {}
        self.word: str = ""

        # renderer 주입(규칙은 renderer/rules 쪽에서 관리)
        self._renderer = HtmlRenderer(
            safe_class=self._safe_class,
            norm_value=self._norm_value_for_render,
            join_with="",
        )

    # -------------------------
    # setter / guard
    # -------------------------
    def set_data(self, data: Mapping[str, Any]) -> None:
        self._raw = dict(data)
        self.word = str(self._raw.get("word", "") or "").strip()
        if not self.word:
            raise ValueError("Formatter: input JSON에 'word'가 비어 있습니다.")

    def _ensure_ready(self) -> None:
        if not self.word:
            raise RuntimeError("Formatter: set_data()가 호출되지 않았습니다.")

    # -------------------------
    # util
    # -------------------------
    def _as_list(self, v: Any) -> List[Any]:
        return v if isinstance(v, list) else []

    def _as_str(self, v: Any) -> str:
        return v if isinstance(v, str) else (str(v) if v is not None else "")

    def _safe_class(self, name: str) -> str:
        return self._class_re.sub("_", name).strip("_") or "_"

    def pretty_html(self, html_text: str, *, parser: str = "html.parser") -> str:
        soup = BeautifulSoup(html_text, parser)
        return soup.prettify()

    def _to_superscript(self, n: int) -> str:
        if n <= 0:
            return ""
        return "".join(self._SUPERSCRIPT_DIGITS[ch] for ch in str(n))
    
    def _assert_tsv_safe(self, field_name: str, s: str) -> str:
        if s is None:
            s = ""
        if "\t" in s:
            raise ValueError(f"[Formatter export] '{field_name}' contains TAB (\\t).")
        if "\n" in s or "\r" in s:
            raise ValueError(f"[Formatter export] '{field_name}' contains NEWLINE (\\n/\\r). "
                             f"Use <br> instead of real newlines.")
        return s
    
    # -------------------------
    # POS normalize
    # -------------------------
    def _norm_pos_text(self, s: str) -> str:
        s = (s or "").strip()
        if not s:
            return ""

        if s in self.pos_en_to_ko:
            return self.pos_en_to_ko[s]

        for en, ko in self.pos_en_to_ko.items():
            if s.startswith(en):
                nxt = s[len(en):len(en) + 1]
                if nxt in ("", " ", "(", ":", "-", "·", "∙"):
                    return ko + s[len(en):]
        return s

    def _pos_head_ko(self, pos_raw: str) -> str:
        s = (pos_raw or "").strip()
        if not s:
            return ""
        head = re.split(r"\s|\(", s, 1)[0].strip()
        return self.pos_en_to_ko.get(head, head)

    def _norm_value_for_render(self, key: str, value: Any) -> Any:
        # renderer가 key별 값 변환을 요청할 때 사용하는 훅
        if key == "part_of_speech" and isinstance(value, str):
            return self._norm_pos_text(value)
        return value

    # -------------------------
    # pronunciation
    # -------------------------
    def format_pronunciation(self, join_with: str = "<br>") -> str:
        self._ensure_ready()
        prons = self._as_list(self._raw.get("pronunciations"))
        parts: List[str] = []

        for p in prons:
            if not isinstance(p, dict):
                continue
            region = self._as_str(p.get("region_label", "")).strip()
            ipa = self._as_str(p.get("ipa_text", "")).strip()
            ipa = ipa.replace("|", "'")

            if region and ipa:
                parts.append(f"{region} {ipa}")
            elif ipa:
                parts.append(ipa)
            elif region:
                parts.append(region)

        return join_with.join([x for x in parts if x])

    # -------------------------
    # conjugation
    # -------------------------
    def _norm_form_text(self, s: Any) -> str:
        t = self._as_str(s).strip()
        if not t:
            return ""
        return t.replace("|", "'")

    def _iter_conj_pairs_from_obj(self, obj: Any) -> List[Tuple[str, str]]:
        pairs: List[Tuple[str, str]] = []

        if isinstance(obj, dict):
            for k, v in obj.items():
                label = self._as_str(k).strip()
                if isinstance(v, list):
                    vs = [self._norm_form_text(x) for x in v]
                    val = ", ".join([x for x in vs if x])
                else:
                    val = self._norm_form_text(v)
                if val:
                    pairs.append((label, val))
            return pairs

        if isinstance(obj, list):
            for it in obj:
                if isinstance(it, dict):
                    label = (
                        self._as_str(it.get("label"))
                        or self._as_str(it.get("type"))
                        or self._as_str(it.get("name"))
                    ).strip()
                    val = (
                        self._as_str(it.get("form"))
                        or self._as_str(it.get("value"))
                        or self._as_str(it.get("text"))
                    ).strip()
                    val = self._norm_form_text(val)
                    if val:
                        pairs.append((label, val))
                else:
                    val = self._norm_form_text(it)
                    if val:
                        pairs.append(("", val))
            return pairs

        val = self._norm_form_text(obj)
        return [("", val)] if val else []

    def _labelize_conj(self, label: str) -> str:
        l = (label or "").strip().lower()
        mapping = {
            "3sg": "3인칭 단수",
            "3rd": "3인칭 단수",
            "third_person_singular": "3인칭 단수",
            "present_3sg": "3인칭 단수",
            "past": "과거",
            "pp": "과거분사",
            "past_participle": "과거분사",
            "present_participle": "현재분사(-ing)",
            "ing": "현재분사(-ing)",
            "plural": "복수형",
            "comparative": "비교급",
            "superlative": "최상급",
        }
        return mapping.get(l, label)

    def _ordered_conj_pairs(self, pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        priority = [
            "3인칭 단수",
            "과거",
            "과거분사",
            "현재분사(-ing)",
            "복수형",
            "비교급",
            "최상급",
        ]

        normed = [(self._labelize_conj(k), v) for k, v in pairs]

        ordered: List[Tuple[str, str]] = []
        used = set()

        for p in priority:
            for k, v in normed:
                if k == p and (k, v) not in used:
                    ordered.append((k, v))
                    used.add((k, v))

        for k, v in normed:
            if (k, v) not in used:
                ordered.append((k, v))
                used.add((k, v))

        return ordered

    def format_conjugation(self, join_with: str = "<br>") -> str:
        self._ensure_ready()

        candidates: List[Any] = []

        for key in ("conjugations", "inflections", "conjugation", "inflection"):
            if key in self._raw:
                candidates.append(self._raw.get(key))

        entries = self._as_list(self._raw.get("entries"))
        for e in entries:
            if not isinstance(e, dict):
                continue
            for key in ("conjugations", "inflections", "conjugation", "inflection"):
                if key in e:
                    candidates.append(e.get(key))

        pairs: List[Tuple[str, str]] = []
        for c in candidates:
            pairs.extend(self._iter_conj_pairs_from_obj(c))

        if not pairs:
            return ""

        pairs = self._ordered_conj_pairs(pairs)

        lines: List[str] = []
        for k, v in pairs:
            if k:
                lines.append(f"{html.escape(k)}: {html.escape(v)}")
            else:
                lines.append(html.escape(v))

        return join_with.join([x for x in lines if x])

    # -------------------------
    # meaning (renderer 위임)
    # -------------------------
    def format_meaning(self, *, join_with: str = "") -> str:
        self._ensure_ready()

        # 호출 단위별 join_with를 바꾸고 싶으면 renderer의 join_with만 교체
        if self._renderer.join_with != join_with:
            self._renderer = HtmlRenderer(
                safe_class=self._safe_class,
                norm_value=self._norm_value_for_render,
                join_with=join_with,
            )

        entries = self._as_list(self._raw.get("entries"))
        # ✅ entries 컨테이너 제거 + 각 item은 div.entry_item
        return self._renderer.render(entries, parent_key="entries")

    # -------------------------
    # tag
    # -------------------------
    def format_tag(self) -> str:
        self._ensure_ready()
        tags: Set[str] = set()

        entries = self._as_list(self._raw.get("entries"))
        for e in entries:
            if not isinstance(e, dict):
                continue
            pos_raw = self._as_str(e.get("part_of_speech", "")).strip()
            pos_ko = self._pos_head_ko(pos_raw)

            if pos_ko in self.tag_dict:
                tags.add(self.tag_dict[pos_ko])

        if " " in self.word:
            tags.add(self.tag_dict["숙어"])

        if self.word.endswith("-") or bool(self._raw.get("is_prefix")):
            tags.add(self.tag_dict["접두사"])

        entry_links = self._as_list(self._raw.get("entry_links"))
        if len(entry_links) >= 2:
            tags.add(self.tag_dict["동음이의어"])

        return " ".join(sorted(tags))

    # -------------------------
    # export
    # -------------------------
    def format_word_export(self, base_word: str, homonym_no: int | None) -> str:
        if homonym_no is None:
            return base_word
        return f"{base_word}{self._to_superscript(homonym_no)}"

    def to_tsv_fields(self, *, word: str, homonym_no: int | None = None) -> list[str]:
        """
        5필드: word / pronunciation / conjugation / meaning / tags
        - export 전용: 탭/개행 절대 금지(검증)
        """
        w = self.format_word_export(word, homonym_no)

        pron = self.format_pronunciation()     # 여기 결과가 단일 라인이어야 함
        conj = self.format_conjugation()       # 단일 라인
        meaning = self.format_meaning()        # 단일 라인 HTML (pretty_html 금지)
        tags = self.format_tag()               # str이든 list든 아래에서 정리

        if isinstance(tags, (list, tuple)):
            tags = " ".join(str(x) for x in tags if x)

        # 최종 검증(여기서 걸리면 format_* 구현을 수정)
        return [
            self._assert_tsv_safe("word", w),
            self._assert_tsv_safe("pronunciation", str(pron)),
            self._assert_tsv_safe("conjugation", str(conj)),
            self._assert_tsv_safe("meaning", str(meaning)),
            self._assert_tsv_safe("tags", str(tags)),
        ]