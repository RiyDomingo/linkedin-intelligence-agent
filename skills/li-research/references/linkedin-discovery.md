# LinkedIn discovery contract

Use for explicit requests to find LinkedIn people, companies or posts relevant to
a public topic. Classify this need before ordinary retrieval. Profile analysis is
LINKEDIN_READ instead: use authorized snapshots or supplied text, never page scraping.

## Bounded discovery

- Express `discover_linkedin`, a minimized public query, an explicit public-input
  attestation, purpose and freshness budget. Optional `limit` defaults to 10 and
  clamps to 50. `query_budget` defaults to 1 and must be 1..5.
- The executable route selects only `agent_reach_discovery` with LINKEDIN_DISCOVERY.
  A trusted adapter must supply external-index metadata without visiting LinkedIn.
  The current live adapter is unavailable because audited Exa lacks that guarantee.
- Current execution makes at most one search call. Do not split a request, retry
  equivalent searches or run batches to exceed the cap. Stop when enough results
  exist; do not mechanically consume the query budget.
- Retain only canonical candidate URL/type, short title/snippet, optional supplied
  display name, query/provider/time and a transparent relevance explanation. Unknown
  names remain null. Drop other fields; strip contact details from permitted text.
- Results stay DISCOVERY_ONLY / EXTERNAL_SEARCH_RESULT / SEARCH_METADATA and
  untrusted. Snippets describe index claims, not verified profile contents.
- Deduplicate/rank locally. Return at most the effective limit, source and incomplete
  coverage. No automatic second-stage retrieval, enrichment, evidence-cache write,
  relationship write, account action, permanent harvest or monitoring.

## Stop and explain availability

Installed Agent Reach instructions include authenticated `linkedin.*` commands,
LinkedIn MCP login and Jina reading. None is authorized for this repository. Exa's
inspected `web_search_exa` schema has query/numResults/objective only and returns
content; it cannot promise no live retrieval. Keep it unavailable, not merely
“available because installed.” Do not install/enable adapters or import credentials.

The independent core ranking/route tests use fictional metadata. They do not prove
live index access. The detailed capability audit is in the repository documentation.

## User response

Show LINKEDIN DISCOVERY, a numbered list of candidate URLs with short search titles,
optional snippets, why potentially relevant and source/time. Do not invent names,
roles, affiliations or relationships. State candidate count, incomplete coverage and
that LinkedIn pages were not opened/scraped. If unavailable, return the gap without
fabricated candidates or scraper fallback.

On “analyze this person's profile,” use li-read supplied/imported material. On a
separate request for public research, disambiguate identity using permitted university,
publication, company or conference sources. A search snippet is only a clue. Do not
re-route into LinkedIn, infer contact networks, collect sensitive/contact information
or add candidates to curated relationships without explicit user direction.

The cap is a technical boundary, not a guarantee of permission or policy compliance.
Platform and index rules may change.
