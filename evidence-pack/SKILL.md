---
name: evidence-pack
description: >-
  Use when launch proof is scattered across PRs, issues, changelogs, analytics, screenshots,
  support notes, customer quotes, or rough release docs and needs to become a structured
  evidence bundle before product context, drafting, or claim checking.
---

# Evidence Pack

## Standard

Act as the proof collector before product messaging work. The job is not to write the launch yet. The job is to turn messy sources into a reusable evidence bundle that downstream mStack skills can trust.

Do not invent proof. Do not smooth weak evidence into stronger claims. Preserve source language, label confidence, and separate allowed claims from claims to avoid.

## Workflow

1. Gather source material.
   Use PRs, issues, changelogs, local release notes, specs, analytics exports, screenshots, customer/support notes, sales objections, and approved positioning. When the user mentions GitHub PRs, issues, changelogs, docs, specs, or local files, run the installed evidence-pack helper with those refs.

   ```bash
   helper="${CODEX_HOME:-$HOME/.codex}/skills/mstack/bin/mstack-evidence-pack"
   [ -x "$helper" ] || helper="${CLAUDE_HOME:-$HOME/.claude}/skills/mstack/bin/mstack-evidence-pack"
   [ -x "$helper" ] || helper="bin/mstack-evidence-pack"
   "$helper" --slug RELEASE-SLUG SOURCE...
   ```

   Use `--repo owner/project` for short refs such as `pr:123` or `issue:456`. If there is no clear release slug, omit `--slug` and return the generated Markdown directly.

2. Normalize the evidence.
   Group entries into:
   - `fact`: shipped scope, product behavior, tradeoff, decision, or constraint.
   - `metric`: usage, performance, conversion, revenue, latency, volume, benchmark, or before/after data.
   - `quote`: customer, user, sales, support, founder, or team language that can be attributed.
   - `screenshot`: screenshot, demo, image, video, or artifact path.
   - `customer_pain`: workflow pain, workaround, objection, support issue, or user cost.
   - `allowed_claim`: claim the sources support.
   - `claim_to_avoid`: claim the sources do not support or wording that is too broad.

3. Label confidence.
   Use high confidence only for explicit source language, labeled metrics, direct quotes, or concrete artifact paths. Use medium for keyword-inferred facts. Use low when the source is available but weak or ambiguous.

4. Persist when useful.
   For multi-step launches, save the evidence pack as `.mstack/evidence/{slug}.jsonl` so product-context, write-product-update, and claim-check can reuse it.

5. Identify missing proof.
   If the evidence pack lacks metrics, quotes, screenshots, or customer pain, say so plainly. Ask for the single missing proof source that would most improve the launch.

## Output

```markdown
# Evidence Pack: {release}

## Saved Artifact
{path or "not saved"}

## Evidence Summary
- fact: {count}
- metric: {count}
- quote: {count}
- screenshot: {count}
- customer_pain: {count}
- allowed_claim: {count}
- claim_to_avoid: {count}

## Strongest Evidence
- {specific fact, metric, quote, screenshot, or pain}

## Allowed Claims
- {claim supported by evidence}

## Claims To Avoid
- {unsupported or overbroad claim}

## Missing Proof
- {highest-value missing metric, quote, screenshot, before/after, approval, or source}

## Recommended Next Step
{run product-context, angle-review, write-product-update, or claim-check}
```

Keep the output compact. The value is a cleaner evidence base, not a long report.
