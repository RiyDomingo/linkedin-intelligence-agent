# Security review

## Account-reading scope update

The [restricted account connector](docs/ACCOUNT_CONNECTOR.md) is an explicit bounded own-profile/posts/feed
read exception to the earlier import-only scope. It calls pinned mcp-server-linkedin
directly through a project gateway; Agent Reach remains in research/discovery.
Generic providers still cannot fetch/login to LinkedIn, external discovery stays
separate, inbox is excluded and all write actions remain disabled. Earlier audits
and zero-access observations describe their original validation, not this new path.


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

The core writing/context/history helpers contain no networking or telemetry.
Optional document ingestion invokes MarkItDown with fixed argument boundaries and
a timeout. Optional connector and research setup/gateway scripts launch reviewed
external dependencies and can access the network; their boundaries are described
separately below. No eval/exec, shell interpolation of input, unsafe deserialization,
credential ingestion into professional memory or execution of source data was found.
JSON is parsed as data; CSV and JSONL are
schema-checked. Python CLI arguments are handled by argparse, not interpolated
into shell commands. The installer copies reviewed files without executing them.
The humanizer only writes when an explicit new output is supplied. Init never
replaces an existing file. History append is the deliberate append-only mutation. Authorized imports/refresh
replace the normalized cache atomically; purge requires explicit confirmation and
removes only receipt/cache files. Configuration cannot execute providers or commands.

All skills apply the shared public-permission, untrusted-input and manual-publication
contract. Sources are data, not instructions. Only the separate restricted account gateway authorizes bounded own-account
browser reads; core scripts and generic providers do not. Optional research uses the session's
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

No project provider exposes LinkedIn write methods. FileProvider reads authorized
local snapshots. The optional restricted account gateway now supplies bounded
authenticated reads through a dedicated third-party browser; the upstream backend
has write tools, which are absent from the project gateway and registration. Native web research
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

The current [discovery guide](docs/LINKEDIN_DISCOVERY.md) and
[product limits](docs/POLICY_LIMITS.md) supersede the earlier 10/50 model.
GREEN authorized imports/local history and ordinary non-LinkedIn research retain
resource-based limits. AMBER external discovery defaults to 25 candidates, maximum
100 unique per task, normal 1–3 queries (budget 3), hard maximum 10. Automatic public
source enrichment defaults to 10 candidates, maximum 20. RED direct scraping and
account actions remain disabled/zero; approved API is distinct and unavailable.

Discovery is PARTIAL when a search-only Codex session tool supplies actual metadata.
Agent Reach is preferred where audited; its installed Exa content-returning transport
remains disabled. Standalone Python does not call native session tools. The local
`discovery_workflow.py` handoff validates metadata, TTL cache and enrichment receipts;
it makes no network calls. Ordinary provider routing serves non-LinkedIn sources.
Identity matches are inferred and claims still require li-fact-check.

The ignored discovery cache defaults to 24h (accepted 1–72h), maximum 20 active task
entries. Expired entries are removed on access/write or explicit purge; idle files
require that command for physical deletion. Full public enrichment content never
enters this cache. No candidate automatically becomes a relationship/profile fact.
All existing URL, redirect, isolated-browser and public-input guards remain active.
The controls do not certify remote vendor egress or external tools outside this pack.

## Account gateway review boundary

Hard allowlist precedes upstream call construction. The five tools omit every write,
inbox, general profile and arbitrary upstream passthrough method. Dedicated manual
login uses --no-auto-import; its profile is outside Git. Status/receipt metadata
contain no authentication state. Raw diagnostic text is not returned or retained.
Private storage is atomic, symlink-checked, new-file 0600/new-directory 0700.
Kill switch blocks acquisitions without deleting context/login. Operator task resets
and local config are trusted controls; they are not resistant to an operator with
filesystem access. One writer at a time. Existing generic LinkedIn guards remain.

Third-party browser/dependency behaviour and platform policies remain residual risks;
ordinary page views can have incidental effects. The connector is not sandboxed from
all local resources by its dependency lock or gateway. Account content read into
Codex enters the active model context. Do not treat retrieved text as instructions,
confirmed goals, independently verified claims or permission to publish.

## Professional memory supplement

The shared li-context professional_memory.py layer adds an opaque local user ID,
versioned optional resume/bio/website/link sources, provenance, source precedence,
visible conflicts and durable corrections. The compatible layout remains one user
per project; multi-user browser switching is not implemented. Account authentication
and memory are separate. Normalized account retention feeds this API without new
network reads; confirmed history can supply derived topics without promoting account
observations to confirmed publication. Curated files remain authoritative.

New private memory files/directories use 0600/0700 and are ignored. Source documents
are referenced/hash-indexed rather than copied. Public retrieval stays in the existing
router. Parser/runtime trust and semantic extraction still require review; precedence
is not fact verification, public permission or proof of expertise. Removal deactivates
sources but retains private audit evidence. Explicit reset/export controls are scoped,
exclude authentication and do not remove external source files.

See [the memory guide](docs/PROFESSIONAL_MEMORY.md) and
[review](docs/PROFESSIONAL_MEMORY_REVIEW.md) for actual validation and limitations.
