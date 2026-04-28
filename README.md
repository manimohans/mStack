# mStack

> A product messaging workflow for Codex, Claude Code, and compatible agent hosts.

mStack turns a general coding agent into a product launch operator: someone who can collect messy context, find the real angle, write the update, critique the draft, package the launch, and learn from what happened.

This is not a prompt dump. It is an ordered workflow for product communication.

## Quick Start

1. Install mStack.
2. Start with `/mstack-product-context`.
3. Run `/mstack-angle-review`.
4. Run `/mstack-write-product-update`.
5. Run `/mstack-critique-update`.
6. Run `/mstack-launch-pack`.
7. After launch, run `/mstack-product-retro`.

## Install

Clone this repo, then run:

```bash
./setup --host codex
```

For Claude Code:

```bash
./setup --host claude
```

Install locations:

| Host | Default skill directory |
|---|---|
| Codex | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |

Use short, unprefixed command names only if you are comfortable with possible name collisions:

```bash
./setup --host codex --no-prefix
```

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

You: /mstack-launch-pack
Agent: [creates changelog, launch email, social post, internal Slack, sales note]
```

## The Sprint

mStack follows the product communication loop:

**Context -> Angle -> Draft -> Critique -> Package -> Learn**

Each skill feeds the next:

| Skill | Specialist | What it does |
|---|---|---|
| `/mstack-product-context` | Product Reporter | Turns messy release notes, customer pain, PRs, support tickets, and founder notes into a launch brief. |
| `/mstack-angle-review` | Positioning Editor | Finds the strongest defensible thesis and rejects generic feature-first framing. |
| `/mstack-write-product-update` | Product Writer | Drafts the update around why now, opinion, tradeoffs, proof, and consequence. |
| `/mstack-critique-update` | Editorial Reviewer | Scores and rewrites drafts for specificity, credibility, proof, voice, and AI gloss. |
| `/mstack-launch-pack` | Launch Operator | Converts the approved story into channel-specific launch assets. |
| `/mstack-product-retro` | Messaging Analyst | Captures what worked, what confused users, and what to remember next time. |

## Who This Is For

- Founders who need to explain what shipped without sounding generic.
- Product marketers who want AI help without losing taste or company-specific context.
- Developer-tool and SaaS teams turning product work into launch narratives.
- Agents that need stronger written output than "we're excited to announce."

## Why Not Just Prompt The Agent?

Because the hard part is not writing sentences. The hard part is deciding what is worth saying.

mStack adds gates before and after drafting:

- Gather private context before writing.
- Choose one angle before generating copy.
- Name tradeoffs so the update feels credible.
- Review against proof and voice.
- Adapt by channel instead of duplicating the same copy.
- Learn from the launch so the next one improves.

## Project Layout

```text
mStack/
|-- product-context/
|-- angle-review/
|-- write-product-update/
|-- critique-update/
|-- launch-pack/
|-- product-retro/
|-- setup
|-- SKILL.md
|-- AGENTS.md
|-- CLAUDE.md
`-- VERSION
```

## Status

This is v0: a focused product messaging stack. The next useful layer is tool support for reading GitHub PRs, Slack launch notes, changelogs, and docs as source context.
