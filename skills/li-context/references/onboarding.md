# Onboarding lifecycle: Connect → Learn → Enrich → Confirm → First Value

This is product setup through existing li-context, li-read and li-brief; no new
skill, operational workflow, screen engine or daemon. User-facing steps are in
Codex chat. Do not expose transport/tool names in the welcome. Local commands below
are for the agent; users need no JSON editing. Resolve `<data-root>` from the active
project. Helper: `<this-skill>/scripts/onboarding.py --root <data-root>`.

## Detect and resume

Run `status` at the first project request in a chat. It is read-only, including on a
fresh install. `not_started` → offer/start setup with `start`; `in_progress`, `partial`
or `blocked` → resume the recorded phase; `complete` → reuse local memory and honor
the request. Network failure alone never reruns completed onboarding. Existing
context without lifecycle state is reused, not cleared or recollected indiscriminately.
Do not require setup to finish a simple standalone task.

Welcome: “Build private professional intelligence from your LinkedIn account and
optional sources. Understand what deserves attention, discover people, draft content
and learn what works. You perform all LinkedIn actions.” Offer **Connect LinkedIn**
first, **Continue without LinkedIn** second. Use an explicit existing connection
request as the choice; otherwise wait for the user's choice. Creating
state/templates is local; choosing account connection does not authorize posting.

## Connect and learn

`choose account`, then `begin-learning`. Apply
[the restricted account workflow](../../li-read/references/account-connected.md).
Set up/enable only for the chosen connection. Before a login read, explain: “A
private browser window may open. Sign in yourself and complete verification there.
The agent does not ask for or store your password.” Explain third-party access before
activation, without presenting it as OAuth. Another browser's login is not shared.

Use one bounded onboarding task for the genuine request. Apply missing profile
stages (experience, professional, interests) and own posts; reuse fresh normalized
observations already acquired. Do not restart successful acquisitions on resume.
Show simple progress from actual section outcomes, not fabricated ticks. Preserve
precise independent capability/section status. Normalize available fields/own-post
voice/themes through account_context.py retain; memory sync is automatic.

Challenges/restrictions pause acquisition. `block AUTH_CHALLENGE` (or actual category)
persists the current phase. Let the user resolve verification manually; `resume`
does not itself restart reads or reset a budget. Retry once only after explicit
manual completion under the account contract. `resume --without-linkedin` is the
alternative. Close owned sessions after work; retain a pending manual login window
only while the user is completing it.

For partial sections, continue using successes; optional failed reads do not make
profile success disappear. Once the bounded attempt ends, `learned` idempotently
syncs cached observations and moves to enrichment. It does not call a browser.
No normalized context? Enrichment can still supply it; do not claim learning succeeded.

`choose without_linkedin` goes directly to enrichment without an account read,
login or connector activation. Do not label this normal choice as a failure.

## Enrich and review

Offer optional **Resume/CV**, **Professional bio**, **Personal website**, **Other
professional links**, **Skip for now**. Apply
[the existing memory workflow](professional-memory.md), including its receipt,
MarkItDown, provenance and failure handling. Never search the user's home for sources.
Register/normalize before proceeding; failed replacement retains working evidence.
Offer retry, replace or skip for a failed optional source, without restarting setup.
A no-account user needs at least one meaningful source or curated professional fact;
ask only for what is essential to give a personalized brief.

`enrichment-done` → REVIEW. `preview` shows meaningful evidence sections only,
Confirmed/Observed/Inferred labels, freshness and source conflicts. Render a concise
“Here's what I understand about you” in chat, including important contradictory
interpretations. Ask **Looks good** / **Make changes**. A general acceptance records
review, not blanket verification/public permission of every claim. For explicit
corrections use professional_memory.py correct (matching field/key), then regenerate
the preview. Do not promote all inferred identity to confirmed facts automatically.

After the user's acceptance, `confirm-profile <review_token> --confirmed`. The token
binds acceptance to the current evidence; a changed preview requires review again.

## Strategy: two questions at most by default

Read `questions` and `strategy` before asking. Reuse already confirmed goals/audiences.
Ask only missing strategic questions:

1. “What would you most like LinkedIn to help you with?” Multiple selections or free
   text: visibility, relevant people, relationships, customers, collaborators, sharing
   expertise, staying current, career opportunities, an audience or another goal.
2. “Which audiences matter most?” Run `audience-proposals` and reason from its actual
   role/expertise/projects/interests evidence. Propose a short relevant list, allow
   edits/additions and multiple selections. Do not use a universal audience list.

Use `set-strategy goals <choices...> --confirmed` and `set-strategy audiences
<choices...> --confirmed` only for actual user selections. The choices replace the
primary strategy value in USER_CONFIRMED memory; they never come from inferred goals.
If the user defers, retain partial STRATEGY and continue other authorized work.
Changes later use the same controls without rerunning onboarding.

## Readiness and first value

Run `readiness`. Show actual source kinds, meaningful context, last observed
capabilities/timestamps, missing coverage and human-only actions. A connector being
enabled is not proof of a current login or successful feed read. Keep the privacy
summary concise: memory local; login in separate dedicated browser; minimal public
research inputs; actions human-executed. Model processing may be remote.

FIRST_VALUE: acquire a small current feed only if useful and authorized, within the
existing budget/freshness rules; skip unavailable feed and retain honest coverage.
Run `run-brief` and apply [li-brief](../../li-brief/SKILL.md) to its actual output,
confirmed goals/audiences, available profile/posts and relevant history. Research only
when it materially helps; don't send private context to public providers. Return
0–5 worthwhile actions with evidence and why they matter to the user's goals/audiences.
Review any supplied CLI draft placeholders before producing final copy. No meaningful
signals: say none were found in available data and name material gaps. Generic tips
or invented opportunities are not a brief.

Display the brief, then `deliver <receipt> --displayed` marks COMPLETE. Generation
alone does not complete onboarding. Delivery is an explicit trusted agent attestation,
not a UI sensor. If context/strategy changed, regenerate/review first. If interrupted
before delivery, read the private `onboarding/first-brief.json` and show it with its
date/coverage, or regenerate for the current request before marking delivered.

Use `workflow <brief|create|discover|engage|review_plan>` for a selective context
handoff. Present **Brief me**, **Create**, **Discover**, **Engage**, **Review & Plan** using
helper `status` workflows. These remain the five operational workflows. Future tasks
load selected memory and relevant freshness; never restart because login is unavailable.

## Reopen and progressive learning

`reset` previews; `reset --confirmed` reruns profile review while keeping memory,
goals/audiences, sources, account cache and authentication. Missing context returns
to enrichment. This is separate from memory reset, source removal, connector disable
and upstream authentication deletion. Unknown/corrupt/version-mismatched state fails
closed: preserve it and diagnose; never overwrite it with invented completion.

“Show what you know”, “where did this come from”, “correct my role”, “add/replace my
resume”, “add my website”, “refresh LinkedIn”, “change goals/audiences” use the existing
controls. New observations/inferences remain labelled. Ask about a material identity
change occasionally (Yes / Not yet / No); a correction/confirmation is durable,
otherwise leave it inferred. Draft approval never means confirmed publication history.
