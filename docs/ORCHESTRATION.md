# Unified research integration

## Working gap analysis (before integration)

| Component | Existing implementation | Gap / smallest change |
| --- | --- | --- |
| LinkedIn reader | Validated local snapshots, capability/freshness status | Keep separate; no web provider implies account access |
| LinkedIn skills | Focused workflows and shared contract | State information needs; delegate external work centrally |
| Local memory | Confirmed/observed history and overlap | Retain; use evidence IDs in ideas/drafts |
| Research orchestration | Prompt guidance only, conflicting native-first wording | Consolidate policy and execution contract in li-research |
| Scrapling | Installed, HTTP/dynamic MCP validated | Connect a bounded optional execution adapter |
| Playwright | Isolated MCP validated | Connect explicit UI steps; no page-provided commands |
| Agent Reach | Installed; V2EX validated, Reddit/X not authorized | Route only supported, actually available capabilities |
| Bright Data | Disabled; no valid credentials, startup provisioning risk | Keep disabled; only justified managed fallback |
| Normalization | LinkedIn models; web packet prose | Add typed web/social evidence with nulls |
| Provenance | LinkedIn receipts and source notes | Carry source IDs/observations through dedup/signals |
| Caching | LinkedIn cache only | Small separate research cache with task-specific freshness |
| Capability detection | Installed names versus tested provider reports | Separate detected/configured/validated capabilities |
| Provider health | Individual tests, no consolidated record | Explicit successful validation receipts; no READY by config alone |
| Cost-aware routing | Duplicated instruction tables | One capability registry and bounded sequential escalation |
| Security | Untrusted-data policy, isolated browsers | Validate public requests before execution; never escalate permissions |

The consolidation below preserves existing provider installations and configuration.

## Final architecture

```text
Natural-language intent → focused LinkedIn skill
  ├─ public identity/claims + local publication memory
  ├─ separate li-read → authorized snapshots/imports → coverage/freshness
  └─ missing public information → li-research request
       → capability/cost/failure router → one suitable provider
       → normalized evidence → deduplicated research cache
       → source assessment + relevant inferred signals
  → reasoning, relationship relevance, novelty/history, audience and authority
  → claim/public-permission gate → voice draft → quality pass → human
```

There is no LinkedIn write arrow. High-level skills describe information needs.
The scripts implement deterministic routing/cache behavior; Codex applies semantic
research needs, source authority and drafting. This is a composable skill workflow,
not a background daemon or autonomous agent scheduler.

## Actual routing matrix

| Need | Installed bridge path | Boundary / availability |
| --- | --- | --- |
| Ordinary public page | Scrapling HTTP | No browser; public DNS and every redirect checked |
| Small site ingestion | Scrapling HTTP breadth-first crawl | Opt-in crawler, robots, 1–5 pages, same-site links |
| CSS field extraction | Scrapling HTTP | Up to ten fields; missing values null |
| JavaScript page content | Scrapling DynamicFetcher | Same installed browser; pre-navigation request guard |
| Trusted UI inspection | Playwright MCP | Isolated Chromium; fixed initPage network guard; up to five clicks |
| Public specialist context | Agent Reach V2EX | Opt-in; hot-topic board, **not query search** |
| Reddit / X / YouTube discussion | No enabled bridge adapter | Honest unavailable; session adapters require actual authorization/validation |
| Search/discovery | Actual session search capability | No free embedded search engine; source pages still need inspection |
| Legitimate managed retrieval/search | Bright Data | Disabled, metered; explicit cost permission and justified failure/need |
| LinkedIn resource (including linkedin.com URLs) | li-read | Imports/manual snapshots; no live account access granted by web tools |
| Rewrite/reply from supplied material | Local context/history/quality | Zero research calls |

Combined crawl/search/structured extraction with rendering or interaction is explicitly
unsupported by the current bridge, rather than silently dropping the operation.
Ordinary rendered pages require both PAGE_FETCH and JAVASCRIPT capability. Providers
are ordered by cost, complexity, tested capability and any known reliability/latency;
unknown measurements remain unknown. A success stops. Only a primary and one justified
fallback run; auth/parse/not-found/network failures never authorize login or paid retries.

## Health and operator use

From the repository root, using the **existing** optional environment:

```sh
.venv/bin/python tools/web/research.py health
.venv/bin/python tools/web/research.py plan request.json
.venv/bin/python tools/web/research.py run request.json
```

Use `--root /path/to/.linkedin-agent` before the command to select context/cache.
A request JSON describes public data, not a whole draft/inbox/profile. Example:

```json
{"operation":"retrieve_url","purpose":"FACT_VERIFICATION","url":"https://example.org/","public_input":true,"max_age_hours":24}
```

For crawl use `operation: crawl_site`, `purpose: DEEP_INGESTION`, and `max_pages: 2`.
For UI inspection use `browse_interactively`, `INTERACTIVE_WORKFLOW`, and trusted
`steps: [{"action":"click","target":"a.next"}]`. Review the control as read-only.
For specialist context use `research_social`, `COMMUNITY_DISCUSSION`, a public query
and explicit platform. The current V2EX adapter returns hot topics and labels that
scope; it does not claim to search that query. Codex filters relevance afterwards.

Existing `.linkedin-agent/sources.json` research booleans govern crawler and Agent
Reach opt-in. Preserve the other fields/providers when changing those booleans:
`research.crawler_enabled` and `research.agent_reach_enabled`. Both default false.
An unavailable adapter leaves placeholders and a precise gap. No reinstall, credentials,
cookies or server activation occurs automatically. In a copied skill pack without
tools/web, use actual available session tools and ingest their reviewed evidence.

Health distinguishes detected, configured and validated. Only a successful live
orchestrator run writes a per-capability receipt to ignored `.web-tools/health.json`;
it expires after 24 hours. Failed attempts remove the attempted capability receipt
and report LAST_ATTEMPT_FAILED until a subsequent success or expiry. Health does
not probe the network: reachable_now remains unknown. A configuration entry is never READY. Receipts attest one
source/task at that time, not every site, runtime version or account capability.
Cached success does not create a new validation receipt. LinkedIn status is reported
separately and currently Manual without actual account reads.

## Evidence, provenance and intelligence

Evidence includes source_type/provider/title/url/author/published_at/retrieved_at/
content/excerpt/metadata/confidence, optional platform ID and real engagement, content
hash, freshness class, extracted fields and every retrieval observation. Unknowns
are null. Opaque provider metadata/instructions cannot become policy or configuration.
All records and inferred signals retain `untrusted_data: true`.

Retrieval is PUBLIC_WEB or SOCIAL_COMMUNITY, not VERIFIED. Explicit source assessments
record source quality, exact supported claims and qualifications. Community opinion
cannot substitute for primary factual evidence. Changed content resets assessment;
identical content can retain it with original supporting provenance. Deduplication
collapses URL/platform/content duplicates without losing provider/date/hash observations.

`research/cache.json` is separate from LinkedIn imports and confirmed history. Task
age budgets determine cache reuse; stale returned packets cannot satisfy fresh requests.
Requests with extraction selectors always retrieve the requested fields, and click
steps always require an interaction provider, even on retrieve_url requests.
A zero budget requires retrieval during the current operation. Historical evidence can
still be explicitly imported for a historical question, but is never relabelled current.

Daily `intelligence.py brief` adds only relevant fresh `research_signals`, separately
from LinkedIn `actions`. Invalid optional research caches produce research_gaps while
preserving the local brief. The default brief uses a 24-hour window for current signals;
external retrieval itself always has an explicit task budget. Codex evaluates novelty,
credibility, audience, authority, projects, relationships and prior posts before making
an opportunity actionable. Signal extraction is transparent keyword matching; semantic
reasoning and claim permission are skill/model responsibilities. Empty/degraded outputs
are valid. A missing LinkedIn provider never causes automatic browser account access.

## Validation and limitations

Offline routing/evidence tests cover scenarios A–H, boundary failures, deduplication,
fresh/stale cache, assessment retention/reset, private-input rejection, provider error
redaction, opt-in health, browser network guards and high-level skill delegation.
Live safe-fixture tests exercise ordinary HTTP, a Playwright Next-page click and a
bounded crawl; optional social validation uses public V2EX. Reddit/X routing is tested
with synthetic available adapters and genuinely unavailable live status, not fake access.
Managed fallback uses synthetic failures; paid Bright Data retrieval is not tested.
These tests validate execution contracts, not deterministic success of every LLM draft.

Bridge browser guards reject LinkedIn/private DNS destinations and non-read requests,
block service workers and WebSockets, and fetch without redirect following before
fulfilling responses. Redirects are refused; supply the canonical public URL. DNS resolution/connection races, third-party runtime behavior and malicious UI controls still require trusted public sources and
operator review. This is not an arbitrary hostile-input fetch service or egress sandbox.
No login, CAPTCHA solving, cookie import, private-account escalation or autonomous
LinkedIn actions are added. See SECURITY.md and VALIDATION.md for actual test results.
