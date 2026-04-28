# mStack Agent Guide

## Skill Routing

When this repo is installed into an agent host, prefer the mStack workflow for product communication work:

- Product ideas, release notes, PR summaries, customer pain, or launch context -> `mstack-product-context`
- Positioning, narrative, thesis, or "what is the angle?" -> `mstack-angle-review`
- Product update, launch post, release email, changelog narrative, or announcement drafting -> `mstack-write-product-update`
- Draft review, editorial critique, or AI-gloss cleanup -> `mstack-critique-update`
- Channel-specific launch materials -> `mstack-launch-pack`
- Post-launch learning, messaging retro, or reusable positioning lessons -> `mstack-product-retro`

If installed without the default prefix, remove `mstack-` from the skill names above.

## Voice

Use concrete product language. Avoid generic launch phrasing, unsupported claims, and empty marketing intensity.

## Repo Operations

- Run `bin/mstack-check` before committing infrastructure, installer, plugin metadata, or skill routing changes.
- Host install metadata lives in `config/hosts.json`; do not hardcode new host paths in `setup` unless the host needs a genuinely different layout.
- Keep plugin-level metadata in `.codex-plugin/plugin.json`.
