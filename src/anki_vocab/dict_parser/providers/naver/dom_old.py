"""
"""

from __future__ import annotations

from bs4.element import Tag

from typing import Any, Dict, List, Optional
import re
from datetime import datetime

from anki_vocab.dict_parser.base import BaseSoupParser
from anki_vocab.dict_parser.models import PronItem, ParsedWord


class NaverOldDomParser(BaseSoupParser):
    """
    너가 원래 쓰던 '구 DOM' 파서(현재 parser.py 로직을 거의 그대로).
    """

    # -----------------------
    # pronunciations (old)
    # -----------------------
    def parse_pronunciations(self) -> List[PronItem]:
        out: list[PronItem] = []

        pron_area: Tag | None = self.soup.select_one("div.entry_pronounce > div.pronounce_area")
        if pron_area is None:
            return out

        for item in pron_area.select("div.pronounce_item"):
            type_tag = item.select_one("span.type")
            pron_tag = item.select_one("span.pronounce")

            region_label = self._text(type_tag)
            ipa_text = self._norm_ipa(self._text(pron_tag))

            if region_label or ipa_text:
                out.append({"region_label": region_label, "ipa_text": ipa_text})

        for d in out:
            for k in list(d.keys()):
                if d[k] is None:
                    d.pop(k, None)

        return out

    # -----------------------
    # conjugations (old)
    # -----------------------
    def parse_conjugation(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"conjugation": []}

        for dl in self.soup.select("dl.entry_conjugation"):
            dt_title = self._text(dl.select_one("dt.tit"))
            if dt_title not in ["부표제어", "VARIANTS"]:
                continue

            variants: Dict[str, Any] = {"title_ko": dt_title, "items": []}

            for item in dl.select("dd.cont .tray > .item"):
                word_span = item.select_one("span.word")
                word_text = self._text(word_span)

                has_type_or_pron = bool(item.select_one("span.type")) or bool(item.select_one("span.pronounce"))
                if not has_type_or_pron:
                    parts = word_text.split(" ", 1)
                    word_en = parts[0] if parts else ""
                    note = parts[1] if len(parts) > 1 else ""
                    variants["items"].append({"word_en": word_en, "note_ko": note, "pronunciations": []})
                    continue

                pronunciations: List[Dict[str, Any]] = []
                current_region: Optional[str] = None
                last_idx: Optional[int] = None

                for child in item.find_all(recursive=False):
                    if not isinstance(child, Tag):
                        continue

                    classes = child.get("class") or []

                    if child.name == "span" and "type" in classes:
                        current_region = self._text(child)
                        pronunciations.append({"region_ko": current_region, "ipa": ""})
                        last_idx = len(pronunciations) - 1
                        continue

                    if child.name == "span" and "pronounce" in classes:
                        ipa = self._norm_ipa(self._text(child))
                        if last_idx is None:
                            pronunciations.append({"region_ko": current_region or "", "ipa": ipa})
                            last_idx = len(pronunciations) - 1
                        else:
                            pronunciations[last_idx]["ipa"] = ipa
                        continue

                pronunciations = [
                    p for p in pronunciations
                    if p.get("region_ko", "").strip() or p.get("ipa", "").strip()
                ]

                variants["items"].append({"word_en": word_text, "pronunciations": pronunciations})

            out["conjugation"].append(variants)

        return out

    # -----------------------
    # examples / references / related / antonyms (old)
    # -----------------------
    def parse_examples(self, li: Tag) -> list[dict[str, str]]:
        examples: list[dict[str, str]] = []
        blocks = li.select(".example, .mean_example, .txt_example, .ex")
        for b in blocks:
            en = self._first_text_by_selectors(b, ["p.origin", ".txt_en", "em", "span"])
            ko = self._first_text_by_selectors(b, ["p.translate", ".txt_ko", ".trans", ".translation"])
            if en or ko:
                examples.append({"en": en, "ko": ko})

        uniq: list[dict[str, str]] = []
        seen = set()
        for e in examples:
            key = (e.get("en", ""), e.get("ko", ""))
            if key not in seen and (key[0] or key[1]):
                seen.add(key)
                uniq.append(e)
        return uniq

    def parse_references(self, li: Tag) -> Dict[str, Any]:
        out: dict[str, Any] = {}
        patterns: list[str] = []
        help_texts: list[str] = []

        for cell in li.select("div.reference dl.cell"):
            tit = self._text(cell.select_one("dt.tit"))
            dd = cell.select_one("dd.cont") or cell.select_one("dd")

            if tit == "Help":
                if isinstance(dd, Tag):
                    txt = self._text(dd)
                    if txt:
                        help_texts.append(txt)
                continue

            if tit in ["문형", "Sentence Structure"]:
                if isinstance(dd, Tag):
                    txt = self._text(dd)
                    if txt:
                        patterns.append(txt)
                continue

        if patterns:
            out["patterns"] = self._norm(" ".join(patterns))
        if help_texts:
            out["help"] = self._norm(" ".join(help_texts))
        return out

    def parse_related_words(self, li: Tag) -> list[str]:
        related: list[str] = []
        related += self._select_all_texts(li, ".related_word a, .related a, .refer a")

        if not related:
            for node in li.find_all(string=lambda s: isinstance(s, str) and "참고어" in s):
                parent = node.parent if isinstance(node.parent, Tag) else None
                if parent:
                    related += self._select_all_texts(parent, "a")

        related = [self._norm(x) for x in related if self._norm(x)]
        uniq = []
        seen = set()
        for w in related:
            if w not in seen:
                seen.add(w)
                uniq.append(w)
        return uniq

    def parse_antonyms(self, li: Tag) -> list[str]:
        antonyms: list[str] = []
        antonyms += self._select_all_texts(li, ".antonym a, .opposite a, .mean_antonym a")

        if not antonyms:
            sec = self._extract_section_by_keyword(li, "반의어")
            if sec:
                txt = self._norm(sec.get_text(" ", strip=True)).replace("반의어", "").strip()
                for w in re.split(r"[,\s]+", txt):
                    w = w.strip()
                    if w:
                        antonyms.append(w)

        uniq: list[str] = []
        seen = set()
        for w in antonyms:
            w = self._norm(w)
            if w and w not in seen:
                seen.add(w)
                uniq.append(w)
        return uniq

    def parse_sense(self, li: Tag, sense_no: int) -> dict[str, Any]:
        cont = li.select_one("div.mean_desc div.cont") or li.select_one("div.cont")

        definition_ko = ""
        if isinstance(cont, Tag):
            definition_ko = self._text(cont.select_one("span.mean"))
        if not definition_ko:
            mean_desc = li.select_one("div.mean_desc") or li
            definition_ko = self._first_text_by_selectors(mean_desc, [".mean", ".txt_mean", ".def", ".definition"])

        tags: list[Tag] = []
        if isinstance(cont, Tag):
            tags = list(cont.select("em.part_speech"))

        part_speech = self._uniq_keep_order([txt for txt in (self._text(t) for t in tags) if txt])

        mean_addition = ""
        if isinstance(cont, Tag):
            mean_addition = self._text(cont.select_one("span.mean_addition"))

        references = self.parse_references(li)
        antonyms = self.parse_antonyms(li)

        sense: dict[str, Any] = {
            "sense_no": sense_no,
            "part_speech": part_speech or None,
            "mean_addition": mean_addition or None,
            "definition_ko": definition_ko,
            "examples": self.parse_examples(li),
            "references": references,
            "related_words": self.parse_related_words(li),
            "antonyms": antonyms,
        }

        if not sense["examples"]:
            sense.pop("examples")
        if not sense["related_words"]:
            sense.pop("related_words")
        if not sense["references"]:
            sense.pop("references")
        if not sense["antonyms"]:
            sense.pop("antonyms")
        if sense.get("part_speech") is None:
            sense.pop("part_speech", None)
        if sense.get("mean_addition") is None:
            sense.pop("mean_addition", None)

        return sense

    def _get_pos_from_ul(self, ul: Tag, scope: Tag) -> str:
        for sib in ul.previous_siblings:
            if not isinstance(sib, Tag):
                continue
            if sib.name == "div" and "part_area" in self._get_classes(sib):
                return self._text(sib)
            t = sib.select_one("div.part_area")
            if isinstance(t, Tag):
                return self._text(t)

        t2 = ul.find_previous("div", class_="part_area")
        if isinstance(t2, Tag):
            if scope in t2.parents or t2 is scope:
                return self._text(t2)
        return ""

    def parse_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []

        all_mean = self._first_tag_by_selectors(self.soup, ["#allMeanGroups", "div.mean_tray"])
        if not all_mean:
            return entries

        uls = all_mean.select(":scope > ul") or all_mean.select("ul")

        for ul in uls:
            if not isinstance(ul, Tag):
                continue

            pos = self._get_pos_from_ul(ul, all_mean) or ""

            sense_items = ul.select(":scope > li") or ul.select("li")
            senses: list[dict[str, Any]] = []
            for idx, li in enumerate(sense_items, start=1):
                if isinstance(li, Tag):
                    senses.append(self.parse_sense(li, idx))

            if senses:
                entries.append({"part_of_speech": pos or None, "senses": senses})

        return entries

    def parse_image(self) -> List[str]:
        image_urls: List[str] = []
        images = self.soup.select("div.thumb")
        for image in images:
            if not isinstance(image, Tag):
                continue
            raw_style = image.get("style")
            if isinstance(raw_style, list):
                style_attr = " ".join(raw_style)
            elif isinstance(raw_style, str):
                style_attr = raw_style
            else:
                style_attr = ""

            match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_attr)
            if match:
                image_urls.append(match.group(1))

        return image_urls

    def parse_to_json(
        self,
        *,
        word: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ParsedWord:
        return {
            "word": word,
            "pronunciations": self.parse_pronunciations(),
            "conjugations": self.parse_conjugation(),
            "entries": self.parse_entries(),
            "images": self.parse_image() or [],
            "meta": {
                "homonym": "",
                "source": "naver",
                "parsed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                **(meta or {}),
            },
        }
