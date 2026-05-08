# mStack Claude Code Guide

Use mStack skills for product messaging and launch communication tasks.

## Skill Routing

- Product context gathering -> `/mstack-product-context`
- Source context and source health checks -> `/mstack-source-intake`
- Launch proof and evidence packaging -> `/mstack-evidence-pack`
- Angle and positioning review -> `/mstack-angle-review`
- Product update drafting -> `/mstack-write-product-update`
- Draft critique and rewrite -> `/mstack-critique-update`
- Pre-publish claim and proof check -> `/mstack-claim-check`
- Launch asset packaging -> `/mstack-launch-pack`
- Publication-readiness check -> `/mstack-publish-check`
- Post-launch messaging retro -> `/mstack-product-retro`
- Reusable voice, proof, positioning, customer-language, or launch lessons -> `/mstack-learn`

If the project was installed with `./setup --no-prefix`, use the same commands without `mstack-`.

## Repo Operations

- Run `bin/mstack-check` before committing infrastructure, installer, plugin metadata, or skill routing changes.
- Edit `SKILL.md.tmpl` files and run `scripts/gen-skill-docs.py` to refresh generated skill docs and OpenAI metadata.
- Host install metadata lives in `config/hosts.json`.
- Installed skills are listed in `config/skills.json`.
- Keep plugin-level metadata in `.codex-plugin/plugin.json`.
