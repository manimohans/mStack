#!/usr/bin/env python3
"""Heuristic pre-publish claim checker for mStack drafts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ABSOLUTE_TERMS = {
    "all",
    "always",
    "any",
    "best",
    "every",
    "everyone",
    "fastest",
    "guarantee",
    "guaranteed",
    "never",
    "only",
    "perfect",
}

LAUNCH_GLOSS = {
    "cutting-edge",
    "game-changing",
    "leverage",
    "revolutionary",
    "robust",
    "seamless",
    "supercharge",
    "unlock",
}

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "because",
    "been",
    "before",
    "being",
    "but",
    "can",
    "could",
    "did",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "into",
    "its",
    "now",
    "our",
    "out",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "this",
    "those",
    "through",
    "to",
    "use",
    "user",
    "users",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "without",
    "you",
    "your",
}


@dataclass(frozen=True)
class ClaimAudit:
    claim: str
    status: str
    evidence: str
    fix: str
    flags: tuple[str, ...]


def normalize(text: str) -> str:
    return " ".join(text.split())


def read_text(path: str) -> str:
    try:
        return Path(path).expanduser().read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Path(path).expanduser().read_text(encoding="utf-8", errors="replace")


def line_candidates(text: str) -> list[str]:
    items: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^\|?\s*Claim\s*\|.*$", "", line, flags=re.I)
        line = re.sub(r"^\d+[.)]\s+", "", line)
        line = line.strip(" |")
        if len(line) >= 12:
            items.append(line)
    return items


def sentence_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for line in line_candidates(text):
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\[])", line):
            clean = normalize(part.strip(" -"))
            if len(clean) >= 24:
                candidates.append(clean)
    return dedupe(candidates)


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9][a-z0-9-]*", text.lower())
        if len(word) > 2 and word not in STOPWORDS
    }


def numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:[.,]\d+)?%?x?\b", text))


def quoted_phrases(text: str) -> set[str]:
    return {
        normalize(match)
        for match in re.findall(r'"([^"]{8,})"|\'([^\']{8,})\'', text)
        for match in match
        if match
    }


def source_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"evidence": [], "risk": []}
    current = "evidence"
    for raw in text.splitlines():
        line = raw.rstrip()
        heading = line.strip().lower()
        if heading.startswith("## "):
            if any(term in heading for term in ["unknown", "claim", "avoid", "missing"]):
                current = "risk"
            else:
                current = "evidence"
            continue
        sections[current].append(line)
    return {key: "\n".join(value) for key, value in sections.items()}


def material_claims(draft: str) -> list[str]:
    claims: list[str] = []
    for candidate in sentence_candidates(draft):
        lower = candidate.lower()
        if lower.startswith(("subject:", "preview:", "cta:", "button:", "link:")):
            continue
        if len(words(candidate)) < 3:
            continue
        if any(term in lower for term in ["shipped", "launch", "release", "now", "replace", "avoid", "support", "faster", "less", "more", "all", "every"]):
            claims.append(candidate)
            continue
        if numbers(candidate) or quoted_phrases(candidate):
            claims.append(candidate)
            continue
        if re.search(r"\b(can|will|lets|allows|helps|means|gives|makes|keeps|removes|adds|supports|improves)\b", lower):
            claims.append(candidate)
    return dedupe(claims)


def best_evidence(claim: str, evidence_lines: list[str]) -> tuple[int, str]:
    claim_words = words(claim)
    best_score = 0
    best_line = ""
    for line in evidence_lines:
        line_words = words(line)
        overlap = len(claim_words & line_words)
        number_bonus = 2 if numbers(claim) and numbers(claim) <= numbers(line) else 0
        quote_bonus = 3 if quoted_phrases(claim) and quoted_phrases(claim) <= quoted_phrases(line) else 0
        score = overlap + number_bonus + quote_bonus
        if score > best_score:
            best_score = score
            best_line = line
    return best_score, best_line


def risky_terms(claim: str) -> list[str]:
    lower_words = words(claim)
    phrase_lower = claim.lower()
    flags = sorted(term for term in ABSOLUTE_TERMS if term in lower_words)
    flags.extend(sorted(term for term in LAUNCH_GLOSS if term in phrase_lower))
    return flags


def audit_claims(draft: str, source_text: str) -> list[ClaimAudit]:
    sections = source_sections(source_text)
    evidence_lines = line_candidates(sections["evidence"])
    evidence_blob = sections["evidence"].lower()
    risk_blob = sections["risk"].lower()
    source_numbers = numbers(source_text)
    source_quotes = quoted_phrases(source_text)

    audits: list[ClaimAudit] = []
    for claim in material_claims(draft):
        flags = risky_terms(claim)
        missing_metric = bool(numbers(claim) - source_numbers)
        missing_quote = bool(quoted_phrases(claim) - source_quotes)
        contradicted = any(term and term in claim.lower() for term in words(risk_blob) if len(term) > 4)
        score, evidence = best_evidence(claim, evidence_lines)

        if missing_metric:
            status = "missing"
            fix = "Replace the metric with a bracketed placeholder or add the source metric."
            evidence_text = "Metric is not present in supplied source context."
        elif missing_quote:
            status = "missing"
            fix = "Remove the quote or add the approved source quote."
            evidence_text = "Quote is not present in supplied source context."
        elif contradicted:
            status = "missing"
            fix = "Narrow the claim so it does not conflict with claims-to-avoid or unknowns."
            evidence_text = "Claim overlaps with source risk or claims-to-avoid sections."
        elif flags and not any(flag in evidence_blob for flag in flags):
            status = "missing"
            fix = "Remove the absolute or hype term, or add direct proof for it."
            evidence_text = f"Risky term not source-backed: {', '.join(flags)}."
        elif score >= 4:
            status = "confirmed"
            fix = "No change needed."
            evidence_text = evidence
        elif score >= 2:
            status = "inferred"
            fix = "Keep only if this inference is acceptable, or add direct proof."
            evidence_text = evidence or "Partially supported by supplied source context."
        else:
            status = "missing"
            fix = "Rewrite to a sourced fact or add proof."
            evidence_text = "No matching source support found."

        audits.append(ClaimAudit(claim, status, evidence_text, fix, tuple(flags)))
    return audits


def publish_status(audits: list[ClaimAudit]) -> str:
    if not audits:
        return "needs review"
    if any(audit.status == "missing" for audit in audits):
        return "blocked"
    if any(audit.status == "inferred" for audit in audits):
        return "needs review"
    return "pass"


def safe_rewrite(audit: ClaimAudit) -> str:
    claim = audit.claim
    for term in audit.flags:
        claim = re.sub(rf"\b{re.escape(term)}\b", "", claim, flags=re.I)
    claim = re.sub(r"\b\d+(?:[.,]\d+)?%?x?\b", "[metric]", claim)
    claim = re.sub(r'"[^"]{8,}"|\'[^\']{8,}\'', "[approved quote]", claim)
    claim = normalize(claim)
    if audit.status == "confirmed":
        return claim
    if claim == audit.claim:
        return f"[Verify or narrow] {claim}"
    return claim


def render_markdown(audits: list[ClaimAudit]) -> str:
    status = publish_status(audits)
    lines = ["## Publish Status", status, "", "## Claim Audit"]
    lines.append("| Claim | Status | Evidence | Fix |")
    lines.append("|---|---|---|---|")
    if not audits:
        lines.append("| No material claims found. | needs review | No product claims were detected. | Review manually before publishing. |")
    for audit in audits:
        lines.append(
            "| "
            + " | ".join(
                escape_cell(value)
                for value in [audit.claim, audit.status, audit.evidence, audit.fix]
            )
            + " |"
        )

    blockers = [audit for audit in audits if audit.status == "missing"]
    lines.extend(["", "## Blockers"])
    if blockers:
        for audit in blockers:
            lines.append(f"- {audit.claim}: {audit.fix}")
    else:
        lines.append("- None.")

    rewrites = [audit for audit in audits if audit.status != "confirmed"]
    lines.extend(["", "## Safe Rewrite"])
    if rewrites:
        for audit in rewrites:
            lines.append(f"- {safe_rewrite(audit)}")
    else:
        lines.append("All detected material claims are confirmed by the supplied source context.")

    lines.extend(["", "## Proof To Add"])
    if blockers:
        for audit in blockers:
            lines.append(f"- {audit.evidence}")
    else:
        lines.append("- None required by this heuristic check.")

    return "\n".join(lines) + "\n"


def escape_cell(value: str) -> str:
    return normalize(value).replace("|", "\\|")


def render_json(audits: list[ClaimAudit]) -> str:
    payload: dict[str, Any] = {
        "publish_status": publish_status(audits),
        "claims": [
            {
                "claim": audit.claim,
                "status": audit.status,
                "evidence": audit.evidence,
                "fix": audit.fix,
                "flags": list(audit.flags),
            }
            for audit in audits
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def run_self_test() -> int:
    source = """# Source Intake

## Shipped Scope
- Added a dashboard that replaces Friday CSV exports.

## Proof
- Customer note: managers were exporting CSVs every Friday.
- Changed files: dashboard.py, tests/test_dashboard.py

## Tradeoffs Or Constraints
- Deferred Slack alerts.

## Claims To Avoid
- Avoid claiming all reporting is automated.
"""
    draft = """We launched the best team dashboard for every manager.

It replaces Friday CSV exports for managers.

It automates all reporting and saves 40% of the week.
"""
    audits = audit_claims(draft, source)
    assert any(audit.status == "confirmed" and "CSV exports" in audit.claim for audit in audits)
    assert any(audit.status == "missing" and "40%" in audit.claim for audit in audits)
    assert publish_status(audits) == "blocked"
    assert publish_status([]) == "needs review"
    no_source = audit_claims("It replaces Friday CSV exports for managers.", "")
    assert no_source and no_source[0].status == "missing"
    rendered = render_markdown(audits)
    assert "## Publish Status" in rendered
    assert "blocked" in rendered

    with tempfile.TemporaryDirectory() as tmp:
        draft_path = Path(tmp) / "draft.md"
        source_path = Path(tmp) / "source.md"
        draft_path.write_text(draft)
        source_path.write_text(source)
        loaded = read_text(str(draft_path)) + read_text(str(source_path))
    assert "dashboard" in loaded
    print("OK claim check self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check product draft claims against source context")
    parser.add_argument("draft", nargs="?", help="Draft file to audit")
    parser.add_argument("sources", nargs="*", help="Source context files, such as source-intake output or launch brief")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--self-test", action="store_true", help="run offline claim-check checks")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if not args.draft:
        parser.error("DRAFT is required unless --self-test is used")

    draft = read_text(args.draft)
    source_text = "\n".join(read_text(path) for path in args.sources)

    audits = audit_claims(draft, source_text)
    output = render_json(audits) if args.format == "json" else render_markdown(audits)
    print(output, end="")
    return 1 if publish_status(audits) == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
