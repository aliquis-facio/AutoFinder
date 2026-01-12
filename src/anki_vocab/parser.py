from __future__ import annotations

from bs4 import BeautifulSoup as bs
from bs4.element import Tag, Comment

from typing import List, Dict, Any, Optional, TypedDict
from datetime import datetime
import re


class PronItem(TypedDict, total=False):
    region_label: str      # "미국∙영국", "미국식"
    ipa_text: str          # "[|wɔːtə(r)]" 같이 정규화

class Parser:
    def __init__(self) -> None:
        self.soup: bs = bs("", 'html.parser')
    
    def set_html(self, html: str) -> "Parser":
        """
        HTML을 나중에 주입하는 setter.
        - soup를 새로 만들고
        - sanitize를 적용
        - chaining 가능하도록 self 반환
        """
        self.soup = bs(html or "", "html.parser")
        self._sanitize(self.soup)
        return self
    
    def _norm(self, s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()
    
    def _norm_ipa(self, s: str) -> str:
        """
        예: "[ ɪnˈkwaɪə(r) ]" -> "[ɪnˈkwaɪə(r)]"
        """
        # 대괄호 내부 앞/뒤 공백 제거
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

        # style 속성에 display:none 이 들어간 모든 태그 제거
        # for t in root.find_all(self._is_display_none):
        #     t.decompose()

        # 불필요 태그 제거 (원하면 추가)
        for t in root.select("script, style, noscript"):
            t.decompose()

        # 라벨(grade) 내용 제거 (태그는 남김)
        for t in root.select("span.label_grade"):
            # t.clear()  # "초급 U" 같은 라벨이 별도 위치에 있으면 여기서 비워짐
            t.decompose()

        # 듣기/버튼류 제거 (네이버 DOM에서 자주 등장)
        for t in root.select(".unit_listen, button"):
            t.decompose()

    def _get_classes(self, tag: Tag) -> List[str]:
        v = tag.get("class")  # bs4 타입상: _AttributeValue | None
        if not v:
            return []
        if isinstance(v, str):
            return v.split()
        # v가 list[str] / AttributeValueList 류인 경우
        return list(v)
    
    def _extract_section_by_keyword(self, li: Tag, keyword: str) -> Optional[Tag]:
        """
        li 내부에서 '문형', 'Help', '반의어' 같은 키워드가 들어간 영역(부모)을 찾아 반환.
        DOM이 다양하므로 보수적으로 parent를 몇 단계 올립니다.
        """
        for s in li.find_all(string=lambda x: isinstance(x, str) and keyword in x):
            if not isinstance(s, str):
                continue
            p = s.parent
            if not isinstance(p, Tag):
                continue
            # 너무 작은 span일 수 있으니 상위로 올리기
            for _ in range(3):
                if p.name in ("div", "dl", "dd", "dt", "p", "li"):
                    return p

                parent = p.parent  # parent는 Tag가 아닐 수도 있음
                if isinstance(parent, Tag):
                    p = parent
                else:
                    break
        return None
    
    def _uniq_keep_order(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []

        for x in items:
            if x and x not in seen:
                seen.add(x)
                out.append(x)

        return out

    def parse_pronunciations(self) -> List[PronItem]:
        out: list[PronItem] = []

        pron_area: Tag | None = self.soup.select_one("div.entry_pronounce > div.pronounce_area")
        if pron_area is None:
            return out

        for item in pron_area.select("div.pronounce_item"):
            type_tag = item.select_one("span.type")
            pron_tag = item.select_one("span.pronounce")

            region_label = self._text(type_tag)               # "미국∙영국"

            # text(가공용): sup 등 제거된 텍스트를 얻고, 대괄호 공백 정리
            ipa_text = self._text(pron_tag)
            ipa_text = self._norm_ipa(ipa_text)

            if region_label or ipa_text:
                out.append({
                    "region_label": region_label,
                    "ipa_text": ipa_text,
                })

        # None 정리(선택)
        for d in out:
            for k in list(d.keys()):
                if d[k] is None:
                    d.pop(k, None)

        return out

    def parse_conjugation(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "conjugation": []
        }

        # 부표제어 (entry_conjugation)
        for dl in self.soup.select("dl.entry_conjugation"):
            dt_title = self._text(dl.select_one("dt.tit"))
            if dt_title not in ["부표제어", "VARIANTS"]:
                continue

            variants: Dict[str, Any] = {"title_ko": dt_title, "items": []}

            for item in dl.select("dd.cont .tray > .item"):
                # item 내부에서 구조가 2가지:
                # (a) en·quire + (type/pronounce/unit_listen 반복)
                # (b) inquire 특히 美 (추가 표기만 존재)
                word_span = item.select_one("span.word")
                word_text = self._text(word_span)

                # (b) 타입/발음 정보가 없는 경우
                has_type_or_pron = bool(item.select_one("span.type")) or bool(item.select_one("span.pronounce"))
                if not has_type_or_pron:
                    # "inquire 특히 美" 같은 텍스트를 분리 시도
                    # - 첫 토큰을 word_en으로, 나머지를 note로
                    parts = word_text.split(" ", 1)
                    word_en = parts[0] if parts else ""
                    note = parts[1] if len(parts) > 1 else ""
                    variants["items"].append({
                        "word_en": word_en,
                        "note_ko": note,
                        "pronunciations": []
                    })
                    continue

                # (a) 발음/오디오 포함 케이스
                pronunciations: List[Dict[str, Any]] = []

                # region(type) -> pronounce -> unit_listen 순서를 보존해야 해서
                # item의 직계 children을 순서대로 훑습니다.
                current_region: Optional[str] = None
                last_idx: Optional[int] = None

                for child in item.find_all(recursive=False):
                    if not isinstance(child, Tag):
                        continue

                    classes = child.get("class") or []

                    # region label: span.type
                    if child.name == "span" and "type" in classes:
                        current_region = self._text(child)
                        pronunciations.append({
                            "region_ko": current_region,
                            "ipa": "",
                        })
                        last_idx = len(pronunciations) - 1
                        continue

                    # ipa: span.pronounce
                    if child.name == "span" and "pronounce" in classes:
                        ipa = self._norm_ipa(self._text(child))
                        if last_idx is None:
                            # region이 먼저 안 나온 예외 케이스 보호
                            pronunciations.append({
                                "region_ko": current_region or "",
                                "ipa": ipa,
                            })
                            last_idx = len(pronunciations) - 1
                        else:
                            pronunciations[last_idx]["ipa"] = ipa
                        continue
                
                pronunciations = [
                    p for p in pronunciations
                    if p.get("region_ko", "").strip() or p.get("ipa", "").strip()
                ]
                
                variants["items"].append({
                    "word_en": word_text,
                    "pronunciations": pronunciations
                })

            out["conjugation"].append(variants)

        return out
    
    def parse_examples(self, li: Tag) -> list[dict[str, str]]:
        """
        예문 영역은 페이지/버전에 따라 class가 달라질 수 있어
        후보 셀렉터를 여러 개 두고 '있으면 파싱'하는 방식이 안전합니다.
        """
        examples: list[dict[str, str]] = []

        # 후보 블록들 (필요시 사용자가 실제 DOM 보고 추가/수정)
        blocks = li.select(".example, .mean_example, .txt_example, .ex")  # fallback
        for b in blocks:
            en = self._first_text_by_selectors(b, ["p.origin", ".txt_en", "em", "span"])
            ko = self._first_text_by_selectors(b, ["p.translate", ".txt_ko", ".trans", ".translation"])
            if en or ko:
                examples.append({"en": en, "ko": ko})

        # 중복 제거(간단 처리)
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

            # ✅ Help
            if tit == "Help":
                if isinstance(dd, Tag):
                    txt = self._text(dd)
                    if txt:
                        help_texts.append(txt)
                continue

            # ✅ 문형
            if tit in ["문형", "Sentence Structure"]:
                if isinstance(dd, Tag):
                    # 문형은 한 줄/여러 줄일 수 있어서 stripped_strings로 수집
                    txt = self._text(dd)
                    if txt:
                        patterns.append(txt)
                continue

        # patterns 정리
        if patterns:
            patterns_text = self._norm(" ".join(patterns))
            out["patterns"] = patterns_text

        # help 정리
        if help_texts:
            help_ko = self._norm(" ".join(help_texts))
            out["help"] = help_ko

        return out
    
    def parse_related_words(self, li: Tag) -> list[str]:
        """
        '참고어' 영역 파싱.
        DOM이 다양해서, 일단 li 내부에서 참고어 관련 링크/텍스트를 최대한 긁어오는 보수적 전략.
        "ul.component_relation"
        """
        related: list[str] = []

        # 가장 흔한 형태: 참고어 옆에 링크로 단어들이 나열됨
        related += self._select_all_texts(li, ".related_word a, .related a, .refer a")

        # 텍스트만 있는 경우도 있으니 fallback
        if not related:
            # "참고어" 텍스트가 있는 노드를 찾아 주변에서 a 태그를 수집하는 방식(보수적)
            for node in li.find_all(string=lambda s: isinstance(s, str) and "참고어" in s):
                parent = node.parent if isinstance(node.parent, Tag) else None
                if parent:
                    related += self._select_all_texts(parent, "a")

        # 정리
        related = [self._norm(x) for x in related if self._norm(x)]
        # 중복 제거
        uniq = []
        seen = set()
        for w in related:
            if w not in seen:
                seen.add(w)
                uniq.append(w)
        return uniq
    
    def parse_antonyms(self, li: Tag) -> list[str]:
        antonyms: list[str] = []

        # 1) class 기반 후보
        antonyms += self._select_all_texts(li, ".antonym a, .opposite a, .mean_antonym a")

        # 2) 키워드 fallback: "반의어 unsympathetic" 같은 텍스트 처리
        if not antonyms:
            sec = self._extract_section_by_keyword(li, "반의어")
            if sec:
                txt = self._norm(sec.get_text(" ", strip=True)).replace("반의어", "").strip()
                # 공백/쉼표로 분리
                for w in re.split(r"[,\s]+", txt):
                    w = w.strip()
                    if w:
                        antonyms.append(w)

        # 정리/중복 제거
        uniq: list[str] = []
        seen = set()
        for w in antonyms:
            w = self._norm(w)
            if w and w not in seen:
                seen.add(w)
                uniq.append(w)
        return uniq

    def parse_sense(self, li: Tag, sense_no: int) -> dict[str, Any]:
        # ✅ cont 영역(있으면 여기에서 part_speech / mean_addition / mean을 뽑는 게 가장 정확)
        cont = li.select_one("div.mean_desc div.cont") or li.select_one("div.cont")

        # ✅ 정의(뜻)는 span.mean을 1순위로
        definition_ko = ""
        if isinstance(cont, Tag):
            definition_ko = self._text(cont.select_one("span.mean"))
        if not definition_ko:
            # fallback
            mean_desc = li.select_one("div.mean_desc") or li
            definition_ko = self._first_text_by_selectors(mean_desc, [
                ".mean", ".txt_mean", ".def", ".definition"
            ])

        # ✅ part_speech (예: BECOME FRIENDLY)
        tags: list[Tag] = []
        if isinstance(cont, Tag):
            tags = list(cont.select("em.part_speech"))

        part_speech: List[str] = self._uniq_keep_order([
            txt for txt in (self._text(t) for t in tags) if txt
        ])

        # ✅ mean_addition (예: [자, 타동사V, VN])
        mean_addition: str = ""
        if isinstance(cont, Tag):
            mean_addition = self._text(cont.select_one("span.mean_addition"))      

        references = self.parse_references(li)
        antonyms = self.parse_antonyms(li)

        sense: dict[str, Any] = {
            "sense_no": sense_no, # 단어 번호
            "part_speech": part_speech or None, 
            "mean_addition": mean_addition or None,
            "definition_ko": definition_ko, # 한글 뜻
            "examples": self.parse_examples(li), # 예문
            "references": references, # 참고: 문형, Help
            "related_words": self.parse_related_words(li), # 참고어: 참고어, 유의어, 반의어
            "antonyms": antonyms,
        }

        # 비어있는 값 정리
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
        """
        ul 기준으로 가장 가까운 div.part_area 텍스트를 품사명으로 사용.
        - 1순위: ul의 previous_siblings를 거슬러 올라가며 바로 앞쪽 part_area 탐색(가장 안전)
        - 2순위: find_previous("div", class_="part_area") fallback
        - scope(#allMeanGroups/div.mean_tray) 바깥의 part_area는 무시하도록 방어
        """

        # 1) 가장 가까운 previous_siblings에서 찾기
        for sib in ul.previous_siblings:
            if not isinstance(sib, Tag):
                continue

            # sibling 자체가 part_area인 경우
            if sib.name == "div" and "part_area" in self._get_classes(sib):
                return self._text(sib)

            # sibling 내부에 part_area가 들어있는 경우
            t = sib.select_one("div.part_area")
            if isinstance(t, Tag):
                return self._text(t)

        # 2) fallback: 문서 전체에서 이전 part_area를 찾되, scope 내부인지 확인
        t2 = ul.find_previous("div", class_="part_area")
        if isinstance(t2, Tag):
            # scope 바깥으로 새는 것을 방지
            if scope in t2.parents or t2 is scope:
                return self._text(t2)

        return ""

    def parse_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []

        # all_mean = self.soup.select_one()
        
        all_mean = self._first_tag_by_selectors(self.soup, ["#allMeanGroups", "div.mean_tray"])
        if not all_mean:
            return entries

        # 가정: #allMeanGroups 바로 아래에 ul들이 있고, 각 ul이 품사 그룹(명사/동사...)일 가능성
        # 다만 실제론 ul 하나에 여러 품사가 섞일 수도 있어 fallback도 둡니다.
        uls = all_mean.select(":scope > ul")
        if not uls:
            uls = all_mean.select("ul")  # fallback

        for ul in uls:
            if not isinstance(ul, Tag):
                continue

            # ✅ 품사명: div.part_area 기반으로 가져오기
            pos = self._get_pos_from_ul(ul, all_mean)
            pos = pos or ""

            # sense li들
            sense_items = ul.select(":scope > li")
            if not sense_items:
                sense_items = ul.select("li")  # fallback

            senses: list[dict[str, Any]] = []
            for idx, li in enumerate(sense_items, start=1):
                if not isinstance(li, Tag):
                    continue
                senses.append(self.parse_sense(li, idx))

            if senses:
                entries.append({
                    "part_of_speech": pos or None,
                    "senses": senses
                })

        return entries

    def parse_image(self) -> List[str] | None:
        # 이미지
        image_urls: List[str] = []
        
        images: List[Tag] | None = self.soup.select("div.thumb")
        if images:
            for image in images:
                if image:
                    raw_style = image.get("style")  # 타입: _AttributeValue | None

                    # 타입 정리
                    if isinstance(raw_style, list):
                        style_attr: str = " ".join(raw_style)
                    elif isinstance(raw_style, str):
                        style_attr = raw_style
                    else:
                        style_attr = ""

                    # 정규식 검색
                    match: Optional[re.Match[str]] = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_attr)
                    if match:
                        image_url: str = match.group(1)
                        image_urls.append(image_url)

        return image_urls

    def parse_to_json(self, word: str) -> dict[str, Any]:
        return {
            "word": word,
            "pronunciations": self.parse_pronunciations(),
            "conjugations": self.parse_conjugation(),
            "entries": self.parse_entries(),   # part_of_speech + senses(...)
            "images": self.parse_image() or [],
            "meta": {
                "homonym": "",
                "source": "naver",
                "parsed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
        }
        