"""
"""

from __future__ import annotations

from bs4.element import Tag

from typing import Any, Dict, List, Optional

from anki_vocab.dict_parser.providers.naver.dom_old import NaverOldDomParser
from anki_vocab.dict_parser.models import PronItem


class NaverNewDomParser(NaverOldDomParser):
    """
    신 DOM 파서.
    - pronunciations selector 완화(크롤러 셀렉터 기준)
    - conjugations: 동사형/명사형 등 dl.entry_conjugation_list 지원
    """

    def parse_pronunciations(self) -> List[PronItem]:
        out: list[PronItem] = []

        # dict_crawler 쪽 셀렉터에 맞춰 완화
        pron_area: Tag | None = self.soup.select_one(
            "div.entry_pronounce div.pronounce_area, div.entry_pronunciation"
        )
        if pron_area is None:
            return out

        # item 다양성 대응(너무 넓게 잡지 않되, 신/구 혼재 허용)
        for item in pron_area.select(".pronounce_item, .pronunciation_item, div.pronounce_item"):
            type_tag = item.select_one("span.type, em.type, .type")
            pron_tag = item.select_one("span.pronounce, span.ipa, .pronounce, .ipa")

            region_label = self._text(type_tag)
            ipa_text = self._norm_ipa(self._text(pron_tag))

            if region_label or ipa_text:
                out.append({"region_label": region_label, "ipa_text": ipa_text})

        return out

    def parse_conjugation(self) -> Dict[str, Any]:
        """
        1) 신 DOM: dl.entry_conjugation_list (동사형/명사형)
        2) 구 DOM: dl.entry_conjugation (부표제어/VARIANTS)
        둘 다 있을 수 있으니 "신 DOM 먼저" + "구 DOM fallback" 전략.
        """
        out: Dict[str, Any] = {"conjugation": []}

        # -----------------------
        # (A) NEW: 동사형/명사형 등
        # -----------------------
        for dl in self.soup.select("dl.entry_conjugation_list"):
            # dt와 dd가 번갈아 나오므로 dt를 순회하면서 다음 dd를 찾음
            for dt in dl.select(":scope > dt.tit"):
                if not isinstance(dt, Tag):
                    continue
                title_ko = self._text(dt)
                if not title_ko:
                    continue

                dd = dt.find_next_sibling("dd")
                if not isinstance(dd, Tag):
                    continue

                variants: Dict[str, Any] = {"title_ko": title_ko, "items": []}

                # item 단위
                for item in dd.select(".tray .item"):
                    if not isinstance(item, Tag):
                        continue

                    # 예: 과거형/복수형
                    type_tag = item.select_one("em.type, span.type, .type")
                    note_ko = self._text(type_tag)

                    # 단어 형태가 여러 개일 수 있음 (dos, do's)
                    forms = []
                    for w in item.select(".data_group span.word"):
                        txt = self._text(w)
                        if txt:
                            forms.append(txt)
                    # fallback: span.word가 깊게 있거나 구조가 바뀐 경우
                    if not forms:
                        w = item.select_one("span.word")
                        txt = self._text(w)
                        if txt:
                            forms = [txt]

                    # normalize + uniq
                    uniq_forms = []
                    seen = set()
                    for f in forms:
                        if f not in seen:
                            seen.add(f)
                            uniq_forms.append(f)

                    if not uniq_forms and not note_ko:
                        continue

                    variants["items"].append({
                        "word_en": ", ".join(uniq_forms) if uniq_forms else "",
                        "note_ko": note_ko,
                        "pronunciations": [],  # 신 DOM 활용형엔 보통 IPA 없음
                        "forms": uniq_forms,   # 필요 없으면 빼도 됨(호환성 위해 optional)
                    })

                if variants["items"]:
                    out["conjugation"].append(variants)

        # -----------------------
        # (B) OLD fallback: 부표제어/VARIANTS
        # -----------------------
        old_part = super().parse_conjugation()
        if old_part.get("conjugation"):
            out["conjugation"].extend(old_part["conjugation"])

        return out
