# anki_vocab/dict_parser/router.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Protocol

from anki_vocab.dict_parser.models import ParsedWord
from anki_vocab.dict_parser.providers.naver.parser import NaverEntryParser


class EntryDocumentLike(Protocol):
    @property
    def html(self) -> str: ...
    @property
    def query(self) -> str: ...


class ParserProvider(Protocol):
    provider: str

    def parse(
        self,
        *,
        html: str,
        word: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ParsedWord: ...


class ParserRouter:
    def __init__(self, providers: List[ParserProvider]) -> None:
        self._providers = {p.provider: p for p in providers}

    @classmethod
    def default(cls) -> "ParserRouter":
        return cls([NaverEntryParser()])

    def _resolve_provider(self, doc: Any, provider: Optional[str]) -> str:
        # 1) 호출자가 명시
        if provider:
            return provider

        # 2) doc에 provider 비슷한 필드가 있으면 사용
        for key in ("provider", "source", "vendor"):
            v = getattr(doc, key, None)
            if isinstance(v, str) and v.strip():
                return v.strip()

        # 3) parser provider가 1개면 그걸로 처리
        if len(self._providers) == 1:
            return next(iter(self._providers.keys()))

        raise ValueError("Provider를 결정할 수 없습니다. doc에 provider/source/vendor를 넣거나 parse_doc(provider=...)를 사용하세요.")
    
    def parse_doc(
        self,
        doc: EntryDocumentLike,
        *,
        provider: Optional[str] = None,
        word: Optional[str] = None,
    ) -> ParsedWord:
        prov = self._resolve_provider(doc, provider)
        p = self._providers.get(prov)
        if not p:
            raise ValueError(f"no parser for provider={prov}")

        w = (word or getattr(doc, "query", "") or "").strip()

        meta = {
            "provider": prov,
            "url": getattr(doc, "url", "") or "",
            "title": getattr(doc, "title", "") or "",
            "fetched_at": getattr(doc, "fetched_at_iso", "") or getattr(doc, "fetched_at", "") or "",
        }

        return p.parse(html=getattr(doc, "html", "") or "", word=w, meta=meta)

    def parse_docs(self, docs: Iterable[EntryDocumentLike], *, provider: Optional[str] = None) -> List[ParsedWord]:
        return [self.parse_doc(d, provider=provider) for d in docs]
