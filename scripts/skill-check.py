#!/usr/bin/env python3
"""Validate mStack skill docs, templates, and generated metadata."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = json.loads((ROOT / "config" / "skills.json").read_text())["skills"]
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def fail(message: str) -> None:
    raise SystemExit(message)


def require_frontmatter(path: Path) -> str:
    text = path.read_text()
    match = FRONTMATTER.match(text)
    if not match:
        fail(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
    header = match.group(1)
    if not re.search(r"^name:\s+\S+", header, re.M):
        fail(f"{path.relative_to(ROOT)}: missing name")
    if not re.search(r"^description:\s+", header, re.M):
        fail(f"{path.relative_to(ROOT)}: missing description")
    return header


def description_from_header(header: str) -> str:
    block = re.search(r"^description:\s*>-\n((?:  .*\n?)*)", header, re.M)
    if block:
        return " ".join(line.strip() for line in block.group(1).splitlines()).strip()

    single = re.search(r"^description:\s*(.*)$", header, re.M)
    if single:
        return single.group(1).strip().strip("\"'")

    return ""


def validate_skill(path: Path, expected_name: str) -> None:
    header = require_frontmatter(path)
    name = re.search(r"^name:\s+(.+)$", header, re.M)
    if name and name.group(1).strip() != expected_name:
        fail(f"{path.relative_to(ROOT)}: expected name {expected_name}, got {name.group(1).strip()}")
    description = description_from_header(header)
    if not description.startswith("Use when "):
        fail(f"{path.relative_to(ROOT)}: description must start with 'Use when '")
    if len(header) > 1800:
        fail(f"{path.relative_to(ROOT)}: frontmatter is too long for portable host metadata")


def validate_openai(path: Path) -> None:
    text = path.read_text()
    for field in ["display_name", "short_description", "default_prompt"]:
        if f"  {field}:" not in text:
            fail(f"{path.relative_to(ROOT)}: missing {field}")


def main() -> int:
    validate_skill(ROOT / "SKILL.md", "mstack")
    if not (ROOT / "SKILL.md.tmpl").exists():
        fail("SKILL.md.tmpl missing")

    seen = set()
    for skill in SKILLS:
        if skill in seen:
            fail(f"config/skills.json: duplicate skill {skill}")
        seen.add(skill)

        skill_dir = ROOT / skill
        validate_skill(skill_dir / "SKILL.md", skill)
        if not (skill_dir / "SKILL.md.tmpl").exists():
            fail(f"{skill}: missing SKILL.md.tmpl")
        validate_openai(skill_dir / "agents" / "openai.yaml")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen-skill-docs.py"), "--dry-run"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        return result.returncode

    print("OK skill docs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
