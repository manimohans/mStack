#!/usr/bin/env python3
"""Generate mStack skill docs and host metadata from templates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from host_config import source_templates, transform_skill_doc


ROOT = Path(__file__).resolve().parents[1]
SKILLS_FILE = ROOT / "config" / "skills.json"

OPENAI_OVERRIDES = {
    "product-context": (
        "Organize messy launch inputs before drafting.",
        "Turn these product notes into a launch context brief. Separate confirmed facts, assumptions, missing proof, and claims to avoid.",
    ),
    "angle-review": (
        "Pressure-test and choose the strongest angle.",
        "Review the product context, generate competing angles, run the swap test, and recommend the strongest defensible thesis.",
    ),
    "write-product-update": (
        "Write product updates with proof and opinion.",
        "Write or rewrite this product update around one defensible angle, concrete proof, tradeoffs, and a clear reader action.",
    ),
    "critique-update": (
        "Critique product copy for proof and voice.",
        "Critique this draft for generic claims, missing proof, weak angle, voice mismatch, and unsupported promises. Rewrite the weak parts.",
    ),
    "claim-check": (
        "Audit launch claims before publishing.",
        "Check this product draft against source context. Classify claims as confirmed, inferred, or missing, and block unsupported metrics or quotes.",
    ),
    "launch-pack": (
        "Adapt an approved story into launch assets.",
        "Create channel-specific launch assets from the approved thesis. Keep the claim consistent while adapting proof, CTA, and tone.",
    ),
    "product-retro": (
        "Capture useful post-launch messaging lessons.",
        "Run a post-launch messaging retro. Separate measured evidence, qualitative signals, product learning, and reusable messaging lessons.",
    ),
    "learn": (
        "Search and save reusable messaging memory.",
        "Search, save, prune, or export durable product messaging learnings for this project. Keep entries specific and source-grounded.",
    ),
}


def load_skills() -> list[str]:
    return json.loads(SKILLS_FILE.read_text())["skills"]


def frontmatter(text: str, path: Path) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise SystemExit(f"{path}: missing YAML frontmatter")
    header = match.group(1)
    data: dict[str, str] = {}
    current = ""
    for line in header.splitlines():
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if key_match:
            current = key_match.group(1)
            value = key_match.group(2).strip()
            if value in {">-", "|"}:
                data[current] = ""
            else:
                data[current] = value.strip("\"'")
            continue
        if current and line.startswith("  "):
            data[current] = (data[current] + " " + line.strip()).strip()
    return data


def display_name(skill: str) -> str:
    return " ".join(part.capitalize() for part in skill.split("-"))


def yaml_string(value: str) -> str:
    return json.dumps(value)


def openai_yaml(skill: str, skill_text: str) -> str:
    metadata = frontmatter(skill_text, Path(skill) / "SKILL.md.tmpl")
    description = metadata.get("description", "").replace("\n", " ").strip()
    short_description, default_prompt = OPENAI_OVERRIDES.get(
        skill,
        (
            description[:117].rstrip() + "..." if len(description) > 120 else description,
            f"Use {display_name(skill)} for this task.",
        ),
    )
    return (
        "interface:\n"
        f"  display_name: {yaml_string(display_name(skill))}\n"
        f"  short_description: {yaml_string(short_description)}\n"
        f"  default_prompt: {yaml_string(default_prompt)}\n"
    )


def write_or_check(path: Path, content: str, dry_run: bool, stale: list[Path]) -> None:
    if dry_run:
        if not path.exists() or path.read_text() != content:
            stale.append(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def generate(dry_run: bool) -> int:
    stale: list[Path] = []

    for template, output, name in source_templates():
        if not template.exists():
            raise SystemExit(f"{template.relative_to(ROOT)} missing")
        content = transform_skill_doc(template.read_text(), path=template, name=name)
        write_or_check(output, content, dry_run, stale)

    for skill in load_skills():
        skill_dir = ROOT / skill
        template = skill_dir / "SKILL.md.tmpl"
        if not template.exists():
            raise SystemExit(f"{skill}: missing SKILL.md.tmpl")
        skill_text = template.read_text()
        write_or_check(skill_dir / "agents" / "openai.yaml", openai_yaml(skill, skill_text), dry_run, stale)

    if stale:
        for path in stale:
            print(f"STALE {path.relative_to(ROOT)}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="exit non-zero if generated files are stale")
    args = parser.parse_args()
    return generate(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
