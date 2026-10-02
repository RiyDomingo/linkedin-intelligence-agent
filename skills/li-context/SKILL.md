---
name: li-context
description: "Set up my LinkedIn Intelligence Agent with progressive voice, public identity, audience, claims, metrics and permitted read sources. Use for first-run onboarding or context maintenance, not profile-page rewrites."
---

# li-context

Read [the shared contract](references/context-contract.md). Initialize with
`python3 <this-skill>/scripts/context.py --root <project>/.linkedin-agent init`.
Show the files created. Help fill relevant identity and knowledge templates from
user-provided evidence, retaining unknown placeholders. Read three actual writing
samples for voice; ask only for the missing facts that matter. Do not promote an
inferred preference or achievement into a saved fact without the user's request.
Run `status` after edits; report completeness without dumping personal data.
Templates live in [templates/identity/voice.md](templates/identity/voice.md),
[templates/identity/bio.md](templates/identity/bio.md),
[templates/identity/audience.md](templates/identity/audience.md),
[templates/knowledge/claims.md](templates/knowledge/claims.md) and
[templates/knowledge/metrics.md](templates/knowledge/metrics.md).

For “Set up my LinkedIn Intelligence Agent”, also apply [li-read](../li-read/SKILL.md): detect
actual sources/session tools, explain operating mode, import initial supplied
history/analytics when available, and curate relationships.json/priorities.json.
Do not require every field before helping. Initialize only missing files, no
credentials or unsolicited provider activation. Read access stays advisory-only.
