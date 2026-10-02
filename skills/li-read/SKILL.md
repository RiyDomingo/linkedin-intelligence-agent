---
name: li-read
description: "Inspect LinkedIn read-source status, import exports or normalize legitimate retrieved snapshots. Use for source setup, refresh and capability troubleshooting; this skill has no account controls."
---

# li-read

Read [the shared contract](../li-context/references/context-contract.md) first.

Read [the source contract](references/read-contract.md). Inspect available session
tools and run `scripts/read_layer.py --root <project>/.linkedin-agent status`.
`tools` detects command presence only; pass actually exposed session tool names with
`--available-tool` when useful. Never equate installed tools with LinkedIn access.

Prefer a supported integration actually present, then user exports, ordinary permitted
public retrieval, supplied material and an explicitly enabled read connector. This
package implements local import/snapshot adapters, not a remote account client. If
legitimate session read tools expose requested data, use only their read operations,
normalize the actual result to the envelope and import it. Otherwise use imports or
state that the capability is unavailable. Do not activate authenticated browser
sessions, scrape a feed or install providers merely to fill a gap.

Run `refresh` for enabled local snapshot providers. If data is stale, refresh through
an available legitimate session tool where authorized, or ask for a newer export;
rereading an old file is not refreshing LinkedIn. Inspect selected items with `show`;
private records are excluded unless `--include-private` is deliberately supplied.
Preserve nulls, source, dates, visibility and qualifications. Do not infer current
facts from missing fields. The schema and CSV mapping live in the source contract.

Use `import` for normalized JSON envelopes or `import-csv` with explicit source and
column mapping. Core imports require no credentials. Private material requires
explicit retention opt-in; never import full inbox/network data without purpose.
`purge` previews only imported receipts/cache; `--confirm-import-purge` executes the
reviewed local removal, preserving curated context/history and code.
