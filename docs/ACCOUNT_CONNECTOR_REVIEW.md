# Account connector implementation and acceptance review

**Verdict: PASS WITH LIMITATIONS — 2 October 2026.** The live account-read path,
normalized context, private opportunity brief/draft, and second-process persistence
worked. A fresh manual login/MFA and real expired/challenged authentication were
not exercised because an existing dedicated authenticated profile was reusable.
Those failure states were tested synthetically. This is a same-agent second review
conducted from an adversarial engineering checklist, not an independent certification.

## Architecture and inspected interface

Codex → restricted project MCP gateway → mcp-server-linkedin 4.26.1 → dedicated
persistent browser → bounded reads → validated local observations/summaries →
existing intelligence and writing Skills. Agent Reach remains separate research.

The installed upstream catalogue contains 19 tools, including write and inbox tools.
Only get_my_profile(sections, max_scrolls), get_feed(num_posts), and lifecycle
close_session are used. No get_my_posts exists; own posts use the posts section.
Profile top-card text is main_profile. These schemas were inspected programmatically
before implementation. A 78-package hash lock pins compatible dependencies in a
separate tools/linkedin/.venv. Codex registration exposes exactly:
connector_status, read_my_profile, read_my_posts, read_feed, close_session.
Upstream catalogue, prompts and resources are not forwarded.

Stdio startup uses --no-auto-import, --no-daemon, --login-inline-wait 0. The upstream
starts its human login browser when required and returns a pending-authentication
state; keep the process alive while the user signs in. Credentials never enter the
project gateway. Upstream update checks are off and stderr is discarded. Dedicated
authentication stays at the upstream ~/.linkedin-mcp/profile, outside Git.
Closing the session preserves it; logout is not implemented by this gateway.

## Live capability matrix

| Capability | Actual result |
| --- | --- |
| Installation / enable | Pinned isolated backend installed; explicit local enable |
| Authentication | Existing dedicated login observed authenticated; no cookie import |
| Profile / experience | Live partial bounded read, name/headline/about and prior roles |
| Education / skills | Live bounded sections returned education and skills |
| Projects | Empty visible section; completeness/current projects remain unknown |
| Interests / certifications / honors / languages | Bounded section reads; coverage remains partial |
| Current employer / role | Not established by the bounded experience sample |
| Own posts | Initial empty-looking page; later bounded routine read returned identifiable bodies; four own-authored excerpts retained |
| Feed | Live target 10; upstream batch included extra blocks; five selected observations retained |
| Session reuse | New stdio gateway subprocess reused dedicated authentication |
| Local memory reuse | New process used saved profile/posts/feed without acquisition |
| Inbox / messages | NOT_ENABLED; li-inbox still accepts permitted local input |
| All account writes | Absent from registered gateway; human executed |
| Approved LinkedIn API | NOT_USED |

Actual profile acquisition began at 15:09 UTC; own-post excerpt acquisition at 15:25
UTC; feed at 15:14 UTC. Exact receipt timestamps remain in private local metadata.
Relative activity ages were not converted into invented event dates. Reposts were
excluded from own-authored voice analysis. A limited older sample supports only an
INFERRED voice assessment, not confirmed current preferences.

A private dated opportunity brief and copy-ready draft are retained under
.linkedin-agent/account/briefs. The draft connects scientific translation with
measurement and additive manufacturing. Its NIST description is SOURCE-SUPPORTED;
the remaining statements are OPINION/questions. Funding amounts, deadlines and
eligibility seen in feed remain NEEDS VERIFICATION and were not repeated as facts.
Confirmed history is empty; topic novelty is tentative, not proof of never posting.
No manual copying or import substituted for this live account test.

Public research used the existing router with minimal public URLs. Manufacturer
pages returned no usable extracted text (PARSE_FAILURE), and no paid/access escalation
was attempted. NIST's additive-manufacturing page was retrieved successfully through
Scrapling in the existing web environment. No private profile, draft, feed interaction
or relationship note was submitted to a research provider.

## Limits, persistence and failure truth

Onboarding: experience up to 5 scroll attempts; combined professional sections up
to 3 each; interests 2; own posts 3. Routine sections/posts 2. Feed target 10, requested
maximum 20. Normal task budget 4, finite onboarding budget 6; duplicate acquisition
in one task is rejected. No background refresh. TTL profile 30 days, posts 3 days,
feed 1 hour when needed. Explicit refresh may bypass TTL; rewrites request no reads.

Normalized account/observations, dated account/summaries, receipt/status metadata,
and shared read/cache are ignored private data. New files 0600/directories 0700.
Curated identity/knowledge and confirmed publication logs were preserved. Raw pages,
screenshots, passwords, cookies and auth profiles were not stored in project data.
Account source public permission remains unknown. Post permalinks remain null.

Simulated tests cover auth expiry/challenge/restriction, timeouts, malformed responses,
partial capability failure, stale-cache preservation and disabled zero-upstream-call
behavior. No real account was logged out or deliberately challenged to create those
states. Session reopening and local-memory reuse were live. All owned test browser
sessions were closed; unrelated user browser tabs were left alone.

## Review findings and repairs

- MCP coercion of string/boolean feed limits: fixed with StrictInt and actual MCP
  regression coverage. Gateway validates unexpected arguments before upstream calls.
- Incorrect stdio stderr sink type: fixed to Path(os.devnull), covered by real
  subprocess stdio transport test against a fake upstream.
- Overbroad phone redaction removed career dates: narrowed and date preservation tested.
- Per-stage capability status replaced earlier sections: now accumulates section states
  and individual attempt timestamps while preserving earlier successful acquisition timestamps.
- Fresh explicitly empty posts caused needless rereads: explicit EMPTY_OBSERVED receipts
  now support fresh empty cache; vague/unknown empty results still require refresh.
- Registration writes were non-atomic: now atomic with a concurrent-change check;
  conflicting registrations remain preserved. Reinstall reuses the isolated environment.
- Prior import-only documentation contradicted account access: current contracts now
  identify the restricted exception while preserving generic-provider guards.

Write and raw-passthrough attempts receive zero upstream calls. No inbox or arbitrary
profile URL parameter is exposed. Account text remains untrusted evidence. Receipt
validation does not prove agent normalization or semantic claims are accurate;
li-fact-check and human review remain required. Public-query minimization is supported
by a strict helper and instructions, not a system-wide interception of arbitrary tools.

Residual risks: trusted-local-operator task resets are not a cryptographic user-turn
boundary; malicious concurrent filesystem manipulation is outside this local-tool
threat model; upstream browser behavior can produce view events and batch overrun;
bounded sections may be incomplete; third-party browser automation is not an approved
LinkedIn API and may encounter platform restrictions. No new evasion/proxy/cookie-import
mechanism was added. Model-session context may be sent to the configured model service.

## Validation

Baseline before changes: 310 core tests passed, 0 failures/skips.

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-account-pycache python3 -m unittest discover -s tests -q
tools/linkedin/.venv/bin/python -m unittest discover -s tools/linkedin -p 'test_mcp.py' -q
```

Final core suite: **372 discovered, 372 passed, 0 failed, 0 skipped**, including 62
new gateway/normalization/storage/freshness/privacy/setup tests. Optional MCP suite:
**9 discovered, 9 passed, 0 failed, 0 skipped**, including exact catalogue, denied
writes, strict limits/unexpected parameters and real subprocess transport with a fake upstream. Skill
metadata/resources and installed-copy consistency are also checked. Core scripts
remain standard-library-only; optional MCP dependencies stay isolated.

Live evidence is reported above separately from synthetic tests. Local humanizer
made no edits to the draft; quality panel found zero generic-language hits, formatting
artefacts or repeated structural patterns. Those are style heuristics, not factual
verification or proof of authorship. LICENSE and upstream MIT attribution remain intact.
No commit or push was performed.

The project-local registration was written and programmatically validated. Restart
Codex/reopen this trusted project to load the new MCP registration if the five tools
are not yet visible. Acceptance used actual MCP clients, not a claim that the current
running Codex session had already reloaded its tool catalogue.

## Subsequent professional-memory validation

The 372-test result above records the account milestone before the memory supplement.
Current combined validation is recorded in
[PROFESSIONAL_MEMORY_REVIEW.md](PROFESSIONAL_MEMORY_REVIEW.md). The account login/MFA
limitations above are not reclassified as tested by the memory work.
