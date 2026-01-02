from __future__ import annotations

from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional, Set, Tuple
import html, re


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

    def _norm_pos(self, pos: str) -> str:
        pos = (pos or "").strip()
        if not pos:
            return ""
        return self.pos_en_to_ko.get(pos, pos)
    
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
    
    def _norm_form_text(self, s: Any) -> str:
        t = self._as_str(s).strip()
        if not t:
            return ""
        return t.replace("|", "'")
    
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
    
    def _safe_class(self, name: str) -> str:
        # class로 쓰기 애매한 문자는 '_'로 치환
        return self._class_re.sub("_", name).strip("_") or "_"
    
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

    def _iter_conj_pairs_from_obj(self, obj: Any) -> List[Tuple[str, str]]:
        """
        conjugations/inflections를 (label, value) 쌍으로 표준화.
        지원 형태 예)
        - {"past":"made", "pp":"made", "ing":"making"}
        - [{"type":"past", "form":"made"}, ...]
        - [{"label":"과거", "value":"made"}, ...]
        - ["made", "making"]  (라벨 없이)
        """
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
        """
        변화형/활용형 출력.
        - 우선순위: self._raw(conjugations/inflections) -> entries 내부(conjugations/inflections)
        - part_of_speech에서 추출하는 fallback은 사용하지 않음.
        """
        self._ensure_ready()

        candidates: List[Any] = []

        # top-level
        for key in ("conjugations", "inflections", "conjugation", "inflection"):
            if key in self._raw:
                candidates.append(self._raw.get(key))

        # entries 내부
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
            return ""  # 변화형 데이터가 없으면 빈 문자열

        pairs = self._ordered_conj_pairs(pairs)

        lines: List[str] = []
        for k, v in pairs:
            if k:
                lines.append(f"{html.escape(k)}: {html.escape(v)}")
            else:
                lines.append(html.escape(v))

        return join_with.join([x for x in lines if x])

    def _format_node(
        self,
        obj: Any,
        *,
        parent_key: Optional[str] = None,
        join_with: str,
        item_wrap_class: Optional[str],
        ol_keys: Set[str],
    ) -> str:
        SKIP_KEYS = {"sense_no"}

        # key별 컨테이너 태그 오버라이드
        TAG_OVERRIDES: Dict[str, str] = {
            "part_of_speech": "p",
            "part_speech": "div",
            "examples": "div",
            "en": "p",   # ✅
            "ko": "p",   # ✅
        }

        # list item class 오버라이드
        ITEM_CLASS_OVERRIDES: Dict[str, str] = {
            "entries": "entry_item",
            "senses": "sense_item",
            "part_speech": "part_speech_item",
            # ✅ examples는 item wrapper 제거하므로 여기서 빼도 됨
        }

        # list item tag 오버라이드
        ITEM_TAG_OVERRIDES: Dict[str, str] = {
            "entries": "div",
            # ✅ examples item tag도 제거(래핑 자체를 안 함)
        }

        # dict
        if isinstance(obj, dict):
            parts: List[str] = []
            for k, v in obj.items():
                key_raw = str(k)
                if key_raw in SKIP_KEYS:
                    continue

                cls = html.escape(self._safe_class(key_raw), quote=True)

                if key_raw == "part_of_speech" and isinstance(v, str):
                    v = self._norm_pos_text(v)

                if key_raw in ol_keys and isinstance(v, list):
                    li_cls_raw = ITEM_CLASS_OVERRIDES.get(key_raw, f"{key_raw}_item")
                    li_cls = html.escape(self._safe_class(li_cls_raw), quote=True)

                    lis: List[str] = []
                    for x in v:
                        inner = self._format_node(
                            x,
                            parent_key=key_raw,
                            join_with=join_with,
                            item_wrap_class=item_wrap_class,
                            ol_keys=ol_keys,
                        )
                        if inner.strip():
                            lis.append(f'<li class="{li_cls}">{inner}</li>')
                    parts.append(f'<ol class="{cls}">' + "".join(lis) + "</ol>")
                    continue

                inner = self._format_node(
                    v,
                    parent_key=key_raw,
                    join_with=join_with,
                    item_wrap_class=item_wrap_class,
                    ol_keys=ol_keys,
                )

                tag = TAG_OVERRIDES.get(key_raw, "span")
                parts.append(f'<{tag} class="{cls}">{inner}</{tag}>')

            return join_with.join([p for p in parts if p])

        # list
        if isinstance(obj, list):
            # ✅ examples는 "예문이 0~1개" 전제: item wrapper 없이 내부만 바로 렌더링
            if parent_key == "examples":
                rendered: List[str] = []
                for x in obj:
                    inner = self._format_node(
                        x,
                        parent_key=parent_key,
                        join_with=join_with,
                        item_wrap_class=item_wrap_class,
                        ol_keys=ol_keys,
                    )
                    if inner.strip():
                        rendered.append(inner)
                return join_with.join(rendered)

            items: List[str] = []
            if parent_key:
                item_cls_raw = ITEM_CLASS_OVERRIDES.get(parent_key, f"{parent_key}_item")
                item_tag = ITEM_TAG_OVERRIDES.get(parent_key, "span")
            else:
                item_cls_raw = item_wrap_class or "__item"
                item_tag = "span"

            item_cls = html.escape(self._safe_class(item_cls_raw), quote=True)

            for x in obj:
                inner = self._format_node(
                    x,
                    parent_key=parent_key,
                    join_with=join_with,
                    item_wrap_class=item_wrap_class,
                    ol_keys=ol_keys,
                )
                if not inner.strip():
                    continue
                items.append(f'<{item_tag} class="{item_cls}">{inner}</{item_tag}>')

            return join_with.join(items)

        # scalar
        s = "" if obj is None else str(obj)

        # raw 텍스트에 혹시 들어있는 <br> 제거
        s = re.sub(r"<\s*br\s*/?\s*>", "", s, flags=re.IGNORECASE)

        # 개행/탭 제거 + 연속 공백 1개로 축약 + 좌우 trim
        s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
        s = re.sub(r"\s+", " ", s).strip()

        s = self.compact_html(s)
        return html.escape(s)

    def compact_html(self, html_text: str) -> str:
        # 혹시 남아있는 <br> 제거
        s = re.sub(r"<\s*br\s*/?\s*>", "", html_text, flags=re.IGNORECASE)

        # 태그 사이 공백/개행 제거(>< 형태로)
        s = re.sub(r">\s+<", "><", s)

        # 전체 공백 정리
        s = s.replace("\r", "").replace("\n", "").replace("\t", "")
        return s.strip()

    def format_meaning(
        self,
        *,
        join_with: str = "",
        item_wrap_class: Optional[str] = "__item",
        ol_keys: Set[str] = {"senses"},
    ) -> str:
        self._ensure_ready()
        entries = self._as_list(self._raw.get("entries"))

        # ✅ entries 컨테이너는 제거하고, entries 리스트만 렌더링
        return self._format_node(
            entries,
            parent_key="entries",   # ✅ entries item을 entry_item(div)로 만들기 위해 지정
            join_with=join_with,
            item_wrap_class=item_wrap_class,
            ol_keys=ol_keys,
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