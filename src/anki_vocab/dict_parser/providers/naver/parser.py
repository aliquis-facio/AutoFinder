from __future__ import annotations

from typing import Any, Dict, Optional

from bs4 import BeautifulSoup as bs

from anki_vocab.dict_parser.models import ParsedWord
from anki_vocab.dict_parser.providers.naver.dom_old import NaverOldDomParser
from anki_vocab.dict_parser.providers.naver.dom_new import NaverNewDomParser


class NaverEntryParser:
    """
    provider 단위 파서.
    - doc.html을 soup로 만들고 sanitize 적용
    - DOM 버전 감지 후 old/new 구현체에 위임
    """

    provider: str = "naver"

    def __init__(self) -> None:
        self._old = NaverOldDomParser()
        self._new = NaverNewDomParser()

    def _is_new_dom(self, soup: bs) -> bool:
        # 신 DOM 시그니처(필요시 더 추가)
        return bool(soup.select_one("dl.entry_conjugation_list, div.entry_pronunciation"))

    def parse(
        self,
        *,
        html: str,
        word: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ParsedWord:
        # soup는 BaseSoupParser가 생성/산타이즈함
        # (old/new 모두 BaseSoupParser 기반)
        soup = bs(html or "", "html.parser")
        dom = self._new if self._is_new_dom(soup) else self._old
        dom.set_html(html or "")
        return dom.parse_to_json(word=word, meta=meta or {})
