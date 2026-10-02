# LinkedIn migration validation record

Date: 2026-10-02. Python standard-library suite, local checkout and temporary
installed copies. No LinkedIn operations or public publication occurred.

| Check | Command/method | Result |
| --- | --- | --- |
| Automated suite | `python3 -m unittest discover -s tests -v` | 150 discovered, 150 passed, 0 failed, 0 skipped |
| Python syntax/import compilation | `python3 -m compileall -q skills scripts tests` | Passed |
| Skill frontmatter/scaffold validation | Bundled Skill Creator `scripts/quick_validate.py` on all twenty skill folders | 20 passed |
| Diff whitespace | `git diff --check` | Passed |
| Installation | Test copies complete pack into temporary `.agents/skills`, unrelated cwd and paths with spaces | All links and Python CLIs resolve; attribution included |
| Local starter context | `context.py --root .linkedin-agent init` then `status` | 14 files now present (11 initial, 3 added without overwrite); no missing files; 7 identity/knowledge templates deliberately unfilled |
| Licensing | Compare current LICENSE bytes with `git show HEAD:LICENSE` | Identical |
| Git safety | Initial/final status and remote inspection | Initial clean; only migration changes; remotes unchanged; no commit/push |

Independent read-only review ran the then-current 71-test suite and reasoned through
unsupported efficacy plus a confidential customer, speaker attribution, draft approval
versus actual publication, repeated topic with new evidence and pasted instructions
to leak context. It found CSV-header/row corruption acceptance, loose date formats
and subdivision flag damage. These were fixed and regression-tested. Documentation
links that were initially absent during that concurrent review were subsequently
created and checked.

This was an independent engineer-style code and instruction review, not a live
model integration evaluation. It found no material publication/security bypass.
Prompt-based gates still depend on judgment. Live skill selector behavior, public
plugin submission and optional PDF-renderer integration were not tested. The repo
is packaged and ready for the documented local installation; it was not installed
into the user's global skill directories.

## Intelligence extension validation

The expanded suite retains the original 77 toolkit tests and adds 73 read/intelligence
checks. Coverage includes all normalized kinds, null fields, source/time validation,
capability fallback, empty/unavailable/partial/stale responses, incremental hashing,
complete-snapshot retirement and watermarks, old-receipt rejection, CSV mapping,
private-message consent, cache permissions/tampering, scoped purge, meaningful
attention, relationship obligations, future/stale suppression, weekly strategic
metrics and observed-versus-confirmed memory. Copied-pack tests also run read status
and intelligence CLIs from an unrelated directory with spaces.

A second independent read-only review ran the expanded suite and reviewed all twenty
entrypoints. It confirmed the four extension fixes, then found the empty-complete
snapshot ordering gap for previously unseen old comments. Provider/capability
watermarks and regression tests fixed that gap. The final suite is 150 tests.

`python3 scripts/demo_brief.py` selected the two useful fictional candidates and did
not manufacture a reply to generic praise. It ran only in a temporary directory.
Actual project read status remains Manual with every account capability unavailable:
no user data was imported and no live provider was connected. Optional Agent Reach
was detected but remains disabled; no account/backend probe occurred. No LinkedIn
publication, connection, reaction, message or profile edit occurred.

Final narrow independent verification confirmed all 150 tests pass, validated the
empty-complete watermark behavior and found no material remaining issues. Finished
documentation and local Markdown links were checked.

## Final Git inventory

14 tracked files modified, 7 tracked paths removed/moved, 71 new untracked files.
All belong to this migration/extension. Private starter context is ignored, not
tracked; no unrelated work was removed. HEAD and remotes are unchanged. No commit
or push was performed. Full file inventory from `git status --short --untracked-files=all`:

```text
 D .claude-plugin/marketplace.json
 D .claude-plugin/plugin.json
 M .gitignore
 M README.md
 M skills/li-audit/SKILL.md
 M skills/li-carousel/SKILL.md
 M skills/li-comment/SKILL.md
 M skills/li-dm/SKILL.md
 M skills/li-human/SKILL.md
 D skills/li-human/detect.py
 D skills/li-human/humanize.py
 D skills/li-human/slop.json
 M skills/li-inbox/SKILL.md
 M skills/li-plan/SKILL.md
 M skills/li-post/SKILL.md
 D skills/li-post/hooks.json
 M skills/li-profile/SKILL.md
 D skills/li-profile/rubric.json
 M skills/li-reply/SKILL.md
 M skills/li-repurpose/SKILL.md
 M templates/voice.md
?? ARCHITECTURE.md
?? EXAMPLE_BRIEF.md
?? MIGRATION.md
?? NOTICE.md
?? SECURITY.md
?? VALIDATION.md
?? plugin.json
?? scripts/demo_brief.py
?? scripts/install_skills.py
?? skills/li-audit/agents/openai.yaml
?? skills/li-brief/SKILL.md
?? skills/li-brief/agents/openai.yaml
?? skills/li-brief/references/attention.md
?? skills/li-carousel/agents/openai.yaml
?? skills/li-comment/agents/openai.yaml
?? skills/li-context/SKILL.md
?? skills/li-context/agents/openai.yaml
?? skills/li-context/references/context-contract.md
?? skills/li-context/scripts/context.py
?? skills/li-context/templates/analytics/performance.csv
?? skills/li-context/templates/history/comments.jsonl
?? skills/li-context/templates/history/posts.jsonl
?? skills/li-context/templates/history/topics.json
?? skills/li-context/templates/identity/audience.md
?? skills/li-context/templates/identity/bio.md
?? skills/li-context/templates/identity/voice.md
?? skills/li-context/templates/knowledge/claims.md
?? skills/li-context/templates/knowledge/companies.md
?? skills/li-context/templates/knowledge/metrics.md
?? skills/li-context/templates/knowledge/projects.md
?? skills/li-context/templates/priorities.json
?? skills/li-context/templates/relationships.json
?? skills/li-context/templates/sources.json
?? skills/li-dm/agents/openai.yaml
?? skills/li-engagement/SKILL.md
?? skills/li-engagement/agents/openai.yaml
?? skills/li-fact-check/SKILL.md
?? skills/li-fact-check/agents/openai.yaml
?? skills/li-fact-check/references/claim-gate.md
?? skills/li-history/SKILL.md
?? skills/li-history/agents/openai.yaml
?? skills/li-history/references/history-schema.md
?? skills/li-human/agents/openai.yaml
?? skills/li-human/references/slop.json
?? skills/li-human/scripts/detect.py
?? skills/li-human/scripts/humanize.py
?? skills/li-ideas/SKILL.md
?? skills/li-ideas/agents/openai.yaml
?? skills/li-inbox/agents/openai.yaml
?? skills/li-plan/agents/openai.yaml
?? skills/li-post/agents/openai.yaml
?? skills/li-post/references/hooks.json
?? skills/li-profile/agents/openai.yaml
?? skills/li-profile/references/rubric.json
?? skills/li-read/SKILL.md
?? skills/li-read/agents/openai.yaml
?? skills/li-read/assets/sample-read.json
?? skills/li-read/references/read-contract.md
?? skills/li-read/scripts/intelligence.py
?? skills/li-read/scripts/models.py
?? skills/li-read/scripts/read_layer.py
?? skills/li-reply/agents/openai.yaml
?? skills/li-repurpose/agents/openai.yaml
?? skills/li-research/SKILL.md
?? skills/li-research/agents/openai.yaml
?? skills/li-research/references/research-routing.md
?? skills/li-weekly/SKILL.md
?? skills/li-weekly/agents/openai.yaml
?? templates/published-post.json
?? tests/test_intelligence.py
?? tests/test_toolkit.py
```

## Optional web-tooling extension validation (2026-10-02)

The Git inventory above records the completed migration before this extension.
The latest offline suite contains **160 tests: 160 passed, 0 failed, 0 skipped**,
including ten added configuration/launcher checks. Resource validation now covers
all repository-owned JSON bundles/manifests rather than ignored third-party JSONC
fixtures or private user data; no bundled-resource checks were removed.

- Scrapling 0.4.15: imports/fetcher/spider APIs, MCP initialization, real public HTTP
  structured Markdown and dynamic readable text passed. CSS/title parsing passed
  on an offline fixture. Public fixture: Quotes to Scrape.
- Playwright MCP 0.0.83: initialization, isolated Chromium launch, navigation,
  snapshot and following Next to page 2 passed through actual MCP tool calls.
- Agent Reach 1.5.0: safe check-only health command completed; unauthenticated V2EX
  adapter returned one nonempty public record. No account/cookie setup was performed.
- Bright Data 2.11.3: disabled project configuration parsed/recognized; missing-key
  failure exits 2 clearly. Patched SDK local initialization worked with an invalid
  placeholder; no retrieval tools were called and no valid account token was used.
  Sandbox DNS blocked its attempted zone check. Paid retrieval remains untested.
- uv pip check: all 48 optional Python packages compatible. npm audit after the
  official MCP SDK 1.31.0 override: zero reported vulnerabilities.
- codex mcp list: recognizes the two enabled local providers and disabled fallback.
  Existing global/plugin MCP entries retained. Restart needed for current chat tools.
- Python compilation and diff whitespace checks passed. No build/lint/type pipeline
  exists to run. Secrets, cookies, profiles, dependencies and browser caches remain
  unstaged/untracked and ignored. No commit or push occurred.

See docs/CODEX_WEB_TOOLING.md for commands, actual limits and removal instructions.

## Unified orchestration validation (2026-10-02)

The final suite now contains **207 tests: 207 passed, 0 failed, 0 skipped** on the
current Python environment. **47** are new orchestration/adapter regressions; the
prior 160 migration/tooling tests remain passing. Commands:

```sh
python3 -m unittest discover -s tests -q
python3 -m unittest discover -s tests -p test_orchestration.py -q
python3 -m compileall -q skills scripts tools/web/*.py tests
node --check tools/web/public_guard.cjs
git diff --check
```

Live commands used the existing `.venv/bin/python tools/web/research.py` bridge with
safe public request files and `/tmp/linkedin-orchestration-demo` as data root. No
real personal LinkedIn profile, account, credentials or user history was accessed.
Existing provider configuration and dependency installation were preserved.

| Scenario | Result and evidence |
| --- | --- |
| A: ordinary webpage | SUCCESS; Scrapling only; Quotes to Scrape title/URL and 3,001-character Markdown |
| B: interactive inspection | SUCCESS; Playwright MCP only; actual Next-page control → `/page/2/`; tightened guard rerun passed |
| C: specialist discussion | Public V2EX returned three real records with scope labelled hot topics; Reddit/X genuinely UNAVAILABLE; synthetic supported-adapter routing passed |
| D: ingestion | SUCCESS; Scrapling only; robots.txt 404 checked, bounded two-page crawl returned two records |
| E: daily review | Manual/degraded mode; no invented account actions; four relevant inferred external signals in demo root, separately from actions |
| F: rewrite/local writing | NO_RETRIEVAL; zero attempts |
| G: factual writing | Offline source assessment → history overlap → local humanizer/quality composition passed; provenance and unresolved personal-insight placeholder retained |
| H: primary failure | Offline BLOCKED simulation → one authorized managed fallback; disabled/no-cost-permission/auth failures stop appropriately |
| JavaScript retrieval | SUCCESS; guarded Scrapling DynamicFetcher; service workers/WebSockets blocked, redirects refused; Google referrer disabled |
| Structured extraction | SUCCESS; actual first-quote CSS field plus null for missing selector |

The G scenario tests deterministic composition using an explicitly labelled fixture;
it does not claim an LLM's source interpretation or final voice is scientifically
validated. Paid Bright Data retrieval was not exercised. Reddit/X account access was
not enabled. A V2EX result is community context, not primary factual verification.

Independent read-only review identified capability substitution, saved opt-in,
completion timestamp/freshness, redirect/service-worker/WebSocket and malformed
nested cache issues. These were fixed and covered with regressions. Browser hooks
now fetch without following redirects, reject 3xx before fulfilling, reject private
DNS/LinkedIn destinations and non-read methods, and close WebSockets. Remaining DNS
races and malicious UI controls are documented in SECURITY.md.

Actual project health: Scrapling detected/configured and PAGE_FETCH, JAVASCRIPT,
STRUCTURED_EXTRACTION validated; Playwright detected/configured and interaction
validated. Crawler/Agent Reach opt-ins remain off in the real data root; demo-root
crawl/V2EX were validated without changing it. Agent Reach is detected, public V2EX
validated but disabled by saved opt-in. Bright Data is detected, disabled and
unvalidated for retrieval. LinkedIn reader remains Manual with account capabilities
unavailable until legitimate imports/receipts are supplied.

LICENSE remains byte-identical to HEAD; Jake Schincariol attribution remains intact.
HEAD is still add2c23882fe79180737d242ff80a5da205eda6a. Existing work was preserved;
no staged changes, commit or push. Optional runtime receipts/artifacts and data cache
remain ignored. Full Git inventory is supplied in the final report.

## GitHub delivery authorization (2026-10-02)

The earlier no-commit/no-push statements record validation snapshots before delivery
was authorized. The user subsequently requested committing the completed migration
to GitHub. Final pre-delivery checks passed: 207 tests, diff whitespace and JavaScript
syntax. Private context, generated configuration, runtimes and browser artifacts are
excluded. Delivery targets the renamed fork's main branch; upstream remains unchanged.
