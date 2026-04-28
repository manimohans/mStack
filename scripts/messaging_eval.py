#!/usr/bin/env python3
"""Heuristic messaging evals for mStack outputs.

This is intentionally model-free. It gives us a cheap regression gate for the
things mStack should protect: concrete user pain, proof, tradeoffs, restrained
claims, and low AI-gloss.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_GLOSS = {
    "seamless",
    "unlock",
    "supercharge",
    "game-changing",
    "revolutionary",
    "leverage",
    "delve",
    "empower",
    "robust",
    "cutting-edge",
}


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9-]*", text.lower()))


def phrase_hits(text: str, phrases: list[str]) -> list[str]:
    lower = text.lower()
    return [phrase for phrase in phrases if phrase.lower() in lower]


def score_fixture(fixture: dict, candidate: str) -> dict:
    lower = candidate.lower()
    word_count = len(candidate.split())

    expected_hits = phrase_hits(candidate, fixture.get("expected_terms", []))
    proof_hits = phrase_hits(candidate, fixture.get("proof_terms", []))
    tradeoff_hits = phrase_hits(candidate, fixture.get("tradeoff_terms", []))
    banned_hits = phrase_hits(candidate, fixture.get("banned_claims", []))
    gloss_hits = [term for term in AI_GLOSS if term in lower]

    has_number = bool(re.search(r"\b\d+([.%x]| minutes?| hours?| days?| weeks?| users?| teams?| CSVs?)?\b", candidate))
    has_user_scene = any(term in lower for term in ["user", "customer", "manager", "team", "support", "sales"])
    has_consequence = any(term in lower for term in ["now", "instead", "without", "avoid", "replace", "decide"])

    score = 0
    score += min(25, len(expected_hits) * 8)
    score += min(20, len(proof_hits) * 10)
    score += min(15, len(tradeoff_hits) * 15)
    score += 10 if has_number else 0
    score += 10 if has_user_scene else 0
    score += 10 if has_consequence else 0
    score -= min(25, len(banned_hits) * 12)
    score -= min(20, len(gloss_hits) * 6)

    min_words = int(fixture.get("min_words", 80))
    if word_count < min_words:
        score -= 10

    return {
        "fixture": fixture["name"],
        "score": max(0, min(100, score)),
        "expected_hits": expected_hits,
        "proof_hits": proof_hits,
        "tradeoff_hits": tradeoff_hits,
        "banned_hits": banned_hits,
        "ai_gloss_hits": gloss_hits,
        "word_count": word_count,
    }


def load_fixture(path: Path) -> dict:
    data = json.loads(path.read_text())
    data.setdefault("name", path.stem)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mStack messaging evals")
    parser.add_argument("--fixtures", default=str(ROOT / "evals" / "fixtures"))
    parser.add_argument("--candidate", help="Candidate text to score against one fixture")
    parser.add_argument("--fixture", help="Fixture name for --candidate")
    parser.add_argument("--min-score", type=int, default=70)
    args = parser.parse_args()

    fixture_dir = Path(args.fixtures)
    fixtures = {path.stem: load_fixture(path) for path in sorted(fixture_dir.glob("*.json"))}
    if not fixtures:
        raise SystemExit(f"No fixtures found in {fixture_dir}")

    failures = 0

    if args.candidate:
        if not args.fixture:
            raise SystemExit("--candidate requires --fixture")
        fixture = fixtures.get(args.fixture)
        if fixture is None:
            raise SystemExit(f"Unknown fixture: {args.fixture}")
        result = score_fixture(fixture, Path(args.candidate).read_text())
        print(json.dumps(result, indent=2))
        return 0 if result["score"] >= args.min_score else 1

    for name, fixture in fixtures.items():
        candidate = fixture.get("golden_output", "")
        if not candidate:
            print(f"FAIL {name}: missing golden_output")
            failures += 1
            continue
        result = score_fixture(fixture, candidate)
        print(f"{name}: {result['score']} expected={len(result['expected_hits'])} proof={len(result['proof_hits'])} tradeoff={len(result['tradeoff_hits'])} gloss={len(result['ai_gloss_hits'])}")
        if result["score"] < args.min_score:
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
