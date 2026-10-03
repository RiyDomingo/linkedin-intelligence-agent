# Onboarding implementation and failure review — 3 October 2026

## Verdict: PASS WITH LIMITATIONS

Implemented the first-class lifecycle within the existing architecture. The 20
Skills remain; onboarding is not a sixth operational workflow. Fresh-user detection,
resumption, no-account completion, evidence review/corrections, confirmed strategy,
first-brief delivery and five-workflow handoff were exercised in synthetic tests.
No new live login, authentication challenge or real-person first-brief run is claimed.
Earlier real account observations remain documented in ACCOUNT_CONNECTOR_REVIEW.md.

## Baseline recorded before edits

- Core: **453 discovered, 453 passed, 0 failed, 0 skipped**.
- Isolated connector MCP: **9 discovered, 9 passed, 0 failed, 0 skipped**.
- Initial worktree: only untracked `.agents/` attribution files. These were preserved.
- Existing implementation/account/memory architecture and Git remotes were retained.

## Behavior exercised

| Case | Observed result |
| --- | --- |
| Fresh project | Read-only status reports not_started/WELCOME; start creates private templates, opaque memory identity and lifecycle state |
| Account-first | Real gateway policy with fake upstream receipts, agent-normalized profile/own posts, memory synchronization; no manual profile paste |
| Partial account read | Profile persists after posts fail; independent profile/posts/feed statuses remain visible; enrichment/review continues |
| Account challenge | Current phase blocked; local resume performs no read, login, retry or budget reset |
| No account | Resume and website evidence build context, review/strategy/first brief complete; connector stays disconnected |
| Interrupted stages | New Python process resumes connection, acquisition, enrichment, review and first-value stages with stored evidence/strategy |
| Resume/bio/website/links | Existing ingestion/normalization layer reused; source versions, pending replacement, provenance and conflicts retained |
| Review | Meaningful Confirmed/Observed/Inferred sections; explicit token acceptance records review without bulk promotion of inferences |
| Corrections | USER_CONFIRMED preferred after another inferred source, including a new process; contradictory evidence retained |
| Strategy | Multiple explicit goals/audiences persist; inferred goals/audiences do not satisfy confirmed strategy; filled curated audience reused |
| No repeat questions | Known fresh fields and current strategic decisions exposed before questions; role/education/interests not requested again by default |
| First value | Existing brief selects a supplied fresh measurement discussion with evidence/strategy; empty fixture returns zero actions with coverage gaps |
| Generation vs delivery | Private brief receipt created; setup stays partial until displayed attestation; changed context/strategy or tampered receipt refused |
| Returning offline | Complete state and professional memory available in second process; disabled connector/network does not restart setup |
| Five workflows | Existing real Skill mappings, selective professional context and same confirmed strategy; no added Skill/workflow |
| Reset review | Memory, source registry, goals/audiences and connector control unchanged; only review/first-delivery checkpoints reopen |
| Privacy | Private state/receipt/lock permissions, Git-ignore, symlink refusal, bounded JSON, user isolation, sanitized CLI failures |

## Second review and repairs

A separate review pass by the implementing engineer examined return/resume, duplicate
sources, corrections, no-account and partial reads, failed replacement, goal/audience
persistence, delivery handoff, repeat questions, reset and privacy. No independent
human or separate-agent review is claimed.

Material issues found and fixed:

1. Completed state could have asserted a first brief without a matching saved receipt.
   Complete detection now verifies user identity, saved output and receipt hash.
2. Readiness/receipt inputs needed the same bounded object/secret checks as memory.
   Central local JSON loading now enforces them.
3. Existing curated audience decisions could cause a redundant audience question.
   Strategy reuses a filled authoritative audience file when no memory decision exists.
4. A strategy save could outlive a failed checkpoint save. Resume reconciles confirmed
   memory with lifecycle flags and advances without repeating strategic questions.
5. Initial workflow mapping names were checked against actual Skill folders and
   corrected to li-engagement/li-weekly before final validation.
6. Strategic-context retrieval now lives in the shared memory API, so the brief
   does not import the onboarding lifecycle and create a circular dependency.
7. Impossible REVIEW checkpoints and confirmation of a profile emptied by source
   removal are refused; review reset correctly returns to enrichment.

An initial test expected a completely empty history template; the actual template
contains a newline. The assertion was corrected to validate zero parsed publication
records, preserving the substantive no-fabricated-history requirement.

## Final automated validation

```sh
PYTHONPYCACHEPREFIX=/tmp/linkedin-onboarding-pycache python3 -m unittest discover -s tests -q
tools/linkedin/.venv/bin/python -m unittest discover -s tools/linkedin -p 'test_mcp.py' -q
PYTHONPYCACHEPREFIX=/tmp/linkedin-onboarding-pycache python3 -m unittest discover -s tests -p test_onboarding_lifecycle.py -q
```

- Core: **530 discovered, 530 passed, 0 failed, 0 skipped**.
- New lifecycle/handoff subset: **77 discovered, 77 passed, 0 failed, 0 skipped**
  (included in the core total).
- Optional connector MCP: **9 discovered, 9 passed, 0 failed, 0 skipped**.

Existing professional-memory/enrichment and connector integration tests remain in
those suites. Negative MCP tests deliberately log denied/invalid calls; the suite
passes. Skill metadata, linked resources, JSON parsing, Python compilation,
Markdown links, CLI examples and diff whitespace were checked separately.

## Boundaries and remaining limits

- This is Codex chat orchestration. The shared contract and project instructions
  require a local status check; no startup plugin event, GUI or daemon is implemented.
- The Python helper persists/validates state and performs the local handoff. Codex
  still does semantic extraction, source interpretation, audience suggestions and
  evidence-based brief presentation. Tests do not measure all model behavior.
- User acceptance/display flags are trusted operator attestations, not UI sensors
  or cryptographic proof. A hostile local operator can edit files or misuse flags.
- Acquisition remains third-party bounded browser reads, not an approved API.
  Existing login/MFA/access restrictions, upstream failure and partial-date coverage
  limitations remain. Onboarding does not provide new inbox/network/analytics access.
- One user per project; Unix locks/private modes tested on macOS. No multi-user
  switching or complete Windows validation is added.
- No-account completion needs meaningful professional evidence. A user who defers
  strategic decisions stays partial and can still use other authorized features.
- Optional parser/OCR quality and installed research capability still constrain
  enrichment. Failed or pending sources do not erase the prior working context.
- Local memory may enter the configured model service; local storage is not local
  inference. Authentication stays separate; no password/cookie import is added.
- Rerun review preserves memory/authentication. Deliberately clearing memory may
  require source rebuilding/review; clearing all data removes onboarding too.

No commit or push was performed for this milestone. MIT LICENSE remains unchanged;
unrelated attribution files and user-private context were preserved.
