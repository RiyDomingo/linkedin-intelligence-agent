# LinkedIn discovery and public enrichment

For finding relevant LinkedIn people, companies or posts, use LINKEDIN_DISCOVERY
before generic retrieval. Local exports/supplied text use LINKEDIN_IMPORTED_DATA;
profile URLs alone grant no access. Direct automation is disabled. Approved API is
separate and currently unavailable; official-tagged snapshots do not grant scopes.

## Prepare a public task

Use `discover_linkedin`, public-input attestation, purpose and freshness budget.
`limit` defaults to 25 and clamps at 100 unique candidates. `query_budget` defaults
to 3, hard maximum 10. Optional `queries` is a bounded list of distinct public
variants; normally use 1–3. Do not split one task into equivalent batches. Stop at
sufficient quality/coverage or when another query adds no candidates. The cap is a
ceiling, not a target: never fabricate or pad weak results.

`enrichment_limit` defaults to 10; accepted 0–20. `cache_ttl_hours` defaults to 24,
accepted 1–72. These are product controls, not platform quotas. None applies to the
number of authorized imported/history records. Public queries contain only the
necessary topic/name clues, never inboxes, analytics, drafts, private notes or NDA
material. The validator rejects unknown fields and obvious restricted/contact text;
semantic privacy review is still necessary.

## Actual external search transport

Prefer an audited Agent Reach external-index capability. Its installed Exa MCP
search currently returns content without an enforceable index-only switch, so that
transport stays disabled. Career/profile/login commands, LinkedIn MCP and Jina
LinkedIn reading must never substitute.

When Codex exposes a search-only web tool, use its **search operation only**, such
as this session's `web.run` with `search_query` only. This is the implemented alternative handoff;
it is not an Exa or Agent Reach network call. Never use open/click/fetch against
LinkedIn, request full profile content, or run a browser. Discard unsolicited long
content returned by search; retain only minimal titles/snippets and URLs.
If no audited search-only capability is exposed, report UNAVAILABLE.

The standard-library `scripts/discovery_workflow.py` makes no network requests.
Before searching, run its `lookup` command against the task request and reuse fresh
metadata. For a MISS, collect actual search-only results, checking the budget before
each call. Do not gather all ten queries upfront. Hand off this JSON shape:

```json
{
  "source": "codex_session_search",
  "searches": [{
    "query": "the exact planned public query",
    "retrieved_at": "2026-10-02T13:00:00Z",
    "results": [{
      "url": "https://www.linkedin.com/in/example",
      "title": "Actual index title",
      "snippet": "A short actual index snippet",
      "display_name_if_available": null
    }]
  }]
}
```

Run `discover <request.json> <search-results.json>` with `--root` pointing to the
private project data area. The helper validates receipts, deduplicates/ranks and
stores only short-lived minimal metadata. Never fabricate receipts. A receipt is
an operator/session attestation, not cryptographic proof of tool execution.

Results remain DISCOVERY_ONLY / EXTERNAL_SEARCH_RESULT / EXTERNAL_DISCOVERY_METADATA
/ SEARCH_METADATA. Names can be null; relevance is inferred lexical matching, not
identity certainty. Search observations retain actual query/provider/time. Never
promote snippets into profile facts or write curated relationships automatically.

## Useful non-LinkedIn enrichment

When helpful for the networking task, run `enrichment-plan <request> <result>`.
Research the strongest named subset (default 10, maximum 20) through ordinary
public-web routing: universities, papers, companies, conferences, GitHub, personal
sites and other permitted sources. Missing names stay missing. Do not open the
LinkedIn candidate URL. Keep provider input to the plan's public query/URL fields,
not the entire result/local profile. Use ordinary freshness, privacy, read-only
browser and cost controls; no automatic paid escalation just to reach a count.

Open useful supporting **non-LinkedIn** sources through the central router. Supply
reviewed receipts to `enrich <request> <result> <receipts>`, keyed by candidate URL.
Each receipt has public `url`, actual `content`, `provider`, `retrieved_at`,
`opened: true`, optional exact-content `excerpt`, and optional `identity_signals`:
`[{"kind":"organization","value":"Actual public organization"}]`.
Allowed signal kinds: organization, role, location, publication. No sensitive traits.

Name match alone stays AMBIGUOUS. Name plus a professional clue appearing both in
index metadata and source text can become CORROBORATED_INFERRED. That is an inferred
association, not verified identity/profile truth. Conflicting or unclear identities
must stay separate. Exact claim support and publication permission still pass
li-fact-check. Sources may be stale or contradictory; do not invent numbers or
credentials from matches. Return source links and qualifications, not full pages.

The helper reranks by corroborating source count, then query match. Codex supplies
semantic relevance/role/publication/recency judgment without fake certainty. Separate
user-selected deeper public research can be comprehensive; the automatic 20-person
bound does not impose a general public-web or local-data cap.

## Retention and response

Use `.linkedin-agent/discovery/cache.json` (ignored by Git); no permanent CRM.
Expired entries are removed on lookup/write or `purge-expired`; idle files require
that command or manual removal for physical deletion. Enrichment content is not
cached here. Cache stores at most 20 active task entries as an engineering bound.
A minimal validation receipt contains only transport/time/count, not people/queries.

Show a useful candidate list, reasons, sources, actual returned count and incomplete
coverage. Explain that LinkedIn pages were not opened/scraped. Distinguish index
clues from public-source evidence and ambiguous identities. For profile content use
li-read authorized imports/snapshots/text. Curated relationships require deliberate
user confirmation/tracking. All LinkedIn actions remain human-executed.
