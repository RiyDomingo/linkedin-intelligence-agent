# LinkedIn Discovery Mode: implementation and focused review

Audit date: 2026-10-02. Baseline: `a0f0bca`; clean working tree at task start.

## Verdict

**BLOCKED for live LinkedIn discovery.** The separate routing, bounded metadata
pipeline and zero-fetch guards are implemented and tested. The currently inspected
Agent Reach search transport cannot guarantee external-index-only operation, so
no live discovery query is issued and no candidate list is fabricated.

This is a capability gap, not permission to enable a scraper. Core writing,
authorized imports and supported ordinary research remain functional. No new
service, database, account connection, dependency or Skill was added. All 20 Skills
remain present. No commit, push, LinkedIn account action or LinkedIn-page validation
request was performed.

## What discovery means

Example request:

> Find up to 30 LinkedIn profiles relevant to sports biomechanics.

The intended route is:

```text
Public user query → LINKEDIN_DISCOVERY → audited Agent Reach external index
→ at most 50 minimal candidates → local deduplication/ranking → STOP
```

The implemented route prefers only `agent_reach_discovery`, never a generic search,
scraper or browser substitute. A trusted index-only adapter can supply packets to
the core pipeline; offline tests exercise that contract. There is currently **no
production index transport** wired to this provider. Changing an enabled flag does
not supply one. The live provider is both unavailable and disabled.

“Analyze this LinkedIn profile” takes a different path: LINKEDIN_READ → authorized
import, supplied snapshot or pasted profile text. Discovery availability never
grants profile, post, feed, network, analytics or inbox access.

Natural-language routing is supported through the existing li-research and
li-engagement descriptions/instructions. The Python classifier handles explicit
LinkedIn discovery/search and read verbs conservatively; it is not a general
natural-language intent model. Ambiguous requests require Codex interpretation.

## Current LinkedIn capability matrix

| Capability | Current behavior |
| --- | --- |
| Discovery | UNAVAILABLE live; core route/metadata contract tested offline |
| Profile read | IMPORT ONLY |
| Post/comment read | IMPORT ONLY |
| Feed read | IMPORT ONLY |
| Network read | IMPORT ONLY; curated relationship context is separate |
| Analytics | IMPORT ONLY / supplied measurements |
| Inbox | IMPORT ONLY, explicit private-data handling |

`tools/web/research.py health` reports this matrix separately from ordinary provider
health. A disabled/unavailable discovery provider does not change reader status.
`available`, `partial` or `stale` in the reader describes supplied coverage, not a
live LinkedIn connection.

## Agent Reach configuration review

Inspected the installed Agent Reach Skill, search/career references, Exa/LinkedIn/web
channel code and passive mcporter configuration inspection. Exa and a server named
`linkedin` are configured globally; editor imports are present but were deliberately
not expanded. These observations do not establish login state or authorized access.
No global configuration, credential store or unrelated server was changed/started.

| Installed path | Classification | Repository decision |
| --- | --- | --- |
| Exa `web_search_exa` through mcporter | Search; content/live-retrieval behavior UNKNOWN for the required index-only boundary | Unavailable/disabled for LinkedIn discovery |
| Exa `web_fetch_exa` | DIRECT FETCH | Not selected for LinkedIn |
| `linkedin.search_people` / `search_jobs` | AUTHENTICATED LinkedIn service, not an external index | Blocked, not invoked |
| `linkedin.get_person_profile` / `get_company_profile` | DIRECT FETCH / SCRAPING / AUTHENTICATED | Blocked, not invoked |
| LinkedIn MCP login command | AUTHENTICATED | Prohibited, not run |
| Agent Reach generic WebChannel / Jina LinkedIn fallback | DIRECT FETCH | Blocked |
| Existing public V2EX adapter | Separate specialist research | Preserved; existing source opt-in remains off |
| Reddit/X authenticated paths; YouTube | Other specialist sources | Existing disabled/unvalidated/unsupported bridge status unchanged |

The public Exa MCP schema was inspected without running a search. It exposes:

- `web_search_exa`: `query`, `numResults`, required `objective`; description says it
  returns clean content. No `livecrawl: never`, metadata-only or equivalent control.
- `web_fetch_exa`: `urls`, `maxCharacters`; a page reader, not discovery.

An objective saying “do not scrape” is prose, not an enforceable transport guarantee.
No unsupported parameter was invented or passed. Resolving this gap requires an
actual supported external-index API/tool with an audited no-page-retrieval contract
and a narrow adapter. There is no proposed authentication/cookie workaround.

## Limits and retention

| Boundary | Implemented value |
| --- | --- |
| Default result limit | 10 |
| Hard result limit | 50 per request |
| Default query budget | 1 |
| Hard accepted query budget | 5 |
| Current execution | At most one index-adapter call; no query/batch loop |
| LinkedIn page fetches | 0 in discovery |
| LinkedIn browser visits | 0 in discovery |
| LinkedIn scrapes | 0 in discovery |
| Current live calls | 0, because no audited transport is available |

Requests above 50 are clamped. An adapter response above 50 rows fails closed,
rather than processing a harvested batch. Discovery failure never enters ordinary
provider escalation, even for timeout/block/rate-limit errors. Query budget is an
upper bound, not an instruction to run five queries. Model instructions also
prohibit splitting one request into equivalent batches.

Minimal output contains canonical LinkedIn URL/type, short search title/snippet,
optional supplied display name, public query, provider, retrieval time and inferred
relevance explanation. Titles/snippets are bounded; email/phone fields and opaque
provider/profile blobs are not retained, and common contact/restricted text is
removed from allowed text fields. This filtering is not a universal sensitive-data
classifier. The caller must still supply only minimized public input.

Every candidate remains `DISCOVERY_ONLY`, `EXTERNAL_SEARCH_RESULT`, `SEARCH_METADATA`
and untrusted. Missing names remain null. Rankings reflect text matches, not verified
identity, expertise or relationship. No profile facts, metrics or connections are
inferred. Coverage is partial, even when the requested count is reached.

Results are ephemeral: no discovery cache, full search page, harvested database,
read import or relationship store is written. The core ordinary evidence normalizer
rejects discovery-tagged packets instead of promoting them into retrieved evidence.
A caller can deliberately save console/chat output; keep any such file private and
minimal. Provider validation receipts, if a supported future operation runs, store
only capability/failure/time metadata, not candidates.

## Provider guard matrix

| Provider | May access LinkedIn pages? | Enforcement in this repository |
| --- | --- | --- |
| Agent Reach discovery | No | Only the separate discovery capability can be selected; unaudited live transport disabled; no fallback |
| Agent Reach career/LinkedIn scraper | No | Not a registered/selectable bridge component; instructions explicitly prohibit its installed commands |
| Scrapling | No | Central URL/redirect guard plus pinned direct-MCP HTTP/browser bootstrap |
| Playwright | No | Isolated/headless launcher, context-wide parsed-host guard, redirects blocked, service workers/websockets blocked |
| Bright Data | No | Disabled; bridge preflight and server-side URL payload filter; only generic search/markdown tools allowlisted |
| Jina Reader | No | Not a bridge component; wrapped LinkedIn targets refused, reader-proxy host blocked in active network/browser guards |
| LinkedIn scraper MCP | No | Not a bridge component, never launched or selected; unrelated global registration left untouched |

Python host checks cover `linkedin.com`, all subdomains, case, trailing dots and IDNA
dots. Deceptive `notlinkedin.com` and `linkedin.com.evil.test` are not LinkedIn.
Candidates discard tracking queries/fragments and collapse country/www host variants.
Encoded malformed hosts and traversal paths are rejected. The HTTP adapter checks
each redirect before the next request. Renderers do not follow unchecked redirects.
MCP destination checks happen before server initialization, including paid startup.

The Scrapling bootstrap guards both HTTP and rendered/session paths without editing
installed third-party packages. It rejects browser/account reuse, cookies/proxies,
nonlocal executable overrides and public write methods. Direct HTTP redirects are
not followed; use the central checked HTTP path for permitted redirect inspection.
Failed browser-hook setup closes the page before upstream can continue unguarded.
Both ordinary HTTP and rendered fixture checks passed afterward.

The managed preload filters URL-bearing API payloads and uses the same ESM Axios
instance as the pinned server, including instances created through `axios.create`.
LinkedIn-specific scraper tools are excluded server-side. Bright Data remains
inactive; no token, billing/zone provisioning or live managed request was tested.
Opaque third-party internal redirects/egress are not certified by these client
checks. Do not enable a provider to get around the discovery boundary.

Restart existing local MCP sessions to load changed launchers/hooks. Installed Skill
copies also require the reviewed reinstall/update procedure; source edits do not
silently replace private/local installation copies.

## Focused independent-style security review

A fresh second pass was performed by the implementing agent; this is not a separate
engineer's certification. Findings were checked against executable paths and tests.

1. **Availability blocker — unaudited index transport.** Exa's current schema cannot
   enforce the requested index-only boundary. Kept unavailable/disabled in
   [research.py](../tools/web/research.py#L268); no false “ready” claim.
2. **Fixed — direct Scrapling MCP bypass.** Raw server requests could bypass central
   LinkedIn checks. Added [guarded_scrapling.py](../tools/web/guarded_scrapling.py#L1)
   through the existing launcher, including indirect browser/redirect checks.
3. **Fixed — managed raw-tool URL exposure.** Added
   [managed_guard.mjs](../tools/web/managed_guard.mjs#L1) and restricted the server's
   tool allowlist. ESM/CJS instance mismatch was caught during review and corrected.
4. **Fixed — failed browser setup could proceed.** Upstream catches setup errors;
   the wrapper closes the page before raising, with a regression covering this.
5. **Fixed — nested proxy/session options.** Bounded reader-proxy recursion and
   rejected nested browser storage/session settings. Sensitive inputs are minimized;
   heuristic redaction is not represented as a privacy guarantee.

Review answers: no discovery candidate is automatically fetched; no discovery
failure escalates; no scraper is selected; HTTP/browser redirects cannot automatically
enter LinkedIn through the guarded local paths; caps have no internal batching loop;
search provenance is retained; no relationship writes occur; documentation explicitly
states the live gap. No claim is made that arbitrary external tools outside the
repository, hostile local processes or opaque remote services are sandboxed by this.

## Validation

Current suite: **273 tests, all passed, zero failed/skipped**. Includes 45 new discovery,
bootstrap and managed-guard regressions; existing v1 tests remain unchanged except
for the launcher-path assertion reflecting the added guard.

Commands run from the repository:

```sh
python3 -m unittest discover -s tests -q
```

```sh
python3 -m unittest discover -s tests -p test_linkedin_discovery.py -v
```

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-discovery-pycache python3 -m compileall -q skills scripts tests tools/web
```

```sh
node --check tools/web/public_guard.cjs
```

```sh
node --check tools/web/managed_guard.mjs
```

```sh
.venv/bin/python tools/web/verify_mcp.py scrapling
```

```sh
.venv/bin/python tools/web/verify_mcp.py playwright
```

Both MCP smoke checks used only the public Quotes to Scrape fixture and closed their
sessions. No real LinkedIn URL was sent to a transport in validation. Domain and
redirect regressions use mocks. Managed guard tests use mock interceptors and the pinned ESM Axios instance with an
offline adapter; no key or managed-server startup.
All 20 Skills passed Skill Creator's validator using an existing isolated interpreter
with YAML support, without adding a project dependency. Local links and Git diff
whitespace were also checked.

A minimized demonstration discovery request was run through plan/run: plan returned
UNAVAILABLE; run returned no candidates/attempts and zero query/page counts, with
expected exit code 2. Health reports discovery UNAVAILABLE independently of imports.

## Use and limitations

Ordinary user prompts do not need provider names. Today, a discovery prompt should
explain the index-only capability gap instead of inventing results. Profile-analysis
requests still work with supplied content. A separate request for wider public
research may use university/publication/company sources, with identity disambiguation.
It must never return to LinkedIn scraping or silently create relationship records.

The 50-result ceiling is a technical product boundary, not legal advice, permission
to scrape or proof of LinkedIn-policy compliance. Platform rules and external index
usage restrictions can change; users/operators remain responsible for permitted use.

MIT LICENSE and upstream attribution remain unchanged. Historical v1 release-audit
claims are retained as historical evidence, not a claim of live discovery readiness.
