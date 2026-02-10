"""
Docstring for anki_vocab.dict_crawler.providers.base

역할
- 사이트 Provider가 반드시 제공해야 하는 기능을 인터페이스(protocol)로 정의
- 상위 계층(Router)은 Provider 구체 구현을 몰라도 동작
"""

from __future__ import annotations

from typing import Protocol, List

from ..models import EntryDocument


class DictionaryProvider(Protocol):
    source: str

    def search(self, query: str) -> List[EntryDocument]:
        ...

    def close(self) -> None:
        ...

    def __enter__(self) -> "DictionaryProvider":
        ...

    def __exit__(self, exc_type, exc, tb) -> None:
        ...
