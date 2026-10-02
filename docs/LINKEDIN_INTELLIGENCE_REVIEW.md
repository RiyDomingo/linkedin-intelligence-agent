# LinkedIn intelligence: second-pass review

Reviewed 2026-10-02 against baseline `9266272`. Verdict **PASS WITH LIMITATIONS**.
This is an independent-engineer-style second pass by the implementing agent, not a
separate reviewer's certification. User-authorized scope was expanded discovery,
cache, public enrichment and distinct risk tiers; direct automation remains disabled.
No LinkedIn page access, login, cookie reuse or account action occurred during
implementation or validation.

## Findings repaired

1. **Correctness: import collision.** The initial helper name collided with existing
   li-read intelligence. Renamed the new helper to discovery_workflow; all existing
   modules/workflows remain intact. See [discovery_workflow.py](../skills/li-research/scripts/discovery_workflow.py#L237).
2. **Correctness/security: combined task budgets.** Each query now requests only the
   remaining allowance, canonical URLs deduplicate across queries, and the route
   stops on enough candidates, non-improvement, repeated empty results or failure.
   Query/result caps have no internal continuation/fallback to harvesting.
   See [orchestrator.py](../skills/li-research/scripts/orchestrator.py#L233) and [discovery.py](../skills/li-research/scripts/discovery.py#L71).
3. **Provenance: native search mislabeling.** Logical routing may prefer the Agent
   Reach discovery layer, but source observations now record the actual
   codex_session_search transport and supplied retrieval time. Receipt ingestion
   validates planned query order, number and lifetime. It does not certify execution
   cryptographically or claim a standalone Python connection.
4. **Privacy: opaque cache/health fields.** Reject unknown cache envelopes and health
   receipts, normalize only minimal metadata, and keep new cache files private.
   Expired tasks are removed on access/purge; task storage is bounded to 20 entries.
   Public enrichment content never enters this cache. See
   [discovery_workflow.py](../skills/li-research/scripts/discovery_workflow.py#L27) and [research.py](../tools/web/research.py#L347).
5. **Factuality: editable result promotion.** Enrichment input is rebuilt from
   SEARCH_METADATA and rejects claimed VERIFIED profile data. Unknown fields and
   prompt-supplied nonzero access limits cannot survive normalization. Name alone
   remains ambiguous; corroborating clues do not bypass li-fact-check. See
   [discovery_workflow.py](../skills/li-research/scripts/discovery_workflow.py#L118) and [discovery_workflow.py](../skills/li-research/scripts/discovery_workflow.py#L180).
6. **Routing: enrichment could re-enter LinkedIn discovery.** Public enrichment
   queries remove the LinkedIn/site restriction and use normal non-LinkedIn routing.
   LinkedIn/Jina/private destination receipts are rejected, while existing active
   transport/redirect/browser guards remain unchanged. See
   [discovery_workflow.py](../skills/li-research/scripts/discovery_workflow.py#L156).
7. **Cache correctness: task freshness.** An unexpired 24-hour cache cannot override
   max_age_hours=0 or a shorter task age budget. Actual timestamps remain provenance;
   source results are not relabeled fresh. See [discovery_workflow.py](../skills/li-research/scripts/discovery_workflow.py#L89).
8. **Observability: attempts versus enrichment.** Separate enrichment_attempted from
   candidates receiving actual public-source evidence. A session receipt replay has
   zero new network queries; attested external queries are counted separately.

9. **Composition: enrichment stripped search observations/debug attempts.** Preserve
   source observations through enrichment, update only enrichment fields in the core
   result, and test fresh and cached composed execution. The discovery cache retains
   metadata only, with no public-source bodies or inferred identity assessment.

## Boundary checks

- At most 100 unique returned candidates; default 25. Up to ten planned queries,
  normally 1–3. No equivalent-task batching instructed or implemented.
- Automatic enrichment: default ten candidates, at most twenty; missing names remain
  missing. Source evidence retains provider/URL/time and identity uncertainty.
- No LinkedIn candidate can enter existing Scrapling/Playwright/Bright Data/Jina
  retrieval. No Agent Reach scraper/fetch/login command was invoked or registered in
  the bridge. The unrelated global LinkedIn registration was left untouched.
- Authorized local data is not constrained by discovery: 4,500 realistic import
  records and 2,000 local history entries process successfully. Private messages
  still require explicit private import opt-in.
- No autonomous account-action/provider write path was added. Unsupported actions
  return DISABLED and can only lead to advice/drafts. No approved API is fabricated;
  source labels cannot grant endpoint scopes.
- No new dependencies, server, database, browser account, paid capability or evasion
  mechanism was installed/enabled. Existing code remains standard-library-only in
  the core; optional bridge dependencies/configuration are preserved.
- Private input minimization is both semantic and structural. Heuristic filtering
  catches obvious contacts/restricted phrases, not all confidential language.

## Actual validation

Full suite: **310 discovered, 310 passed, 0 failed, 0 skipped**. New intelligence suite:
37 tests; preserved/updated discovery suite: 45 tests. Baseline 273 tests plus 37 new.

Commands run from the repository:

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-intelligence-pycache python3 -m unittest discover -s tests -q
```

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-intelligence-pycache python3 -m unittest discover -s tests -p test_linkedin_intelligence.py -q
```

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-intelligence-pycache python3 -m unittest discover -s tests -p test_linkedin_discovery.py -q
```

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-intelligence-pycache python3 -m compileall -q skills scripts tests tools/web
```

```sh
node --check tools/web/public_guard.cjs
```

```sh
node --check tools/web/managed_guard.mjs
```

```sh
git diff --check
```

All 20 Skills passed Skill Creator quick_validate using the existing isolated Agent
Reach Python interpreter with YAML support. No project/runtime dependency was added.
Local links/anchors and source line references were checked; beginner shell blocks
retain their existing validation. No live LinkedIn page was used as a test fixture.

Live validation used one native external search-only query, retained three minimal
real candidates in private temporary files, and checked cache HIT via the helper.
Separately, the central router used Scrapling for a public Clemson dissertation page
(HTTP 200); one opened public-source receipt enriched a candidate without promoting
its LinkedIn snippet to profile truth. The other selected candidates received no
invented evidence. No browser or paid provider was needed.

Debug health distinguishes actual configured Exa/global scraper names from enabled
repository capabilities, with editor imports/credentials untouched. Session discovery
is PARTIAL; standalone Exa is disabled and approved API unavailable. Imported adapter
support is AVAILABLE but actual data coverage may be missing/partial/stale.

## Remaining limitations

No unresolved material bypass was found within the reviewed paths/tests. This is
not proof that arbitrary hostile code or tools outside the repository are sandboxed.
Native discovery requires an exposed search-only session tool and genuine caller
receipts. Exa content behavior remains unaudited. A host must budget calls before
issuing them; receipt import cannot undo an already-issued request.

Identity/relevance are conservative text heuristics plus Codex judgment, not a
scientific identity verifier. Cache physical deletion occurs on use/purge, not a
background timer. Existing local parsers load data in memory. No approved remote API
or managed-provider live billing/egress test was performed. DNS races and opaque
remote vendor behavior retain the pre-existing limitations in SECURITY.md.

MIT attribution/LICENSE and both Git remotes remain unchanged. Discovery quantities
are internal product controls, not platform-approved quotas or legal advice.
