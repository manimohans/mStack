#!/usr/bin/env python3
"""Track a multi-step mStack launch session."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUSES = {"pending", "in_progress", "complete", "blocked"}


@dataclass(frozen=True)
class Stage:
    key: str
    label: str
    artifact: str
    command: str
    purpose: str


STAGES = [
    Stage(
        "source-intake",
        "Source Intake",
        "source-intake.md",
        "mstack-source-intake --strict SOURCE... > {artifact}",
        "Resolve PRs, issues, changelogs, docs, specs, or files into source context.",
    ),
    Stage(
        "evidence-pack",
        "Evidence Pack",
        "evidence-pack.jsonl",
        "mstack-evidence-pack --format jsonl --output {artifact} SOURCE...",
        "Collect typed proof, allowed claims, and claims to avoid.",
    ),
    Stage(
        "product-context",
        "Product Context",
        "product-context.md",
        "mstack-product-context {previous}",
        "Turn messy source material into a launch context brief.",
    ),
    Stage(
        "angle-review",
        "Angle Review",
        "angle-review.md",
        "mstack-angle-review {previous}",
        "Choose the strongest defensible thesis.",
    ),
    Stage(
        "write-product-update",
        "Draft",
        "draft.md",
        "mstack-write-product-update {previous}",
        "Draft the core update around proof, opinion, and tradeoffs.",
    ),
    Stage(
        "critique-update",
        "Critique",
        "critique-update.md",
        "mstack-critique-update {previous}",
        "Review the draft for specificity, proof, voice, and generic language.",
    ),
    Stage(
        "claim-check",
        "Claim Check",
        "claim-check.md",
        "mstack-claim-check {draft} {sources} > {artifact}",
        "Audit material claims against available proof.",
    ),
    Stage(
        "launch-pack",
        "Launch Pack",
        "launch-pack.md",
        "mstack-launch-pack {previous}",
        "Adapt the approved story into channel-specific launch assets.",
    ),
    Stage(
        "publish-check",
        "Publish Check",
        "publish-check.md",
        "mstack-publish-check {package} {sources} > {artifact}",
        "Return one publication-readiness verdict before handoff.",
    ),
    Stage(
        "product-retro",
        "Retro",
        "product-retro.md",
        "mstack-product-retro {previous}",
        "Capture what worked, what confused users, and what to remember.",
    ),
    Stage(
        "learn",
        "Remember",
        "learnings.jsonl",
        "mstack-learn save",
        "Save durable voice, proof, positioning, and customer-language lessons.",
    ),
]

STAGE_BY_KEY = {stage.key: stage for stage in STAGES}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug_value(raw: str) -> str:
    slug = raw.strip().lower()
    allowed = []
    last_dash = False
    for char in slug:
        if char.isalnum():
            allowed.append(char)
            last_dash = False
        elif char in {"-", "_", ".", " "}:
            if not last_dash:
                allowed.append("-")
                last_dash = True
    clean = "".join(allowed).strip("-")
    if not clean:
        raise SystemExit("slug must contain at least one letter or number")
    return clean


def session_dir(root: Path, slug: str) -> Path:
    return root / slug_value(slug)


def manifest_path(root: Path, slug: str) -> Path:
    return session_dir(root, slug) / "manifest.json"


def empty_manifest(slug: str, title: str | None, sources: list[str]) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": 1,
        "slug": slug,
        "title": title or slug.replace("-", " ").title(),
        "created_at": now,
        "updated_at": now,
        "sources": sources,
        "stage_order": [stage.key for stage in STAGES],
        "stages": {
            stage.key: {
                "status": "pending",
                "artifact": stage.artifact,
                "updated_at": None,
                "notes": [],
            }
            for stage in STAGES
        },
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"No mStack session found at {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from None


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def stage_artifact(path: Path, manifest: dict[str, Any], stage_key: str) -> Path:
    artifact = manifest["stages"][stage_key]["artifact"]
    return path.parent / artifact


def effective_status(path: Path, manifest: dict[str, Any], stage_key: str) -> str:
    status = str(manifest["stages"][stage_key].get("status", "pending"))
    if status in {"complete", "blocked"}:
        return status
    if stage_artifact(path, manifest, stage_key).exists():
        return "complete"
    return status if status in STATUSES else "pending"


def previous_artifacts(path: Path, manifest: dict[str, Any], stage_key: str) -> list[Path]:
    artifacts: list[Path] = []
    for key in manifest["stage_order"]:
        if key == stage_key:
            break
        artifact = stage_artifact(path, manifest, key)
        if artifact.exists():
            artifacts.append(artifact)
    return artifacts


def command_for(path: Path, manifest: dict[str, Any], stage_key: str) -> str:
    stage = STAGE_BY_KEY[stage_key]
    artifact = stage_artifact(path, manifest, stage_key)
    previous = previous_artifacts(path, manifest, stage_key)
    source_artifacts = [stage_artifact(path, manifest, key) for key in ("source-intake", "evidence-pack") if stage_artifact(path, manifest, key).exists()]
    values = {
        "slug": manifest["slug"],
        "artifact": str(artifact),
        "previous": " ".join(str(item) for item in previous[-2:]) or "SOURCE...",
        "draft": str(stage_artifact(path, manifest, "write-product-update")),
        "sources": " ".join(str(item) for item in source_artifacts) or "SOURCE...",
        "package": str(stage_artifact(path, manifest, "launch-pack")),
    }
    return stage.command.format(**values)


def next_stage(path: Path, manifest: dict[str, Any]) -> str | None:
    for key in manifest["stage_order"]:
        if effective_status(path, manifest, key) != "complete":
            return key
    return None


def init_session(args: argparse.Namespace) -> int:
    slug = slug_value(args.slug)
    root = Path(args.root)
    path = manifest_path(root, slug)
    if path.exists() and not args.force:
        raise SystemExit(f"{path} already exists. Use --force to recreate it.")
    if path.exists() and args.force:
        shutil.rmtree(path.parent)

    manifest = empty_manifest(slug, args.title, args.source)
    write_manifest(path, manifest)
    print(f"Created mStack session: {path.parent}")
    print(f"Manifest: {path}")
    print()
    print_next(path, manifest)
    return 0


def print_status(path: Path, manifest: dict[str, Any]) -> None:
    print(f"# mStack Session: {manifest['title']}")
    print()
    print(f"- Slug: {manifest['slug']}")
    print(f"- Manifest: {path}")
    print(f"- Updated: {manifest.get('updated_at', 'unknown')}")
    if manifest.get("sources"):
        print(f"- Sources: {', '.join(manifest['sources'])}")
    print()
    print("| Stage | Status | Artifact |")
    print("|---|---|---|")
    for key in manifest["stage_order"]:
        stage = STAGE_BY_KEY[key]
        artifact = stage_artifact(path, manifest, key)
        exists = "yes" if artifact.exists() else "no"
        print(f"| {stage.label} | {effective_status(path, manifest, key)} | {artifact} ({exists}) |")


def print_next(path: Path, manifest: dict[str, Any]) -> None:
    key = next_stage(path, manifest)
    if key is None:
        print("Next step: all tracked mStack stages are complete.")
        return

    stage = STAGE_BY_KEY[key]
    print(f"Next step: {stage.label}")
    print(stage.purpose)
    print()
    print("Suggested command:")
    print(command_for(path, manifest, key))


def status_session(args: argparse.Namespace) -> int:
    path = manifest_path(Path(args.root), args.slug)
    manifest = load_manifest(path)
    print_status(path, manifest)
    print()
    print_next(path, manifest)
    return 0


def next_session(args: argparse.Namespace) -> int:
    path = manifest_path(Path(args.root), args.slug)
    manifest = load_manifest(path)
    print_next(path, manifest)
    return 0


def record_session(args: argparse.Namespace) -> int:
    path = manifest_path(Path(args.root), args.slug)
    manifest = load_manifest(path)
    stage_key = args.stage
    if stage_key not in STAGE_BY_KEY:
        raise SystemExit(f"Unknown stage: {stage_key}")
    if args.status not in STATUSES:
        raise SystemExit(f"status must be one of: {', '.join(sorted(STATUSES))}")

    artifact = stage_artifact(path, manifest, stage_key)
    artifact.parent.mkdir(parents=True, exist_ok=True)

    if args.file == "-":
        artifact.write_text(sys.stdin.read())
    else:
        source = Path(args.file).expanduser()
        if not source.exists() or not source.is_file():
            raise SystemExit(f"Artifact source is not a readable file: {source}")
        if source.resolve() != artifact.resolve():
            shutil.copyfile(source, artifact)

    stage_data = manifest["stages"][stage_key]
    stage_data["status"] = args.status
    stage_data["updated_at"] = utc_now()
    if args.note:
        notes = stage_data.setdefault("notes", [])
        notes.append({"at": utc_now(), "text": args.note})

    write_manifest(path, manifest)
    print(f"Recorded {stage_key}: {artifact}")
    print()
    print_next(path, manifest)
    return 0


def run_self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "launches"
        init_args = argparse.Namespace(root=str(root), slug="Team Dashboards", title=None, source=["pr:123"], force=False)
        with contextlib.redirect_stdout(io.StringIO()):
            init_session(init_args)
        path = manifest_path(root, "team-dashboards")
        manifest = load_manifest(path)
        if manifest["slug"] != "team-dashboards":
            raise SystemExit("self-test failed: slug normalization")
        source_file = Path(tmp) / "source.md"
        source_file.write_text("# Source\n\nShipped team dashboards.\n")
        record_args = argparse.Namespace(
            root=str(root),
            slug="team-dashboards",
            stage="source-intake",
            file=str(source_file),
            status="complete",
            note="self-test",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            record_session(record_args)
        manifest = load_manifest(path)
        if effective_status(path, manifest, "source-intake") != "complete":
            raise SystemExit("self-test failed: record status")
        if next_stage(path, manifest) != "evidence-pack":
            raise SystemExit("self-test failed: next stage")
    print("OK session self-test")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and track an mStack launch session")
    parser.add_argument("--root", default=".mstack/launches", help="session root directory")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="create a launch session")
    init.add_argument("slug")
    init.add_argument("--title")
    init.add_argument("--source", action="append", default=[], help="source ref to store in the manifest")
    init.add_argument("--force", action="store_true", help="recreate an existing session")
    init.set_defaults(func=init_session)

    status = sub.add_parser("status", help="show session stage status")
    status.add_argument("slug")
    status.set_defaults(func=status_session)

    next_cmd = sub.add_parser("next", help="show the next incomplete stage")
    next_cmd.add_argument("slug")
    next_cmd.set_defaults(func=next_session)

    record = sub.add_parser("record", help="record a stage artifact")
    record.add_argument("slug")
    record.add_argument("stage", choices=[stage.key for stage in STAGES])
    record.add_argument("file", help="file to copy into the session artifact, or - for stdin")
    record.add_argument("--status", default="complete", choices=sorted(STATUSES))
    record.add_argument("--note")
    record.set_defaults(func=record_session)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
