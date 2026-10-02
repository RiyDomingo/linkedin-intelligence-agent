# Professional memory implementation review

**Memory: IMPLEMENTED. Overall account experience: PASS WITH LIMITATIONS.**

The supplement was implemented and validated on 2 October 2026. It preserves the
restricted gateway, manual authentication, existing public research routing, all
20 Skills and MIT attribution. No new account or public network acquisition was
needed for the actual existing-context reuse test. The previous fresh-login/MFA
and real auth-expiry acceptance gap remains; see the account review.

## Gap analysis and final architecture

Before this supplement, account observations and voice summaries were reusable,
but there was no generic source-version registry, durable correction mechanism or
shared precedence/conflict API. New li-context professional_memory.py centralizes
those operations with standard-library local code.

```text
LinkedIn normalized observations / receipts
User-selected resume or bio → local extraction → semantic normalization
User-linked website / other link → existing research router → normalization
Permitted user import / confirmed local history
Explicit corrections
    ↓
User-scoped evidence, sources/versions, conflicts and preferred values
    ↓
Compact derived summary + progressive shared getters
    ↓
Existing Skills, factuality review and human-executed actions
```

Current UX remains one user per project. A stable opaque usr_<UUID> and user IDs on
sources/evidence provide generic scoping; IDs do not encode names/emails. Separate
roots have separate IDs and context; cross-user records are rejected. Multiple
selectable users/browser profiles are not implemented. The existing upstream single
auth profile must not be shared among different people; such deployments need
separate OS/browser authentication environments. Memory and authentication remain
separate. No global environment or upstream authentication settings were altered.

## Supported sources and controls

| Source | Implemented support |
| --- | --- |
| LinkedIn | Bridge from validated normalized account observations, no browser call |
| Resume/CV | PDF/DOCX through installed MarkItDown, TXT/Markdown locally; source reference/hash, no copy |
| Professional bio | File or inline text; FACT versus POSITIONING normalization |
| Personal website | Actual public-router evidence adapter, selective relevant pages, 30-day TTL |
| Other links | Labeled association and PUBLIC_WEB provenance; ownership not assumed |
| Imports | Existing normalized manual/user-export read envelope; primary profile fields bridged, inbox refused |
| Confirmed history | Existing publication records can supply derived topics; account observations do not confirm publication |
| User correction | Explicit USER_CONFIRMED item with durable version/correction history |

Natural-language li-context instructions compose these controls, so users do not edit
internal JSON. Python validates structure and resolves provenance/freshness/precedence;
Codex performs semantic extraction. Arbitrary prose extraction and scientific truth
are not falsely presented as deterministic Python capabilities.

## Precedence, temporal evidence and removal

Current prompt decisions and curated context remain authoritative. The memory API
ranks USER_CONFIRMED → USER_DOCUMENT → LINKEDIN_OBSERVED → USER_LINKED_WEBSITE →
PUBLIC_WEB → LOCAL_HISTORY → INFERRED. Contradictions remain stored. The working value
uses precedence, temporal validity and recency; whitespace/case/trailing-period-only
changes do not create conflicts. Semantic entity/key alignment remains an agent
review responsibility. Confirmation is not independent verification/public permission.

Explicit audience corrections persist and prevent a rejected inference becoming the
preferred answer again. New account evidence never silently rewrites curated files.
Expertise strength is explicit; inference cannot establish experienced_in/expert_in.
Voice/theme assessments remain inferred unless the user explicitly confirms them.

Source versions retain references, hashes and actual ingestion/retrieval timestamps.
Pending replacements do not erase the working version; failed/empty extraction leaves
it usable. Historical source versions remain available explicitly. Partial account
refreshes retain missing prior fields with their original age. Website changes produce
versions; removed sources stop contributing and cannot silently reactivate during sync.
Removal retains private historical audit, while unrelated confirmations survive.

Freshness is non-destructive: documents until replaced, confirmations no automatic
expiry, website/link 30 days, LinkedIn profile 30 days/posts 3 days/feed 1 hour.
Refresh-plan reports selected needs; it never accesses the network. Offline context
queries load only relevant categories and do not reread original source documents.

## Validation: synthetic versus actual

Starting combined baseline: **372 core tests passed** and **9 optional MCP tests passed**.

Final core suite: **453 discovered, 453 passed, 0 failed, 0 skipped**. This adds
**81 memory/onboarding tests**, covering persistence, precedence/conflicts, corrections,
replacement/pending failure, removal, temporal validity, freshness, offline context,
user-scoped roots, credentials, permissions, URL boundaries, export/reset, document
conversion failure, and progressive loading. Optional MCP suite: **9 discovered,
9 passed, 0 failed, 0 skipped**. All 20 Skills validate; installed resources match.

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-memory-pycache python3 -m unittest discover -s tests -q
tools/linkedin/.venv/bin/python -m unittest discover -s tools/linkedin -p 'test_mcp.py' -q
```

Synthetic onboarding starts with no memory; uses the actual gateway policy with a
fake upstream, retains profile/posts, adds a resume, bio and synthetic website receipt,
preserves three conflicting role values, and records an audience correction. New
subprocesses load content/profile/daily context with account access disabled. Store
bytes remain unchanged by those reads and acquisition count does not increase.
Website retrieval in this synthetic test is a receipt fixture, not a live personal-site
crawl. The existing research router and its actual prior public-source validation remain
unchanged; no personal website/resume/bio was supplied for live enrichment.

Real installed MarkItDown converted generated synthetic DOCX and PDF resumes. Both
contained generic Alex Example/Example University data. Extracted text was successfully
normalized; no source document was copied, and temporary fixtures were removed.

Actual existing account observations were bridged locally, then loaded in a separate
process with the account connector disabled by process environment. Eleven selected
identity/career/education/voice/theme context groups survived. Same opaque identity,
zero new LinkedIn reads, zero source-document rereads. Audience remained unknown;
it was not invented. Live account reads are the previous milestone's acceptance,
not simulated reads renamed as live memory acquisition.

## Second engineering review and repairs

This was a same-agent second engineering review, not independent certification.

- Resolved /in/<slug>/ URLs and recent-activity variants normalize to one identity;
  /in/me/ is an unresolved placeholder and skipped. Different resolved accounts fail.
- New roots were initially inheriting permissive parent creation: fixed to 0700.
- Empty parser output could stage an empty replacement: now refused before registration.
- Replacement was activated before semantic normalization: now pending until validation;
  old context survives failed normalization.
- Version references initially followed the newest file: now retained per version,
  with private document paths scrubbed from exports, including version metadata.
- Identical reconfirmation retained an old confirmation date: timestamp now updates.
- Derived snapshots duplicated full evidence: now compact, with evidence IDs and bounded
  groups; API recalculates freshness instead of trusting a stale snapshot.
- A source example link resolved only in the repository: moved into bundled skill
  resources and validated after copy installation.
- Credential-like strings/API keys and unignored Git-project documents are refused.
  Public-web ingestion rejects LinkedIn URLs, preserving the separate account boundary.

## Privacy and residual limits

Memory is under ignored .linkedin-agent/memory. New directories/root are 0700; files
0600; existing permissions are not globally rewritten. Original documents are referenced
and hashed, not copied. Public retrieval never receives complete private memory.
Exports contain normalized private professional context, active source/version metadata,
provenance and explicit confirmations; history is opt-in, local document paths redacted,
authentication/configuration excluded. No export restore/import feature is claimed.

Reset controls distinguish derived inference, supplied sources, all memory and all user
data. All-memory retains opaque identity/account binding; all-data removes the selected
.linkedin-agent including anything deliberately placed inside it. External source files
and browser auth are untouched. Historical audit after source removal remains private;
users requiring removal of that audit can deliberately clear all memory/data.

Remaining limits: trusted local workspace/Unix locking, optional third-party parser
trust and OCR quality, bounded evidence/output sizes, agent semantic normalization/key
alignment, first-party ownership association not verified automatically, and lack of
multi-user/browser switching. Source labels are attestations, not cryptographic proof.
Private context entering Codex may reach its configured model service. No provider-wide
DLP interception is claimed. No account credentials enter memory. No commit or push.
