# Contributing To mStack

mStack is a messaging workflow, not a pile of prompts. Changes should preserve the loop:

**Source Intake -> Evidence -> Context -> Angle -> Draft -> Critique -> Claim Check -> Package -> Publish Check -> Retro -> Remember**

## Local Checks

Run the full repo validation before opening a PR:

```bash
bin/mstack-check
```

This verifies shell syntax, JSON manifests, host config, generated skill docs, agent metadata, temp installs for Codex and Claude Code, migrations, and messaging eval fixtures.

## Development Install

For live local development, install from this checkout:

```bash
./setup --host codex --force
```

By default, setup creates small runtime skill directories and symlinks support files so edits in this repo are picked up without copying the whole repo into the host.

Use a standalone copy when testing a packaged install:

```bash
./setup --host codex --copy --force
```

## Skill Naming

Default installs use the `mstack-` prefix:

- `mstack-source-intake`
- `mstack-product-context`
- `mstack-evidence-pack`
- `mstack-angle-review`
- `mstack-write-product-update`
- `mstack-critique-update`
- `mstack-claim-check`
- `mstack-launch-pack`
- `mstack-publish-check`
- `mstack-product-retro`
- `mstack-learn`

Use `--no-prefix` only for local experiments where command collisions are acceptable.

## Adding A Skill

1. Add the skill directory with `SKILL.md.tmpl`.
2. Add the directory name to `config/skills.json`.
3. Run `scripts/gen-skill-docs.py` to generate `SKILL.md` and `agents/openai.yaml`.
4. Update `SKILL.md.tmpl`, `AGENTS.md`, `CLAUDE.md`, and `README.md` routing.
5. Run `bin/mstack-check`.

## Template Generation

Edit `SKILL.md.tmpl` files first. Then run:

```bash
scripts/gen-skill-docs.py
```

Generated source docs should be fresh before committing:

```bash
scripts/gen-skill-docs.py --dry-run
```

Host-specific sidecars are generated from `config/hosts.json` and ignored by git:

```bash
scripts/host_config.py generate --host codex
scripts/host_config.py generate --host claude
```

## Messaging Evals

Add fixtures under `evals/fixtures/` when a workflow behavior should not regress. Run:

```bash
scripts/messaging_eval.py --min-score 70
```

The current model-free score checks specificity, proof, tradeoffs, banned claims, and AI-gloss terms.

## Adding A Host

Add the host to `config/hosts.json`, then follow [docs/ADDING_A_HOST.md](docs/ADDING_A_HOST.md).

## Migrations

Install migrations live in `mstack-upgrade/migrations/v*.sh`. They run during `./setup` when the migration version is newer than `~/.mstack/.last-setup-version` and not newer than `VERSION`.

## Plugin Manifest

The Codex plugin manifest lives at `.codex-plugin/plugin.json`. Keep repo-level plugin metadata there. Do not bury install-critical metadata inside an individual skill directory.

When changing plugin metadata, run:

```bash
jq . .codex-plugin/plugin.json
bin/mstack-check
```

## Release Checklist

1. Update `VERSION`.
2. Update `.codex-plugin/plugin.json` version.
3. Run `bin/mstack-check`.
4. Run a temp copy install:

```bash
CODEX_HOME="$(mktemp -d)" ./setup --host codex --copy --force
```

5. Commit with a concrete message.
