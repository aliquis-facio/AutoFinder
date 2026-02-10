# tsv_writer.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO, Optional, Sequence, Union


TagsType = Union[str, Sequence[str], None]


@dataclass(frozen=True)
class TsvWriterConfig:
    delimiter: str = "\t"
    encoding: str = "utf-8"
    line_ending: str = "\n"

    # Writer는 "가공"하지 않고, TSV가 깨지는 입력은 예외로 막는다(권장).
    validate_no_delimiter_in_fields: bool = True
    validate_no_newlines_in_fields: bool = True

    # 동음이의어 구분(윗첨자): word 필드에만 적용(HTML 수정 아님)
    disambiguate_word: bool = True


class TsvWriter:
    """
    5필드 TSV Writer: word / pronunciation / conjugation / meaning / tags
    - HTML(meaning)은 그대로 출력(수정 없음)
    - TSV 구조를 깨는 문자(탭/개행)는 기본적으로 예외 처리
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
        config: TsvWriterConfig | None = None,
    ) -> None:
        self.path = Path(out_path)
        self.mode = mode
        self.config = config or TsvWriterConfig()
        self._fp: IO[str] | None = None
        self._open()

    def _open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self.path.open(
            self.mode,
            encoding=self.config.encoding,
            newline=self.config.line_ending,  # OS별 개행 변환 방지
        )

    def close(self) -> None:
        if self._fp is not None:
            self._fp.close()
            self._fp = None

    def __enter__(self) -> "TsvWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _to_superscript(self, n: int) -> str:
        if n <= 0:
            return ""
        return "".join(self._SUPERSCRIPT_DIGITS[ch] for ch in str(n))

    def _normalize_tags(self, tags: TagsType) -> str:
        # tags는 HTML이 아니고 TSV 한 필드여야 하므로 문자열로 정리만 함
        if tags is None:
            return ""
        if isinstance(tags, str):
            return tags
        return " ".join(str(x) for x in tags if x is not None)

    def _validate_field(self, field_name: str, value: str) -> None:
        if self.config.validate_no_delimiter_in_fields and self.config.delimiter in value:
            raise ValueError(
                f"[TsvWriter] Field '{field_name}' contains delimiter {repr(self.config.delimiter)}."
            )
        if self.config.validate_no_newlines_in_fields and ("\n" in value or "\r" in value):
            raise ValueError(
                f"[TsvWriter] Field '{field_name}' contains newline characters (\\n/\\r)."
            )

    def write_row(self, fields: Sequence[str], *, field_names: Sequence[str] | None = None) -> None:
        if self._fp is None:
            raise RuntimeError("TsvWriter is closed.")

        if field_names is None:
            field_names = [f"field_{i}" for i in range(len(fields))]

        for name, val in zip(field_names, fields):
            self._validate_field(name, val)

        self._fp.write(self.config.delimiter.join(fields) + self.config.line_ending)

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
        # NOTE: meaning(HTML)은 그대로 출력. 여기서 어떤 치환도 하지 않음.
        final_word = word
        if self.config.disambiguate_word and homonym_no is not None:
            final_word = f"{word}{self._to_superscript(homonym_no)}"

        tag_str = self._normalize_tags(tags)

        self.write_row(
            [final_word, pronunciation, conjugation, meaning, tag_str],
            field_names=["word", "pronunciation", "conjugation", "meaning", "tags"],
        )
