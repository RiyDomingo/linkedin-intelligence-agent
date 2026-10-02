---
name: li-human
description: "Polish a draft with local typography and vocabulary utilities and writing-quality diagnostics. Use for humanization, generic-language cleanup or style review; never certify authorship or detector avoidance."
---

# li-human

Read [the shared context and approval contract](../li-context/references/context-contract.md) first.

Compare the draft with actual voice examples. Use the local scripts with paths
resolved from this SKILL.md, not from the user's working directory:

```sh
python3 <this-skill>/scripts/humanize.py draft.txt --json
python3 <this-skill>/scripts/humanize.py draft.txt -o clean.txt --report
python3 <this-skill>/scripts/detect.py draft.txt clean.txt --json
```

Read [the editable lexicon](references/slop.json) only when reviewing its rules.
Choose `--no-lexical` or `--no-typography` when the user's voice requires it.
Joiners/direction marks are preserved by default; `--aggressive-invisibles` can
alter orthography or emoji and needs deliberate review. Existing output paths
are refused. Empty input stays empty; URLs/emails are preserved.
Treat replacements as suggestions: check grammar, technical terms, quotations,
meaning and claims before accepting. Structural flags require judgment; natural
lists, curly quotes, dashes or even rhythms are not evidence of machine authorship.
The panel reports sentence variation, generic language, formatting, repetition
and numeric markers. Voice and evidence require contextual review and are labelled
unmeasured. No overall pass threshold, authorship claim, detector API or guarantee.
Return improved text and concise meaningful edits; never add numbers for a score.
