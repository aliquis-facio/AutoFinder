from typing import List
from dataclasses import dataclass


@dataclass
class WordEntry:
    word: str
    pronounce: str
    meaning: str
    image_url: str
    tag: List[str]