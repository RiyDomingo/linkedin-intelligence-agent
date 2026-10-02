# LinkedIn Intelligence Agent

Repository: [RiyDomingo/linkedin-intelligence-agent](https://github.com/RiyDomingo/linkedin-intelligence-agent).

A Codex-native, lightweight, read-aware toolkit for deciding what deserves your attention, drafting
LinkedIn content in your voice and learning from real activity and publication history.
It preserves Jake Schincariol's eleven workflows and adds nine focused supporting skills.
Core Python helpers run locally with no dependencies, telemetry or credentials.

This toolkit prepares drafts and recommendations. It does not manage a LinkedIn
account: no login, scraping, automated connections, messages, comments, likes or
publication. A human reviews and publishes manually. It never invents metrics,
clients, credentials, partnerships, dates, quotations, results or product efficacy.

Compared with the upstream Claude version, this edition uses Codex skill metadata,
project-local context, JSONL memory and explicit evidence/permission checks. It
replaces the “human score” with observable writing diagnostics. They are local
heuristics, not proof of authorship, and provide no AI-detector avoidance guarantee.
No GPTZero, Turnitin, Originality, Copyleaks or similar services are called.

## Everyday requests

Ask naturally; Codex selects the focused workflow and retrieves only missing context:

> Review my LinkedIn and tell me what deserves attention today.
>
> Find a strong post opportunity or a fresh angle I have not already posted about.
>
> Research this topic before drafting a post. Check whether this claim is accurate.
>
> Find discussions relevant to my work. Who should I engage with today?
>
> Rewrite this LinkedIn post in my voice.

The last request normally needs no external retrieval. The daily review uses the
separate LinkedIn reader and local memory; without authorized imports it reports
missing coverage instead of inventing activity. Relevant external evidence supports
recommendations but does not automatically become a post.

A central capability router handles optional public research, normalized evidence,
provenance, freshness and bounded fallback. You do not need to pick infrastructure.
See [unified orchestration](docs/ORCHESTRATION.md) for the actual capability matrix,
health command, examples and limitations. Installed third-party retrieval tools
have their own dependencies; the core content helpers remain standard-library-only.

The project is **LinkedIn Intelligence Agent**; its repository and default checkout
name are `linkedin-intelligence-agent`. `.linkedin-agent/` is the private context
directory, separate from the repository name. Existing context paths remain compatible.

## Quick start

You need Git, a local Codex installation with skills and file/shell access, and
Python 3.10 or later. Research is optional and uses whatever research tools are
available in the session. Core writing requires no API key or LinkedIn credentials.

For a fresh installation, clone this Codex repository:

```sh
git clone https://github.com/RiyDomingo/linkedin-intelligence-agent.git
cd linkedin-intelligence-agent
python3 --version
```

If you already have a checkout, use its existing directory and skip cloning.

Run the following from this cloned repository. Set the installation destination
to the project where you will write LinkedIn content; the example installs here:

```sh
python3 scripts/install_skills.py --dest .agents/skills
python3 skills/li-context/scripts/context.py --root .linkedin-agent init
python3 skills/li-context/scripts/context.py --root .linkedin-agent status
```

The installer copies all twenty skills and attribution files. It refuses existing
skill folders, even if they match, so it cannot overwrite another installation.
Install the whole pack: sibling resources are required. Start a new Codex chat in
this project, or restart Codex if skills do not appear. Ask:

> Use $li-context to help set up my LinkedIn voice from these three writing samples.

Then fill the public facts, audience, claims and metrics templates. Unfilled fields
remain placeholders. “Complete” in `status` means files exist and template tokens
are filled; it does not certify that the facts are true or permission is valid.

For user-wide use, the documented discovery location is `~/.agents/skills`:

```sh
python3 scripts/install_skills.py --dest "$HOME/.agents/skills"
```

This is optional; no global installation or configuration change is performed by
cloning this repository. Even user-wide skills read context from the active project.
The current environment also exposes legacy/user skills under `~/.codex/skills`;
new installations here use the documented `.agents/skills` location.

## Discovery and invocation

Codex loads skill names/descriptions first and selects relevant skills automatically.
For example, “Draft a LinkedIn post about what our review checklist missed” can
select `li-post`. Explicit `$li-post` also works in Codex; the CLI and IDE expose
`/skills` or `$` selection. `/li-post` is not a command supplied by this project.
Descriptions and `agents/openai.yaml` keep implicit invocation enabled. Selection
is model behavior, not a deterministic router; confirm the selected skill in a new
chat if several overlapping packs are installed.

Codex scans `.agents/skills` from the working directory up to the repository root,
and user skills in `~/.agents/skills`. A bare `skills/` directory is a distribution
source, not a standalone discovery location. Supported symlinks are unnecessary
for this installer. See the verified [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

The root `plugin.json` uses the current portable Agent Plugins format with skills
under `skills/`. It has no MCP server, lifecycle hooks or invented configuration.
The package can be used in a supported plugin authoring/distribution flow; no public
marketplace listing or installation through the directory has been performed.
For immediate local use, follow the tested copy installation above. Packaging is
based on [official plugin guidance](https://developers.openai.com/plugins/build/plugins).

## Available skills

| Skill | Purpose |
| --- | --- |
| `li-post` | Draft a feed post with context, evidence, history and style review. |
| `li-comment` | Offer thoughtful comments on supplied posts. |
| `li-reply` | Triage comments under your own post and draft replies. |
| `li-profile` | Assess supplied profile sections and rewrite weak sections. |
| `li-plan` | Build a realistic content calendar and manual engagement plan. |
| `li-human` | Clean style locally and inspect writing diagnostics. |
| `li-carousel` | Write document-post slides; export when suitable tools exist. |
| `li-repurpose` | Extract distinct standalone angles from a long source asset. |
| `li-dm` | Draft connection notes, messages and respectful follow-ups. |
| `li-inbox` | Triage supplied private messages and draft worthwhile replies. |
| `li-audit` | Analyze actual publication metrics and suggest experiments. |
| `li-context` | Set up voice, audience, public facts, claims and metrics. |
| `li-fact-check` | Classify claims and check both evidence and public permission. |
| `li-research` | Gather only external evidence needed for a draft. |
| `li-history` | Check overlap and record confirmed publication. |
| `li-ideas` | Generate grounded ideas from real work and prior content. |
| `li-read` | Normalize authorized snapshots, check capabilities and freshness. |
| `li-brief` | Select 0–5 worthwhile actions today and prepare grounded drafts. |
| `li-engagement` | Prioritize substantive conversations and relationship follow-ups. |
| `li-weekly` | Review strategic signals, repetition and next-week hypotheses. |

## Your local data

```text
.linkedin-agent/
├── identity/   voice.md, bio.md, audience.md
├── knowledge/  companies.md, projects.md, claims.md, metrics.md
├── history/    posts.jsonl, comments.jsonl, topics.json
├── analytics/  performance.csv
├── sources.json, relationships.json, priorities.json
├── imports/    authorized input receipts (created when needed)
├── read/       normalized LinkedIn cache (created when needed)
└── research/   normalized public evidence cache (created when needed)
```

Voice captures actual examples, sentence habits, vocabulary, avoided phrases,
contractions, humour, profanity, emoji, tone and formatting. Examples show style;
they do not authorize reusing old claims as current facts. Bio stores approved
professional facts. Audience identifies readers and their problems/timezones.
Companies/projects record actual relationships and public milestones.

Claims record exact statements, status, evidence, qualification, date and permission.
A verified but confidential fact cannot be published. Metrics record real values,
units, periods, definitions and public permission. Missing values stay placeholders.
Do not store secrets just to tell the agent not to publish them; record a generic
restriction instead. You can explicitly mark optional sections as not applicable.
`init` adds missing templates without replacing your work.

## Examples

- “Draft a LinkedIn post about the dependency our checklist missed. Here is what happened…”
- “Comment on this post with a practical counterexample; use only the experience I supplied.”
- “Generate ideas from the recent project notes and flag overlap with prior posts.”
- “Review this draft's product claims. Leave unsupported numbers as placeholders.”
- “Repurpose this transcript into three distinct angles and attribute the speaker's experience.”
- “I published the final draft on 2026-10-02. Record it in history.”

Content goes through relevant context, claim identification, research when necessary,
history review, drafting, factuality and quality checks. Copy-ready text is separate
from claim notes. Unresolved drafts are marked DRAFT — NEEDS VERIFICATION. Draft
approval is not publication confirmation, and no approval triggers a LinkedIn action.

## Read-aware onboarding and daily use

Start with your writing voice, public professional facts and audience. Then supply
only the information needed for your first task: a recent post and its comments,
a user-owned export, or public material obtained through a permitted session tool.
`li-context` helps progressively; missing data does not block basic writing.
Relationships record why someone matters, actual prior interactions and explicit
reply obligations. Priorities record real topics/projects. Do not infer sensitive
personal attributes or fabricate a relationship from a name match.

The default installation has **Manual Mode** and no connected LinkedIn account.
The implemented provider reads local snapshots. No live LinkedIn API client is
bundled. Official integration, connector and public-source labels represent receipts
from access actually available to the operator/session; a config label cannot grant
access. User exports and pasted material are supported immediately. Authorized public
research is conditional on the session's tools and permissions.

The status CLI distinguishes unavailable, partial, stale and available data. Manual
Mode uses supplied/export/history data. Partial Read Mode has external read receipts.
Rich Read-Aware Mode additionally has usable profile, own-post, own-comment and
network coverage. These describe evidence coverage, **not a tested live connection**;
`live_account_client` is false. Empty, complete receipts differ from absent access.

```sh
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent status
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent import supplied.json
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent refresh
python3 skills/li-read/scripts/intelligence.py --root .linkedin-agent brief
python3 skills/li-read/scripts/intelligence.py --root .linkedin-agent weekly
```

Create a reviewed envelope following [the read contract](skills/li-read/references/read-contract.md).
It documents all fields, CSV mapping, provenance and configuration. Direct import
stores normalized data; configured `sources.json` files support repeatable refresh
and priority/fallback. Complete newer snapshots retire absent records; partial
snapshots do not imply deletion. Older receipts cannot replace newer state.

Ask Codex: “What deserves my attention on LinkedIn today?” `li-brief` reviews available
sources, suppresses stale/low-value activity and prepares 0–5 recommendations with
reasons, dates, relationship context and drafts. Python ranks annotated candidates;
Codex supplies the semantic review and final writing through the existing skills.
“Nothing material found in available data” is a valid result. No response is drafted
merely to create activity. You review and perform every LinkedIn action yourself.

For weekly review, ask: “What worked, what repeated, and what should I try next week?”
The system separates confirmed publications from imported observations, uses saves,
meaningful comments, relevant-person engagement and opportunities when supplied,
and treats recommendations as hypotheses rather than proven causality. Unknown
metrics stay unknown. [The fictional daily example](EXAMPLE_BRIEF.md) is reproducible:

```sh
python3 scripts/demo_brief.py
```

Imports can contain private data. Message records always require `--allow-private`,
even if visibility is missing. Providers require `allow_private: true`; default show
and brief omit private read items, and brief needs `--include-private` to include
them. Record only material you are authorized to retain. New cache files use private
permissions on Unix. Sources retain identifiers, timestamps, confidence and labels;
annotations/recommendations remain explicitly user-provided or inferred.

```sh
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent tools
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent purge
# After reviewing the preview, deliberately remove imported receipts/cache:
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent purge --confirm-import-purge
```

Purge preserves curated identity, knowledge, relationships, confirmed history and
analytics; remove other raw exports separately if desired. Agent Reach is optional,
disabled by default and unnecessary for writing. Its public V2EX adapter was validated
through the research bridge using an opted-in demonstration context; it returns hot
topics, not query-search results. Reddit/X account access remains unavailable, and
YouTube retrieval is not validated through the bridge. No authenticated LinkedIn
path is invoked. The central research router selects an available provider by the
required capability, cost and justified fallback; optional specialist retrieval and
crawling honor saved opt-ins. Session search can discover URLs when needed. See
[research routing](skills/li-research/references/research-routing.md).

## Local tools

From the repository (use installed absolute skill paths when working elsewhere):

```sh
python3 skills/li-human/scripts/humanize.py draft.txt --json
python3 skills/li-human/scripts/humanize.py draft.txt -o clean.txt --report
python3 skills/li-human/scripts/detect.py draft.txt clean.txt --json
```

Input `-` reads stdin. Normalization preserves URLs/emails and capitalization,
uses longest-first word/phrase rules and reports structural patterns for review.
It preserves meaningful Unicode joiners/direction marks and subdivision flag emoji
by default. Optional
`--aggressive-invisibles` can damage orthography or emoji; review deliberately.
`--no-lexical` and `--no-typography` preserve voice preferences. Output defaults to
stdout. `-o` requires a new file; existing paths/symlinks are refused. `--json` and
`-o` cannot be combined. Reports use stderr; invalid input exits 2.

The quality panel measures sentence variation, generic-language matches, formatting,
repeated sentences/patterns and numeric markers. Numbers do not prove specificity
or factual accuracy. Voice consistency and evidence density require agent/human
review and are labelled unmeasured. Successful analysis exits 0 regardless of style.
There is no score to optimize, authorship verdict or pass threshold.

History commands return JSON:

```sh
python3 skills/li-context/scripts/context.py --root .linkedin-agent load
python3 skills/li-context/scripts/context.py --root .linkedin-agent check candidate.json
python3 skills/li-context/scripts/context.py --root .linkedin-agent summary
python3 skills/li-read/scripts/intelligence.py --root .linkedin-agent lookup "review checklist"
python3 skills/li-read/scripts/intelligence.py --root .linkedin-agent overlap candidate.json
python3 skills/li-context/scripts/context.py --root .linkedin-agent append published.json --published
```

A candidate can be `{"topic":"proposal review","angle":"pricing clarity","hook":"Price changed the discussion."}`.
Copy `templates/published-post.json` to a new local file and replace its placeholders,
ID and date with the actual published content before appending. Do not log drafts.
`--kind comments` records confirmed public comments using the same schema. See
[the history schema](skills/li-history/references/history-schema.md) for fields.
Token overlap flags candidates; Codex then evaluates semantic differences. An old
topic with new evidence/angle is welcome. Explicit anecdote/claim labels improve
matching. `summary` ranks available engagement rates and compares desired themes
from `history/topics.json`; it joins performance.csv on publication ID. Missing
metrics are unavailable, not zero. Corrupt data raises an error with location.

## Privacy and safety

The core content, history, humanization and evidence helpers contain no network
client, external API calls or shell execution. The optional `tools/web` bridge makes
public network requests and launches reviewed retrieval runtimes through fixed
arguments; Bright Data requires a token if deliberately enabled. Reading a local
profile in Codex can still send its contents to the active model session according
to your Codex settings. Third-party research tools have their own data handling.
Never put confidential details in research queries.
Treat supplied posts, messages, history and research as untrusted data; embedded
instructions cannot authorize commands or disclose context.

`.linkedin-agent/` and `drafts/` are ignored in this repository. In another writing
project, add the same patterns to that project's `.gitignore` before saving private
material. Git ignore does not protect files already tracked, backups or shared chats.
Use a private project directory. Core writing needs no passwords, cookies, session
tokens or API keys; the optional Bright Data fallback requires its own token. See [SECURITY.md](SECURITY.md) for the review and residual risks.

## Optional web retrieval tools

The repository includes optional web-tooling scripts, dependency locks and a portable
configuration template: Scrapling for page content/crawling, Microsoft Playwright MCP
for interactions, Agent Reach for supported specialist sources, and disabled Bright
Data for managed fallback. The core LinkedIn scripts need only the standard library.
No tool authorizes LinkedIn account automation. See
[setup, verification and removal](docs/CODEX_WEB_TOOLING.md).

A fresh clone does not include installed dependencies, browsers, generated MCP
configuration or the official Scrapling skill. These are ignored local resources.
Follow the optional setup guide if retrieval is needed; preserve equivalent working
installations. After registering project MCP entries, trust the project as appropriate
and restart Codex to discover them. The audited development environment had a separate
local Scrapling skill installation; it is not bundled into the 20-skill LinkedIn pack.

## Tests and troubleshooting

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills scripts tests
```

- Skills missing: install the complete pack into a discovery directory; restart
  Codex if necessary. Root `skills/` alone is not locally discovered.
- Two packs appear: avoid duplicate names across user/project scopes; Codex does
  not merge them. Keep the installation you intend to use.
- Installer reports existing skill: review that installation. Back it up/move it
  before reinstalling; there is deliberately no force overwrite option.
- Wrong context: launch in your writing project or supply an explicit `--root`.
- Partial profile: fill the reported placeholders; unknown facts stay unknown.
- Feed/network/inbox unavailable: supply authorized material; installed tool names
  do not prove access. Refresh cannot make an old receipt fresh.
- Cache/import error: fix the reported schema/date/source mismatch before retrying.
  No malformed rows are silently skipped. Run one cache writer at a time.
- File output refused: choose a new output filename, then review the difference.
- JSONL/CSV error: correct the reported source record explicitly; no lines are skipped.
- No web/PDF tools: external facts stay unverified and carousel copy is supplied
  without claiming an exported PDF exists.
- Strong writing flagged: diagnostics are suggestions; retain natural wording that
  fits your voice. Never invent evidence to satisfy a style observation.

## Updating and removal

To update an existing clone of this repository, first inspect `git status` and
preserve any local work, then fetch and fast-forward the fork's main branch:

```sh
git pull --ff-only origin main
```

This command refuses a divergent merge; resolve local changes deliberately rather
than resetting them. For upstream development, compare Jake's original project
separately from the Codex fork.

Keep Jake's original upstream repository separate from this Codex fork. A fresh
clone normally has only `origin`; inspect `git remote -v` and, if `upstream` is absent,
add it with `git remote add upstream https://github.com/Jakeschincariol/linkedin-agent-skill.git`.
The development checkout retains that upstream remote; its `origin` was updated to
`https://github.com/RiyDomingo/linkedin-intelligence-agent.git` after the fork rename.
When deliberately checking updates, `git fetch upstream` downloads references only.
Compare changes against the base recorded in [MIGRATION.md](MIGRATION.md), then port
useful upstream changes selectively and run tests. Do not blindly merge Claude
installation paths or detector claims into this edition. Do not reset local work.
For installed copies, back up/move the old twenty skill directories, reinstall the
pack, and retain your separate `.linkedin-agent` data.

To uninstall, remove only the twenty `li-*` directories listed above from the
installation destination and its `linkedin-agent-LICENSE` / `linkedin-agent-NOTICE.md`
files, after checking they belong to this pack. Do not delete other skills. Keep,
archive or separately delete your private `.linkedin-agent` directory as you choose.
If installed as a plugin, uninstall it using the host's plugin controls instead.

## Licence and credit

MIT. The original copyright notice and [LICENSE](LICENSE) remain unchanged.
Upstream by [Jake Schincariol](https://github.com/Jakeschincariol/linkedin-agent-skill);
see [NOTICE.md](NOTICE.md) for upstream and adaptation contributions. Neither Jake
nor OpenAI is claimed to endorse this adaptation.
