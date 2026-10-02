# LinkedIn Intelligence Agent migration audit and decisions

Audit date: 2026-10-02. Starting commit:
`add2c23882fe79180737d242ff80a5da205eda6a`.
The existing checkout was used. Initial `git status --short` was empty. No reset,
stash, clean, commit or push was performed. `origin` is the user's fork and
`upstream` is Jake Schincariol's repository; both remote URLs were preserved.
The MIT LICENSE remains byte-for-byte identical to the starting commit.

## Verified Codex conventions

Inspected the installed system Skill Creator and OpenAI Docs instructions, their
metadata examples, the environment's available-skill catalog and local installed
skill directories. The environment exposes both `.agents/skills` and legacy
`.codex/skills` user resources plus plugin-cache skills; this is observed behavior,
not a new path invented for this project.

Read current official [skill documentation](https://learn.chatgpt.com/docs/build-skills)
and [plugin packaging guidance](https://developers.openai.com/plugins/build/plugins).
They establish frontmatter name/description, progressive resource loading,
`scripts/`, `references/`, optional `agents/openai.yaml`, implicit selection and
explicit `$skill` usage. Documented repo discovery uses `.agents/skills` up to the
repo root and user discovery uses `~/.agents/skills`. Plugin distribution now
prefers a portable root `plugin.json`; the Codex compatibility overlay is still
supported, but unnecessary for this skills-only package. No MCP or lifecycle hooks
are required. Writing “hook” here means an opening-copy formula, not an executable
Codex lifecycle hook.

Accordingly, the repository's `skills/` is a distribution source, installed as a
complete pack using a tested copy helper. The helper preserves sibling resource
paths and attribution and refuses conflicts. No invented config variable, command
or universal plugin-install command is documented. Live marketplace acceptance and
model-driven automatic triggering are not established by unit tests.

## Original inventory

All tracked non-Git files were inspected, including README, LICENSE, ignore rules,
both Claude manifests, the voice template, all eleven SKILL.md files, the two
Python scripts, slop.json, hooks.json and rubric.json. `.DS_Store` was ignored OS
metadata, not project logic; it was left alone.

| Upstream files/behavior | Classification | Migration |
| --- | --- | --- |
| `.claude-plugin/plugin.json`, `marketplace.json` | Claude packaging | Removed; portable root plugin.json added |
| README install and slash-command examples | Claude-specific | Rewritten for verified discovery/invocation |
| `~/.claude/linkedin/voice.md`, plan.md, log.md | Shared context with hard-coded vendor path | Explicit project-local context; JSONL history |
| Eleven `skills/*/SKILL.md` files | Portable workflows plus vendor instructions | Focused Codex metadata and composed context/gates |
| li-post hook options/structure | Prompt workflow | Retained flexible selection; fictional examples never user facts |
| li-comment nine comment types | Prompt workflow | Retained choices and batch comments |
| li-reply five buckets | Prompt workflow | Retained prioritization and manual replies |
| li-profile 12-part scoring rubric | Portable JSON + reasoning | Retained 100 points; unknown inputs unassessed |
| li-plan weekly/calendar/engagement workflow | Prompt workflow | Retained; frequency/timing are experiments, not universal truths |
| li-carousel sequence and accompanying post | Prompt workflow, optional renderer | Retained; actual PDF requires available tools and verification |
| li-repurpose extraction categories | Prompt workflow | Retained; attribution and intra-batch overlap review added |
| li-dm invite/first message/two follow-ups | Prompt workflow | Retained; unsupported throttling claims removed |
| li-inbox five buckets | Prompt workflow | Retained; spam/sequence judgments explicitly uncertain |
| li-audit normalized metrics and patterns | Reasoning on user data | Retained formulas; missing denominators/sample uncertainty explicit |
| humanize.py three passes/case/URL logic | Deterministic Python | Moved to scripts; meaningful Unicode and output behavior hardened |
| detect.py five weighted “human” scores | Deterministic heuristics, misleading conclusions | Replaced with descriptive quality panel, no classifier verdict |
| slop.json vocabulary and patterns | Shared deterministic rules | Moved to references; structural advice reframed as preferences |
| hooks.json, rubric.json | Portable reference libraries | Moved to references; unsupported performance/mandatory-number claims removed |
| templates/voice.md | Portable content with Claude setup | Revised; expanded starter tree bundled in li-context |
| LICENSE | Required MIT terms and copyright | Unchanged; NOTICE and installer attribution added |
| `.gitignore` | Portable ignore rules | Retained and extended for private context and installed copies |

## Compatibility baseline and improvements

The original eleven names and user-facing capabilities remain. They are workflows,
not programs that need a Claude runtime. Native equivalents preserve useful choices
and outputs while removing `/li-*` commands and account-management language. The
original source remains recoverable from the starting Git commit; no archival copy
of unsafe instructions is loaded by the migrated skills.

New support skills: context, fact-check, research, history and ideas. Context files
are loaded progressively from the active project, independent of installation.
Shared contract and templates live inside li-context because loose root resources
would break copied skills. All twenty siblings are installed together. Large JSON
libraries stay outside entrypoints, and support logic is referenced rather than
repeated in each writing skill.

New deterministic code initializes missing templates, validates profiles/structured
history, appends confirmed publications, checks token overlap and summarizes measured
performance/neglected themes. Semantic novelty, source assessment, factuality and
voice matching remain explicitly agent/human reasoning. No truth classifier,
embedding service or database is implied.

The humanizer retains upstream transformation mechanisms but removes URL sentinel
collisions, handles punctuation-ending phrases, preserves paragraph boundaries,
protects emails/URLs, offers voice-preserving switches and rejects output overwrites.
It preserves meaningful joiners/direction marks and subdivision flag emoji by default. The new analyzer counts
observable features without rewarding fabricated evidence or forcing personal
pronouns. No detector-service claims remain in runtime guidance.

## Validation and review

Automated tests exercise transformations, Unicode, protected spans, reports, malformed
input, quality samples, profile states, history operations, duplication, metrics,
symlink/traversal rejection, copied installation, resource links and licence fidelity.
The bundled Skill Creator validator checks each entrypoint. Installed-copy CLI tests
run from an unrelated directory with spaces in the path. Tests establish resource
resolution and program behavior; they do not establish model selection quality or
publication-platform compatibility.

Fresh review found and fixed OS path-alias rejection, spaces lost between protected
URLs, invalid-regex tracebacks, paragraph-consuming dash cleanup, invalid-history-kind
side effects, quadratic repeated-sentence counting and attribution-path symlink
handling. Independent review additionally found and fixed loose ISO date parsing,
duplicate/extra CSV fields and subdivision flag-emoji damage. See SECURITY.md for boundaries and residual risks. No migration changes
were committed, and no LinkedIn account was accessed.

## Supplementary intelligence extension

The supplementary request was audited against the working migration before further
changes. The original eleven entrypoints were retained and upgraded in place; four
new read/attention skills extend the five initial support skills, totaling twenty.

| Requirement | State before extension | Delivered implementation |
| --- | --- | --- |
| Source/capability detection | Research tool availability only | Read-only protocol, local snapshots, explicit status and fallback |
| Profile/posts/comments/people/analytics | Supplied prose plus history | Allowlisted normalized models; unknown values remain null |
| Freshness/provenance/incremental refresh | Publication dates only | Source timestamps, hashes, changed/active state and snapshot retirement |
| Daily attention | Individual reply/comment workflows | li-brief: 0–5 material recommendations with reasons and writing composition |
| Relationships | Audience and supplied conversation | Curated relationship context, explicit obligations and no sensitive inference |
| Weekly learning | Metric audit and history summary | li-weekly: observed versus confirmed activity and strategic signals |
| Content memory | Confirmed publications | Combined read-only observed/confirmed view, lookup and overlap |
| Optional external research | Session research tools | Native-first routing, optional disabled Agent Reach/crawler flags |
| Privacy/removal | Ignored context and public-permission gate | Private import opt-in, default attention exclusion, scoped preview/purge |
| Degraded modes | Missing context placeholders | Manual/Partial/Rich evidence coverage with explicit unavailable/stale data |

New code lives under li-read and uses fixed sibling context helpers; sources cannot
load modules or commands. Data configuration is project-local and not presented as
Codex host configuration. A FileProvider transports local receipts for every source
type. No live LinkedIn API/client was available or added; no label is marketed as
an actual account integration. Core daily use works from authorized supplied data.
Public session research is conditional on actual tool access, not executable presence.

Local optional-tool audit found Agent Reach, mcporter and opencli executable paths.
Only Agent Reach help and installed reference instructions were inspected. No doctor,
backend probe, login, cookies, package installation or account configuration occurred.
Its documented authenticated LinkedIn path was explicitly excluded. Native web and
Firecrawl capabilities are exposed in the session; LinkedIn access was not probed.

Independent review of the extension found absent records surviving complete snapshots,
unknown-visibility inbox imports bypassing consent, future-dated curated follow-ups,
and malformed cached status raising an uncontrolled error. Each was fixed with
regression coverage. A further review found unseen old items bypassing an empty
complete receipt; provider/capability watermarks now reject that ordering. Historical records remain for memory after retirement; private
messages require consent regardless of visibility; future observations are suppressed;
cache status is validated before use. See VALIDATION.md for the final checks.

## Subsequent integration consolidation

The completed pack and optional provider setup were retained. The orchestration
extension consolidates routing under li-research rather than duplicating provider
instructions in writing skills. New local evidence/router scripts connect the
existing optional runtimes through tools/web/research.py; focused skills ask for
information by purpose and preserve source IDs. Daily intelligence reads relevant
normalized research signals alongside the separate LinkedIn reader and local memory.
No provider configuration, installation, credential or account capability was replaced.
See docs/ORCHESTRATION.md for the working gap analysis, actual routing/health matrix
and limitations, and VALIDATION.md for safe live and offline scenario results.

## Project name

The adapted project is named **LinkedIn Intelligence Agent**, distributed with the
`linkedin-intelligence-agent` identity. The user's GitHub fork was renamed from
`RiyDomingo/linkedin-agent-skill` to `RiyDomingo/linkedin-intelligence-agent` on
2026-10-02. The upstream repository and attribution retain their original name.
The local checkout folder and `.linkedin-agent/` data paths are retained for
compatibility with existing context and generated absolute MCP paths. The installer
retains its established attribution filenames for compatibility. Renaming the
GitHub repository does not commit or push the local migration.

## Optional account-connected milestone (2 October 2026)

The former import-first default now has an explicitly enabled account path through
[the restricted gateway](docs/ACCOUNT_CONNECTOR.md). The pinned third-party backend
is isolated under tools/linkedin; generic research/discovery LinkedIn blocks remain.
Only five project read/lifecycle tools are registered, with no inbox or account writes.
Manual dedicated-browser authentication replaces neither the Skills installation nor
the existing research router. Normalized observations and labelled dated summaries
enrich preserved curated context. Imports remain available as fallback.

The live acceptance and exact test results are recorded in
[ACCOUNT_CONNECTOR_REVIEW.md](docs/ACCOUNT_CONNECTOR_REVIEW.md). Existing MIT LICENSE,
Jake Schincariol attribution and all 20 Skills are preserved; this addition does not
imply LinkedIn, OpenAI or upstream endorsement.

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
