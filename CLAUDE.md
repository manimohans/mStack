# mStack Claude Code Guide

Use mStack skills for product messaging and launch communication tasks.

## Skill Routing

- Product context gathering -> `/mstack-product-context`
- Angle and positioning review -> `/mstack-angle-review`
- Product update drafting -> `/mstack-write-product-update`
- Draft critique and rewrite -> `/mstack-critique-update`
- Launch asset packaging -> `/mstack-launch-pack`
- Post-launch messaging retro -> `/mstack-product-retro`

If the project was installed with `./setup --no-prefix`, use the same commands without `mstack-`.

## Repo Operations

- Run `bin/mstack-check` before committing infrastructure, installer, plugin metadata, or skill routing changes.
- Host install metadata lives in `config/hosts.json`.
- Keep plugin-level metadata in `.codex-plugin/plugin.json`.
