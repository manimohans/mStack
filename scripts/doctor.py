#!/usr/bin/env python3
"""Diagnose mStack install and launch-readiness state."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HOSTS_FILE = ROOT / "config" / "hosts.json"
SKILLS_FILE = ROOT / "config" / "skills.json"

REQUIRED_BINS = [
    "mstack-claim-check",
    "mstack-config",
    "mstack-doctor",
    "mstack-evidence-pack",
    "mstack-learn",
    "mstack-publish-check",
    "mstack-session",
    "mstack-source-intake",
    "mstack-team-init",
    "mstack-uninstall",
    "mstack-update-check",
    "mstack-upgrade",
]

SELF_TEST_BINS = [
    "mstack-claim-check",
    "mstack-evidence-pack",
    "mstack-learn",
    "mstack-publish-check",
    "mstack-session",
    "mstack-source-intake",
]

REQUIRED_SCRIPTS = [
    "claim_check.py",
    "doctor.py",
    "evidence_pack.py",
    "gen-skill-docs.py",
    "host_config.py",
    "learn.py",
    "messaging_eval.py",
    "publish_check.py",
    "session.py",
    "skill-check.py",
    "source_intake.py",
]

STATUS_ORDER = {"pass": 0, "skip": 1, "warn": 2, "fail": 3}


@dataclass(frozen=True)
class Check:
    status: str
    area: str
    name: str
    detail: str
    fix: str = ""


@dataclass
class Options:
    host: str
    network: bool
    env: dict[str, str]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"{path.relative_to(ROOT)} missing") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.relative_to(ROOT)} invalid JSON: {exc}") from None


def state_dir(env: dict[str, str]) -> Path:
    raw = env.get("MSTACK_HOME") or env.get("MSTACK_STATE_DIR") or str(Path.home() / ".mstack")
    return Path(raw).expanduser()


def host_dest(host: dict[str, Any], env: dict[str, str]) -> Path:
    home = env.get(str(host["homeEnv"]), str(host["defaultHome"]))
    return Path(os.path.expanduser(home)) / str(host["skillDir"])


def configured_skills() -> list[str]:
    return list(load_json(SKILLS_FILE)["skills"])


def configured_hosts() -> dict[str, dict[str, Any]]:
    return dict(load_json(HOSTS_FILE)["hosts"])


def autodetect_hosts(hosts: dict[str, dict[str, Any]], env: dict[str, str]) -> list[str]:
    detected: list[str] = []
    for name, host in hosts.items():
        home = Path(os.path.expanduser(env.get(str(host["homeEnv"]), str(host["defaultHome"]))))
        if home.exists():
            detected.append(name)
    return detected or ["codex"]


def selected_hosts(options: Options, hosts: dict[str, dict[str, Any]]) -> list[str]:
    if options.host == "auto":
        return autodetect_hosts(hosts, options.env)
    if options.host == "all":
        return list(hosts)
    if options.host not in hosts:
        raise SystemExit(f"unsupported host: {options.host}")
    return [options.host]


def run_command(args: list[str], *, env: dict[str, str], timeout: int = 15) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, f"{args[0]} not found"
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        return 124, f"timed out after {timeout}s\n{output}".strip()
    return result.returncode, result.stdout.strip()


def check_config(options: Options) -> list[Check]:
    checks: list[Check] = []
    skills = configured_skills()

    checks.append(Check("pass", "config", "skills", f"{len(skills)} skills configured"))
    if "doctor" in skills:
        checks.append(Check("pass", "config", "doctor skill", "doctor is listed in config/skills.json"))
    else:
        checks.append(Check("fail", "config", "doctor skill", "doctor is missing from config/skills.json", "Add doctor to config/skills.json and regenerate skill docs."))

    plugin = ROOT / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(plugin.read_text())
    except Exception as exc:
        checks.append(Check("fail", "config", "plugin metadata", f"{plugin.relative_to(ROOT)} is invalid: {exc}", "Fix .codex-plugin/plugin.json."))
    else:
        skills_path = payload.get("skills")
        status = "pass" if skills_path == "./" else "warn"
        fix = "" if status == "pass" else "Expose repo-level skills with \"skills\": \"./\"."
        checks.append(Check(status, "config", "plugin metadata", f"skills={skills_path!r}", fix))

    code, output = run_command([sys.executable, "scripts/gen-skill-docs.py", "--dry-run"], env=options.env)
    if code == 0:
        checks.append(Check("pass", "config", "generated docs", "SKILL.md and OpenAI metadata are fresh"))
    else:
        detail = output.splitlines()[0] if output else f"exit {code}"
        checks.append(Check("fail", "config", "generated docs", detail, "Run scripts/gen-skill-docs.py."))

    return checks


def check_state(options: Options) -> list[Check]:
    checks: list[Check] = []
    path = state_dir(options.env)
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".doctor-", delete=True) as handle:
            handle.write(b"ok")
        checks.append(Check("pass", "state", "MSTACK_HOME", f"writable at {path}"))
    except Exception as exc:
        checks.append(Check("fail", "state", "MSTACK_HOME", f"{path} is not writable: {exc}", "Set MSTACK_HOME to a writable directory."))

    config_file = path / "config"
    update_check = "true"
    source = "default"
    if config_file.exists():
        for line in config_file.read_text().splitlines():
            if line.startswith("update_check="):
                update_check = line.split("=", 1)[1]
                source = str(config_file)
    checks.append(Check("pass", "state", "update_check", f"{update_check} ({source})"))

    cache = path / "last-update-check"
    if cache.exists():
        checks.append(Check("pass", "state", "update cache", cache.read_text().strip() or str(cache)))
    else:
        checks.append(Check("skip", "state", "update cache", "no cached update check yet"))

    return checks


def installed_skill_path(dest: Path, prefix: str, skill: str) -> tuple[Path | None, str]:
    candidates = []
    if prefix:
        candidates.append(dest / f"{prefix}-{skill}")
    candidates.append(dest / skill)
    for candidate in candidates:
        if candidate.exists():
            return candidate, candidate.name
    return None, candidates[0].name


def check_host_install(name: str, host: dict[str, Any], options: Options) -> list[Check]:
    checks: list[Check] = []
    dest = host_dest(host, options.env)
    prefix = str(host.get("defaultPrefix", "mstack"))
    skills = configured_skills()

    if dest.exists():
        checks.append(Check("pass", "host", name, f"skill directory exists at {dest}"))
    else:
        checks.append(Check("fail", "host", name, f"skill directory missing at {dest}", f"Run ./setup --host {name}."))
        return checks

    root_skill = dest / "mstack"
    if root_skill.exists():
        checks.append(Check("pass", "install", "root skill", f"{root_skill} exists"))
    else:
        checks.append(Check("fail", "install", "root skill", f"{root_skill} missing", f"Run ./setup --host {name} --force."))

    missing: list[str] = []
    metadata_missing: list[str] = []
    for skill in skills:
        skill_path, expected_name = installed_skill_path(dest, prefix, skill)
        if skill_path is None:
            missing.append(expected_name)
            continue
        skill_doc = skill_path / "SKILL.md"
        if not skill_doc.exists():
            missing.append(f"{expected_name}/SKILL.md")
        if host.get("generation", {}).get("generateMetadata") and not (skill_path / "agents" / "openai.yaml").exists():
            metadata_missing.append(expected_name)

    if missing:
        checks.append(Check("fail", "install", "skills", f"missing: {', '.join(missing)}", f"Run ./setup --host {name} --force."))
    else:
        checks.append(Check("pass", "install", "skills", f"{len(skills)} runtime skills installed"))

    if metadata_missing:
        checks.append(Check("fail", "install", "metadata", f"missing OpenAI metadata: {', '.join(metadata_missing)}", f"Run ./setup --host {name} --force."))
    elif host.get("generation", {}).get("generateMetadata"):
        checks.append(Check("pass", "install", "metadata", "OpenAI metadata installed for runtime skills"))
    else:
        checks.append(Check("skip", "install", "metadata", f"{name} does not require OpenAI metadata"))

    support = root_skill
    bin_missing = [item for item in REQUIRED_BINS if not os.access(support / "bin" / item, os.X_OK)]
    script_missing = [item for item in REQUIRED_SCRIPTS if not (support / "scripts" / item).exists()]
    if bin_missing:
        checks.append(Check("fail", "install", "support binaries", f"missing or not executable: {', '.join(bin_missing)}", f"Run ./setup --host {name} --force."))
    else:
        checks.append(Check("pass", "install", "support binaries", f"{len(REQUIRED_BINS)} binaries available"))
    if script_missing:
        checks.append(Check("fail", "install", "support scripts", f"missing: {', '.join(script_missing)}", f"Run ./setup --host {name} --force."))
    else:
        checks.append(Check("pass", "install", "support scripts", f"{len(REQUIRED_SCRIPTS)} scripts available"))

    return checks


def check_helpers(options: Options) -> list[Check]:
    checks: list[Check] = []
    for helper in SELF_TEST_BINS:
        code, output = run_command([str(ROOT / "bin" / helper), "--self-test"], env=options.env, timeout=20)
        if code == 0:
            checks.append(Check("pass", "helpers", helper, "self-test passed"))
        else:
            detail = output.splitlines()[-1] if output else f"exit {code}"
            checks.append(Check("fail", "helpers", helper, detail, f"Run bin/{helper} --self-test and fix the failure."))

    code, output = run_command([str(ROOT / "bin" / "mstack-learn"), "--root", str(ROOT), "path"], env=options.env)
    if code == 0 and output:
        checks.append(Check("pass", "helpers", "mstack-learn path", output.splitlines()[-1]))
    else:
        checks.append(Check("fail", "helpers", "mstack-learn path", output or f"exit {code}", "Fix mstack-learn path resolution."))

    with tempfile.TemporaryDirectory(prefix="mstack-doctor-session.") as tmp:
        root = Path(tmp) / "launches"
        code, output = run_command(
            [str(ROOT / "bin" / "mstack-session"), "--root", str(root), "init", "doctor-dry-run", "--source", "README.md"],
            env=options.env,
        )
        if code != 0:
            checks.append(Check("fail", "helpers", "session dry run", output or f"exit {code}", "Fix mstack-session init."))
        else:
            code, output = run_command(
                [str(ROOT / "bin" / "mstack-session"), "--root", str(root), "next", "doctor-dry-run"],
                env=options.env,
            )
            if code == 0:
                checks.append(Check("pass", "helpers", "session dry run", "created a temporary launch session and resolved the next stage"))
            else:
                checks.append(Check("fail", "helpers", "session dry run", output or f"exit {code}", "Fix mstack-session next."))

    return checks


def check_network(options: Options) -> list[Check]:
    if not options.network:
        return [Check("skip", "network", "GitHub reachability", "not requested; rerun with --network to check GitHub access")]

    if shutil.which("gh") is None:
        return [Check("warn", "network", "GitHub reachability", "gh CLI is not installed", "Install gh or skip network checks.")]

    code, output = run_command(["gh", "repo", "view", "manimohans/mStack", "--json", "nameWithOwner"], env=options.env, timeout=20)
    if code == 0:
        return [Check("pass", "network", "GitHub reachability", output or "gh repo view succeeded")]
    return [Check("warn", "network", "GitHub reachability", output or f"exit {code}", "Check GitHub auth or network access before source-intake work.")]


def run_diagnostic(options: Options) -> list[Check]:
    hosts = configured_hosts()
    checks = []
    chosen = selected_hosts(options, hosts)
    checks.append(Check("pass", "host", "selection", ", ".join(chosen)))
    checks.extend(check_config(options))
    checks.extend(check_state(options))
    for name in chosen:
        checks.extend(check_host_install(name, hosts[name], options))
    checks.extend(check_helpers(options))
    checks.extend(check_network(options))
    return checks


def overall_status(checks: list[Check]) -> str:
    worst = max((STATUS_ORDER[check.status] for check in checks), default=0)
    if worst >= STATUS_ORDER["fail"]:
        return "blocked"
    if worst >= STATUS_ORDER["warn"]:
        return "needs review"
    return "pass"


def render_markdown(checks: list[Check]) -> str:
    lines = ["# mStack Doctor", "", f"Status: {overall_status(checks)}", "", "| Status | Area | Check | Detail |", "|---|---|---|---|"]
    for check in checks:
        detail = check.detail.replace("\n", " ")
        lines.append(f"| {check.status} | {check.area} | {check.name} | {detail} |")

    fixes = [check for check in checks if check.fix and check.status in {"fail", "warn"}]
    if fixes:
        lines.extend(["", "## Fix First"])
        for check in fixes:
            lines.append(f"- {check.area} / {check.name}: {check.fix}")
    return "\n".join(lines) + "\n"


def render_json(checks: list[Check]) -> str:
    return json.dumps(
        {
            "status": overall_status(checks),
            "checks": [check.__dict__ for check in checks],
        },
        indent=2,
    ) + "\n"


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="mstack-doctor-test.") as tmp:
        env = os.environ.copy()
        env["CODEX_HOME"] = str(Path(tmp) / "codex")
        env["MSTACK_HOME"] = str(Path(tmp) / "state")
        code, output = run_command(["./setup", "--host", "codex", "--force", "--quiet"], env=env, timeout=30)
        if code != 0:
            raise SystemExit(output or "setup failed")
        checks = run_diagnostic(Options(host="codex", network=False, env=env))
        failures = [check for check in checks if check.status == "fail"]
        if failures:
            raise SystemExit(render_markdown(failures))
    print("OK doctor self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose mStack install and launch-readiness state")
    parser.add_argument("--host", default="auto", help="auto, all, codex, or claude")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--network", action="store_true", help="check GitHub reachability")
    parser.add_argument("--self-test", action="store_true", help="run offline doctor checks against a temp Codex install")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    checks = run_diagnostic(Options(host=args.host, network=args.network, env=os.environ.copy()))
    if args.format == "json":
        sys.stdout.write(render_json(checks))
    else:
        sys.stdout.write(render_markdown(checks))
    return 1 if overall_status(checks) == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
