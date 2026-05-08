#!/usr/bin/env python3
"""Collect launch source context from GitHub refs and local files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SECTION_KEYS = [
    "shipped_scope",
    "user_pain",
    "proof",
    "tradeoffs",
    "unknowns",
    "claims_to_avoid",
]

KEYWORDS = {
    "shipped_scope": [
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
    ],
    "user_pain": [
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
    ],
    "proof": [
        "benchmark",
        "comment",
        "demo",
        "example",
        "metric",
        "proof",
        "quote",
        "screenshot",
        "test",
        "usage",
    ],
    "tradeoffs": [
        "constraint",
        "defer",
        "deferred",
        "instead",
        "limit",
        "not",
        "scope",
        "tradeoff",
        "won't",
    ],
    "unknowns": [
        "?",
        "missing",
        "needs",
        "open question",
        "todo",
        "unknown",
    ],
    "claims_to_avoid": [
        "all-in-one",
        "best",
        "every",
        "fastest",
        "guarantee",
        "perfect",
        "revolutionary",
        "seamless",
    ],
}


@dataclass(frozen=True)
class SourceRef:
    kind: str
    value: str
    repo: str | None = None


def empty_result() -> dict[str, Any]:
    result: dict[str, Any] = {"sources": []}
    for key in SECTION_KEYS:
        result[key] = []
    return result


def append_unique(items: list[str], item: str) -> None:
    clean = " ".join(item.split())
    if clean and clean not in items:
        items.append(clean)


def sentence_candidates(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^\d+[.)]\s+", "", line)
        if len(line) < 8:
            continue
        lines.append(line)
    return lines


def classify_text(text: str, prefix: str = "") -> dict[str, list[str]]:
    buckets = {key: [] for key in SECTION_KEYS}
    for line in sentence_candidates(text):
        lower = line.lower()
        if lower.startswith(("missing:", "unknown:", "todo:")):
            append_unique(buckets["unknowns"], f"{prefix}{line}" if prefix else line)
            continue
        if lower.startswith(("avoid ", "avoid:", "do not claim", "don't claim")):
            append_unique(buckets["claims_to_avoid"], f"{prefix}{line}" if prefix else line)
            continue
        for key, terms in KEYWORDS.items():
            if any(term_matches(lower, term) for term in terms):
                append_unique(buckets[key], f"{prefix}{line}" if prefix else line)
                break
    return buckets


def term_matches(lower: str, term: str) -> bool:
    if term == "?":
        return "?" in lower
    if " " in term or "-" in term or "'" in term:
        return term in lower
    return re.search(rf"\b{re.escape(term)}\b", lower) is not None


def merge_buckets(result: dict[str, Any], buckets: dict[str, list[str]], limit: int = 8) -> None:
    for key in SECTION_KEYS:
        for item in buckets.get(key, []):
            if len(result[key]) < limit:
                append_unique(result[key], item)


def parse_source(raw: str, default_repo: str | None) -> SourceRef:
    if raw.startswith("pr:") and raw[3:].isdigit():
        return SourceRef("pr", raw[3:], default_repo)
    if raw.startswith("issue:") and raw[6:].isdigit():
        return SourceRef("issue", raw[6:], default_repo)

    parsed = urlparse(raw)
    if parsed.netloc.lower() == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 4 and parts[2] in {"pull", "issues"} and parts[3].isdigit():
            kind = "pr" if parts[2] == "pull" else "issue"
            return SourceRef(kind, parts[3], f"{parts[0]}/{parts[1]}")

    return SourceRef("file", raw, default_repo)


def run_gh(args: list[str]) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    if shutil.which("gh") is None:
        return None, "gh CLI is not installed or not on PATH"

    proc = subprocess.run(
        ["gh", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or f"gh exited with {proc.returncode}"
        return None, message
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"gh returned invalid JSON: {exc}"


def gh_args(kind: str, number: str, repo: str | None) -> list[str]:
    base = [kind, "view", number]
    if repo:
        base.extend(["--repo", repo])
    if kind == "pr":
        fields = "number,title,body,labels,files,url,comments,reviews"
    else:
        fields = "number,title,body,labels,url,comments"
    base.extend(["--json", fields])
    return base


def label_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names = []
    for item in value:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def body_parts(data: dict[str, Any]) -> list[str]:
    parts = [str(data.get("title") or ""), str(data.get("body") or "")]
    for comment in data.get("comments") or []:
        if isinstance(comment, dict):
            parts.append(str(comment.get("body") or ""))
    for review in data.get("reviews") or []:
        if isinstance(review, dict):
            parts.append(str(review.get("body") or ""))
    return [part for part in parts if part.strip()]


def collect_github(source: SourceRef) -> dict[str, Any]:
    result = empty_result()
    source_label = f"{source.kind}:{source.value}"
    data, error = run_gh(gh_args(source.kind, source.value, source.repo))
    if error or not isinstance(data, dict):
        result["sources"].append(
            {
                "type": source.kind,
                "ref": source_label,
                "repo": source.repo,
                "status": "unavailable",
                "message": error or "No data returned",
            }
        )
        append_unique(result["unknowns"], f"{source_label}: unavailable source context ({error or 'no data returned'}).")
        return result

    title = str(data.get("title") or "").strip()
    url = str(data.get("url") or "").strip()
    result["sources"].append(
        {
            "type": source.kind,
            "ref": source_label,
            "repo": source.repo,
            "title": title,
            "url": url,
            "labels": label_names(data.get("labels")),
            "status": "ok",
        }
    )
    if title:
        append_unique(result["shipped_scope"], f"{source_label}: {title}")

    if source.kind == "pr":
        files = data.get("files") or []
        changed = []
        for item in files:
            if isinstance(item, dict) and item.get("path"):
                additions = item.get("additions", 0)
                deletions = item.get("deletions", 0)
                changed.append(f"{item['path']} (+{additions}/-{deletions})")
        if changed:
            append_unique(result["proof"], f"{source_label}: changed files: {', '.join(changed[:12])}")

    merge_buckets(result, classify_text("\n".join(body_parts(data)), f"{source_label}: "))
    return result


def collect_file(path_text: str) -> dict[str, Any]:
    result = empty_result()
    path = Path(path_text).expanduser()
    source = {"type": "file", "path": str(path), "status": "ok"}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        source["status"] = "unavailable"
        source["message"] = str(exc)
        result["sources"].append(source)
        append_unique(result["unknowns"], f"{path_text}: unavailable file source ({exc}).")
        return result

    result["sources"].append(source)
    merge_buckets(result, classify_text(text, f"{path}: "))
    if not any(result[key] for key in SECTION_KEYS):
        append_unique(result["unknowns"], f"{path}: no obvious launch facts found; read source manually before drafting.")
    return result


def merge_result(into: dict[str, Any], item: dict[str, Any]) -> None:
    into["sources"].extend(item.get("sources", []))
    for key in SECTION_KEYS:
        for value in item.get(key, []):
            append_unique(into[key], value)


def source_health(result: dict[str, Any]) -> dict[str, Any]:
    sources = result.get("sources", [])
    ok_count = sum(1 for source in sources if source.get("status", "ok") == "ok")
    unavailable = [source for source in sources if source.get("status", "ok") != "ok"]
    fact_count = sum(len(result.get(key, [])) for key in ["shipped_scope", "user_pain", "proof", "tradeoffs"])
    reasons: list[str] = []

    if not sources:
        verdict = "blocked"
        reasons.append("No sources were provided.")
    elif unavailable:
        verdict = "blocked"
        reasons.append(f"{len(unavailable)} source(s) could not be resolved.")
    elif fact_count == 0:
        verdict = "needs_review"
        reasons.append("Sources resolved, but no clear launch facts were detected.")
    elif not result.get("proof"):
        verdict = "needs_review"
        reasons.append("Sources resolved, but proof cues are thin or missing.")
    else:
        verdict = "safe_to_use"
        reasons.append("Sources resolved with usable launch facts and proof cues.")

    if verdict == "blocked":
        next_step = "Fix source refs, authentication, network access, or file paths before downstream mStack work."
    elif verdict == "needs_review":
        next_step = "Review the sources manually or add stronger proof before turning this into claims."
    else:
        next_step = "Use this intake as source context for evidence-pack, product-context, claim-check, or publish-check."

    return {
        "verdict": verdict,
        "total_sources": len(sources),
        "ok_sources": ok_count,
        "unavailable_sources": len(unavailable),
        "source_backed_fact_count": fact_count,
        "reasons": reasons,
        "next_step": next_step,
    }


def collect_sources(raw_sources: list[str], repo: str | None) -> dict[str, Any]:
    result = empty_result()
    for raw in raw_sources:
        ref = parse_source(raw, repo)
        if ref.kind in {"pr", "issue"}:
            merge_result(result, collect_github(ref))
        else:
            merge_result(result, collect_file(ref.value))
    result["source_health"] = source_health(result)
    return result


def markdown_list(items: list[str]) -> str:
    if not items:
        return "- Missing: no source-backed facts found."
    return "\n".join(f"- {item}" for item in items)


def render_markdown(result: dict[str, Any]) -> str:
    health = result.get("source_health") or source_health(result)
    lines = [
        "# Source Intake",
        "",
        "## Source Health Report",
        f"- Verdict: {health['verdict']}",
        f"- Sources resolved: {health['ok_sources']}/{health['total_sources']}",
        f"- Unavailable sources: {health['unavailable_sources']}",
        f"- Source-backed facts: {health['source_backed_fact_count']}",
        f"- Reason: {' '.join(health['reasons'])}",
        f"- Next step: {health['next_step']}",
        "",
        "## Sources",
    ]
    if result["sources"]:
        for source in result["sources"]:
            status = source.get("status", "ok")
            if source.get("type") == "file":
                label = source.get("path")
            else:
                label = source.get("url") or source.get("ref")
            detail = source.get("title") or source.get("message") or ""
            suffix = f" - {detail}" if detail else ""
            lines.append(f"- {status}: {source.get('type')}: {label}{suffix}")
    else:
        lines.append("- Missing: no sources provided.")

    headings = [
        ("shipped_scope", "Shipped Scope"),
        ("user_pain", "User Pain"),
        ("proof", "Proof"),
        ("tradeoffs", "Tradeoffs Or Constraints"),
        ("unknowns", "Unknowns"),
        ("claims_to_avoid", "Claims To Avoid"),
    ]
    for key, heading in headings:
        lines.extend(["", f"## {heading}", markdown_list(result[key])])
    return "\n".join(lines) + "\n"


def run_self_test() -> int:
    parsed = parse_source("https://github.com/acme/widget/pull/42", None)
    assert parsed == SourceRef("pr", "42", "acme/widget")
    parsed = parse_source("issue:7", "acme/widget")
    assert parsed == SourceRef("issue", "7", "acme/widget")

    fixture = """# Release notes

- Added source intake for PRs and docs.
- Customers were manually pasting changelogs into launch briefs.
- Deferred Slack parsing to keep scope small.
- Proof: README example and parser self-test.
- Missing: real customer quote.
- Avoid claiming every source is supported.
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "release.md"
        path.write_text(fixture)
        result = collect_sources([str(path)], None)

    assert result["sources"][0]["status"] == "ok"
    assert any("source intake" in item.lower() for item in result["shipped_scope"])
    assert any("manually pasting" in item.lower() for item in result["user_pain"])
    assert any("slack" in item.lower() for item in result["tradeoffs"])
    assert any("customer quote" in item.lower() for item in result["unknowns"])
    assert any("every source" in item.lower() for item in result["claims_to_avoid"])
    assert result["source_health"]["verdict"] == "safe_to_use"
    assert result["source_health"]["ok_sources"] == 1
    assert "# Source Intake" in render_markdown(result)
    assert "## Source Health Report" in render_markdown(result)
    print("OK source intake self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect source context for mStack product briefs")
    parser.add_argument("sources", nargs="*", metavar="SOURCE", help="GitHub PR/issue ref or local file path")
    parser.add_argument("--repo", help="GitHub repository in owner/name form for pr:N or issue:N refs")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when required source context is blocked")
    parser.add_argument("--self-test", action="store_true", help="run offline parser and renderer checks")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if not args.sources:
        parser.error("at least one SOURCE is required")

    result = collect_sources(args.sources, args.repo)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(render_markdown(result), end="")
    if args.strict and result["source_health"]["verdict"] == "blocked":
        print("mstack-source-intake: blocked source context in strict mode", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
