from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from anki_vocab.dict_crawler import DictionaryRouter, NaverDictProvider, NaverProviderConfig
from anki_vocab.dict_parser.router import ParserRouter
from anki_vocab.formatter.formatter import Formatter
from anki_vocab.tsv_writer import TsvWriter


def load_words(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    words_path = base_dir / "test_words.txt"

    out_path = Path("output") / "anki_notes.tsv"

    words = load_words(words_path)
    parser = ParserRouter.default()
    formatter = Formatter()

    provider = NaverDictProvider(NaverProviderConfig(headless=True))

    with DictionaryRouter([provider]) as crawler, TsvWriter(out_path) as writer:
        for query in words:
            docs = crawler.search(query, strategy="first_non_empty")
            if not docs:
                print(f"[skip] no result: {query}")
                continue

            # Parser -> ParsedWord(TypedDict) 리스트
            parsed_list = parser.parse_docs(docs)

            # Formatter.format_tag()가 entry_links 길이로 동음이의어 태그를 붙이도록 되어 있어서 주입
            entry_links = [d.entry_url for d in docs]
            is_homonym = len(parsed_list) >= 2

            for idx, parsed in enumerate(parsed_list, start=1):
                # ✅ TypedDict(ParsedWord) -> Dict[str, Any]로 변환해서 Pylance 타입 에러 제거
                data: Dict[str, Any] = dict(parsed)
                data["entry_links"] = entry_links

                formatter.set_data(data)

                fields = formatter.to_tsv_fields(
                    word=formatter.word,  # or query
                    homonym_no=(idx if is_homonym else None),
                )

                writer.write_row(
                    fields,
                    field_names=["word", "pronunciation", "conjugation", "meaning", "tags"],
                )

            print(f"[ok] {query}: {len(parsed_list)} entries")

    print(f"[DONE] wrote: {out_path}")


if __name__ == "__main__":
    main()
