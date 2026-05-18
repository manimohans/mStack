#!/usr/bin/env python3
"""Search and save durable mStack product messaging learnings."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEARNING_TYPES = (
    "voice",
    "positioning",
    "proof",
    "customer-language",
    "avoid",
    "channel",
    "retro",
)

VAGUE_MARKERS = {"", "todo", "tbd", "replace this", "n/a", "none"}


@dataclass(frozen=True)
class LearningFile:
    project_root: Path
    slug: str
    path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_root(start: Path) -> Path | None:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    root = output.strip()
    return Path(root) if root else None


def slug_value(root: Path) -> str:
    raw = str(root)
    slug = "".join(char if char.isalnum() or char in "._-" else "-" for char in raw)
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "default"


def mstack_home() -> Path:
    import os

    raw = os.environ.get("MSTACK_HOME") or os.environ.get("MSTACK_STATE_DIR")
    return Path(raw).expanduser() if raw else Path.home() / ".mstack"


def learning_file(root_arg: str | None = None) -> LearningFile:
    start = Path(root_arg).expanduser() if root_arg else Path.cwd()
    project_root = git_root(start) or start.resolve()
    slug = slug_value(project_root)
    return LearningFile(project_root, slug, mstack_home() / "projects" / slug / "learnings.jsonl")


def read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL entry: {exc}") from exc
        if not isinstance(raw, dict):
            raise SystemExit(f"{path}:{line_number}: entry must be a JSON object")
        entries.append(normalize_entry(raw))
    return entries


def normalize_entry(raw: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "ts": str(raw.get("ts") or utc_now()),
        "type": str(raw.get("type") or "retro"),
        "source": str(raw.get("source") or "user"),
        "learning": str(raw.get("learning") or "").strip(),
        "example": str(raw.get("example") or "").strip(),
    }
    if entry["type"] not in LEARNING_TYPES:
        entry["type"] = "retro"
    return entry


def write_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(entry, separators=(",", ":")) + "\n" for entry in entries)
    path.write_text(text)


def append_entry(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(entry, separators=(",", ":")) + "\n")


def matches(entry: dict[str, Any], query: str | None, type_filter: str | None) -> bool:
    if type_filter and entry.get("type") != type_filter:
        return False
    if not query:
        return True
    haystack = " ".join(str(entry.get(key, "")) for key in ("type", "source", "learning", "example")).lower()
    return query.lower() in haystack


def render_markdown(entries: list[dict[str, Any]], path: Path) -> str:
    lines = ["## Relevant Learnings"]
    if not entries:
        lines.append("- None found.")
    else:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in entries:
            grouped[str(entry["type"])].append(entry)
        for type_name in LEARNING_TYPES:
            for entry in grouped.get(type_name, []):
                example = f" Example: {entry['example']}" if entry.get("example") else ""
                lines.append(f"- {type_name}: {entry['learning']}{example}")

    lines.extend(
        [
            "",
            "## How This Should Affect The Next Update",
            "- Apply the relevant lessons to angle, proof, vocabulary, CTA, and channel choices.",
            "",
            "## Gaps",
        ]
    )
    lines.append("- No saved learnings found for this filter." if not entries else "- Check whether newer launch evidence should update these lessons.")
    lines.extend(["", f"File: {path}"])
    return "\n".join(lines)


def command_path(args: argparse.Namespace) -> int:
    info = learning_file(args.root)
    info.path.parent.mkdir(parents=True, exist_ok=True)
    print(info.path)
    return 0


def command_save(args: argparse.Namespace) -> int:
    info = learning_file(args.root)
    learning = args.learning or ""
    if args.stdin:
        learning = sys.stdin.read().strip()
    learning = learning.strip()
    if not learning:
        raise SystemExit("save requires a learning string or --stdin")

    entry = normalize_entry(
        {
            "ts": utc_now(),
            "type": args.type,
            "source": args.source,
            "learning": learning,
            "example": args.example or "",
        }
    )
    append_entry(info.path, entry)
    print("## Updated Learnings")
    print("- Added: 1")
    print("- Removed: 0")
    print(f"- File: {info.path}")
    return 0


def command_search(args: argparse.Namespace) -> int:
    info = learning_file(args.root)
    entries = [entry for entry in read_entries(info.path) if matches(entry, args.query, args.type)]
    if args.format == "json":
        print(json.dumps({"file": str(info.path), "entries": entries}, indent=2))
    else:
        print(render_markdown(entries, info.path))
    return 0


def command_export(args: argparse.Namespace) -> int:
    info = learning_file(args.root)
    entries = [entry for entry in read_entries(info.path) if matches(entry, args.query, args.type)]
    if args.format == "jsonl":
        for entry in entries:
            print(json.dumps(entry, separators=(",", ":")))
    elif args.format == "json":
        print(json.dumps({"file": str(info.path), "entries": entries}, indent=2))
    else:
        print(render_markdown(entries, info.path))
    return 0


def prune_plan(entries: list[dict[str, Any]], type_filter: str | None, contains: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    needle = contains.lower() if contains else None

    for entry in entries:
        learning = str(entry.get("learning", "")).strip()
        key = (str(entry.get("type", "")), learning.lower(), str(entry.get("example", "")).strip().lower())
        in_scope = (not type_filter or entry.get("type") == type_filter) and (not needle or needle in learning.lower())
        vague = learning.lower() in VAGUE_MARKERS or len(learning) < 12
        duplicate = key in seen
        if in_scope and (vague or duplicate):
            removed.append(entry)
            continue
        kept.append(entry)
        seen.add(key)
    return kept, removed


def command_prune(args: argparse.Namespace) -> int:
    info = learning_file(args.root)
    entries = read_entries(info.path)
    kept, removed = prune_plan(entries, args.type, args.contains)
    if args.apply:
        write_entries(info.path, kept)

    print("## Updated Learnings")
    print(f"- Added: 0")
    print(f"- Removed: {len(removed) if args.apply else 0}")
    print(f"- Would remove: {len(removed)}")
    print(f"- File: {info.path}")
    if not args.apply:
        print("- Mode: dry run; pass --apply to rewrite the file.")
    for entry in removed[:10]:
        print(f"- Candidate: {entry['type']}: {entry['learning']}")
    return 0


def run_self_test() -> None:
    import os

    with tempfile.TemporaryDirectory() as tmp:
        old_home = os.environ.get("MSTACK_HOME")
        os.environ["MSTACK_HOME"] = str(Path(tmp) / "state")
        root = Path(tmp) / "project"
        root.mkdir()
        try:
            info = learning_file(str(root))
            assert info.path.name == "learnings.jsonl"
            append_entry(info.path, normalize_entry({"type": "voice", "source": "user", "learning": "Use concrete product language.", "example": "Replace generic launch copy."}))
            append_entry(info.path, normalize_entry({"type": "voice", "source": "user", "learning": "Use concrete product language.", "example": "Replace generic launch copy."}))
            entries = read_entries(info.path)
            assert len(entries) == 2
            assert matches(entries[0], "concrete", "voice")
            kept, removed = prune_plan(entries, None, None)
            assert len(kept) == 1
            assert len(removed) == 1
            markdown = render_markdown(kept, info.path)
            assert "Use concrete product language." in markdown
        finally:
            if old_home is None:
                os.environ.pop("MSTACK_HOME", None)
            else:
                os.environ["MSTACK_HOME"] = old_home
    print("OK learn self-test")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search and save durable mStack product messaging learnings")
    parser.add_argument("--root", help="project root used to derive the mStack learning file")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("path", help="print the project learning file path").set_defaults(func=command_path)

    save = sub.add_parser("save", help="append a durable learning")
    save.add_argument("learning", nargs="?", help="learning text to append")
    save.add_argument("--type", choices=LEARNING_TYPES, default="retro")
    save.add_argument("--source", default="user")
    save.add_argument("--example", default="")
    save.add_argument("--stdin", action="store_true", help="read learning text from stdin")
    save.set_defaults(func=command_save)

    search = sub.add_parser("search", help="search saved learnings")
    search.add_argument("query", nargs="?", help="case-insensitive search text")
    search.add_argument("--type", choices=LEARNING_TYPES)
    search.add_argument("--format", choices=("markdown", "json"), default="markdown")
    search.set_defaults(func=command_search)

    export = sub.add_parser("export", help="export saved learnings")
    export.add_argument("query", nargs="?", help="case-insensitive search text")
    export.add_argument("--type", choices=LEARNING_TYPES)
    export.add_argument("--format", choices=("markdown", "json", "jsonl"), default="markdown")
    export.set_defaults(func=command_export)

    prune = sub.add_parser("prune", help="remove duplicate or vague learnings")
    prune.add_argument("--type", choices=LEARNING_TYPES)
    prune.add_argument("--contains", help="only consider learnings containing this text")
    prune.add_argument("--apply", action="store_true", help="rewrite the learning file")
    prune.set_defaults(func=command_prune)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
