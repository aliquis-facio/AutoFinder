# anki_vocab/dict_parser/base.py
from __future__ import annotations

from bs4 import BeautifulSoup as bs
from bs4.element import Comment, Tag

from typing import Any, List, Optional
import re


class BaseSoupParser:
    """
    provider/dom parser들의 공통 베이스.
    - soup 생성/보관
    - sanitize + 공통 유틸
    """

    def __init__(self) -> None:
        self.soup: bs = bs("", "html.parser")

    def set_html(self, html: str) -> "BaseSoupParser":
        self.soup = bs(html or "", "html.parser")
        self._sanitize(self.soup)
        return self

    # -----------------------
    # util
    # -----------------------
    def _norm(self, s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    def _norm_ipa(self, s: str) -> str:
        s = re.sub(r"\[\s*", "[", s)
        s = re.sub(r"\s*\]", "]", s)
        return s

    def _text(self, tag: Optional[Tag]) -> str:
        if tag is None:
            return ""
        return self._norm(tag.get_text(" ", strip=True))

    def _first_tag_by_selectors(self, root: Tag, selectors: List[str]) -> Optional[Tag]:
        for sel in selectors:
            t = root.select_one(sel)
            if t:
                return t
        return None

    def _first_text_by_selectors(self, root: Tag, selectors: list[str]) -> str:
        for sel in selectors:
            t = root.select_one(sel)
            if t:
                val = self._text(t)
                if val:
                    return val
        return ""

    def _select_all_texts(self, root: Tag, sel: str) -> list[str]:
        out: list[str] = []
        for t in root.select(sel):
            v = self._text(t)
            if v:
                out.append(v)
        return out

    def _attr_to_str(self, v: Any) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, (list, tuple)):
            return " ".join(str(x) for x in v)
        return ""

    def _is_display_none(self, tag: Tag) -> bool:
        style_str = self._attr_to_str(tag.get("style"))
        return bool(re.search(r"display\s*:\s*none", style_str, flags=re.I))

    def _sanitize(self, root: Tag) -> None:
        # HTML comments 제거
        for c in root.find_all(string=lambda s: isinstance(s, Comment)):
            c.extract()

        # NOTE: 더보기 내용이 display:none으로 들어오는 케이스가 있어 기본은 OFF 권장
        # for t in root.find_all(self._is_display_none):
        #     t.decompose()

        for t in root.select("script, style, noscript"):
            t.decompose()

        for t in root.select("span.label_grade"):
            t.decompose()

        for t in root.select(".unit_listen, button"):
            t.decompose()

    def _get_classes(self, tag: Tag) -> List[str]:
        v = tag.get("class")
        if not v:
            return []
        if isinstance(v, str):
            return v.split()
        return list(v)

    def _uniq_keep_order(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in items:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def _extract_section_by_keyword(self, li: Tag, keyword: str) -> Optional[Tag]:
        for s in li.find_all(string=lambda x: isinstance(x, str) and keyword in x):
            if not isinstance(s, str):
                continue
            p = s.parent
            if not isinstance(p, Tag):
                continue
            for _ in range(3):
                if p.name in ("div", "dl", "dd", "dt", "p", "li"):
                    return p
                parent = p.parent
                if isinstance(parent, Tag):
                    p = parent
                else:
                    break
        return None
