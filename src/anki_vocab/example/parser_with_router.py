from __future__ import annotations

import json

from anki_vocab.dict_crawler import DictionaryRouter, NaverDictProvider
from anki_vocab.dict_parser.router import ParserRouter


if __name__ == "__main__":
    parser = ParserRouter.default()

    with DictionaryRouter([NaverDictProvider()]) as router:
        docs = router.search("do", strategy="first_non_empty")

    for doc in docs:
        data = parser.parse_doc(doc)
        print(json.dumps(data, ensure_ascii=False, indent=2))
