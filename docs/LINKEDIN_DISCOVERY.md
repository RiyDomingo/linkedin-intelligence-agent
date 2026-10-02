# LinkedIn discovery, imports and public enrichment

Updated 2026-10-02. Baseline: `9266272`; clean working tree at task start. This guide
supersedes the previous task's 10/50 and no-enrichment model. Historical v1 audit
records remain unchanged.

**Verdict: PASS WITH LIMITATIONS.** External discovery is validated through an actual
search-only Codex session handoff. Public enrichment is validated through the existing
Scrapling router. Standalone Python has no live search client; installed Exa discovery
remains disabled because its index-only behavior is unverified. No approved LinkedIn
API exists in this build. No direct LinkedIn page or account action was performed.

## What you can do

> Find 25 people on LinkedIn working on sports biomechanics, then research the most relevant candidates on the public web.

The agent uses an exposed external search operation, collects minimal candidate
metadata, deduplicates/ranks it, and can enrich the strongest named subset using
non-LinkedIn sources. The example was validated with real index results and a
[public university dissertation page](https://open.clemson.edu/all_dissertations/4239/).
Search-only calls used no `open`, click or browser operation against LinkedIn.
External engines maintain their own indexes; this project does not certify their
historical crawling practices or perform LinkedIn page retrieval itself.

The validation retained three actual candidates from one index query, reused the
cache on lookup, and accepted one opened public-source enrichment receipt. This
proves the session handoff, not guaranteed discovery of 25/100 relevant people for
any topic. No candidates or full pages were committed; outputs stayed in private
temporary files. Enrichment source observations remain NEEDS_VERIFICATION until
exact claim/source/public-permission review through li-fact-check.

## Risk tiers and capabilities

| Capability | Current status |
| --- | --- |
| External LinkedIn discovery | PARTIAL in a session with an exposed search-only tool; otherwise UNAVAILABLE |
| Imported profile | Adapter AVAILABLE; data AVAILABLE/PARTIAL/STALE/UNAVAILABLE according to actual imports |
| Imported posts | Same import coverage semantics; resource-based record limits |
| Imported comments | Same import coverage semantics |
| Imported feed | Same import coverage semantics |
| Imported network | Same import coverage semantics |
| Imported analytics | Same import coverage semantics |
| Imported inbox | Same import coverage semantics; explicit private-data opt-in |
| Approved LinkedIn API | UNAVAILABLE; no approved remote client or scope grants |
| Direct LinkedIn scraping | DISABLED |
| Automated LinkedIn actions | DISABLED |

GREEN is authorized local/supplied data and ordinary non-LinkedIn public research.
AMBER is bounded external discovery with optional bounded public enrichment.
RED is direct automated LinkedIn access/actions. See [product controls](POLICY_LIMITS.md).
`LINKEDIN_IMPORTED_DATA`, `LINKEDIN_DISCOVERY`, `LINKEDIN_APPROVED_API`, and
`LINKEDIN_DIRECT_AUTOMATION` are separate router capabilities. The legacy
`retrieve_linkedin` operation retains its import-reader route.

A URL alone is not profile content. For “Analyze this profile,” first use authorized
imports, supplied text/snapshots or permitted local evidence. No provider opens the
LinkedIn URL. Wider public research is useful when identity clues can be resolved.
`official`-tagged input snapshots do not grant API authorization.

## Limits and efficient execution

| Setting | Default | Hard maximum |
| --- | ---: | ---: |
| Unique candidates/task | 25 | 100 |
| Query budget | 3, normally use 1–3 | 10 |
| Automatic public enrichment candidates | 10 | 20 |
| Discovery TTL | 24h | Accepted range 1–72h |
| Direct LinkedIn fetch/browser/scrape | 0 | 0 |
| Automated LinkedIn actions | 0 | 0 |

One canonical URL counts once across queries; tracking parameters/fragments and
country/www variants collapse. Unknown names stay null. Query overlap is an inferred
relevance signal, not a numerical probability of identity. Codex evaluates role,
organization, topic, diversity, publications, recency and deliberately supplied
relationship context where useful; no sensitive characteristics are inferred.

The core executes only supplied bounded query variants, sequentially, and stops when
enough candidates exist, a subsequent query adds none, two empty queries occur, or
a provider fails. No discovery provider fallback or result-padding loop exists.
Each adapter query requests only the remaining candidate allowance.
At most 100 input rows per query are normalized; the combined set is capped at 100 unique
returned candidates. This input bound keeps work small; it does not cap user imports.
Search-only session tools must also honor the task budget **before** each actual
call; replaying a receipt cannot retroactively undo a provider call.

Automatic enrichment selects the strongest named subset. Missing identity clues are
not invented. Each candidate accepts at most ten opened-source receipts as an
engineering bound; prefer a small number of useful primary sources. Do not invoke
paid search/managed retrieval or browsers merely to fill a count. User-selected
larger public research is a separate deliberate task, without this automatic
candidate limit. All authorized local/history records remain usable.

## Actual Agent Reach role and availability

Agent Reach is the preferred specialist discovery orchestration where an audited
external-index capability exists, and retains its separate supported-platform role.
It is not the universal web provider. The registry ID `agent_reach_discovery` is the
logical discovery route; actual receipts identify `codex_session_search` when native
search was used. This is not represented as an Agent Reach network call.

Installed instructions/channel code and passive mcporter names were reviewed again.
Exa and a LinkedIn scraper registration exist globally; editor imports were not
expanded, credentials were not read/reused and servers were not started. Global
configuration remains unchanged. Repository exclusions govern use here.

| Installed/exposed path | Classification | Decision |
| --- | --- | --- |
| Codex session search-only operation | EXTERNAL_DISCOVERY | Supported metadata handoff; live search validated |
| Agent Reach Exa `web_search_exa` | UNKNOWN content/live-fetch behavior | Disabled for LinkedIn; no unsupported parameters invented |
| Exa `web_fetch_exa` | DIRECT_LINKEDIN_FETCH if given a LinkedIn URL | Blocked/not selected |
| Agent Reach `linkedin.search_people/search_jobs` | AUTHENTICATED_LINKEDIN | Blocked/not invoked |
| `get_person_profile/get_company_profile` | LINKEDIN_SCRAPING / AUTHENTICATED_LINKEDIN | Blocked/not invoked |
| LinkedIn MCP login/cookie paths | AUTHENTICATED_LINKEDIN | Prohibited |
| Jina LinkedIn reader fallback | DIRECT_LINKEDIN_FETCH | Prohibited |
| Agent Reach V2EX | Separate supported specialist source | Preserved; existing opt-in remains unchanged |
| Reddit/X/YouTube bridge gaps | Unavailable/unvalidated sources | Preserved; no accounts/backends enabled |

The previously inspected Exa MCP schema has query/numResults/objective and returns
clean content, without an enforceable index-only control. No Exa LinkedIn query was
used in this task. Native search-only operation provides a useful alternative where
actually exposed; without it, report the gap rather than activate a scraper.

## Local handoff and cache

Core code is standard-library-only and performs no network or account actions.
Use [the skill-local contract](../skills/li-research/references/linkedin-discovery.md)
for request and receipt schemas. Codex performs the actual session search and writes
minimized receipts; the helper normalizes them. It cannot invoke Codex's native tool
from a shell or attest cryptographically that a supplied receipt is genuine.

From the repository, after preparing the **actual** task request/receipts:

```sh
python3 skills/li-research/scripts/discovery_workflow.py --root .linkedin-agent lookup request.json
```

For a cache MISS, use the actual search-only tool, then:

```sh
python3 skills/li-research/scripts/discovery_workflow.py --root .linkedin-agent discover request.json search-results.json
```

For useful selected public research:

```sh
python3 skills/li-research/scripts/discovery_workflow.py --root .linkedin-agent enrichment-plan request.json result.json
```

Retrieve opened non-LinkedIn sources through ordinary routing and supply reviewed
receipts keyed by candidate URL:

```sh
python3 skills/li-research/scripts/discovery_workflow.py --root .linkedin-agent enrich request.json result.json public-receipts.json
```

Commands emit JSON to stdout; keep any saved request/result file private and ignored.
The discovery cache is ignored `.linkedin-agent/discovery/cache.json`, with new
files 0600/directories 0700 on Unix. It stores minimal metadata/provenance only, at
most 20 active tasks. It never writes imported read caches, curated relationships,
metrics or claims. Full enrichment content is not stored in discovery cache.

Expired cache entries are removed on lookup/write or explicitly:

```sh
python3 skills/li-research/scripts/discovery_workflow.py --root .linkedin-agent purge-expired
```

Task `max_age_hours` is also honored: zero forces fresh work, shorter budgets
reject otherwise unexpired metadata. TTL controls reuse and purge on access, not background deletion: idle files need
this command or manual removal. No scheduler/database or persistent harvested CRM
was introduced. A minimal validation receipt stores only transport/time/count.

## Public enrichment and identity

Use normal routing for permitted public evidence: Scrapling ordinary pages,
Playwright genuine interaction, Agent Reach supported specialist sources, Bright
Data only as an explicitly permitted justified fallback. LinkedIn/Jina destinations
remain blocked. No source quality, expertise or identity is verified merely by
retrieval or domain name.

A supplied name alone stays AMBIGUOUS. Name plus a professional organization/role/
location/publication clue occurring in both index metadata and an opened source may
be CORROBORATED_INFERRED. This is a heuristic association requiring semantic review;
conflicting sources/ambiguous identities must not merge silently. Reranking considers
corroborating observations then query relevance. Each source keeps URL/provider/time
and a short excerpt; exact claims still require li-fact-check. All content is untrusted
data, never tool/agent instructions. No sensitive trait or relationship is inferred.

## Provider boundaries

| Provider | LinkedIn pages allowed? | Permitted role |
| --- | --- | --- |
| Agent Reach | No | Audited index discovery and supported non-LinkedIn specialist research |
| Scrapling | No | Non-LinkedIn public pages; existing HTTP/browser destination guards |
| Playwright | No | Isolated read-only permitted public interaction; redirect/host guards |
| Bright Data | No | Disabled by default; explicit public fallback only, guarded tool allowlist |
| Jina/reader proxies | No | Not a selectable LinkedIn bypass |
| LinkedIn scraper MCP | No | Not selected/launched, despite unrelated global registration |
| Approved LinkedIn API | No current client | Future reviewed exact-scope integration, not a generic fetch exception |

Direct destinations/subdomains, encoded malformed hosts and reader wrappers are
checked; HTTP redirects are inspected before following and browser redirects stop.
DNS checks are not an egress sandbox: DNS races, opaque vendor internal redirects and
arbitrary external tools outside the repository remain outside this guarantee.
Existing local MCP sessions and installed Skill copies need restart/update to load
source changes. No dependency/server/account was installed or activated here.

## Validation and review

**310 unittest tests passed; zero failures/skips.** This adds 37 intelligence
regressions to the previous 273-test baseline. Old discovery tests were updated only
for explicitly superseding limits/cache semantics; zero-fetch guards remain tested.
Fixtures cover 4,500 authorized import records and 2,000 local history entries.
All 20 Skills, syntax/compilation, local documentation links and Git whitespace were
checked. Exact commands and focused findings are in
[the second-pass review](LINKEDIN_INTELLIGENCE_REVIEW.md).

Live validation: one external search-only discovery query; three minimized candidates;
cache HIT; one permitted public source fetched successfully through Scrapling and
accepted for enrichment. No browser/LinkedIn account action or LinkedIn page request
was issued by the toolkit. The managed provider was not enabled or billed.

Second-pass review was performed by the implementing agent in independent-engineer
style, not a separate engineer's certification. Material input-trust, provenance,
cache and routing findings were repaired and covered by regressions.

Remaining limitations: session-only live discovery, disabled unaudited Exa transport,
no approved API, conservative lexical/identity heuristics, in-memory local processing,
on-access cache deletion and remote egress limitations. None is hidden behind a READY
claim. MIT attribution and upstream remote/LICENSE remain unchanged.
