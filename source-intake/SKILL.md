---
name: source-intake
description: >-
  Use when GitHub PRs, issues, changelogs, docs, specs, or local release files need to be
  resolved into source context with an explicit health report before product context, evidence
  packaging, claim checking, or publish checks.
---

# Source Intake

## Standard

Resolve launch sources before turning them into messaging. The job is not to draft, summarize broadly, or hide broken inputs. The job is to make source availability visible and separate usable facts from missing proof.

Do not treat unavailable PRs, issues, docs, or files as weak evidence. Mark them as blocked source context. Do not turn keyword matches into stronger claims than the source supports.

## Workflow

1. Gather the exact source refs.
   Use GitHub PRs, issues, changelogs, release notes, specs, docs, local files, or source URLs the user provides. Prefer exact refs such as `pr:123`, `issue:456`, `CHANGELOG.md`, or a GitHub PR/issue URL.

2. Run the installed source-intake helper.
   Use `--repo owner/project` for short refs such as `pr:123` or `issue:456`. Use `--strict` when downstream product-context, evidence-pack, claim-check, or publish-check will rely on the result.

   ```bash
   helper="${CODEX_HOME:-$HOME/.codex}/skills/mstack/bin/mstack-source-intake"
   [ -x "$helper" ] || helper="${CLAUDE_HOME:-$HOME/.claude}/skills/mstack/bin/mstack-source-intake"
   [ -x "$helper" ] || helper="bin/mstack-source-intake"
   "$helper" --strict --repo owner/project SOURCE...
   ```

   Use `--format json` when another tool or script needs structured output.

3. Read the Source Health Report first.
   Treat verdicts as:
   - `safe_to_use`: sources resolved and contain usable source-backed facts.
   - `needs_review`: sources resolved, but proof cues or launch facts are thin.
   - `blocked`: one or more required sources could not be resolved, or no source context exists.

4. Stop on blocked source context.
   If the report is `blocked`, fix the source refs, repository, authentication, network access, or file paths before downstream mStack work. If the user explicitly asks to proceed anyway, label every affected claim as missing.

5. Preserve source boundaries.
   Keep shipped scope, user pain, proof, tradeoffs, unknowns, and claims to avoid separate. Do not merge unknowns into proof.

## Output

Return the helper report first. Then add only the smallest useful next-step note:

```markdown
# Source Intake

## Source Health Report
{helper output}

## Recommended Next Step
{evidence-pack, product-context, claim-check, publish-check, or fix sources first}
```

Keep the output compact. The value is knowing whether the launch sources are ready to trust.
