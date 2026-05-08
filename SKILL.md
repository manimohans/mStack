---
name: mstack
description: >-
  Use when the user wants help turning a feature, release, PR, customer insight, changelog,
  launch idea, rough draft, or post-launch result into product messaging, launch assets, or
  reusable messaging learning.
---

# mStack

## Workflow

Use the smallest useful part of the loop:

1. **Source Intake** - Use the installed source-intake skill when PRs, issues, changelogs, docs, specs, or files need a health report before downstream work.
2. **Evidence** - Use the installed evidence-pack skill when proof is scattered across PRs, metrics, screenshots, support notes, or customer quotes.
3. **Context** - Use the installed product-context skill when the raw material is messy or missing.
4. **Angle** - Use the installed angle-review skill when the thesis, positioning, or story is unclear.
5. **Draft** - Use the installed write-product-update skill when it is time to write or rewrite the core update.
6. **Critique** - Use the installed critique-update skill when a draft exists and needs review.
7. **Claim Check** - Use the installed claim-check skill before publication when claims, metrics, quotes, or launch assets need proof review.
8. **Package** - Use the installed launch-pack skill when the story is approved and needs channel assets.
9. **Publish Check** - Use the installed publish-check skill when launch assets need one final readiness verdict before handoff.
10. **Learn** - Use the installed product-retro skill after launch to capture reusable messaging lessons.
11. **Remember** - Use the installed learn skill to search or save durable voice, proof, positioning, customer-language, and launch lessons.

Before drafting, check whether durable project learnings exist and whether the user already supplied enough source material. If context is thin, ask for the single missing input that would most improve the result instead of asking a long questionnaire.

## Routing

Commands below use the `mstack-` prefix. If the project was installed with `--no-prefix`, drop it (`mstack-angle-review` -> `angle-review`).

- PRs, issues, changelogs, docs, specs, or files that need source health -> `mstack-source-intake`
- Feature or release with rough notes -> `mstack-product-context`
- Scattered proof, metrics, screenshots, or quotes -> `mstack-evidence-pack`
- "What should the angle be?" -> `mstack-angle-review`
- "Write the launch post/update/email" -> `mstack-write-product-update`
- "Review this draft" -> `mstack-critique-update`
- "Check these claims before publishing" -> `mstack-claim-check`
- "Turn this into launch assets" -> `mstack-launch-pack`
- "Is this launch package ready to publish?" -> `mstack-publish-check`
- "What did we learn from this launch?" -> `mstack-product-retro`
- "Remember this for future launches" or "what have we learned?" -> `mstack-learn`

## Standard

The goal is memorable clarity, not volume. Prefer one defensible argument over many generic claims. Never invent proof, metrics, customer quotes, or shipped scope. Mark placeholders clearly, preserve useful source language, and separate facts from hypotheses.
