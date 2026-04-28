---
name: product-context
description: >-
  Collect messy product, customer, market, and release context before writing a product update, launch post, changelog narrative, release email, or announcement. Use when the user has a feature, release, customer problem, PR, support thread, Slack notes, founder notes, or vague launch idea and needs the raw material organized before angle selection or drafting.
---

# Product Context

## Standard

Do not draft yet. Turn scattered facts into a useful launch brief.

The brief should answer:

- What changed for the user?
- Why was this worth building now?
- What private context makes this story credible?
- What tradeoffs or constraints shaped the release?
- What proof can the update use?
- What should not be claimed?

## Workflow

1. Gather inputs.
   Read the user's notes and, when relevant, inspect local docs, PRs, changelogs, tickets, transcripts, screenshots, or specs they mention. If source context is thin, ask for the single highest-value missing input.

2. Sort the evidence.
   Group facts into: user pain, market shift, product behavior, team belief, tradeoffs, proof, objections, and unknowns.

3. Extract user language.
   Preserve concrete phrases from customers, sales, support, or internal debates. Mark invented placeholders clearly.

4. Define the release boundary.
   Separate what shipped, what is planned, what was rejected, and what should not be implied.

5. Produce a launch brief.
   Use this format:

```markdown
# Product Context Brief: {release}

## One-Line Summary
{plain English description of what changed}

## User Pain
- {specific workflow, cost, or frustration}

## Why Now
- {market, product, customer, technical, or strategic shift}

## Product Change
- Shipped: {facts}
- Not shipped: {facts}
- Deferred: {facts}

## Opinion
- {belief the company is acting on}

## Tradeoffs
- {choice, constraint, or refusal}

## Proof
- {customer quote, usage data, benchmark, example, before/after, PR, screenshot, or demo path}

## Smart Skeptic Questions
- {question}

## Claims To Avoid
- {unsupported or overbroad claim}

## Missing Context
- {highest-value facts still needed}
```

## Output

Return the brief first. Then list the 3-5 missing details that would most improve the eventual update.
