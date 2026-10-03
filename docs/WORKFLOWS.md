# Five operational workflows

[Onboarding](ONBOARDING.md) prepares memory and strategy, delivers the first existing
brief, then hands off to these five workflows. It is a lifecycle, not another workflow.
The 20 Skills remain composable implementation components. Natural-language requests
select the relevant Skills; these are not new slash commands or a GUI menu.

| Workflow | Ask | Existing components | Output |
| --- | --- | --- | --- |
| **Brief me** | What deserves my attention today? | li-brief → li-read, selective history/research | 0–5 evidence-backed priorities and manual next steps |
| **Create** | Find something worth saying and draft it in my voice. | li-ideas → li-research when useful → li-post; li-repurpose/carousel when relevant | New angle, supported draft, claim and quality notes |
| **Discover** | Find relevant people and research the best candidates. | li-read discovery path → li-research → bounded enrichment | Deduplicated candidates, evidence, ambiguity and prioritization |
| **Engage** | Where can I contribute usefully? | li-engagement → li-comment/reply/dm; li-inbox for permitted supplied messages | Selective triage and drafts for human action |
| **Review & Plan** | Review the week and plan what to do next. | li-weekly → li-history/li-audit → li-plan | What happened, hypotheses, gaps and realistic next steps |

All five load confirmed goals/audiences from the same memory API. The shared
`onboarding.py workflow <brief|create|discover|engage|review_plan>` handoff returns
only relevant professional fields, the current strategic decisions and actual Skill
mapping. It does not perform account reads or research. Curated/current instructions
remain authoritative. Missing strategy stays unknown until the user supplies it.

The deterministic brief helper includes professional and strategic context in its
result. Codex reasons about goal/audience fit and may reprioritize supported signals
with an explanation; numeric ordering is not a measure of opportunity probability.
The other four use their existing Skill logic and the same shared context contract.
This does not introduce an automatic scheduler or hard-coded goal-to-action rules.

Profile-only audit, humanization, source maintenance and other focused requests can
still select their individual existing Skills directly. A simple rewrite is useful
before onboarding completes; normal work is not held hostage to a wizard.

Account reads remain bounded own profile/posts/feed. Discovery never opens arbitrary
candidate LinkedIn pages. Inbox/network/analytics require authorized additional data.
Research remains in the existing central router. Public content passes fact/permission
and voice/quality checks; every LinkedIn write action is performed by the human.
