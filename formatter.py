from typing import List, Dict, Tuple, Set, Any, Optional
from word_entry import WordEntry


class Formatter:
    part_area: Tuple[str, ...] = (
        "명사", "대명사", "동사", "형용사", "부사",
        "전치사", "접속사", "한정사", "감탄사", "수사", "관계사"
    )
    
    part_speech: Tuple[str, ...] = (
        # 명사
        "가산명사", "불가산명사",
        # 동사
        "계사", "자동사", "타동사", "조동사",
        # 한정사
        "관사", "양화사", "소유격"
    )

    tag_dict: Dict[str, str] = {
        "숙어": "Idiom(숙어)",
        "다의어": "Polysemy(다의어)",
        # "예문": "Example(예문)",
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

    related_type: List[str] = [
        "문형", "유의어", "반의어", "참고어",
        "상호참조", "Help", "약어", "부가설명", "전문용어", "줄임말"
    ]

    def __init__(self, data: Dict[str, Any]) -> None:
        # WebDriver4.Crawler.search_word() 의 결과 한 건 (word_data dict)
        self._raw: Dict[str, Any] = data

        self.word: str = data.get("word", "").strip()
        self.pronounce_raw: str = data.get("pronounce", "")
        self.conjugation_raw: str = data.get("conjugation", "")
        self.meaning_raw: str = data.get("meaning", "")
        self.polysemy: bool = bool(data.get("polysemy", False))
        # idiom / error 는 크롤러에서 안 채워도 기본값으로 False
        self.idiom: bool = bool(data.get("idiom", False))
        self.error: bool = bool(data.get("error", False))
        # ▶ 이미지 URL 원본도 보관
        self.image_url_raw: str = data.get("image_url", "")

        # 파싱된 결과
        self.sections: Dict[str, List[str]] = self._split_sections(self.meaning_raw)

    # --- 내부 유틸 ---

    def _split_sections(self, text: str) -> Dict[str, List[str]]:
        """
        Crawler.get_detailed_data() 가 meaning 을
        '## section-name\\n내용...' 형태로 붙여두기 때문에
        이를 섹션별 dict 로 쪼갠다.
        """
        sections: Dict[str, List[str]] = {}
        current: Optional[str] = None

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("## "):
                current = line[3:].strip()
                sections.setdefault(current, [])
            elif current:
                sections[current].append(line)

        return sections

    def _normalize_multiline(self, lines: List[str]) -> str:
        """
        여러 줄을 파일 저장용 문자열로 합친다.
        README 에서 말한 것처럼 HTML 태그(<br>)를 사용해 줄바꿈을 표현한다.
        """
        cleaned: List[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            cleaned.append(line)
        return "<br>".join(cleaned)

    def _format_pronounce(self) -> str:
        """
        pronounce_raw 역시 '## pronounce' 같은 헤더가 섞여 있으므로 정리한다.
        """
        lines = []
        for raw_line in self.pronounce_raw.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("## "):
                continue
            lines.append(line)
        # 여러 발음(예: 미국식/영국식)이 있으면 ' / ' 로 구분
        return " / ".join(lines)

    def _extract_tags(self) -> List[str]:
        """
        품사/다의어/숙어 여부를 기준으로 태그 리스트 생성.
        """
        tags: List[str] = []

        # 의미 문자열에 포함된 품사/관계 키워드 기반
        source_text = " ".join(
            self.sections.get("part area", [])
            + self.sections.get("part speech", [])
            + self.sections.get("reference", [])
            + self.sections.get("component relation", [])
        )

        for key, label in self.tag_dict.items():
            if key in source_text:
                tags.append(label)

        if self.polysemy and self.tag_dict["다의어"] not in tags:
            tags.append(self.tag_dict["다의어"])
        if self.idiom and self.tag_dict["숙어"] not in tags:
            tags.append(self.tag_dict["숙어"])

        # 중복 제거 & 정렬
        uniq = sorted(set(tags))
        return uniq

    # --- 외부에서 사용하는 메인 진입점 ---

    def to_entry(self) -> WordEntry:
        """
        최종적으로 파일에 쓰기 좋은 WordEntry 로 변환.
        """
        # 뜻 / 예문 분리
        meaning_lines: List[str] = []
        for key in ("mean", "mean addition"):
            if key in self.sections:
                meaning_lines.extend(self.sections[key])

        example_lines: List[str] = self.sections.get("example", [])

        # ✅ 뜻에 예문을 포함시키기
        if example_lines:
            # 가독성을 위해 한 줄 띄우고 [예문] 헤더 추가 (원하면 제거해도 됨)
            meaning_lines.append("")
            meaning_lines.append("[예문]")
            meaning_lines.extend(example_lines)

        meaning = self._normalize_multiline(meaning_lines)

        # ✅ image_url은 실제 이미지 URL 사용 (없으면 빈 문자열)
        image_url = self.image_url_raw

        pronounce = self._format_pronounce()
        tags = self._extract_tags()

        return WordEntry(
            word=self.word,
            pronounce=pronounce,
            meaning=meaning,
            image_url=image_url,
            tag=tags,
        )