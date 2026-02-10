"""
Docstring for anki_vocab.dict_crawler.models

역할
- 프로젝트 전역에서 공통으로 쓰는 타입/데이터 모델 정의
- EntryDocument는 수집 결과(HTML 포함)를 표준화한 DTO
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

Locator = tuple[str, str] # Selenium locator를 (By.CSS_SELECTOR, "#id") 같은 형태로 통일
Strategy = Literal["all", "first_non_empty"] # Router 전략을 문자열 리터럴로 고정해 오타/분기 오류 방지


@dataclass(frozen=True)
class EntryDocument:
    source: str
    query: str
    entry_url: str
    html: str
    fetched_at_iso: str
    status: Literal["ok", "empty", "error"] = "ok"
    error: Optional[str] = None
