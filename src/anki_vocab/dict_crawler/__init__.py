"""
Docstring for anki_vocab.dict_crawler

역할
- 패키지의 top-level export 정의
- 라이브러리 사용자 입장에선 dict_crawler만 알면 되게 만드는 용도
"""

from .router import DictionaryRouter
from .models import EntryDocument, Strategy
from .providers import NaverDictProvider, NaverProviderConfig

__all__ = [
    "DictionaryRouter",
    "EntryDocument",
    "Strategy",
    "NaverDictProvider",
    "NaverProviderConfig",
]
