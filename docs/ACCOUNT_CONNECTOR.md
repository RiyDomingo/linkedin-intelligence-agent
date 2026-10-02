# Connect LinkedIn in Codex desktop

The optional account connector reads your own profile, professional sections, recent
own posts and a bounded feed sample. You sign in yourself in its dedicated browser;
Codex handles normalization and builds dated professional context. No manual copying
is required on this path. Imports remain available when connection is unavailable.

**Mechanism:** third-party browser automation using a dedicated persistent browser
profile, not OAuth or an approved LinkedIn API. The upstream project and LinkedIn
policies may change. A read-only gateway does not imply platform approval or guarantee
no incidental profile/feed view events. See [upstream](https://github.com/stickerdaniel/linkedin-mcp-server)
and [LinkedIn's policy](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions).

## Setup

Core local writing works without this integration. Account setup needs macOS, uv and
Python 3.12; it uses a separate `tools/linkedin/.venv`, not the web research venv.
Run from the repository folder (or ask Codex to perform these steps):

```sh
python3 tools/linkedin/setup.py --install --provision-browser --write
python3 tools/linkedin/manage.py --root .linkedin-agent enable
```

The setup installs the hashed lock, provisions the upstream browser, validates the
five-tool catalogue and previews/adds the project-local registration. Conflicting
registrations are preserved. No global Agent Reach configuration changes. First
installation requires network access; normal gateway startup uses the installed
package, not uvx/@latest. Browser provisioning can update the upstream-managed cache.

Restart Codex if necessary, then ask:

> Connect LinkedIn and build my professional context from my profile and own posts.

A dedicated connector window opens if authentication is needed. Enter credentials
and complete verification there, never in chat. Return to Codex and confirm login
finished if requested. An existing saved dedicated login may be reused. Signing in
inside the Codex browser or Chrome does not automatically authenticate this connector.

Then ask:

> What deserves my attention today?

> What have I been posting about recently?

> Review my profile.

> Give me three post ideas relevant to my current work.

## Actual interfaces and bounds

Codex sees exactly connector_status, read_my_profile, read_my_posts, read_feed,
close_session. Upstream 4.26.1 provides get_my_profile(sections, max_scrolls),
get_feed(num_posts) and close_session. No get_my_posts exists: gateway own posts use
get_my_profile(sections="posts"). Profile main text is named main_profile.

| Read | Initial onboarding | Routine refresh |
| --- | --- | --- |
| Experience | up to 5 scroll attempts | up to 2 |
| Education, skills, projects, honors, certifications, languages | up to 3 each, combined call | up to 2 each, combined call |
| Interests | up to 2 | up to 2 |
| Own posts | up to 3 | up to 2 |
| Feed | target 10, max requested 20 | target 10, max requested 20 |
| Acquisition calls | maximum 6 | maximum 4 |

These are upper bounds, not targets or guarantees of completeness. Upstream feed
loading batches can exceed the requested count; only up to 20 clearly attributable
bodies may be retained. There is no exact browser item-count guarantee. Unordered
feed links are omitted; normalized observed post URLs remain null. Truncated text,
missing dates and incomplete career sections are reported, not invented.

A local `begin-task` control establishes each finite budget once per genuine user
request. Onboarding stages require an onboarding task. Identical acquisitions cannot
repeat in that task. This is a trusted local operator boundary, not cryptographic
proof of the number of Codex turns; don't reset budgets to continue harvesting.

Freshness: profile 30 days; own posts 3 days; feed 1 hour when feed analysis matters.
Explicit refresh bypasses TTL. Simple rewrites trigger no account access. Retrieval
freshness and post event age are distinct; an undated post is not today's activity.

## Storage and disabling

Normalized observations live in `.linkedin-agent/account/observations`, shared
read/cache.json, and dated labelled summaries in account/summaries. Receipt metadata
and independent capability status preserve actual retrieval times and section errors.
New data files are 0600 and directories 0700 on Unix. Curated identity/knowledge and
confirmed publication history remain unchanged. Observed facts are not independently
verified or automatically cleared for public use. Voice/themes and inferred interests
remain INFERRED. Context sent to Codex may enter its model service; local storage is
not a guarantee of entirely local inference.

Authentication stays in the upstream's dedicated `~/.linkedin-mcp/profile`, outside
the repository. No cookies, passwords, screenshots, raw pages or browser profiles
are saved into `.linkedin-agent`. Upstream diagnostics/update checks are suppressed;
no browser-cookie import, proxy or general upstream tool catalogue is exposed.

```sh
python3 tools/linkedin/manage.py --root .linkedin-agent disable
python3 tools/linkedin/manage.py --root .linkedin-agent status
```

Disabling blocks new reads immediately on the next call without deleting login or
local context. `LINKEDIN_ACCOUNT_CONNECTOR_ENABLED=false` is an additional process
kill switch and cannot be overridden by local enable. Closing a session preserves
login. No MCP logout tool is exposed; deliberate logout uses the upstream operator
flow, which can remove its dedicated profile. Never point it at a project directory.

## Capability truth and failures

connector_status is passive and describes the last observation; it does not probe
cookies or prove the current login remains valid. Profile, posts and feed report
independently. Inbox/network/analytics are not added by this connector. Imported
messages can still be used by li-inbox with its existing privacy rules.

NOT_INSTALLED, DISABLED, NOT_AUTHENTICATED, AUTH_CHALLENGE,
RATE_LIMIT_OR_RESTRICTION, PARTIAL_READ, UPSTREAM_TIMEOUT, UPSTREAM_ERROR,
MALFORMED_RESPONSE and SUCCESS are distinct outcomes. Challenges/restrictions stop
acquisitions. Only the user resolves verification; there is no automated retry,
identity rotation, CAPTCHA solver or alternate scraper fallback. Useful cached
context survives failures and is explicitly dated. Acceptance never substitutes
imports and claims account success.

All publication, messaging, comments, reactions, follows, connections and profile
edits are unavailable through this gateway. Public research still uses the existing
router and must not receive private account content. External LinkedIn discovery
remains search metadata through its existing separate bounded path.

See [the account implementation review](ACCOUNT_CONNECTOR_REVIEW.md) for actual
live validation and remaining limitations.

## Optional professional enrichment

After connection, resume/CV, bio, personal website and other professional links can
optionally enrich [private professional memory](PROFESSIONAL_MEMORY.md). All can be
skipped or added later. Account observations synchronize into the shared memory API;
curated context and authentication remain separate. Existing cache can be reused
without another account read.
