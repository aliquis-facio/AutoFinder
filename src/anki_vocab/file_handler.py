# file_handler.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union, List


TagsType = Union[str, Sequence[str], None]


@dataclass(frozen=True)
class FileHandlerConfig:
    """
    TSV(탭 구분) 텍스트 내보내기 설정.
    Anki import 안전성을 위해 기본값은 보수적으로 설정.
    """
    delimiter: str = "\t"
    encoding: str = "utf-8"
    line_ending: str = "\n"

    # 필드 안전 처리
    tab_replacement: str = " "      # 필드 내 탭 제거(필드 밀림 방지)
    newline_replacement: str = "<br>"  # 필드 내 개행 제거(한 줄 = 한 노트 유지)
    strip_fields: bool = True

    # 동음이의어 구분(윗첨자 숫자)
    disambiguate_word: bool = True


class FileHandler:
    """
    Formatter 결과를 TSV(txt)로 저장하는 라이터.

    - write_row(fields): 일반 row 쓰기
    - write_anki_note(word, pronunciation, meaning, tags): Anki용 4필드 쓰기
    """

    _SUPERSCRIPT_DIGITS = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    }

    def __init__(
        self,
        out_path: str | Path,
        *,
        mode: str = "w",
        config: FileHandlerConfig | None = None,
    ) -> None:
        self.path: Path = Path(out_path)
        self.mode = mode
        self.config = config or FileHandlerConfig()

        self._fp = None  # type: ignore[assignment]
        self._open()

    def _open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self.path.open(
            self.mode,
            encoding=self.config.encoding,
            newline=self.config.line_ending,
        )

    def close(self) -> None:
        if self._fp is not None:
            self._fp.close()
            self._fp = None

    def __enter__(self) -> "FileHandler":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _sanitize_field(self, s: str) -> str:
        s = (s or "")
        s = str(s).replace("\t", self.config.tab_replacement)
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = s.replace("\n", self.config.newline_replacement)
        return s.strip() if self.config.strip_fields else s

    def _normalize_tags(self, tags: TagsType) -> str:
        if tags is None:
            return ""
        if isinstance(tags, str):
            t = tags.replace("\t", " ").replace("\r", " ").replace("\n", " ")
            return " ".join(t.split())

        parts: List[str] = []
        for x in tags:
            if x is None:
                continue
            t = str(x).replace("\t", " ").replace("\r", " ").replace("\n", " ")
            t = " ".join(t.split())
            if t:
                parts.append(t)
        return " ".join(parts)

    def _to_superscript(self, n: int) -> str:
        """
        1 -> ¹, 2 -> ², 10 -> ¹⁰ (각 자리수 조합)
        """
        if n <= 0:
            return ""
        return "".join(self._SUPERSCRIPT_DIGITS[ch] for ch in str(n))

    def write_row(self, fields: Sequence[str]) -> None:
        if self._fp is None:
            raise RuntimeError("FileHandler is closed.")
        safe = [self._sanitize_field(x) for x in fields]
        self._fp.write(self.config.delimiter.join(safe) + self.config.line_ending)

    def write_note(
        self,
        *,
        word: str,
        pronunciation: str,
        conjugation: str,
        meaning: str,
        tags: TagsType = "",
        homonym_no: Optional[int] = None,
    ) -> None:
        """
        5필드 고정: word / pronunciation / conjugation / meaning / tags
        homonym_no: 동음이의어 번호(1,2,3...) -> word¹, word² ...
        """
        final_word = word
        if self.config.disambiguate_word and homonym_no is not None:
            final_word = f"{word}{self._to_superscript(homonym_no)}"

        tag_str = self._normalize_tags(tags)

        self.write_row([final_word, pronunciation, conjugation, meaning, tag_str])