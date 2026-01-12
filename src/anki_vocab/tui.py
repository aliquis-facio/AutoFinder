# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

from anki_vocab.crawler import Crawler
from anki_vocab.parser import Parser
from anki_vocab.formatter import Formatter
from anki_vocab.file_handler import FileHandler, FileHandlerConfig


_WORD_SPLIT_RE = re.compile(r"[,\s]+")


def _default_output_dir() -> Path:
    """Desktop이 있으면 Desktop, 없으면 현재 작업 디렉토리."""
    home = Path.home()
    desktop = home / "Desktop"
    return desktop if desktop.is_dir() else Path.cwd()


def _is_plausible_word(token: str) -> bool:
    """
    영단어 토큰 간단 검증:
    - 알파벳 시작
    - 알파벳/하이픈/어포스트로피 허용
    """
    return re.fullmatch(r"[A-Za-z][A-Za-z'\-]*", token) is not None


def _entry_get(entry: Any, key: str, default: str = "") -> str:
    """
    WordEntryDict(=dict) 우선, dataclass/obj 형태도 fallback.
    """
    if isinstance(entry, dict):
        v = entry.get(key, default)
        return "" if v is None else str(v)
    v = getattr(entry, key, default)
    return "" if v is None else str(v)


def _tags_to_string(tags: Any) -> str:
    """
    tags:
    - List[str] / Set[str] / Tuple[str] → "#tag1 #tag2"
    - str → 그대로(이미 "#..."일 수 있으니 보존)
    - None → ""
    """
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags.strip()
    if isinstance(tags, (list, set, tuple)):
        out: List[str] = []
        for t in tags:
            if t is None:
                continue
            ts = str(t).strip()
            if not ts:
                continue
            out.append(ts if ts.startswith("#") else f"#{ts}")
        return " ".join(out)
    return str(tags).strip()


def _normalize_entry_fields(entry: Any) -> Tuple[str, str, str, str, str]:
    """
    최종 TSV 5필드(README 요구):
    word, pronounce, meaning, example, tags

    - 프로젝트 내 키 변형 흡수:
      pronounce/pronunciation
      tag/tags
      example/examples
    """
    word = _entry_get(entry, "word")
    pronounce = _entry_get(entry, "pronounce") or _entry_get(entry, "pronunciation")

    meaning = _entry_get(entry, "meaning")

    # example은 프로젝트마다 example(문자열) 또는 examples(리스트/문자열)일 수 있음
    example_raw: Any
    if isinstance(entry, dict):
        example_raw = entry.get("example", "")
        if not example_raw:
            example_raw = entry.get("examples", "")
    else:
        example_raw = getattr(entry, "example", "") or getattr(entry, "examples", "")

    example = ""
    if isinstance(example_raw, str):
        example = example_raw
    elif isinstance(example_raw, (list, tuple)):
        # list면 줄바꿈을 <br>로 합친다는 기존 컨벤션을 존중
        example = "<br>".join([str(x).strip() for x in example_raw if str(x).strip()])
    else:
        example = str(example_raw) if example_raw is not None else ""

    tags_raw: Any
    if isinstance(entry, dict):
        tags_raw = entry.get("tag", None)
        if tags_raw is None:
            tags_raw = entry.get("tags", None)
    else:
        tags_raw = getattr(entry, "tag", None) or getattr(entry, "tags", None)

    tags = _tags_to_string(tags_raw)
    return word, pronounce, meaning, example, tags


@dataclass
class TuiConfig:
    dict_type: str = "naver"  # "naver" | "cambridge"(확장 가능)
    output_dir: Path = _default_output_dir()
    filename_template: str = "{date}_영단어.txt"
    file_handler_config: FileHandlerConfig = FileHandlerConfig()


class AnkiTui:
    """
    1) 사용자로부터 여러 영단어 입력
    2) Selenium 크롤링
    3) Parser/Formatter로 WordEntryDict 생성
    4) FileHandler로 날짜 기반 파일에 누적 저장(TSV)
    """

    def __init__(self, config: Optional[TuiConfig] = None) -> None:
        self.cfg = config or TuiConfig()
        today = time.strftime("%Y%m%d")
        self.file_name = self.cfg.filename_template.format(date=today)

        self.input_words: Set[str] = set()
        self.error_words: List[str] = []

        self.commands_info: Dict[str, str] = {
            "!help": "show help",
            "!list": "list queued words",
            "!remove <word>": "remove a word from queue",
            "!clear": "clear queued words",
            "!run": "crawl + save now (keep the program running)",
            "!quit": "crawl + save and exit",
        }

        self.finish: bool = False

    # -------------------------
    # 저장(FileHandler)
    # -------------------------
    def _output_path(self) -> Path:
        self.cfg.output_dir.mkdir(parents=True, exist_ok=True)
        return self.cfg.output_dir / self.file_name

    def _write_with_file_handler(self, rows: List[List[str]], out_path: Path) -> None:
        """
        FileHandler API가 프로젝트에서 어떻게 정의되어 있든 동작하게끔
        '우선 시도' 방식으로 연결.

        기대하는 대표 패턴들:
        - FileHandler(config).write_rows(rows, path)
        - FileHandler(config).write(rows, path)
        - FileHandler(config).export(rows, path)
        - FileHandler(config).append_rows(rows, path)
        - FileHandler(config).open(path) + write_row(...)
        """
        cfg = self.cfg.file_handler_config

        # 생성자 시그니처가 다를 수 있어 둘 다 시도
        try:
            handler = FileHandler(cfg)  # type: ignore[arg-type]
        except TypeError:
            handler = FileHandler(config=cfg)  # type: ignore[call-arg]

        candidates: List[Tuple[str, Callable[..., Any]]] = []
        for name in ("write_rows", "append_rows", "write", "export", "append", "save"):
            if hasattr(handler, name):
                candidates.append((name, getattr(handler, name)))

        # 1) (rows, path) 또는 (path, rows) 형태 둘 다 시도
        for name, fn in candidates:
            try:
                fn(rows, out_path)  # type: ignore[misc]
                return
            except TypeError:
                pass
            try:
                fn(out_path, rows)  # type: ignore[misc]
                return
            except TypeError:
                pass

        # 2) open/write_row/close 스타일
        if hasattr(handler, "open") and hasattr(handler, "close"):
            opened = False
            try:
                handler.open(out_path)  # type: ignore[misc]
                opened = True

                if hasattr(handler, "write_row"):
                    for r in rows:
                        handler.write_row(r)  # type: ignore[misc]
                    return

                if hasattr(handler, "write"):
                    for r in rows:
                        handler.write(r)  # type: ignore[misc]
                    return
            finally:
                if opened:
                    try:
                        handler.close()  # type: ignore[misc]
                    except Exception:
                        pass

        # 여기까지 왔다면 FileHandler API를 못 찾은 것
        raise AttributeError(
            "FileHandler에 저장 메서드를 찾지 못했습니다. "
            "(write_rows/write/export/append_rows/open+write_row 등의 메서드 존재 여부를 확인하세요.)"
        )

    # -------------------------
    # 크롤링/파싱/포매팅 파이프라인
    # -------------------------
    def _crawl_raw_list(self, crawler: Crawler, word: str) -> List[Any]:
        if hasattr(crawler, "search_from_naver") and self.cfg.dict_type == "naver":
            return crawler.search_from_naver(word)  # type: ignore[misc]
        if hasattr(crawler, "search_from_cambridge") and self.cfg.dict_type == "cambridge":
            return crawler.search_from_cambridge(word)  # type: ignore[misc]
        if hasattr(crawler, "search_word"):
            try:
                return crawler.search_word(word, dict_type=self.cfg.dict_type)  # type: ignore[misc]
            except TypeError:
                return crawler.search_word(word)  # type: ignore[misc]
        raise AttributeError("Crawler에 검색 메서드가 없습니다. (search_from_naver/search_word 등 확인 필요)")

    def _parse(self, raw: Any, word: str) -> Any:
        p = Parser(raw)  # type: ignore[arg-type]
        if hasattr(p, "parse_to_json"):
            return p.parse_to_json(word)  # type: ignore[misc]
        if hasattr(p, "parse"):
            return p.parse(word)  # type: ignore[misc]
        if hasattr(p, "to_dict"):
            return p.to_dict(word)  # type: ignore[misc]
        raise AttributeError("Parser에 parse_to_json/parse/to_dict 메서드가 없습니다.")

    def _format(self, parsed_or_raw: Any):
        f = Formatter(parsed_or_raw)  # type: ignore[arg-type]
        if hasattr(f, "to_entry"):
            return f.to_entry()  # type: ignore[no-any-return]
        if hasattr(f, "format"):
            return f.format()  # type: ignore[no-any-return]
        if hasattr(f, "run"):
            return f.run()  # type: ignore[no-any-return]
        raise AttributeError("Formatter에 to_entry/format/run 메서드가 없습니다.")

    def _to_entry(self, word: str, raw: Any):
        # 1) Formatter가 raw(html)를 직접 처리하는 구현이면 우선
        try:
            return self._format(raw)
        except Exception:
            pass

        # 2) Parser → Formatter 흐름
        parsed = self._parse(raw, word)
        return self._format(parsed)



    def run_crawl_and_save(self) -> None:
        if not self.input_words:
            print("입력된 단어가 없습니다.\n")
            return

        crawler = Crawler()
        entries: List[Any] = []
        processed: Set[str] = set()

        try:
            words_sorted = sorted(self.input_words, key=lambda x: x.lower())
            for i, w in enumerate(words_sorted, start=1):
                print(f"[{i}/{len(words_sorted)}] 검색 중: {w}")
                try:
                    raw_list = self._crawl_raw_list(crawler, w)
                    if not raw_list:
                        print(f"[WARN] 결과 없음: {w}\n")
                        self.error_words.append(w)
                        continue

                    for raw in raw_list:
                        entry = self._to_entry(w, raw)
                        entries.append(entry)

                    processed.add(w)

                except Exception as e:
                    self.error_words.append(w)
                    print(f"[ERROR] {w} → {type(e).__name__}: {e}\n")

        finally:
            try:
                crawler.driver_close()
            except Exception:
                pass

        # 저장
        if entries:
            out_path = self._output_path()

            # FileHandler가 “formatter에서 받은 5개 필드”만 내보내는 설계이므로,
            # 여기서 5필드 rows로 변환해 전달합니다.
            rows: List[List[str]] = []
            for e in entries:
                word, pronounce, meaning, example, tags = _normalize_entry_fields(e)
                rows.append([word, pronounce, meaning, example, tags])

            self._write_with_file_handler(rows, out_path)
            print(f"\n총 {len(entries)}개의 항목을 '{out_path}' 에 저장했습니다.\n")

        # 에러 단어 표시
        if self.error_words:
            uniq: List[str] = []
            seen: Set[str] = set()
            for w in self.error_words:
                if w not in seen:
                    seen.add(w)
                    uniq.append(w)
            print("--- error words ---")
            for w in uniq:
                print(w)
            print()

        # 처리 후 큐 정리: 성공한 단어는 제거하고 실패한 단어만 남김
        failed_set = set(self.error_words)
        self.input_words = failed_set
        self.error_words.clear()

    # -------------------------
    # 커맨드
    # -------------------------
    def cmd_help(self, _: List[str]) -> None:
        print("\n--- commands ---")
        for k, v in self.commands_info.items():
            print(f"{k:<16} : {v}")
        print()

    def cmd_list(self, _: List[str]) -> None:
        if not self.input_words:
            print("대기 중인 단어가 없습니다.\n")
            return
        print("\n--- queued words ---")
        for w in sorted(self.input_words, key=lambda x: x.lower()):
            print(w)
        print()

    def cmd_remove(self, parse_lst: List[str]) -> None:
        if len(parse_lst) < 2:
            print("사용법: !remove <word>\n")
            return
        w = parse_lst[1].strip()
        if w in self.input_words:
            self.input_words.remove(w)
            print(f"removed: {w}\n")
        else:
            print(f"not found: {w}\n")

    def cmd_clear(self, _: List[str]) -> None:
        self.input_words.clear()
        print("cleared.\n")

    def cmd_run(self, _: List[str]) -> None:
        self.run_crawl_and_save()

    def cmd_quit(self, _: List[str]) -> None:
        self.run_crawl_and_save()
        self.finish = True

    # -------------------------
    # 메인 루프
    # -------------------------
    def main(self) -> None:
        print("사전을 선택하세요.")
        print("1) 네이버 영한 사전 (기본)")
        print("2) 캠브리지 영영 사전 (미구현일 수 있음 - 구현되어 있으면 사용)")
        choice = input("번호 입력 후 Enter: ").strip()

        if choice == "2":
            self.cfg.dict_type = "cambridge"
            print("캠브리지를 선택했습니다.\n")
        else:
            self.cfg.dict_type = "naver"
            print("네이버 영한 사전을 사용합니다.\n")

        self.cmd_help([])

        while not self.finish:
            intro_msg = "영단어 입력 (여러 개: 공백/쉼표) | 명령: !help\n-> "
            line = input(intro_msg).strip()
            print()

            if not line:
                continue

            if line.startswith("!"):
                parse_lst = line.split()
                cmd = parse_lst[0].lower()

                if cmd == "!help":
                    self.cmd_help(parse_lst)
                elif cmd == "!list":
                    self.cmd_list(parse_lst)
                elif cmd == "!remove":
                    self.cmd_remove(parse_lst)
                elif cmd == "!clear":
                    self.cmd_clear(parse_lst)
                elif cmd == "!run":
                    self.cmd_run(parse_lst)
                elif cmd == "!quit":
                    self.cmd_quit(parse_lst)
                else:
                    print(f"알 수 없는 명령입니다: {line}\n")
                continue

            # 일반 입력(단어 추가)
            tokens = line
            added = 0
            skipped: List[str] = []

            for t in tokens:
                if not _is_plausible_word(t):
                    skipped.append(t)
                    continue
                self.input_words.add(t)
                added += 1

            if added:
                print(f"추가됨: {added}개 (총 {len(self.input_words)}개 대기)\n")
            if skipped:
                print(f"무시됨(형식 불일치): {', '.join(skipped)}\n")


if __name__ == "__main__":
    AnkiTui().main()
