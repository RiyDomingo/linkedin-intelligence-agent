# First-run onboarding in Codex

Open this project in the Codex desktop app and ask:

> Set up my LinkedIn Intelligence Agent.

Setup is a conversation in Codex, with progress saved locally. There is no separate
wizard application to launch. The existing 20 Skills support this lifecycle; it is
not a sixth operational workflow or a new Skill.

## Connect → Learn → Enrich → Confirm → First Brief

1. **Welcome.** Choose **Connect LinkedIn** or **Continue without LinkedIn**. The
   agent prepares recommendations and drafts; you perform every LinkedIn action.
2. **Connect.** If chosen, a dedicated browser may open. Enter your LinkedIn password
   and complete any verification there, never in chat. An existing saved dedicated
   login may be reused. This is optional third-party browser access, not OAuth or
   an approved API. Another browser's login does not connect the agent. Technical
   prerequisites and setup are in [Connect LinkedIn](ACCOUNT_CONNECTOR.md).
3. **Learn.** Codex reads available bounded profile/career, professional sections,
   interests and own posts, then normalizes evidence into professional memory.
   Progress reflects actual section results. Missing skills or posts do not erase
   a successful profile read. Voice and inferred interests remain labelled.
4. **Enrich.** Optionally add a resume/CV, bio, website or professional link now or
   later. Or skip. The no-account path uses these sources or authorized local context
   instead. A new user needs at least one meaningful professional source to get a
   personalized brief. No long form or manual copying of successfully read profile
   data is required. Failed source parsing can be retried, replaced or skipped.
5. **Review.** “Here's what I understand about you” shows meaningful current role,
   background, expertise, interests, projects, content themes and writing style,
   with **Confirmed**, **Observed** or **Inferred** labels, sources and conflicts.
   Choose **Looks good** or **Make changes**. General acceptance records review;
   it does not certify every claim or make every inference confirmed. Explicit
   corrections persist and outrank rejected source interpretations.
6. **Choose strategy.** Answer at most two default strategic questions: what you
   want LinkedIn to help with, and which audiences matter. Multiple choices are
   supported. Audience suggestions come from your actual context. Already confirmed
   goals and audiences, including a filled curated audience file, are reused.
7. **See readiness.** Source/context availability, last observed account capability
   and missing coverage are shown honestly. Profile/posts/feed success are separate;
   inbox, connections and analytics still need authorized additional data.
8. **Receive first value.** The existing Daily Intelligence Brief uses your memory,
   goals, audience and available dated signals. A relevant bounded feed refresh or
   public research is optional. It gives **0–5** worthwhile actions with evidence,
   rationale and manual next steps. No supported signals is a valid result with
   coverage gaps, rather than fabricated recommendations.
9. **Continue.** After the brief is shown, onboarding becomes complete and hands off
   to [the five operational workflows](WORKFLOWS.md).

## Interrupted and returning sessions

A passive local status check detects a fresh project and offers setup. If setup was
interrupted, its exact phase survives in `.linkedin-agent/onboarding/state.json`.
Resume after login, acquired context, enrichment, review, strategy or brief generation
without repeating successful acquisition. A generated but undisplayed brief leaves
setup partial. Account challenges pause reads until you handle them manually; the
normal no-account path remains available.

A completed user loads relevant local memory and can work immediately, including
when offline or the connector is disabled. Temporary account failure does not reopen
setup. Codex checks existing evidence before asking context questions. Missing essential
information, material conflicts, stale unrefreshable context and strategic intent may
still need clarification. A simple standalone rewrite need not wait for setup.

## Controls in normal use

Ask Codex:

- “Show what you know about me, with sources.”
- “Correct my current role.”
- “Add my resume” or “Replace my resume.”
- “Add my bio, website or professional link.”
- “Refresh my LinkedIn context.”
- “Change my goals” or “Change my important audiences.”
- “Rerun setup review.”

Rerunning review preserves memory, sources, goals/audiences, account cache and login.
It does not delete files or disconnect LinkedIn. Memory resets, source removal,
connector disabling and authentication deletion are distinct operations. New inferred
context remains inferred until explicitly confirmed. Draft approval does not record
publication. See [memory controls](PROFESSIONAL_MEMORY.md).

## Local helper and state

The shared agent entry point is `skills/li-context/scripts/onboarding.py` in the
repository or the corresponding installed Skill. It uses the selected project data
root, not the Skill install directory. Users normally let Codex run these controls.

```sh
python3 skills/li-context/scripts/onboarding.py --root .linkedin-agent status
python3 skills/li-context/scripts/onboarding.py --root .linkedin-agent readiness
python3 skills/li-context/scripts/onboarding.py --root .linkedin-agent preview
python3 skills/li-context/scripts/onboarding.py --root .linkedin-agent workflow brief
```

Persistent phases:

```text
WELCOME → CONNECTING → ACQUIRING_CONTEXT → ENRICHMENT → REVIEW
       ↘ without LinkedIn ────────────────↗
REVIEW → STRATEGY → FIRST_VALUE → COMPLETE
```

`not_started`, `in_progress`, `partial`, `blocked` and `complete` are explicit statuses.
A blocked status retains its recovery phase. Version, opaque user identity, timestamps,
connection choice, checkpoints, review token and first-brief receipt are validated.
Malformed/unknown-version/cross-user state is preserved and refused, not silently reset.

The CLI exposes start, choose, begin-learning, learned, enrichment-done, preview,
confirm-profile, set-strategy, audience-proposals, questions, readiness, strategy,
workflow, run-brief, deliver, block, resume and reset. `--help` documents arguments.
`confirm-profile --confirmed` and `set-strategy --confirmed` represent actual user
acceptance; `deliver --displayed` is the agent's attestation that it showed the
actual generated brief. It cannot sense the UI. Passing flags without performing
those steps does not constitute valid onboarding.

State, locks and the first brief use private permissions and atomic saves under the
Git-ignored data root. One user per project; no multi-user/browser switching is added.
Goals are an additive memory field; existing version-1 stores remain readable.

## Privacy and validation

Professional memory is local. Authentication stays in the connector's separate
private browser profile. Public research receives only minimal public inputs. Text
read into Codex may reach the configured model service. All LinkedIn actions are
human-executed. No new retrieval endpoint, provider, credential ingestion or telemetry
is introduced by onboarding.

The lifecycle was validated with synthetic fresh-user/account/enrichment/signals,
second-process recovery and offline fixtures, not a new live login or a live first
brief for a new person. Earlier live account acceptance is recorded separately in
[the account review](ACCOUNT_CONNECTOR_REVIEW.md). See
[the onboarding review](ONBOARDING_REVIEW.md) for exact checks and limits.
