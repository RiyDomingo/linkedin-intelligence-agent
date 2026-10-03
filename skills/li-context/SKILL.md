---
name: li-context
description: "Set up or maintain my private professional memory: add/replace a resume, bio or website, show what you know about me, correct a fact, manage sources or export context. Use for onboarding and local context maintenance; profile rewrites use li-profile."
---

# li-context

For first-run setup, interrupted setup or “rerun setup review”, apply
[the onboarding lifecycle](references/onboarding.md). Its local state governs
progress; it hands off to the existing five workflows after the first brief.
Returning users reuse memory. Onboarding adds no user-facing skill.

Read [the shared contract](references/context-contract.md). Initialize with
`python3 <this-skill>/scripts/context.py --root <project>/.linkedin-agent init`.
Show the files created. Help fill relevant identity and knowledge templates from
user-provided evidence, retaining unknown placeholders. Use available own posts through li-read to bootstrap voice assessment; request
writing samples only when account/local evidence is unavailable or insufficient. Do not promote an
inferred preference or achievement into a saved fact without the user's request.
Run `status` after edits; report completeness without dumping personal data.
Templates live in [templates/identity/voice.md](templates/identity/voice.md),
[templates/identity/bio.md](templates/identity/bio.md),
[templates/identity/audience.md](templates/identity/audience.md),
[templates/knowledge/claims.md](templates/knowledge/claims.md) and
[templates/knowledge/metrics.md](templates/knowledge/metrics.md).

For “Set up my LinkedIn Intelligence Agent”, also apply [li-read](../li-read/SKILL.md): detect
actual sources/session tools, prefer restricted account onboarding when configured,
explain operating mode and automatically build observed career and inferred interest/
voice summaries. Imports remain an optional alternative. Curate relationships.json/
priorities.json only from permitted evidence.
Do not require every field before helping. Initialize only missing files, no
credentials or unsolicited provider activation. Read access stays advisory-only.

For professional memory, source enrichment, durable corrections or local context
questions, apply [the shared memory workflow](references/professional-memory.md).
Use its central API for precedence, conflicts, provenance and selective loading.
After connection offer optional resume/bio/website/link enrichment; allow skipping.
Most writing/context tasks use local memory and need no account or network reads.
