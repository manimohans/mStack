#!/usr/bin/env python3
"""Host config loading, validation, and skill document transforms."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "hosts.json"
SKILLS_PATH = ROOT / "config" / "skills.json"
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PATH_RE = re.compile(r"^[a-zA-Z0-9_./${}~:-]+$")


@dataclass(frozen=True)
class Host:
    name: str
    raw: dict[str, Any]

    @property
    def aliases(self) -> list[str]:
        return list(self.raw.get("aliases", []))

    @property
    def display_name(self) -> str:
        return str(self.raw.get("displayName", self.name))

    @property
    def default_prefix(self) -> str:
        return str(self.raw.get("defaultPrefix", "mstack"))

    @property
    def generated_root(self) -> Path:
        return ROOT / str(self.raw["generatedRoot"])

    @property
    def frontmatter(self) -> dict[str, Any]:
        return dict(self.raw.get("frontmatter", {}))

    @property
    def generation(self) -> dict[str, Any]:
        return dict(self.raw.get("generation", {}))

    @property
    def path_rewrites(self) -> list[dict[str, str]]:
        return list(self.raw.get("pathRewrites", []))


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text())


def skill_order(config: dict[str, Any] | None = None) -> list[str]:
    if SKILLS_PATH.exists():
        return list(json.loads(SKILLS_PATH.read_text())["skills"])
    data = config or load_config()
    return list(data.get("skillOrder", []))


def all_hosts(config: dict[str, Any] | None = None) -> list[Host]:
    data = config or load_config()
    return [Host(name, raw) for name, raw in data["hosts"].items()]


def resolve_host(name: str, config: dict[str, Any] | None = None) -> Host:
    data = config or load_config()
    for host_name, raw in data["hosts"].items():
        if name == host_name or name in raw.get("aliases", []):
            return Host(host_name, raw)
    raise SystemExit(f"Unsupported host: {name}")


def host_dest(host_name: str) -> Path:
    host = resolve_host(host_name)
    home = os.environ.get(host.raw["homeEnv"], host.raw["defaultHome"])
    return Path(os.path.expanduser(home)) / host.raw["skillDir"]


def validate_config() -> list[str]:
    data = load_config()
    errors: list[str] = []
    seen_generated: dict[str, str] = {}

    for skill in skill_order(data):
        if not NAME_RE.match(skill):
            errors.append(f"skillOrder entry {skill!r} must be lowercase kebab-case")
        if not (ROOT / skill / "SKILL.md.tmpl").exists():
            errors.append(f"{skill}: missing SKILL.md.tmpl")

    if not (ROOT / "SKILL.md.tmpl").exists():
        errors.append("root SKILL.md.tmpl is missing")

    for host_name, host in data.get("hosts", {}).items():
        if not NAME_RE.match(host_name):
            errors.append(f"host {host_name!r} must be lowercase kebab-case")
        if not host.get("displayName"):
            errors.append(f"{host_name}: displayName is required")
        for field in ("homeEnv", "defaultHome", "skillDir", "generatedRoot"):
            value = str(host.get(field, ""))
            if not value:
                errors.append(f"{host_name}: {field} is required")
            elif field != "homeEnv" and not PATH_RE.match(value):
                errors.append(f"{host_name}: {field} has unsafe characters: {value}")
        generated = str(host.get("generatedRoot", ""))
        if generated in seen_generated:
            errors.append(f"{host_name}: generatedRoot duplicates {seen_generated[generated]}")
        seen_generated[generated] = host_name

        fm = host.get("frontmatter", {})
        if fm.get("mode") not in ("allowlist", "denylist"):
            errors.append(f"{host_name}: frontmatter.mode must be allowlist or denylist")
        behavior = fm.get("descriptionLimitBehavior", "error")
        if behavior not in ("error", "truncate", "warn"):
            errors.append(f"{host_name}: invalid descriptionLimitBehavior {behavior!r}")
        limit = fm.get("descriptionLimit")
        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            errors.append(f"{host_name}: descriptionLimit must be positive integer or null")

    return errors


def split_frontmatter(text: str, path: Path) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"{path}: unterminated frontmatter")
    return text[4:end], text[end + 5 :]


def extract_description(header: str) -> str:
    block = re.search(r"^description:\s*>-\n((?:  .*\n?)*)", header, re.M)
    if block:
        return " ".join(line.strip() for line in block.group(1).splitlines()).strip()

    single = re.search(r"^description:\s*(.*)$", header, re.M)
    if single:
        return single.group(1).strip().strip('"')

    return ""


def wrap_description(description: str) -> str:
    words = description.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > 92 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(f"  {line}" for line in lines) or "  "


def transform_skill_doc(text: str, *, path: Path, name: str, host: Host | None = None) -> str:
    header, body = split_frontmatter(text, path)
    description = extract_description(header)

    if host is not None:
        limit = host.frontmatter.get("descriptionLimit")
        behavior = host.frontmatter.get("descriptionLimitBehavior", "error")
        if limit is not None and len(description) > limit:
            if behavior == "error":
                raise ValueError(f"{path}: description is {len(description)} chars, limit is {limit} for {host.name}")
            if behavior == "truncate":
                description = description[: limit - 1].rstrip() + "..."
            elif behavior == "warn":
                print(f"WARN {path}: description is {len(description)} chars, limit is {limit}", file=sys.stderr)

        for rewrite in host.path_rewrites:
            body = body.replace(rewrite["from"], rewrite["to"])

    new_header = f"---\nname: {name}\ndescription: >-\n{wrap_description(description)}\n---\n"
    return new_header + body


def source_templates() -> list[tuple[Path, Path, str]]:
    items = [(ROOT / "SKILL.md.tmpl", ROOT / "SKILL.md", "mstack")]
    for skill in skill_order():
        items.append((ROOT / skill / "SKILL.md.tmpl", ROOT / skill / "SKILL.md", skill))
    return items


def write_if_changed(path: Path, content: str, *, dry_run: bool) -> bool:
    old = path.read_text() if path.exists() else None
    if old == content:
        return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def generate_source(*, dry_run: bool) -> list[Path]:
    changed: list[Path] = []
    for tmpl, output, name in source_templates():
        content = transform_skill_doc(tmpl.read_text(), path=tmpl, name=name)
        if write_if_changed(output, content, dry_run=dry_run):
            changed.append(output)
    return changed


def generate_host(host: Host, *, dry_run: bool) -> list[Path]:
    changed: list[Path] = []
    root = host.generated_root
    prefix = host.default_prefix

    root_skill = root / "mstack" / "SKILL.md"
    content = transform_skill_doc((ROOT / "SKILL.md.tmpl").read_text(), path=ROOT / "SKILL.md.tmpl", name="mstack", host=host)
    if write_if_changed(root_skill, content, dry_run=dry_run):
        changed.append(root_skill)

    for skill in skill_order():
        install_name = f"{prefix}-{skill}" if prefix else skill
        skill_root = root / install_name
        tmpl = ROOT / skill / "SKILL.md.tmpl"
        content = transform_skill_doc(tmpl.read_text(), path=tmpl, name=install_name, host=host)
        if write_if_changed(skill_root / "SKILL.md", content, dry_run=dry_run):
            changed.append(skill_root / "SKILL.md")

        agents_dir = ROOT / skill / "agents"
        if host.generation.get("generateMetadata") and agents_dir.exists():
            target = skill_root / "agents"
            for source_file in agents_dir.iterdir():
                if not source_file.is_file():
                    continue
                target_file = target / source_file.name
                if write_if_changed(target_file, source_file.read_text(), dry_run=dry_run):
                    changed.append(target_file)

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="mStack host config and generation tool")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate")

    gen = sub.add_parser("generate")
    gen.add_argument("--host", default="source", help="source, all, or configured host name")
    gen.add_argument("--dry-run", action="store_true")

    dest = sub.add_parser("dest")
    dest.add_argument("host")

    render = sub.add_parser("render")
    render.add_argument("--host", required=True)
    render.add_argument("--skill", required=True, help="mstack for the root skill, or a skill name from config/skills.json")
    render.add_argument("--name", required=True, help="runtime skill name to write into frontmatter")

    args = parser.parse_args()

    if args.command == "validate":
        errors = validate_config()
        if errors:
            for error in errors:
                print(f"ERROR {error}", file=sys.stderr)
            return 1
        print("OK host config")
        return 0

    if args.command == "dest":
        print(host_dest(args.host))
        return 0

    if args.command == "render":
        host = resolve_host(args.host)
        if args.skill == "mstack":
            template = ROOT / "SKILL.md.tmpl"
        else:
            template = ROOT / args.skill / "SKILL.md.tmpl"
        if not template.exists():
            raise SystemExit(f"{template.relative_to(ROOT)} missing")
        sys.stdout.write(transform_skill_doc(template.read_text(), path=template, name=args.name, host=host))
        return 0

    changed: list[Path] = []
    if args.host in ("source", "all"):
        changed.extend(generate_source(dry_run=args.dry_run))

    hosts = all_hosts() if args.host == "all" else ([] if args.host == "source" else [resolve_host(args.host)])
    for host in hosts:
        changed.extend(generate_host(host, dry_run=args.dry_run))

    for path in changed:
        print(f"STALE {path.relative_to(ROOT)}" if args.dry_run else f"WROTE {path.relative_to(ROOT)}")

    return 1 if args.dry_run and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
