# mStack Agent Guide

## Skill Routing

When this repo is installed into an agent host, prefer the mStack workflow for product communication work:

- Multi-step launch work that needs a durable handoff workspace, artifact manifest, status report, or next-step recommendation -> `mstack-session`
- Install, host-runtime, helper, state, or launch-readiness diagnostics -> `mstack-doctor`
- Product ideas, release notes, PR summaries, customer pain, or launch context -> `mstack-product-context`
- GitHub PRs, issues, changelogs, docs, specs, or local release files that need source context and a health report -> `mstack-source-intake`
- Launch proof scattered across PRs, issues, changelogs, metrics, screenshots, support notes, or customer quotes -> `mstack-evidence-pack`
- Positioning, narrative, thesis, or "what is the angle?" -> `mstack-angle-review`
- Product update, launch post, release email, changelog narrative, or announcement drafting -> `mstack-write-product-update`
- Draft review, editorial critique, or AI-gloss cleanup -> `mstack-critique-update`
- Pre-publish proof check for product claims, metrics, quotes, or launch assets -> `mstack-claim-check`
- Channel-specific launch materials -> `mstack-launch-pack`
- Publication-readiness check across proof, claims, channels, placeholders, and copy hygiene -> `mstack-publish-check`
- Post-launch learning, messaging retro, or reusable positioning lessons -> `mstack-product-retro`
- Reusable voice, proof, positioning, customer-language, or launch lessons -> `mstack-learn`

If installed without the default prefix, remove `mstack-` from the skill names above.

## Voice

Use concrete product language. Avoid generic launch phrasing, unsupported claims, and empty marketing intensity.

## Repo Operations

- Run `bin/mstack-check` before committing infrastructure, installer, plugin metadata, or skill routing changes.
- Edit `SKILL.md.tmpl` files, then run `scripts/gen-skill-docs.py`; generated `SKILL.md` and `agents/openai.yaml` must stay fresh.
- Host install metadata lives in `config/hosts.json`; do not hardcode new host paths in `setup` unless the host needs a genuinely different layout.
- Installed skills are listed in `config/skills.json`; update that file instead of duplicating skill lists across scripts.
- Keep plugin-level metadata in `.codex-plugin/plugin.json`.
