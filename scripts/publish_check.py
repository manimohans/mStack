#!/usr/bin/env python3
"""Final publication-readiness check for mStack launch packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from claim_check import audit_claims, publish_status
from messaging_eval import AI_GLOSS


EVIDENCE_TYPES = [
    "fact",
    "metric",
    "quote",
    "screenshot",
    "customer_pain",
    "allowed_claim",
    "claim_to_avoid",
]

DEFAULT_CHANNELS = [
    "Changelog",
    "Release Email",
    "Social Post",
    "Internal Slack",
    "Sales Note",
]

MESSAGE_MAP_FIELDS = [
    "Thesis",
    "Proof",
    "CTA",
    "Audience",
    "Product boundary",
    "Claims to avoid",
]

PLACEHOLDER_RE = re.compile(
    r"\b(TBD|TODO|FIXME|TK)\b|\[(?:metric|quote|customer|company|link|cta|date|owner|proof|screenshot|todo|tk)[^\]]*\]|\{\{[^}]+\}\}",
    re.I,
)
METRIC_RE = re.compile(
    r"(?<![A-Za-z])(?:\$?\d[\d,]*(?:\.\d+)?\s*(?:%|x|ms|s|sec|secs|seconds?|minutes?|hours?|days?|k|m|b|users?|customers?|requests?|signups?|latency|revenue|arr|mrr)|\$\d[\d,]*(?:\.\d+)?)",
    re.I,
)
QUOTE_RE = re.compile(r'(^|\s)(customer|user|sales|support|quote)\s*[:\-]|["“”]', re.I)
SCREENSHOT_RE = re.compile(r"\.(png|jpe?g|gif|webp|avif)\b|screenshot|screen shot|demo", re.I)
PAIN_RE = re.compile(r"\b(blocked|confusing|customer|customers|friction|manual|manually|pain|problem|slow|support|user|users|workaround)\b", re.I)
FACT_RE = re.compile(r"\b(add|added|built|changed|feature|fix|fixed|implemented|release|ship|shipped|support|update)\b", re.I)
AVOID_RE = re.compile(r"\b(avoid|do not claim|don't claim|claim to avoid|unsupported|overbroad)\b", re.I)
ALLOWED_RE = re.compile(r"\b(allowed claim|safe claim|safe to claim|approved claim)\b", re.I)
BLOCKED_SOURCE_RE = re.compile(r"^\s*[-*]?\s*Verdict\s*:\s*blocked\s*$", re.I | re.M)


@dataclass(frozen=True)
class Issue:
    severity: str
    category: str
    detail: str
    fix: str


@dataclass(frozen=True)
class PublishReport:
    status: str
    evidence_counts: dict[str, int]
    channel_presence: dict[str, bool]
    claim_counts: dict[str, int]
    blocking_issues: list[Issue]
    review_items: list[Issue]
    next_fix: str


def read_text(path: str) -> str:
    try:
        return Path(path).expanduser().read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SystemExit(f"{path}: {exc}") from exc


def clean_line(line: str) -> str:
    line = re.sub(r"^[-*]\s+", "", line.strip())
    line = re.sub(r"^#{1,6}\s+", "", line)
    return " ".join(line.split())


def empty_counts() -> dict[str, int]:
    return {entry_type: 0 for entry_type in EVIDENCE_TYPES}


def add_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    for entry_type in EVIDENCE_TYPES:
        left[entry_type] += right.get(entry_type, 0)
    return left


def counts_from_jsonl(text: str) -> dict[str, int] | None:
    counts = empty_counts()
    parsed = 0
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(item, dict) and item.get("type") in counts:
            counts[str(item["type"])] += 1
            parsed += 1
    return counts if parsed else None


def counts_from_summary(text: str) -> dict[str, int]:
    counts = empty_counts()
    for entry_type in EVIDENCE_TYPES:
        label = entry_type.replace("_", "[ _-]")
        match = re.search(rf"^\s*[-*]\s+{label}\s*:\s*(\d+)\s*$", text, re.I | re.M)
        if match:
            counts[entry_type] = int(match.group(1))
    return counts


def counts_from_lines(text: str) -> dict[str, int]:
    counts = empty_counts()
    for raw in text.splitlines():
        line = clean_line(raw)
        if len(line) < 8:
            continue
        lower = line.lower()
        if AVOID_RE.search(line):
            counts["claim_to_avoid"] += 1
        if ALLOWED_RE.search(line):
            counts["allowed_claim"] += 1
        if QUOTE_RE.search(line):
            counts["quote"] += 1
        if METRIC_RE.search(line):
            counts["metric"] += 1
        if SCREENSHOT_RE.search(line):
            counts["screenshot"] += 1
        if PAIN_RE.search(line):
            counts["customer_pain"] += 1
        if FACT_RE.search(line) and "claim_to_avoid" not in lower:
            counts["fact"] += 1
    return counts


def evidence_counts(source_text: str) -> dict[str, int]:
    counts = empty_counts()
    if not source_text.strip():
        return counts
    jsonl_counts = counts_from_jsonl(source_text)
    if jsonl_counts is not None:
        return jsonl_counts
    summary_counts = counts_from_summary(source_text)
    if any(summary_counts.values()):
        return summary_counts
    add_counts(counts, counts_from_lines(source_text))
    return counts


def section_present(text: str, name: str) -> bool:
    return re.search(rf"^#{{2,4}}\s+{re.escape(name)}\s*$", text, re.I | re.M) is not None


def channel_presence(asset_text: str) -> dict[str, bool]:
    return {channel: section_present(asset_text, channel) for channel in DEFAULT_CHANNELS}


def missing_message_map_fields(asset_text: str) -> list[str]:
    missing: list[str] = []
    for field in MESSAGE_MAP_FIELDS:
        if not re.search(rf"^\s*[-*]?\s*{re.escape(field)}\s*:\s*\S+", asset_text, re.I | re.M):
            missing.append(field)
    return missing


def claim_counts(audits: list[Any]) -> dict[str, int]:
    return {
        "confirmed": sum(1 for audit in audits if audit.status == "confirmed"),
        "inferred": sum(1 for audit in audits if audit.status == "inferred"),
        "missing": sum(1 for audit in audits if audit.status == "missing"),
    }


def first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end == -1:
        line_end = len(text)
    return clean_line(text[line_start:line_end])


def source_label(source: dict[str, Any]) -> str:
    label = source.get("url") or source.get("ref") or source.get("path") or "unknown source"
    status = source.get("status") or "unknown"
    message = source.get("message")
    if message:
        return f"{label} ({status}: {message})"
    return f"{label} ({status})"


def json_values(text: str) -> list[Any]:
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        pass

    values: list[Any] = []
    decoder = json.JSONDecoder()
    index = 0
    while index < len(text):
        match = re.search(r"[\{\[]", text[index:])
        if not match:
            break
        start = index + match.start()
        try:
            value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        values.append(value)
        index = start + end
    return values


def source_health_issue(source_text: str) -> Issue | None:
    payload = next(
        (
            value
            for value in json_values(source_text)
            if isinstance(value, dict) and isinstance(value.get("source_health"), dict)
        ),
        None,
    )
    if not isinstance(payload, dict):
        return None

    health = payload.get("source_health")
    if not isinstance(health, dict) or health.get("verdict") != "blocked":
        return None

    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    unavailable = [source for source in sources if isinstance(source, dict) and source.get("status", "ok") != "ok"]
    if unavailable:
        shown = ", ".join(source_label(source) for source in unavailable[:3])
        extra = "" if len(unavailable) <= 3 else f", plus {len(unavailable) - 3} more"
        detail = f"Source-intake JSON reported blocked source context: {shown}{extra}."
    else:
        reasons = health.get("reasons")
        reason_text = (
            " ".join(str(reason) for reason in reasons)
            if isinstance(reasons, list)
            else str(reasons or "").strip()
        )
        detail = "Source-intake JSON reported blocked source context."
        if reason_text:
            detail += f" Reason: {reason_text}"

    return Issue(
        "blocked",
        "source context",
        detail,
        "Fix unavailable PRs, issues, docs, files, authentication, or network access before publishing.",
    )


def build_report(asset_text: str, source_text: str) -> PublishReport:
    counts = evidence_counts(source_text)
    channels = channel_presence(asset_text)
    audits = audit_claims(asset_text, source_text)
    claim_summary = claim_counts(audits)
    blockers: list[Issue] = []
    review: list[Issue] = []

    if not source_text.strip():
        blockers.append(Issue("blocked", "source context", "No source context was supplied.", "Add an evidence pack, source-intake output, launch brief, or approved proof file."))
    elif issue := source_health_issue(source_text):
        blockers.append(issue)
    elif BLOCKED_SOURCE_RE.search(source_text):
        blockers.append(Issue("blocked", "source context", "Source-intake reported blocked source context.", "Fix unavailable PRs, issues, docs, files, authentication, or network access before publishing."))

    claim_status = publish_status(audits)
    if claim_status == "blocked":
        missing_claims = [audit.claim for audit in audits if audit.status == "missing"]
        example = f" Example: {missing_claims[0]}" if missing_claims else ""
        blockers.append(Issue("blocked", "claims", f"{claim_summary['missing']} material claim(s) are missing source support.{example}", "Run claim-check details and rewrite or source every missing claim."))
    elif claim_status == "needs review":
        review.append(Issue("needs review", "claims", f"{claim_summary['inferred']} material claim(s) are inferred rather than directly confirmed.", "Add direct proof or explicitly accept the inference before publishing."))

    placeholder = first_match(PLACEHOLDER_RE, asset_text)
    if placeholder:
        blockers.append(Issue("blocked", "placeholders", f"Unresolved placeholder found: {placeholder}", "Replace the placeholder with approved copy or remove it."))

    if counts["metric"] + counts["quote"] + counts["screenshot"] == 0:
        blockers.append(Issue("blocked", "evidence coverage", "No metric, quote, screenshot, or demo artifact was found in source context.", "Add at least one concrete proof artifact before publishing."))
    if counts["customer_pain"] == 0:
        review.append(Issue("needs review", "evidence coverage", "No customer pain or user workflow evidence was found.", "Add support notes, sales notes, user language, or a concrete workflow problem."))
    if counts["claim_to_avoid"] == 0:
        review.append(Issue("needs review", "evidence coverage", "No claims-to-avoid were supplied.", "Add explicit boundaries so launch copy does not overreach."))

    missing_fields = missing_message_map_fields(asset_text)
    if missing_fields:
        review.append(Issue("needs review", "message map", f"Missing message map field(s): {', '.join(missing_fields)}.", "Fill in the message map before final channel review."))

    if any(channels.values()):
        missing_channels = [channel for channel, present in channels.items() if not present]
        if missing_channels:
            review.append(Issue("needs review", "channels", f"Missing default launch channel(s): {', '.join(missing_channels)}.", "Add the missing channel assets or note that they were intentionally skipped."))
    else:
        review.append(Issue("needs review", "channels", "No standard launch-pack channel sections were detected.", "Confirm this is a single-asset publish check or add launch-pack channel sections."))

    gloss_hits = sorted(term for term in AI_GLOSS if term in asset_text.lower())
    if gloss_hits:
        review.append(Issue("needs review", "copy hygiene", f"AI-gloss term(s) found: {', '.join(gloss_hits)}.", "Replace generic launch language with concrete product consequence."))

    if "we're excited to announce" in asset_text.lower() or "we are excited to announce" in asset_text.lower():
        review.append(Issue("needs review", "copy hygiene", "Launch-template phrasing found.", "Lead with the product consequence instead of announcement boilerplate."))

    status = "pass"
    if blockers:
        status = "blocked"
    elif review:
        status = "needs review"

    next_fix = "No fix required."
    if blockers:
        next_fix = blockers[0].fix
    elif review:
        next_fix = review[0].fix

    return PublishReport(status, counts, channels, claim_summary, blockers, review, next_fix)


def render_markdown(report: PublishReport) -> str:
    lines = ["## Publish Readiness", report.status, "", "## Blocking Issues"]
    if report.blocking_issues:
        for issue in report.blocking_issues:
            lines.append(f"- {issue.detail} Fix: {issue.fix}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Review Items"])
    if report.review_items:
        for issue in report.review_items:
            lines.append(f"- {issue.detail} Fix: {issue.fix}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Evidence Coverage"])
    for entry_type in EVIDENCE_TYPES:
        lines.append(f"- {entry_type}: {report.evidence_counts[entry_type]}")

    lines.extend(["", "## Channel Check"])
    for channel, present in report.channel_presence.items():
        lines.append(f"- {channel}: {'present' if present else 'missing'}")

    lines.extend(["", "## Claim Check Summary"])
    for status in ["confirmed", "inferred", "missing"]:
        lines.append(f"- {status}: {report.claim_counts[status]}")

    lines.extend(["", "## Next Fix", report.next_fix])
    return "\n".join(lines) + "\n"


def render_json(report: PublishReport) -> str:
    payload = {
        "status": report.status,
        "evidence_counts": report.evidence_counts,
        "channel_presence": report.channel_presence,
        "claim_counts": report.claim_counts,
        "blocking_issues": [asdict(issue) for issue in report.blocking_issues],
        "review_items": [asdict(issue) for issue in report.review_items],
        "next_fix": report.next_fix,
    }
    return json.dumps(payload, indent=2) + "\n"


def run_self_test() -> int:
    source = """# Evidence Pack

## Summary
- fact: 1
- metric: 1
- quote: 1
- screenshot: 1
- customer_pain: 1
- allowed_claim: 1
- claim_to_avoid: 1

## Fact
- Added team dashboards that replace Friday CSV exports for managers.

## Metric
- Metric: 32% fewer Friday CSV exports in the beta group.

## Quote
- Quote: "This replaces our Friday export ritual."

## Screenshot
- Screenshot: screenshots/team-dashboard.png

## Customer Pain
- Managers were manually exporting CSVs every Friday.

## Allowed Claim
- Allowed claim: managers replace Friday CSV exports with team dashboards.

## Claims To Avoid
- Avoid claiming all reporting is automated.
"""
    package = """## Message Map
- Thesis: Managers replace Friday CSV exports with team dashboards.
- Proof: 32% fewer Friday CSV exports in the beta group.
- CTA: Open the dashboard.
- Audience: Managers.
- Product boundary: Slack alerts are not included.
- Claims to avoid: Do not claim all reporting is automated.

## Assets

### Changelog
Managers replace Friday CSV exports with team dashboards.

### Release Email
Subject: Team dashboards replace Friday CSV exports
Managers replace Friday CSV exports with team dashboards.

### Social Post
Managers replace Friday CSV exports with team dashboards.

### Internal Slack
Managers replace Friday CSV exports with team dashboards.

### Sales Note
Managers replace Friday CSV exports with team dashboards.
"""
    report = build_report(package, source)
    assert report.status == "pass", render_markdown(report)
    linked = build_report(package + "\nRead the [dashboard guide](https://example.com).\n", source)
    assert linked.status == "pass", render_markdown(linked)
    blocked = build_report(package + "\nIt saves 99% of every week with revolutionary dashboards.\n", source)
    assert blocked.status == "blocked"
    assert "99%" in render_markdown(blocked)
    placeholder = build_report(package + "\nCTA: [link]\n", source)
    assert placeholder.status == "blocked"
    blocked_source = build_report(package, "# Source Intake\n\n## Source Health Report\n- Verdict: blocked\n")
    assert blocked_source.status == "blocked"
    blocked_source_json = build_report(
        package,
        json.dumps(
            {
                "sources": [
                    {
                        "type": "issue",
                        "ref": "issue:404",
                        "repo": "owner/project",
                        "status": "unavailable",
                        "message": "not found",
                    }
                ],
                "source_health": {
                    "verdict": "blocked",
                    "total_sources": 1,
                    "ok_sources": 0,
                    "unavailable_sources": 1,
                    "source_backed_fact_count": 0,
                    "reasons": ["1 source(s) could not be resolved."],
                    "next_step": "Fix source refs.",
                },
            }
        ),
    )
    assert blocked_source_json.status == "blocked"
    assert "issue:404" in render_markdown(blocked_source_json)
    embedded_blocked_source_json = build_report(
        package,
        source + "\n" + json.dumps({"source_health": {"verdict": "blocked", "reasons": ["JSON gate blocked."]}}),
    )
    assert embedded_blocked_source_json.status == "blocked"

    jsonl = "\n".join(
        [
            json.dumps({"type": "metric", "text": "Metric: 32% fewer exports", "source": "x", "confidence": "high"}),
            json.dumps({"type": "customer_pain", "text": "Manual Friday exports", "source": "x", "confidence": "high"}),
        ]
    )
    counts = evidence_counts(jsonl)
    assert counts["metric"] == 1
    assert counts["customer_pain"] == 1

    with tempfile.TemporaryDirectory() as tmp:
        asset_path = Path(tmp) / "launch.md"
        source_path = Path(tmp) / "evidence.md"
        asset_path.write_text(package)
        source_path.write_text(source)
        loaded_report = build_report(read_text(str(asset_path)), read_text(str(source_path)))
    assert loaded_report.status == "pass"
    print("OK publish check self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check launch assets for publication readiness")
    parser.add_argument("assets", nargs="?", help="Publish-bound launch asset file")
    parser.add_argument("sources", nargs="*", help="Evidence pack, source-intake output, launch brief, or approved proof files")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--self-test", action="store_true", help="run offline publish-check checks")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()
    if not args.assets:
        parser.error("ASSETS is required unless --self-test is used")

    asset_text = read_text(args.assets)
    source_text = "\n".join(read_text(path) for path in args.sources)
    report = build_report(asset_text, source_text)
    output = render_json(report) if args.format == "json" else render_markdown(report)
    print(output, end="")
    return 1 if report.status == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
