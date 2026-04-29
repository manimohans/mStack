---
name: launch-pack
description: >-
  Use when a product update, launch angle, or product story is approved and the user wants
  channel-specific launch materials such as a blog post, changelog, release email, social
  posts, Slack or internal announcement, sales note, support note, or founder talking points.
---

# Launch Pack

## Standard

Keep the same thesis across channels, but change density, proof, CTA, risk level, and tone for each audience. Do not paste the same paragraph everywhere.

## Channel Rules

- Blog post: argument-first, more context, proof, and tradeoffs.
- Changelog: concise, concrete, product consequence first.
- Release email: clear subject, fast why, one proof point, obvious CTA.
- Social: one sharp claim, concrete example, no launch-template language.
- Internal Slack: what shipped, why it matters, who needs to know, rollout risk.
- Sales note: buyer pain, objection handling, talk track, proof.
- Support note: what changed, customer-facing explanation, known limitations.
- Founder talking points: opinionated, memorable, grounded in real choices.

## Workflow

1. Confirm source of truth.
   Identify the approved thesis, product facts, proof, CTA, and claims to avoid.

2. Build a message map.
   Capture: core claim, audience-specific pain, proof, CTA, product boundary, owner, timing, and banned claims.

3. Generate assets.
   Produce only the channels requested by the user. If unspecified, create: changelog, release email, social post, internal Slack, sales note.

4. Preserve consistency.
   Ensure every asset uses the same core claim and does not invent proof, roadmap promises, metrics, customer quotes, or availability details.

5. Add review notes.
   Flag where legal, customer approval, screenshot, or metric validation is needed.

6. Add execution details when useful.
   Include subject lines, preview text, audience, CTA, owner, and timing only when they help the user publish.

## Output

```markdown
## Message Map
- Thesis:
- Proof:
- CTA:
- Audience:
- Product boundary:
- Claims to avoid:

## Assets

### Changelog
{copy}

### Release Email
Subject: {subject}
{copy}

### Social Post
{copy}

### Internal Slack
{copy}

### Sales Note
{copy}

## Review Before Publishing
- {item}
```
