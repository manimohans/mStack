---
name: doctor
description: >-
  Use when the user needs to check whether mStack is installed correctly, whether Codex or
  Claude Code runtime skills are available, or whether a local project is ready to run the
  mStack launch workflow.
---

# Doctor

## Standard

Diagnose install and launch-readiness before doing product messaging work. The job is to make missing runtime pieces visible, not to draft launch copy or run contributor-only checks.

Use Doctor when setup may be stale, a host install looks broken, a teammate cannot find mStack commands, or a launch session should be checked before downstream work.

## Workflow

1. Run the installed doctor helper.

   ```bash
   helper="${CODEX_HOME:-$HOME/.codex}/skills/mstack/bin/mstack-doctor"
   [ -x "$helper" ] || helper="${CLAUDE_HOME:-$HOME/.claude}/skills/mstack/bin/mstack-doctor"
   [ -x "$helper" ] || helper="bin/mstack-doctor"
   "$helper"
   ```

2. Pick the host explicitly when needed.

   ```bash
   mstack-doctor --host codex
   mstack-doctor --host claude
   mstack-doctor --host all
   ```

3. Keep network checks explicit.
   The default diagnostic is offline. Use `--network` only when GitHub source-intake reachability matters for the next launch step.

   ```bash
   mstack-doctor --network
   ```

4. Treat the status as the gate.
   - `pass`: the install and local launch helpers are ready.
   - `needs review`: non-blocking readiness risk exists, usually network or optional state.
   - `blocked`: setup, metadata, writable state, helper self-tests, or session dry run failed.

5. Fix before downstream work.
   If the report is `blocked`, repair the install with `./setup --host {host} --force`, fix writable `MSTACK_HOME`, or refresh generated docs before running source-intake, evidence-pack, claim-check, or publish-check.

## Output

Return the doctor report first. Then add only the next concrete fix:

```markdown
# mStack Doctor
{helper output}

## Next Fix
{one command or file change}
```
