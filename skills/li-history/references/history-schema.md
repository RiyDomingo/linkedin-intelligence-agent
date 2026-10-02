# Publication history schema

Each nonblank JSONL line is an object. Required string fields: id, date (ISO
YYYY-MM-DD, actual publication date), topic, angle, hook, body, cta. Optional
string lists: tags, source_material, anecdotes, claims. Optional metrics object:
finite nonnegative numeric values only. IDs must be unique per history file.
Do not store secrets or full private third-party messages here. comments.jsonl
uses the same fields, with the public comment as body and post topic as topic.

```json
{"id":"p-001","date":"2026-10-02","topic":"proposal review","angle":"what the review missed","hook":"The checklist missed a dependency.","body":"The published text.","cta":"","tags":[],"source_material":[],"anecdotes":[],"claims":[],"metrics":{}}
```

Missing metadata is not inferred evidence. Store full text for semantic comparison;
explicit anecdotes/claims improve local matching. `check` accepts a partial object
with topic, angle, hook, body and optional anecdotes/claims. It reports Unicode token
Jaccard overlap: .75 for topic/angle/hook/labels, .60 for body. These thresholds
produce review candidates, never publication vetoes. Semantic review is Codex's job.

`history/topics.json`: {"themes":["proposal review","hiring"]}. Summary compares
these desired themes to past topics. It returns all ranked measured examples;
small sample sizes do not establish a successful strategy. Performance CSV headers:
`id,impressions,reactions,comments,reposts`. Join on publication id. Blank means
unavailable. CSV observations override same-key history metrics when present.
Duplicate ids, malformed lines, nonfinite/negative numbers and invalid dates fail
with an error. Fix the reported input explicitly; do not skip corrupt lines.

`append --published` requires human confirmation outside the script. The flag is
an explicit operator attestation, not verification of LinkedIn state. It generates
an id when absent, requires the real date, refuses duplicate ids and malformed
existing history. Unix writers lock the file; other platforms require one writer.

Optional project/company/author_id/parent_post strings may be null. Optional lists
people_mentioned, evidence_used and related_research retain public source links/IDs.
Summary counts projects, companies and people; lookup matches terms in full text
and metadata. Imported snapshots do not automatically populate this confirmed log.
