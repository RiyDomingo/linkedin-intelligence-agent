---
name: li-history
description: "Review LinkedIn publication memory for reused topics, hooks, anecdotes and claims, or record confirmed published content. Use for duplicate checks, successful themes and neglected angles."
---

# li-history

Read [the shared context and approval contract](../li-context/references/context-contract.md) first.

Read [the history schema](references/history-schema.md). Run the sibling
li-context script using its installed path:

```sh
python3 <li-context>/scripts/context.py --root <project>/.linkedin-agent load
python3 <li-context>/scripts/context.py --root <project>/.linkedin-agent check candidate.json
python3 <li-context>/scripts/context.py --root <project>/.linkedin-agent summary
python3 <li-context>/scripts/context.py --root <project>/.linkedin-agent append published.json --published
```

`check` uses transparent Unicode token overlap. Then reason semantically about
actual meaning, evidence and angle: repeated topic is not necessarily duplicate.
Compare explicit anecdotes/claims as well as the body; missing labels reduce recall.
Explain overlap, a distinct angle and needed fresh evidence. Use summary plus
user-provided metrics for successful and neglected themes; no causal guarantees.
Log only after confirmation of actual publication/sending and the actual date.
Malformed data must be reported with line number, not silently discarded. Never
rewrite history to hide errors. `--kind comments` supports confirmed public comments.

Use `context.py lookup <query>` for prior discussion dates or `--kind comments` for
past public engagement. Optional project/company, people_mentioned, evidence_used
and related_research fields support company/project fatigue and attribution checks.
Read imported activity through [li-read](../li-read/SKILL.md) without silently merging
it into confirmed publication memory. Source snapshots and curated history are distinct.

When imported activity is available, use sibling li-read `scripts/intelligence.py
memory`, `lookup <query>` or `overlap candidate.json`. This combined read view
includes observed own posts and keeps provenance/unknown topics/dates explicit. It
never promotes imports into confirmed publication history. Review imported hooks,
body and claims as well as the curated log before repeating a story or argument.
