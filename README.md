# mStack

> Product messaging workflow for Codex, Claude Code, and compatible agent hosts.

mStack turns a general coding agent into a product launch operator: someone who can collect messy release context, find the real angle, write the update, critique the draft, check claims against proof, package the launch, and learn from what happened.

This is not a prompt dump. It is an ordered communication loop:

**Context -> Angle -> Draft -> Critique -> Claim Check -> Package -> Retro -> Remember**

## Who This Is For

- Founders who need to explain what shipped without sounding generic.
- Product marketers who want AI help without losing taste or company-specific context.
- Developer-tool and SaaS teams turning product work into launch narratives.
- Agents that need stronger written output than "we're excited to announce."

## Quick Start

1. Install mStack.
2. Run `/mstack-product-context` with release notes, PRs, customer pain, or rough launch ideas.
3. Run `/mstack-angle-review` to choose the strongest defensible thesis.
4. Run `/mstack-write-product-update` to draft the core update.
5. Run `/mstack-critique-update` before publishing.
6. Run `/mstack-claim-check` when claims, metrics, quotes, or launch assets need proof review.
7. Run `/mstack-launch-pack` for channel-specific launch assets.
8. After launch, run `/mstack-product-retro` to capture what worked.
9. Run `/mstack-learn` when you want durable voice, proof, positioning, or customer-language lessons available for the next launch.

Stop after step 4 if you only need the core update.

## Install

### Codex

```bash
git clone --single-branch --depth 1 https://github.com/manimohans/mStack.git ~/.codex/skills/mstack
cd ~/.codex/skills/mstack && ./setup --host codex
```

### Claude Code

```bash
git clone --single-branch --depth 1 https://github.com/manimohans/mStack.git ~/.claude/skills/mstack
cd ~/.claude/skills/mstack && ./setup --host claude
```

### Auto-detect Hosts

If you already have Codex or Claude Code installed locally, `setup` can detect the host directories:

```bash
git clone --single-branch --depth 1 https://github.com/manimohans/mStack.git ~/mstack
cd ~/mstack && ./setup
```

Install into both supported hosts:

```bash
./setup --host all
```

By default, setup creates lightweight runtime skill folders with host-safe command names and symlinked support files. Use `--copy` for a standalone copy, `--force` to replace an existing install, and `--no-prefix` only if you are comfortable with possible skill name collisions.

```bash
./setup --host codex --copy --force
./setup --host codex --no-prefix
```

## Manage mStack

Upgrade an existing checkout and rerun setup:

```bash
bin/mstack-upgrade --host codex --force
```

Uninstall generated runtime skill folders:

```bash
bin/mstack-uninstall --host codex --force
```

Validate the repo before publishing changes:

```bash
bin/mstack-check
```

Regenerate skill docs and OpenAI host metadata after editing templates:

```bash
scripts/gen-skill-docs.py
```

Generate host-transformed sidecar docs for a specific host:

```bash
scripts/host_config.py generate --host codex
scripts/host_config.py generate --host claude
```

Check for a newer upstream release without upgrading:

```bash
bin/mstack-update-check --force
```

Read or write local mStack preferences:

```bash
bin/mstack-config list
bin/mstack-config set update_check false
```

Collect source context from GitHub refs and local files before writing a launch brief:

```bash
bin/mstack-source-intake --repo owner/project pr:123 CHANGELOG.md docs/release-notes.md
bin/mstack-source-intake --format json https://github.com/owner/project/issues/456
```

Check a draft against source context before publishing:

```bash
bin/mstack-claim-check draft.md source-intake.md launch-brief.md
bin/mstack-claim-check --format json draft.md source-intake.md
```

## Codex Plugin

mStack includes a Codex plugin manifest at `.codex-plugin/plugin.json`. The repository root is the plugin root, and the manifest exposes the existing `SKILL.md` files through:

```json
{
  "skills": "./"
}
```

That means the same repo works as a skill checkout and as a plugin package. Keep new runtime assets beside the repo-level manifest instead of burying install-critical files inside an individual skill directory.

## Add mStack To A Project

For shared repos, add a short routing section to `AGENTS.md` or `CLAUDE.md` so teammates know when to use the workflow:

```bash
bin/mstack-team-init optional --project /path/to/project
bin/mstack-team-init required --project /path/to/project
```

The generated routing block looks like this:

```markdown
## mStack

Use mStack for product communication work:

- Product ideas, release notes, PR summaries, customer pain, or launch context -> `/mstack-product-context`
- Positioning, narrative, thesis, or angle review -> `/mstack-angle-review`
- Product update, launch post, release email, or announcement drafting -> `/mstack-write-product-update`
- Draft review or AI-gloss cleanup -> `/mstack-critique-update`
- Pre-publish proof check for product claims, metrics, quotes, or launch assets -> `/mstack-claim-check`
- Channel-specific launch materials -> `/mstack-launch-pack`
- Post-launch learning or messaging retro -> `/mstack-product-retro`
- Reusable voice, proof, positioning, customer-language, or launch lessons -> `/mstack-learn`
```

If mStack was installed with `--no-prefix`, remove `mstack-` from the command names.

`mstack-team-init` also writes `.mstack/config.json` so teams can see whether mStack is optional or required for product communication work in that repo.

## See It Work

```text
You: We shipped team dashboards. Need a launch post.
You: /mstack-product-context
Agent: What user pain caused this? What changed in the workflow? What did you refuse to build?

You: Managers were exporting CSVs every Friday. The dashboard replaces the ritual.
Agent: [writes a context brief: pain, why now, shipped scope, tradeoffs, proof, missing details]

You: /mstack-angle-review
Agent: Recommended angle: "The weekly status ritual should disappear, not get prettier."

You: /mstack-write-product-update
Agent: [drafts a launch post around the argument, not a feature list]

You: /mstack-critique-update
Agent: [flags generic claims, missing proof, and rewrites weak sections]

You: /mstack-claim-check
Agent: [classifies material claims as confirmed, inferred, or missing before publication]

You: /mstack-launch-pack
Agent: [creates changelog, launch email, social post, internal Slack, sales note]

You: /mstack-learn
Agent: [saves the reusable positioning and voice lessons for future launches]
```

## The Workflow

Each skill does one job and hands useful context to the next one.

| Stage | Skill | Specialist | What it does |
|---|---|---|---|
| Context | `/mstack-product-context` | Product Reporter | Turns messy release notes, customer pain, PRs, support tickets, and founder notes into a launch brief. |
| Angle | `/mstack-angle-review` | Positioning Editor | Finds the strongest defensible thesis and rejects generic feature-first framing. |
| Draft | `/mstack-write-product-update` | Product Writer | Drafts the update around why now, opinion, tradeoffs, proof, and consequence. |
| Critique | `/mstack-critique-update` | Editorial Reviewer | Scores and rewrites drafts for specificity, credibility, proof, voice, and AI gloss. |
| Claim Check | `/mstack-claim-check` | Proof Guard | Audits product claims, metrics, quotes, and launch assets against source context before publication. |
| Package | `/mstack-launch-pack` | Launch Operator | Converts the approved story into channel-specific launch assets. |
| Retro | `/mstack-product-retro` | Messaging Analyst | Captures what worked, what confused users, and what to remember next time. |
| Remember | `/mstack-learn` | Messaging Memory | Searches and saves durable voice, proof, positioning, customer-language, and channel lessons. |

## Why Not Just Prompt The Agent?

Because the hard part is not writing sentences. The hard part is deciding what is worth saying.

mStack adds gates before and after drafting:

- Gather private context before writing.
- Choose one angle before generating copy.
- Name tradeoffs so the update feels credible.
- Review against proof and voice.
- Check material claims against source context before publishing.
- Adapt by channel instead of duplicating the same copy.
- Learn from the launch so the next one improves.

## Project Layout

```text
mStack/
|-- .codex-plugin/
|   `-- plugin.json
|-- .github/
|   `-- workflows/check.yml
|-- bin/
|   |-- mstack-check
|   |-- mstack-claim-check
|   |-- mstack-config
|   |-- mstack-source-intake
|   |-- mstack-team-init
|   |-- mstack-uninstall
|   |-- mstack-update-check
|   `-- mstack-upgrade
|-- config/
|   |-- hosts.json
|   `-- skills.json
|-- docs/
|   `-- ADDING_A_HOST.md
|-- evals/
|   `-- fixtures/
|-- mstack-upgrade/
|   `-- migrations/
|-- scripts/
|   |-- claim_check.py
|   |-- gen-skill-docs.py
|   |-- host_config.py
|   |-- messaging_eval.py
|   |-- skill-check.py
|   `-- source_intake.py
|-- product-context/
|-- angle-review/
|-- write-product-update/
|-- critique-update/
|-- claim-check/
|-- launch-pack/
|-- product-retro/
|-- learn/
|-- setup
|-- SKILL.md
|-- SKILL.md.tmpl
|-- AGENTS.md
|-- CLAUDE.md
|-- CONTRIBUTING.md
`-- VERSION
```

## Status

This is v0: a focused product messaging stack. The current useful layer is tool support for source intake and pre-publish proof checks; the next layer is richer connectors for Slack launch notes, analytics, screenshots, and customer evidence.
