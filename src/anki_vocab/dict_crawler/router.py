"""
Docstring for anki_vocab.dict_crawler.router

역할
- Provider 여러 개를 등록하고, 어떤 전략으로 조회할지를 결정하는 오케스트레이터

전략
- all: 모든 provider 결과를 합침
- first_non_empty: 우선순위대로 호출하다가 결과가 있다면 종료
"""

from __future__ import annotations

from typing import List

from .models import EntryDocument, Strategy
from .providers.base import DictionaryProvider


class DictionaryRouter:
    def __init__(self, providers: List[DictionaryProvider]) -> None:
        self.providers = providers

    def __enter__(self) -> "DictionaryRouter":
        for p in self.providers:
            p.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for p in self.providers:
            try:
                p.__exit__(exc_type, exc, tb)
            except Exception:
                pass

    def search(self, query: str, strategy: Strategy = "first_non_empty") -> List[EntryDocument]:
        if strategy == "all":
            out: List[EntryDocument] = []
            for p in self.providers:
                out.extend(p.search(query))
            return out

        for p in self.providers:
            docs = p.search(query)
            if docs:
                return docs
        return []
