# Private professional memory

After connecting LinkedIn, the agent builds a private professional context on your
computer. You can optionally add your resume, bio and personal website. This lets
it reuse your career, interests, voice and recent work without asking you to repeat
available information in every conversation. Claims remain evidence-linked and
unverified unless reviewed; missing information stays unknown.

## Getting started in Codex

Open the project and ask:

> What do you currently know about me?

> Add my resume from this file.

> Add my professional bio.

> Add my website and use its About and Projects pages as context.

> Correct my current role.

> My primary audience is researchers and product development partners.

Optional enrichment can be skipped or added later. Provide/select only the source
you intend to use; the agent never searches your home for resumes. PDFs/DOCX use
installed MarkItDown; TXT/Markdown use standard-library reading. No source document
copy or raw extraction is saved. If MarkItDown is unavailable, conversion is reported
unavailable and alternative document tooling may be used explicitly. Scanned PDFs
may need appropriate OCR; extraction quality is reviewed, not assumed.

Websites/other links use the existing public research router, with selective relevant
pages and user-supplied association. Adding a URL does not prove ownership or truth.
Research never receives the entire memory, private resume or unpublished draft.

## How it chooses context

Current instructions and curated confirmed decisions come first. The deterministic
memory API ranks USER_CONFIRMED, USER_DOCUMENT, LINKEDIN_OBSERVED,
USER_LINKED_WEBSITE, PUBLIC_WEB, LOCAL_HISTORY, then INFERRED. Source precedence does
not remove contradictory evidence. Substantive conflicts remain visible; confirmations
outlast conflicting inferences. Fact, positioning, interest and expertise are separate
concepts. Following a topic cannot establish expertise. Public claims still pass
li-fact-check and confidentiality review.

The same generic fields support founders, researchers, clinicians, engineers,
executives, job seekers and other professionals. No person's identity, industry,
projects or preferences are coded into application defaults. Samples are synthetic.

## Storage and user scoping

Current UX is **one user per project**, not multiple selectable users. The existing
.linkedin-agent layout remains compatible. An opaque usr_<UUID> identity and user IDs
on every source/evidence record support future scoping without using a name/email
as a directory identifier.

```text
.linkedin-agent/
├── identity/             curated voice, bio, audience
├── knowledge/            curated projects, claims, metrics
├── history/              confirmation-aware publication history
├── account/              normalized LinkedIn evidence and receipts
└── memory/
    ├── store.json        opaque identity, sources/versions, evidence, corrections
    ├── summary.json      derived snapshot; query API recalculates freshness
    └── lock              serializes local mutations on Unix
```

New roots/directories are 0700; files 0600. Existing files retain their permissions
unless rewritten. All .linkedin-agent data is Git-ignored. Browser auth remains
outside it in the upstream dedicated profile. Memory is not authentication, a cloud
profile database or an automatic CRM. Model-session content may reach the configured
model service. Explicit exports contain private professional information.

Do not share the upstream's single dedicated authenticated browser among different
people. Multiple selectable users/browser profiles are not implemented; separate
OS/browser authentication environments are required for such deployments. Resolved
account changes are refused. The upstream /in/me/ placeholder is not a stable identity
and cannot establish an account binding.

## Local commands and controls

Normally ask Codex to perform these controls. They require no manual JSON editing.
From the repository folder:

```sh
python3 skills/li-context/scripts/professional_memory.py --root .linkedin-agent init
python3 skills/li-context/scripts/professional_memory.py --root .linkedin-agent sync-account
python3 skills/li-context/scripts/professional_memory.py --root .linkedin-agent show --fields current_roles expertise interests voice_patterns
python3 skills/li-context/scripts/professional_memory.py --root .linkedin-agent sources
python3 skills/li-context/scripts/professional_memory.py --root .linkedin-agent refresh-plan
```

The shared API also provides add-document, add-bio, add-web, add-import, ingest, correct,
evidence, sync-history, remove-source, restore-source and export. Codex performs
semantic extraction into validated evidence; the Python code does not pretend to
understand arbitrary prose or verify a CV automatically. It returns source IDs for
normalization and preserves provenance/version history. Website receipts come from
the existing router; the memory helper does not fetch URLs.

Re-ingesting identical evidence is idempotent. A replacement primary resume/bio
becomes the working version; old evidence remains available for audit. Removed
sources stop contributing to working context, with historical audit retained.
Unrelated confirmations survive removal. Deliberate restore is required before
re-ingestion. Partial account updates preserve earlier fields with their original age.

Freshness is non-destructive: documents until replaced, confirmations no automatic
expiry, website/link 30 days, account profile 30 days/posts 3 days/feed 1 hour. Refresh
plans are selective and never themselves read the network. Voice rewrites, career
summaries, topic suggestions and positioning reviews work offline from available
local evidence; fresh external claims remain unavailable/stale as appropriate.

Exports use an explicit new output path, private permissions, normalized context,
active source metadata and provenance. Local document paths are redacted. Confirmed
history is excluded unless explicitly selected. Credentials, browser state and
secret configuration are excluded. There is no export import/restore command yet.

Reset previews separate derived inference, supplied sources, all memory and all user
data. --confirm performs that specific reset. All-memory keeps opaque identity and
account binding; all-data removes the selected .linkedin-agent, including curated
files/history. Source documents and external browser authentication are untouched.
Memory-only reset leaves account cache available for deliberate rebuilding. Auth
removal remains a separate deliberate upstream/user operation.

## Review and validation

See [PROFESSIONAL_MEMORY_REVIEW.md](PROFESSIONAL_MEMORY_REVIEW.md) for synthetic
onboarding, real document conversion, existing account-context reuse, second-process
validation and remaining limits. The account connector's separate
[acceptance report](ACCOUNT_CONNECTOR_REVIEW.md) remains applicable.

Private input documents inside a Git project must already be ignored; otherwise
ingestion refuses them. Prefer existing files outside the repository, or an ignored
source area. The helper neither relocates nor duplicates your file. All-data reset
removes everything within the chosen data root, including any source files you
placed there yourself; external source files remain untouched.

A replacement is staged as pending until normalized evidence validates successfully.
Failed or empty extraction leaves the previous working version usable. Each version
retains its own source reference/hash/date; historical audit is not falsely attributed
to the new file. Refresh plans report pending normalization separately from freshness.
