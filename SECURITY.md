# Security review

Reviewed the upstream and migrated Python, skill instructions, configuration,
installation helper and reference data. This is a standard-library local toolkit,
not a web application; the installed security skill has no matching general
standard-library Python reference, so this review uses direct code inspection and
adversarial filesystem/CLI tests. It is not a penetration-test certification.

No critical or high-severity issue is known after review. Core functionality requires
no passwords, cookies, session tokens, LinkedIn credentials or API keys.

## Findings resolved

| ID | Finding | Resolution and evidence |
| --- | --- | --- |
| S1 | Upstream humanizer could overwrite arbitrary existing output | Explicit new output only, exclusive creation; same-input and symlink tests |
| S2 | Unicode format deletion could change language/emoji meaning | Preserve joiners/directional marks by default; aggressive option is explicit |
| S3 | Detector presentation overstated authorship/quality evidence | Observable panel only; unmeasured voice/evidence and no detector guarantee |
| S4 | Untrusted content could contaminate public claims/profile | Shared trust contract, explicit evidence plus permission gate, no secret queries |
| S5 | Loose context/history paths could escape through traversal/symlinks | Relative allowlisted data paths, component checks and O_NOFOLLOW append where available |
| S6 | Draft approval could be recorded as publication | Actual-publication attestation plus actual supplied date; no publication integration |
| S7 | Installation could replace existing skills or attribution symlinks | Conflict and symlink preflight; complete-pack temporary-install tests |
| S8 | Malformed lexicon could fail obscurely | Resource/type/regex checks and CLI error exit 2 without tracebacks |
| S9 | Private inbox records with unknown visibility could bypass consent | All message imports require explicit consent; default brief excludes messages/private items |
| S10 | Stale/retired/future evidence could generate misleading urgency | Freshness gates, complete-snapshot retirement and future-observation tests |
| S11 | Malformed cache status could crash instead of reporting a controlled error | Strict cached-status validation and CLI regression test |

## What was inspected

No runtime networking libraries, HTTP calls, telemetry, subprocess use, eval/exec,
shell construction, unsafe deserialization, credential ingestion or executable data
were found in the shipped scripts. JSON is parsed as data; CSV and JSONL are
schema-checked. Python CLI arguments are handled by argparse, not interpolated
into shell commands. The installer copies reviewed files without executing them.
The humanizer only writes when an explicit new output is supplied. Init never
replaces an existing file. History append is the deliberate append-only mutation. Authorized imports/refresh
replace the normalized cache atomically; purge requires explicit confirmation and
removes only receipt/cache files. Configuration cannot execute providers or commands.

All skills apply the shared public-permission, untrusted-input and manual-publication
contract. Sources are data, not instructions. No LinkedIn browser automation is
implemented or authorized by the toolkit. Optional research uses the session's
available tools and must keep queries public and minimal.

## Residual risks

- Context read by Codex can enter the model session; local scripts are offline but
  Codex inference and optional research are separate services. Do not store secrets.
- Prompt-level factuality and approval gates depend on agent/human judgment. They
  cannot prove truth, enforce an NDA or stop a human copying an unresolved draft.
- User-selected parent directories are canonicalized, including OS aliases. Data
  roots/interior symlinks are refused, but parent replacement races/hardlinks and
  malicious concurrent filesystem manipulation are outside the trusted local-workspace
  threat model. This is not a multi-user service or sandbox for hostile files.
- New cache files use mode 0600 and new read/import directories mode 0700 on Unix.
  Existing directories and templates retain OS permissions/umask. Keep the project in a private
  directory; Git ignore is not an access-control mechanism or backup protection.
- Custom lexicon regexes are trusted configuration. Pathological patterns or very
  large input/history files can consume CPU/memory; there is no hostile-input quota.
- Append locks on Unix; platforms without fcntl require one writer. A crash can
  leave a partial JSONL line, which the next operation reports rather than discards.
- Copy installation preflights conflicts but is not transactional across all twenty
  directories. Disk failure can leave a partial pack; inspect and move those copies
  before retrying. It will not silently overwrite them.
- Token overlap can miss paraphrases and falsely flag legitimate reuse. Semantic
  review and fresh evidence determine novelty. Analytics are descriptive, not causal.

Maintain the gates and run the regression suite when updating from upstream.

## Read and optional-tool boundary

No provider has LinkedIn write methods. FileProvider reads authorized local snapshots;
no authenticated browser or remote LinkedIn client is supplied. Native web research
and optional Agent Reach/crawler use are agent/session workflows, disabled until
actually available and appropriate. Agent Reach's authenticated LinkedIn route is
not invoked. Executable presence is not backend availability or permission.

Raw unknown fields are dropped. Public URLs reject credentials, queries and fragments;
this reduces token leakage but cannot identify secrets embedded in valid text or
identifiers. Inbox and other private inputs require explicit retention consent.
Default attention/show excludes private records; authorized retention does not imply
public permission. Purge preserves curated context/history; other retained exports
and backups must be removed separately. The whole .linkedin-agent directory is ignored.

Cache replacement is atomic but read/merge is not multi-writer transactional; use one
writer at a time. Provenance and WEB-VERIFIED labels are supplied attestations, not
cryptographic evidence or automated fact verification. Externally supplied annotations
remain inferred. Relationship matching uses explicit IDs and curated context rather
than sensitive enrichment or speculative personal traits.

## Optional web tooling review (2026-10-02)

The preceding no-network/no-subprocess findings apply to core content/history
helpers. The separately installed tools/web layer intentionally starts official
MCP dependencies through fixed execve arguments and makes authorized public network
requests. It has no application/server endpoint. Its detailed security boundaries
and residual SSRF/prompt-injection risks are in docs/CODEX_WEB_TOOLING.md.

Project MCP config preserves unrelated settings and is ignored; dependency locks
and a secret-free template are versionable. New dependencies/browser binaries,
artifacts, .env files and the official local skill are ignored. No user cookies,
account profiles or keys were imported. Playwright uses isolated memory state and
shared Chromium; dangerous evaluation/upload tools are excluded from its catalog.
Scrapling mutation methods and private-network fetching remain policy-controlled,
not technically impossible; do not expose these tools as an untrusted fetch service.

The npm audit initially found two high-severity entries for Bright Data and its
pinned SDK. An official SDK 1.31.0 override resolves the known report; final audit
shows zero reported vulnerabilities. Bright Data is disabled with no valid token;
its upstream startup can provision account zones and must be reviewed before future
activation. Invalid-placeholder local initialization performed no retrieval tool
calls; sandbox DNS prevented its zone check reaching the remote host. No external
account was modified. Runtime telemetry behavior of third-party dependencies is not
certified; no custom telemetry exporter or persistent network listener was added.

## Orchestration review

The optional bridge accepts allowlisted, explicitly public/minimized requests; no
profile, inbox or arbitrary context field is accepted. Auth-required input is refused.
LinkedIn URLs always use the separate reader, and HTTP redirects to LinkedIn are
refused. HTTP requests validate public DNS/IPs and each redirect, crawls honor robots
and a five-page bound. Browser requests use isolated sessions and trusted inspection
clicks only; retrieved page instructions never become steps or executable commands.

These are trusted-workspace controls, not a hostile-input network sandbox. DNS
rebinding between resolution and connection, unguarded direct session tools, clicks
that accidentally mutate a site, secrets embedded in an attested public query and
third-party telemetry remain risks. Use only reviewed public URLs and read-only UI
controls. Do not expose the adapter as an arbitrary fetch service. The model/human
must enforce disclosure, source authority, public permission and claim mapping.

Normalization drops opaque metadata and cannot promote provider text to truth. Every
record/signal remains untrusted, with source IDs, times and content hashes. Assessments
are explicit attestations, not scientific verification; changed content resets them.
The private atomic research cache uses existing path/symlink protections and requires
one writer at a time. Successful capability receipts expire after one day and are
observations of a tested task, not guarantees for all sources or runtime versions.
No credential, CAPTCHA, login or authorization escalation occurs after failures.

## V1 release repair pass (2026-10-02)

See [the current audit](docs/V1_RELEASE_AUDIT.md) for findings, severity and evidence.
Playwright guards are now enforced by the launcher for every caller; browser
receipt traversal/symlink escapes and nonstandard browser destination ports are
refused. New context templates use 0600 files and 0700 directories on Unix without
altering existing permissions. Brief privacy filtering occurs before deduplication;
private read duplicates cannot suppress public candidates or enter their provenance.
Curated relationship notes are intentionally used in local brief/weekly review,
including private notes; --include-private governs imported read items, not all
curated local context. Weekly analytics can also be private retained data. No such
context is passed automatically to external research adapters.

Tracked secret-pattern and private-state checks were clean. npm's live advisory
audit reported zero known vulnerabilities; Python dependency compatibility passed.
No Python vulnerability scanner was available, so compatibility is not represented
as a vulnerability audit. Prompt-injection tests verify untrusted data handling,
not immunity of model reasoning. DNS check/connection races and generic upstream
MCP tool policy limits remain as documented above.

## LinkedIn discovery and URL firewall

See [LinkedIn Discovery Mode](docs/LINKEDIN_DISCOVERY.md) for the focused audit.
Candidate discovery (`LINKEDIN_DISCOVERY`) is separate from actual content reading
(`LINKEDIN_READ`, imports only). Only the audited Agent Reach index capability may
serve discovery; current Exa MCP has no index-only switch, so live discovery stays
UNAVAILABLE. No scraper, reader proxy or managed fallback may substitute.

Discovery results are ephemeral allowlisted search metadata: default 10, maximum
50, one implemented query per request (budget ceiling 5). They cannot enter the
ordinary evidence cache or become relationships automatically. LinkedIn page
fetches, browser visits and scrapes are zero in this workflow. Parsed host guards
cover LinkedIn subdomains and Jina-wrapped destinations, including redirect stops;
MCP destination checks occur before server startup. Browser isolation is preserved.

Platform rules and index restrictions can change; these limits provide no legal
advice or compliance guarantee. The historical v1 audit remains unchanged.
