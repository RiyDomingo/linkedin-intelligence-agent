---
name: li-read
description: "Connect LinkedIn and read my profile, career, own posts or feed through the restricted account gateway. Use for account onboarding, relevant refreshes and source troubleshooting; imports remain a fallback."
---

# li-read

Read [the shared contract](../li-context/references/context-contract.md) and
[the read-source contract](references/read-contract.md).

Prefer ACCOUNT_CONNECTED when the project gateway is installed, enabled and actually
usable for the requested capability. Read [the account workflow](references/account-connected.md)
for onboarding, refresh, normalization and failure handling. Inspect the actual
session tool catalogue: only connector_status, read_my_profile, read_my_posts,
read_feed and close_session belong to this connector. No inbox or account writes.
Tool presence is not evidence of successful authentication or data acquisition.

Otherwise identify LOCAL_CACHE, IMPORT or USER_SUPPLIED explicitly. Use
`scripts/read_layer.py --root <project>/.linkedin-agent status`, `show`, local
`refresh`, `import` or `import-csv` as appropriate. A local file refresh is not a live
LinkedIn refresh. Do not silently substitute imports in an account acceptance test.
Private imported messages still require retention opt-in and stay excluded by default.
Preserve sources, nulls, coverage, errors and dates. Unseen sections remain unknown.

Candidate discovery remains separate: apply [li-research](../li-research/SKILL.md)
for bounded external-index metadata and non-LinkedIn research. Never use generic
Scrapling, Playwright, Bright Data, Jina or Agent Reach account commands as a fallback
for the restricted account gateway. Stop on authentication challenges/restrictions;
only the user completes login/verification in the dedicated connector browser.

Local `purge` previews imported receipts/cache; `--confirm-import-purge` removes only
its documented local files. Account observations/summaries have separate retention;
closing the connector preserves authentication and curated context.
