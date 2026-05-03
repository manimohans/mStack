#!/usr/bin/env python3
"""Build a structured mStack launch evidence pack from messy sources."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from source_intake import SourceRef, collect_sources, parse_source, sentence_candidates


ENTRY_TYPES = [
    "fact",
    "metric",
    "quote",
    "screenshot",
    "customer_pain",
    "allowed_claim",
    "claim_to_avoid",
]

CLAIM_TO_AVOID_TERMS = [
    "all-in-one",
    "best",
    "every",
    "fastest",
    "guarantee",
    "perfect",
    "revolutionary",
    "seamless",
    "game-changing",
]

FACT_TERMS = [
    "add",
    "added",
    "build",
    "built",
    "change",
    "changed",
    "feature",
    "fix",
    "fixed",
    "implement",
    "implemented",
    "release",
    "ship",
    "shipped",
    "support",
    "update",
]

PAIN_TERMS = [
    "blocked",
    "confusing",
    "customer",
    "customers",
    "friction",
    "manual",
    "manually",
    "pain",
    "problem",
    "slow",
    "support",
    "user",
    "users",
    "workaround",
]

SCREENSHOT_RE = re.compile(r"\.(png|jpe?g|gif|webp|avif)\b|screenshot|screen shot|demo", re.I)
METRIC_RE = re.compile(
    r"(?<![A-Za-z])(?:\$?\d[\d,]*(?:\.\d+)?\s*(?:%|x|ms|s|sec|secs|seconds?|minutes?|hours?|days?|k|m|b|users?|customers?|requests?|signups?|latency|revenue|arr|mrr)|\$\d[\d,]*(?:\.\d+)?)",
    re.I,
)
QUOTE_RE = re.compile(r'(^|\s)(customer|user|sales|support|quote)\s*[:\-]|["“”]', re.I)


@dataclass(frozen=True)
class EvidenceEntry:
    type: str
    text: str
    source: str
    confidence: str


def append_unique(entries: list[EvidenceEntry], entry: EvidenceEntry) -> None:
    key = (entry.type, " ".join(entry.text.lower().split()), entry.source)
    for existing in entries:
        existing_key = (existing.type, " ".join(existing.text.lower().split()), existing.source)
        if existing_key == key:
            return
    entries.append(entry)


def term_matches(lower: str, term: str) -> bool:
    if " " in term or "-" in term:
        return term in lower
    return re.search(rf"\b{re.escape(term)}\b", lower) is not None


def classify_line(line: str, source: str) -> EvidenceEntry | None:
    text = " ".join(line.split())
    lower = text.lower()
    explicit = bool(re.match(r"^(fact|metric|quote|screenshot|customer pain|pain|allowed claim|claim to avoid|avoid|do not claim|don't claim)\s*:", lower))

    if lower.startswith(("avoid:", "avoid ", "do not claim", "don't claim", "claim to avoid:")):
        return EvidenceEntry("claim_to_avoid", text, source, "high")
    if lower.startswith(("allowed claim:", "safe claim:", "safe to claim:", "claim:")):
        return EvidenceEntry("allowed_claim", text, source, "high")
    if QUOTE_RE.search(text):
        return EvidenceEntry("quote", text, source, "high" if explicit else "medium")
    if METRIC_RE.search(text):
        return EvidenceEntry("metric", text, source, "high" if explicit else "medium")
    if SCREENSHOT_RE.search(text):
        return EvidenceEntry("screenshot", text, source, "high" if explicit else "medium")
    if any(term_matches(lower, term) for term in CLAIM_TO_AVOID_TERMS):
        return EvidenceEntry("claim_to_avoid", text, source, "medium")
    if any(term_matches(lower, term) for term in PAIN_TERMS):
        return EvidenceEntry("customer_pain", text, source, "medium")
    if any(term_matches(lower, term) for term in FACT_TERMS):
        return EvidenceEntry("fact", text, source, "medium")
    return None


def collect_file(path_text: str) -> list[EvidenceEntry]:
    path = Path(path_text).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [EvidenceEntry("claim_to_avoid", f"Unavailable source file: {path_text} ({exc})", path_text, "high")]
    entries: list[EvidenceEntry] = []
    for line in sentence_candidates(text):
        entry = classify_line(line, str(path))
        if entry:
            append_unique(entries, entry)
    return entries


def intake_entries(raw_sources: list[str], repo: str | None) -> list[EvidenceEntry]:
    result = collect_sources(raw_sources, repo)
    entries: list[EvidenceEntry] = []

    source_labels = []
    for source in result.get("sources", []):
        if source.get("type") == "file":
            source_labels.append(str(source.get("path", "source")))
        else:
            source_labels.append(str(source.get("url") or source.get("ref") or "source"))
    source_label = ", ".join(source_labels) if source_labels else "source-intake"

    mapping = {
        "shipped_scope": "fact",
        "user_pain": "customer_pain",
        "tradeoffs": "fact",
        "claims_to_avoid": "claim_to_avoid",
    }
    for bucket, entry_type in mapping.items():
        for item in result.get(bucket, []):
            append_unique(entries, EvidenceEntry(entry_type, item, source_label, "medium"))

    for item in result.get("proof", []):
        entry_type = "metric" if METRIC_RE.search(item) else "screenshot" if SCREENSHOT_RE.search(item) else "fact"
        append_unique(entries, EvidenceEntry(entry_type, item, source_label, "medium"))

    return entries


def collect_evidence(raw_sources: list[str], repo: str | None) -> list[EvidenceEntry]:
    entries: list[EvidenceEntry] = []
    github_sources: list[str] = []

    for raw in raw_sources:
        ref = parse_source(raw, repo)
        if ref.kind == "file":
            path = Path(ref.value).expanduser()
            if SCREENSHOT_RE.search(ref.value) and (not path.exists() or path.is_file()):
                confidence = "high" if path.exists() else "low"
                append_unique(entries, EvidenceEntry("screenshot", f"Screenshot artifact: {ref.value}", ref.value, confidence))
            elif path.exists() and path.is_file():
                for entry in collect_file(ref.value):
                    append_unique(entries, entry)
            elif path.exists() and path.is_dir():
                append_unique(entries, EvidenceEntry("claim_to_avoid", f"Source is a directory, not a readable evidence file: {ref.value}", ref.value, "high"))
            else:
                append_unique(entries, EvidenceEntry("claim_to_avoid", f"Missing source file: {ref.value}", ref.value, "high"))
        elif isinstance(ref, SourceRef):
            github_sources.append(raw)

    if github_sources:
        for entry in intake_entries(github_sources, repo):
            append_unique(entries, entry)

    return entries


def counts_by_type(entries: list[EvidenceEntry]) -> dict[str, int]:
    return {entry_type: sum(1 for entry in entries if entry.type == entry_type) for entry_type in ENTRY_TYPES}


def render_jsonl(entries: list[EvidenceEntry]) -> str:
    return "\n".join(json.dumps(asdict(entry), sort_keys=True) for entry in entries) + ("\n" if entries else "")


def render_json(entries: list[EvidenceEntry]) -> str:
    data: dict[str, Any] = {
        "entries": [asdict(entry) for entry in entries],
        "counts": counts_by_type(entries),
    }
    return json.dumps(data, indent=2) + "\n"


def render_markdown(entries: list[EvidenceEntry]) -> str:
    lines = ["# Evidence Pack", "", "## Summary"]
    counts = counts_by_type(entries)
    for entry_type in ENTRY_TYPES:
        lines.append(f"- {entry_type}: {counts[entry_type]}")

    for entry_type in ENTRY_TYPES:
        typed = [entry for entry in entries if entry.type == entry_type]
        lines.extend(["", f"## {entry_type.replace('_', ' ').title()}"])
        if not typed:
            lines.append("- Missing: no evidence found.")
            continue
        for entry in typed:
            lines.append(f"- [{entry.confidence}] {entry.text} (source: {entry.source})")
    return "\n".join(lines) + "\n"


def output_path(slug: str | None, output: str | None) -> Path | None:
    if output:
        return Path(output).expanduser()
    if slug:
        safe_slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", slug.strip()).strip("-").lower()
        if not safe_slug:
            raise SystemExit("--slug must contain at least one letter or number")
        return Path(".mstack") / "evidence" / f"{safe_slug}.jsonl"
    return None


def run_self_test() -> int:
    fixture = """# Release notes

- Added evidence packs for launch proof.
- Customers were manually copying metrics into drafts.
- Metric: 42% fewer missing proof placeholders in review.
- Quote: "This keeps the launch honest."
- Screenshot: docs/images/evidence-pack.png
- Allowed claim: evidence is collected before drafting.
- Avoid claiming every source is verified automatically.
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "release.md"
        path.write_text(fixture)
        entries = collect_evidence([str(path)], None)

    counts = counts_by_type(entries)
    assert counts["fact"] >= 1
    assert counts["customer_pain"] >= 1
    assert counts["metric"] >= 1
    assert counts["quote"] >= 1
    assert counts["screenshot"] >= 1
    assert counts["allowed_claim"] >= 1
    assert counts["claim_to_avoid"] >= 1
    assert '"type": "metric"' in render_jsonl(entries)
    assert "# Evidence Pack" in render_markdown(entries)
    print("OK evidence pack self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a structured evidence pack for mStack launch work")
    parser.add_argument("sources", nargs="*", metavar="SOURCE", help="GitHub PR/issue ref or local source file")
    parser.add_argument("--repo", help="GitHub repository in owner/name form for pr:N or issue:N refs")
    parser.add_argument("--slug", help="write JSONL to .mstack/evidence/{slug}.jsonl")
    parser.add_argument("--output", help="write output to this path")
    parser.add_argument("--format", choices=["markdown", "json", "jsonl"], default="markdown")
    parser.add_argument("--self-test", action="store_true", help="run offline parser and renderer checks")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()
    if not args.sources:
        parser.error("at least one SOURCE is required")

    entries = collect_evidence(args.sources, args.repo)
    if args.format == "json":
        rendered = render_json(entries)
    elif args.format == "jsonl":
        rendered = render_jsonl(entries)
    else:
        rendered = render_markdown(entries)

    path = output_path(args.slug, args.output)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".jsonl" and args.format == "markdown":
            path.write_text(render_jsonl(entries))
        else:
            path.write_text(rendered)
        print(f"WROTE {path}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
