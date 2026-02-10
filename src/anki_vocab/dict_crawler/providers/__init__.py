"""
Docstring for anki_vocab.dict_crawler.providers

역할
- 외부에서 from dict_crawler.providers import NaverDictProvider처럼 깔끔한 import 경로 제공
- Provider가 늘어나면 여기 export만 추가하면 됨
"""

from .naver import NaverDictProvider, NaverProviderConfig

__all__ = ["NaverDictProvider", "NaverProviderConfig"]
