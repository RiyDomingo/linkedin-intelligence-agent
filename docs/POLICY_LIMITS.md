# LinkedIn intelligence product controls

## Account-reading scope update

The [restricted account connector](ACCOUNT_CONNECTOR.md) is an explicit bounded own-profile/posts/feed
read exception to the earlier import-only scope. It calls pinned mcp-server-linkedin
directly through a project gateway; Agent Reach remains in research/discovery.
Generic providers still cannot fetch/login to LinkedIn, external discovery stays
separate, inbox is excluded and all write actions remain disabled. Earlier audits
and zero-access observations describe their original validation, not this new path.


These controls supersede the earlier 10/50 discovery model. They do not change the
human-action boundary or authorize direct LinkedIn scraping.

| Capability | Default | Maximum |
| --- | ---: | ---: |
| External LinkedIn candidate discovery | 25 | 100 unique candidates/task |
| Discovery query budget | 3; normally use 1–3 | 10/task |
| Automatic non-LinkedIn public enrichment | 10 candidates | 20/task |
| Authorized user-owned imported records/history | Resource-based | Resource-based |
| Direct LinkedIn scraping/browser access | 0 | 0 |
| Automated LinkedIn actions | 0 | 0 |
| Discovery metadata cache lifetime | 24 hours | Configurable 1–72 hours |
| Active cached discovery tasks | — | 20 (engineering retention bound) |

Discovery limits are conservative product controls designed to prevent bulk
harvesting and unnecessary external requests. They are not LinkedIn-issued quotas
and do not create permission to scrape LinkedIn. Platform/index rules may change;
this software is not legal advice or a policy-compliance guarantee.

## GREEN: authorized data and ordinary public research

Analyze authorized exports, supplied text/snapshots, posts, comments, connections,
analytics, inbox data and local history within normal CPU/memory/file constraints.
Discovery/enrichment caps never truncate these inputs. Preserve explicit private
import opt-in, provenance, nulls and factuality gates. Processing may use chunking
or streaming when needed; current local import/history utilities load records in
memory. Tests exercise 4,500 read records and 2,000 local history entries.

Non-LinkedIn papers, university/company pages, news, GitHub and permitted community
sources retain ordinary capability/cost/privacy routing. Discovery origin does not
make a person off-limits for deliberate public research. No arbitrary small global
public-web cap is introduced by the automatic candidate-enrichment bound.

## AMBER: external index discovery

Select audited external-index search, retain minimal unverified metadata, deduplicate
canonical URLs across diversified queries, and stop early. Do not batch/retry one
task to exceed the result/query bounds. Do not pad counts with invented candidates.
Rank by available query relevance and corroboration; semantic interpretation remains
with Codex. Name alone is not verified identity.

Use `limit`, `query_budget`, `queries`, `enrichment_limit` and `cache_ttl_hours` in a
validated discovery request. Defaults apply when absent. Candidate requests above
100 are clamped; invalid query/enrichment/TTL overrides are rejected. Hard direct
access/action restrictions have no ordinary prompt override.

The cache stores only minimized search metadata, provenance and task budget context
under ignored `.linkedin-agent/discovery/`. Expired entries are physically purged
on cache access/write or `purge-expired`; an idle checkout needs that command or
manual removal. No scheduler is installed. Enrichment content stays outside this
cache. Discovery alone creates no relationship/CRM record. Deliberate confirmation
or tracking is required for curated relationship context.

## RED: direct automation

Generic research/discovery providers cannot scrape LinkedIn profiles, companies,
posts or feeds, log into accounts or reuse account sessions. The sole account-read
exception is the explicitly enabled restricted gateway described in
[ACCOUNT_CONNECTOR.md](ACCOUNT_CONNECTOR.md): manual dedicated login and bounded
own-profile, own-post and feed reads. Inbox and account writes remain excluded.
No CAPTCHA solving, evasion or alternate scraper fallback is allowed.
Providers cannot use a discovered LinkedIn URL as a second-stage retrieval target.
All posts, likes, comments, replies, connections, follows, DMs and profile edits
remain human-executed. The system researches, recommends and drafts.

Approved API is a distinct future capability. No approved remote client is currently
configured. A future reviewed integration must enforce exact grants, ownership,
endpoint restrictions and quotas; one endpoint is not blanket LinkedIn access.
Local `official` source labels are provenance attestations, not credentials/scopes.
