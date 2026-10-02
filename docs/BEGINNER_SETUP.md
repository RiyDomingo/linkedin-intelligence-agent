# Beginner Setup Guide

## What you are installing

LinkedIn Intelligence Agent is a set of Codex Skills and local tools that help you review imported LinkedIn information, find ideas, plan content, draft posts and replies, and learn from your real publication history.

**The current toolkit is import-based.** It does not log into LinkedIn or read your live account. You supply authorized snapshots (saved copies at a particular time), exports or pasted content. Installing a research browser does not change this.

> **You control LinkedIn.** The agent drafts and recommends. It does not press LinkedIn's Post, Comment, Like, Connect or Send buttons, or edit your profile. Agent suggests → you review → you decide → you perform the LinkedIn action.

The commands below were checked on **macOS**, including a temporary project folder containing spaces. Linux and Windows have not been fully validated. Windows uses different virtual-environment paths; do not copy the optional macOS commands into PowerShell.

Jump to [Fastest Setup](#fastest-setup), [First Run](#first-run),
[imports](#give-the-agent-linkedin-information), [optional research](#optional-enable-web-research),
or [troubleshooting](#troubleshooting). You can stop before optional research.

## Fastest Setup

**Required:** a local Codex client, Git and Python 3.10 or later. You do **not** need Node, npm, a virtual environment, a research-provider account, an API key or LinkedIn credentials for this path.

Commands go in **Terminal**, not the Codex chat. Prompts beginning with “Ask Codex” go in the chat. Copy one command at a time, press Return, and wait for the next prompt before continuing. If you see an error, stop at that step and use [Troubleshooting](#troubleshooting).

### Step 1 — Check the basics

On macOS, open Spotlight with Command–Space, type **Terminal**, and open it. Terminal is an app where you type instructions for your computer.

| Requirement | What it does | How to get it if missing |
| --- | --- | --- |
| Local Codex | Reads this project's files and applies Skills to your requests | Follow the [official quickstart](https://learn.chatgpt.com/docs/quickstart), sign in, select Codex and open a local project. Product labels may change; use the current official instructions. A browser-only chat without local file access is insufficient. |
| Git | Downloads the project and later retrieves updates | Use the [official macOS Git instructions](https://git-scm.com/install/mac). macOS may offer Apple's developer-tool installer when you first check Git; complete it, then reopen Terminal. |
| Python 3.10+ | Runs the small local helpers | Use the [official macOS Python download](https://www.python.org/downloads/macos/). Open its installer and follow its instructions, then reopen Terminal. Choose Python 3.11+ if you also want optional research later. |

These checks work from any folder. Check Python:

```sh
python3 --version
```

**Expected:** `Python 3.10...` or newer, for example `Python 3.14.7`. If you see `command not found`, install Python first. Do not substitute the old `python` command.

Check Git:

```sh
git --version
```

**Expected:** a version beginning `git version`, rather than an installation error.

**Check Codex:** open your local app/client and confirm you can select a folder and start a Codex chat there. Account sign-in and desktop onboarding are manual steps; the command checks do not verify your account or plan.

### Step 2 — Download the project, or open the copy you already have

**Already have the folder?** Do not clone again. In Terminal, type `cd` followed by a space, drag the project folder from Finder into Terminal, then press Return. The drag inserts a correctly escaped path, including spaces. Continue with the folder checks below.

**Starting from scratch?** Create or choose a folder in Finder where you keep projects. In Terminal, type `cd` followed by a space, drag that parent folder into Terminal, and press Return. `cd` means “change directory”: subsequent commands run inside that folder.

From your chosen parent folder, download the project:

```sh
git clone https://github.com/RiyDomingo/linkedin-intelligence-agent.git
```

**Expected:** cloning progress and a new folder named `linkedin-intelligence-agent`. If that folder already exists, use it rather than cloning over it.

From the same parent folder, enter the downloaded project:

```sh
cd linkedin-intelligence-agent
```

**Expected:** no error; the command may print nothing. An existing folder might have a different name, so use the Finder drag method for an existing copy.

From inside the project, display your location:

```sh
pwd
```

**Expected:** the path to your project folder. Check its contents:

```sh
ls
```

**Expected:** entries including `README.md`, `skills`, `scripts` and `tests`.

**From now on, run all commands in this guide from this project folder**, unless a step explicitly says otherwise. Keep this Terminal window open. In a new window, repeat the Finder drag method and folder checks.

### Step 3 — Install the Skills and create local context

A **Skill** is a small instruction pack that teaches Codex a particular workflow. The source packs live in `skills/`. The installer copies the complete set into `.agents/skills/`, where Codex discovers them for this project.

Project-local installation is recommended: it keeps these workflows attached to this folder. From the project folder:

```sh
python3 scripts/install_skills.py --dest .agents/skills
```

**Expected:** a report that **20 skills** were installed. The installer also copies licence/attribution files. It refuses existing skill folders instead of overwriting them. If it says a folder exists, see [Skill installation already exists](#skill-installation-already-exists).

Check the number installed:

```sh
python3 -c "from pathlib import Path; print(len(list(Path('.agents/skills').glob('li-*/SKILL.md'))))"
```

**Expected:** `20`. Install the whole pack; the skills share resources with their siblings.

Create the private context templates:

```sh
python3 skills/li-context/scripts/context.py --root .linkedin-agent init
```

**Expected:** a report containing `created` and filenames. Repeating it preserves existing files and creates only missing templates; `created: []` is normal on a repeat.

Check the templates:

```sh
python3 skills/li-context/scripts/context.py --root .linkedin-agent status
```

**Expected on first use:** `missing: []`, an `unfilled` list, and `status: "partial"`. Setup worked; you still need to add your information. You can start writing before every template is filled.

### Step 4 — Open the project in Codex and try one request

Select this same project folder in your local Codex client. Start a new chat; restart the client if newly installed skills are not visible.

Codex can choose a Skill from a natural request. You do not normally need to remember skill names. Explicit selection is also supported: type `$li-human` with your request to select that Skill. CLI/IDE clients also expose `/skills`. This project does not supply `/li-human` slash commands. Discovery and selection follow the [official Skill conventions](https://learn.chatgpt.com/docs/build-skills).

**Ask Codex:**

> Rewrite this LinkedIn post in my voice. I have not configured my voice yet, so use a plain, restrained tone and tell me what you need to personalize it. Do not research or add facts. Text: “I spent today reviewing our checklist. One step was unclear. I rewrote it so the next person can follow it.”

**Success:** a readable draft based only on supplied text, no invented results and no attempt to open LinkedIn. It may ask for writing samples. No browser tool or paid service is needed.

You now have the basic installation. Continue below to personalize it and add real information. The [one-page quickstart](QUICKSTART.md) is available for later reference.

## First Run

### Step 5 — Set up your profile a little at a time

**Ask Codex:**

> Set up my LinkedIn Intelligence Agent. Use the local .linkedin-agent context. Ask for the minimum useful information first, preserve existing files, and leave unknown facts as placeholders. Do not access LinkedIn.

Codex should apply `li-context`, read the templates and help fill them using what you actually provide. It should not claim to know your job or achievements from the installation itself.

| Local file | What to provide |
| --- | --- |
| `.linkedin-agent/identity/voice.md` | Real writing samples and style preferences |
| `.linkedin-agent/identity/bio.md` | Public professional facts: role, experience, expertise |
| `.linkedin-agent/identity/audience.md` | Who you want to help or reach, and what matters to them |
| `.linkedin-agent/knowledge/companies.md` | Organizations you can discuss publicly |
| `.linkedin-agent/knowledge/projects.md` | Actual work, milestones and lessons; mark private details |
| `.linkedin-agent/knowledge/claims.md` | Verified, user-provided, qualified, unsupported or confidential statements, and permission for public use |
| `.linkedin-agent/knowledge/metrics.md` | Real numbers, dates, sources and permission to use them; leave missing numbers unknown |
| `.linkedin-agent/history/` | Posts/comments you confirm you actually published, plus topic memory |
| `.linkedin-agent/analytics/performance.csv` | Actual performance measurements when available |

Start with voice, bio and audience. Add projects, permitted claims and metrics as needed. Do not manufacture content to fill a template. `{{...}}` marks a placeholder to replace only when you have the information.

Run the context `status` command from Step 3 again to check progress. A complete template is not proof that a fact is true or that you may publish it.

## Teach It How You Write

### Step 6 — Supply three real samples

The context Skill asks for **three actual writing samples**. Choose posts you wrote yourself that sound representative of you. Remove confidential or unnecessary personal details before pasting them.

**Ask Codex:**

> Here are three LinkedIn posts I wrote myself. Use them to improve my voice profile without copying them. Learn my tone, sentence length, vocabulary, formality, typical openings and formatting. Ask me about anything you cannot infer. [Paste the three posts here.]

Also tell it about contractions, humour, profanity tolerance, emojis, phrases you avoid, and phrases it must never generate. The samples help it describe your style; they are not a licence to recycle whole posts.

Check its proposed `identity/voice.md`. Repeat the rewrite request with another piece of your own text. **Success:** it sounds closer to you while preserving the meaning and facts.

## Give the Agent LinkedIn Information

### Step 7 — Start with pasted content

**Account access** would mean logging in and fetching your live account. This toolkit does not do that. **Imported data** is a local copy you are authorized to use. It represents only what you supplied, at the time supplied.

The easiest input is text pasted into Codex: a post, its comments, your profile sections, or your analytics. Pasted text works for a one-off draft/review. It does **not** become saved import data automatically unless you ask Codex to save/import it.

**Ask Codex:**

> These are my own posts and comments that I am authorized to use. Review only this supplied material. Tell me what deserves attention and what data is missing. Do not assume this is my complete account. [Paste the material here.]

For reuse, have Codex prepare the supported import file:

> Prepare the posts I supplied as a li-read import envelope and save it as .linkedin-agent/imports/my-posts.json. Use the read contract and sample-read.json as references. Preserve the text, identify the source as manual and the coverage as partial. Leave unknown URLs, authors, metrics and event dates null; do not invent LinkedIn IDs. Use clear local record IDs where needed. Record the actual preparation time separately from event dates. Show me what you saved and flag private information before import.

An **import envelope** is a JSON file that bundles records with their source and coverage. JSON is a structured text format. Codex can prepare it; you do not need to hand-write it. Review the saved file first. Public permission and factual accuracy still need checking; import success does not certify either.

**Only after that file exists**, from the project folder, import it:

```sh
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent import .linkedin-agent/imports/my-posts.json
```

**Expected:** counts named `new`, `updated`, `unchanged`, `older_ignored` and `retired`. This command validates the envelope before saving records. Invalid data produces an error. Ask Codex to fix the file against the read contract and retry; keep the original source material.

Check that your own posts can be read:

```sh
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent show --capability own_posts
```

**Expected:** imported records and their sources. Empty `[]` means no visible records of that type; check capability and visibility with Codex.

Private/restricted material is excluded by default. Do not mark it public to make an import pass. Ask Codex about explicit private-data options only if you intend local private analysis; these options do not authorize publication or external research.

### Try a complete fictional example first

The full working example is in [sample-read.json](../skills/li-read/assets/sample-read.json). It contains **fictional practice posts/comments**, not your activity. These commands put it in a **separate practice area**, `.linkedin-agent/practice`, rather than your real reader data.

From the project folder, validate and import it:

```sh
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent/practice import skills/li-read/assets/sample-read.json
```

**Expected first time:** `new: 4`. A repeat may report unchanged records. Unknown URLs and metrics are `null` in the complete example. Required source/coverage fields must still be present; ask Codex to prepare them for real material.

Read the practice post:

```sh
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent/practice show --capability own_posts
```

**Expected:** a post by `Example user`, ID `demo-p1`. Do not treat it as your experience or publish it as yours.

**Ask Codex:**

> Review the fictional LinkedIn information in .linkedin-agent/practice and tell me what deserves attention. Treat it only as a setup exercise. Do not add it to my real publication history or use it as evidence about me. Note its dates and missing coverage.

**Success:** it identifies practice material, explains limits, and suggests only human-reviewed next steps. The example has fixed dates and can become stale; that is expected.

For a repeatable demonstration independent of the example's age, from the project folder:

```sh
python3 scripts/demo_brief.py
```

**Expected:** fictional `RESPOND` and `COMMENT` recommendations with draft placeholders. It uses a fixed demonstration clock in temporary storage. It does not update your real data or produce personalized final copy.

### Other supported inputs

- **Snapshot JSON:** use the envelope/import method. A LinkedIn export ZIP is not directly accepted; let Codex inspect relevant authorized files first.
- **CSV:** spreadsheet-style text. The reader has `import-csv` with source information and optional column mapping. Raw export headings vary; ask Codex to inspect your headings and prepare source/mapping files instead of guessing a universal format. See the [read contract](../skills/li-read/references/read-contract.md).
- **Performance CSV:** have Codex add actual observations using the header in `.linkedin-agent/analytics/performance.csv`. Missing measurements stay unknown.
- **Publication history:** after publishing manually, tell Codex to record the actual post/date. A draft is not published. Importing a reader snapshot does not automatically add publication history.

Check your real reader from the project folder:

```sh
python3 skills/li-read/scripts/read_layer.py --root .linkedin-agent status
```

**Expected:** `mode: "Manual"` and `live_account_client: false`. Each capability (a type of information, such as your posts) can be `available`, `partial`, `stale` or `unavailable`. Partial means limited coverage, unavailable means missing usable data, and stale means old data. None means a live connection. Local refresh re-reads configured local files; it does not contact LinkedIn.

## Things You Can Ask

### Step 8 — Use ordinary requests

You do not normally need Skill names. Supply the material, or say which local imports to use.

1. “Review my imported LinkedIn data and tell me what deserves my attention.”
2. “Find me something worth posting about from my actual recent projects.”
3. “Have I already posted about this topic? Is this angle meaningfully different?”
4. “Rewrite this in my voice without adding facts.”
5. “Review the comments on my latest imported post.”
6. “Who should I engage with, based only on the information I've supplied?”
7. “Research this public topic before drafting a post, using available tools.”
8. “Do my weekly LinkedIn review and identify missing information.”
9. “Audit these LinkedIn profile sections I pasted.”
10. “Draft a reply to this comment. Leave unknown results as placeholders.”

Missing data should produce a gap or question, not invented activity. Research requires available research tools; the other examples can use supplied material. Facts, public permission, voice and quality still need review before you copy a draft into LinkedIn.

## Optional: Enable Web Research

### Step 9 — Decide whether you need more tools

**Optional research setup.** Stop here if writing and imported-data review are enough. Codex may already have public research tools; check those before adding duplicate servers. Nothing below grants LinkedIn account access.

**MCP** lets Codex talk to an external tool such as a browser or page reader. An MCP server is the program providing that tool. This project's optional bridge is a local helper connecting research requests to suitable tools, so you do not have to choose a provider for every request.

| Tool | Plain-English role | Do I need this? | Current implementation |
| --- | --- | --- | --- |
| Scrapling | Reads ordinary public webpages; can render pages when needed | **YES** for local webpage extraction. **NO** for supplied writing/imports or if existing tools suffice. | Optional pinned Python package, local MCP bridge and verification utility. Not installed merely by cloning. |
| Playwright | Opens an isolated browser for pages needing clicking/interaction | **YES** for permitted public interaction. **NO** for drafting or simple page reads. | Optional pinned Node package and separate Chromium download. No logged-in browser reuse. |
| Agent Reach | Adds supported specialist/community sources | **YES** only for a supported source you need. **NO** for basic use. | Audited machine: installed, source opt-in disabled. Bridge supports public V2EX; Reddit/X authentication paths remain disabled/unvalidated; YouTube retrieval is not supported by this bridge. A fresh clone does not install it. |
| Bright Data | Managed fallback for difficult public websites | **YES** only after reviewing access, credentials and cost. **NO** for most beginners. | Disabled by default. Optional Node installation includes its dependency but does not enable it. |

Do not authenticate personal social accounts, import cookies or enable extra adapters to finish setup. Access restrictions still apply. Supply blocked LinkedIn material through authorized imports, not bypass tools.

### Optional prerequisite checks

Run these from the project folder. Research setup needs **Python 3.11+**, **Node 20+** and npm. Node runs JavaScript tools; **npm** installs their locked packages. Neither is needed for core writing.

Recheck Python using Step 1. Check Node:

```sh
node --version
```

**Expected:** `v20...` or newer. If absent, use the [official Node download](https://nodejs.org/en/download), choose the macOS installer, complete it and reopen Terminal.

Check npm:

```sh
npm --version
```

**Expected:** a numeric version. npm comes with the normal Node installer. If missing, repair that installation before continuing.

### Create an isolated Python environment

A **virtual environment** is a folder containing Python tools for this project. It avoids installing research packages into system Python. Core setup did not need one.

**If `.venv` already exists, stop and check it with Codex.** Do not replace another environment or reinstall over a functioning setup. These commands are for a fresh optional installation.

From the project folder, create it:

```sh
python3 -m venv .venv
```

**Expected:** no error and a `.venv` folder. Later commands use its Python directly, so you need **no activation command** or changed Terminal prompt.

Install the locked Python packages, checking download hashes:

```sh
.venv/bin/python -m pip install --require-hashes -r tools/web/requirements.lock
```

**Expected:** successful installation, or `Requirement already satisfied` where appropriate. Downloads take time. `requirements.in` is the short list; `requirements.lock` pins the full set. Do not substitute an unpinned install.

Check the environment's Python:

```sh
.venv/bin/python --version
```

**Expected:** Python 3.11+. This standard venv/pip route is supported and was checked in a fresh macOS copy. Developer setup also supports uv, an alternative environment/package manager; you do not need uv for this route.

### Install the optional Node tools and browser

From the project folder, install locked Node packages:

```sh
npm ci --prefix tools/web --ignore-scripts --no-audit --no-fund
```

**Expected:** an installation summary. Packages go inside `tools/web/node_modules`; lifecycle scripts are disabled. This also downloads the disabled Bright Data dependency. It does not use a key or access your provider account.

Download Chromium, the browser shared by the local servers:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.web-tools/browsers" .venv/bin/python -m playwright install chromium --no-shell
```

**Expected:** download progress and completed installation. `$PWD` means the current folder; quotes support spaces. This one-command setting puts the browser in `.web-tools/browsers`.

Record its location for the launchers, the small scripts that start these tools. This is **one multi-line command**: copy the entire block, including the last `PY`, into Terminal from the project folder. It writes only the local browser-location file:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.web-tools/browsers" .venv/bin/python - <<'PY'
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    executable = p.chromium.executable_path
assert Path(executable).is_file()
path = Path('.web-tools/browser.json')
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps({'executable_path': executable}) + '\n')
PY
```

**Expected:** no error. An assertion error means the executable was not found; complete the download first.

### Preview and register tools

From the project folder, preview configuration:

```sh
python3 tools/web/configure.py
```

**Expected:** `scrapling_local`, `playwright_local` and `brightdata_fallback`, with `written: false` and Bright Data disabled. Preview does not change configuration.

If correct, and you have no equivalent registrations, write it:

```sh
python3 tools/web/configure.py --write
```

**Expected:** `written: true`. This adds entries to project `.codex/config.toml`, preserves other settings and leaves Bright Data disabled. It does not change user-wide Codex configuration. A repeat refuses existing names to protect your setup.

Open only projects you trust in Codex. Restart the local client to load project configuration. If asked to approve/trust the folder, review it and the configuration first. An already-running chat cannot acquire new tools automatically.

### Verify Scrapling and Playwright

These checks request a public demonstration website, not LinkedIn. Run separately from the project folder; each closes its browser/server session when finished.

Check Scrapling:

```sh
.venv/bin/python tools/web/verify_mcp.py scrapling
```

**Expected:** `initialized: true` and `PASS` for `structured_output`, `http_markdown` and `dynamic_text`. Failure may mean missing packages/browser, blocked network access or a changed test site. Do not disable access protections to force success.

Check Playwright:

```sh
.venv/bin/python tools/web/verify_mcp.py playwright
```

**Expected:** `initialized: true` and `navigate_snapshot_follow_link: "PASS"`. If it cannot launch, check the browser download and location file.

Check provider status:

```sh
.venv/bin/python tools/web/research.py health
```

**Expected:** `research_providers` and `linkedin_reader`. **Installed does not always mean ready.** Actual states:

| State | Meaning |
| --- | --- |
| `DISABLED` | Deliberately off; normal for optional providers |
| `UNAVAILABLE` | Required runtime/tool missing |
| `AVAILABLE_UNVALIDATED` | Detected, but no recent successful research request has been recorded for this capability |
| `VALIDATED` | A recent successful request through the research bridge confirms the listed capability |
| `LAST_ATTEMPT_FAILED` | Latest recorded research request failed; inspect its error |

The verification commands are short test requests; they do not update the bridge's health records. A provider can pass these checks and still show `AVAILABLE_UNVALIDATED`. Ask Codex for a small permitted public research task to exercise the bridge; health then reflects its recorded outcome. Not every provider needs enabling.

### Find candidates, then research them on the public web

Ask “Find 25 people on LinkedIn working on sports biomechanics.” With an available
search-only Codex web tool, the agent can find relevant candidate URLs and research
selected people using permitted public sources. It does not log into LinkedIn or
scrape those profiles. Search snippets are unverified clues; the agent should explain
identity uncertainty. To analyze actual LinkedIn content, provide an authorized
snapshot/export or paste the relevant information.

Discovery defaults to 25 candidates, never more than 100 unique candidates per task.
Normally use 1–3 queries, never more than 10. Public research of the strongest subset
defaults to 10 people, maximum 20. A private 24-hour metadata cache avoids repeated
searches; it does not create relationships automatically. Your imported posts,
connections, comments and analytics have ordinary resource limits, not discovery caps.

**Availability is PARTIAL and session-dependent.** Native search-only handoff is
validated; the installed Agent Reach Exa content-returning transport remains disabled.
Without an appropriate session search tool, discovery is unavailable. Agent Reach
and optional web tooling remain optional for core writing/imports. See [the discovery
guide](LINKEDIN_DISCOVERY.md) for the handoff and [product limits](POLICY_LIMITS.md).

### Leave Agent Reach and Bright Data optional

**Agent Reach:** no install or account-authentication step is required here. Its presence on the audited machine does not mean it is on yours. Public V2EX requires deliberate source opt-in; leave it off unless needed. Installed Reddit/X/YouTube utilities are not evidence of working bridge capabilities.

**Bright Data:** keep `brightdata_fallback.enabled` false in project `.codex/config.toml`. Most beginners need nothing more. Advanced use requires a privately supplied `API_TOKEN` and may incur costs. An **environment variable** is a named setting passed to a program. The token belongs in the private environment launching Codex, not a chat, command argument, URL, tracked file or TOML.

`.env.example` has only an empty placeholder. Codex does not automatically load `.env`. The upstream server can provision account zones at startup; review provisioning/billing before enabling it. No real key or paid operation was used for this guide. See [advanced web setup](CODEX_WEB_TOOLING.md#bright-data-credentials) before deliberate activation.

## Troubleshooting

### Step 10 — Match the symptom

Before retrying, return to the project folder with the Finder drag method and check `pwd`/`ls`. Do not paste a guessed path or a command from an external webpage.

| What you see | What it means / what to do | How to verify |
| --- | --- | --- |
| `python3: command not found` or Python too old | Install supported Python from Step 1; reopen Terminal. | Version is 3.10+ for core, 3.11+ for research. |
| `node: command not found` | Optional runtime missing. Skip research or install Node. | Node version is 20+. |
| `npm: command not found` | Package manager missing in this Terminal. Repair official Node installation; reopen Terminal. | npm reports a number. |
| `No module named venv`, pip/download error | Optional setup incomplete or network failed. Use supported Python; inspect the error before recreating anything. Do not force system-wide pip/admin installation. | Environment's Python works; locked install succeeds. |
| `Permission denied` | Folder read-only or owned by someone else. Use a writable folder you own; preserve data before moving. Do not use `sudo`. | Installer/context init can write normally. |
| `can't open file` / “No such file” | Wrong folder, typo or conditional input file not created. | `ls` shows the stated script/input; retry. |
| Skill not found | Wrong project, missing copies, duplicate installations or stale client discovery. | Count is 20; reopen folder/new chat and ask for `$li-context`. |
| MCP server does not start | Missing optional runtime, project trust or stale launcher path. Inspect preview/error. | Relevant verification passes; restart Codex and test in a new chat. |
| Scrapling verification fails | Package/browser/network missing, or test site unavailable. | Check locked install/browser receipt; retry only Scrapling's check. Report persistent failure. |
| Playwright browser fails | Missing download, stale receipt or unsupported runtime. | Repeat browser download/receipt in current folder, then verify. Never import browser accounts. |
| Agent Reach `DISABLED` | Expected opt-in setting, not core failure. | Core rewrite/import works; enable only a needed supported source. |
| Bright Data missing token | Expected disabled fallback. No key needed for setup. | Keep disabled; core/local research work without it. |
| No LinkedIn data | Missing real imports, wrong capability/root or visibility. | Real reader status/show match intended input; practice is separate. |
| `stale` data / no recommendation | Old/incomplete snapshot or no useful signal. | Supply new authorized material with real dates; never relabel old dates. |
| Spaces in path | Unquoted typed path split into words. | Finder drag for `cd`; keep browser-command quotes. |
| Moved/renamed folder / stale launcher | Generated paths/receipt/environment point to old folder. | Use recovery below, then both MCP checks. |
| Existing MCP names refused | Helper protects registrations from overwrite. | Review entries; even preview refuses existing names without changing files. Repeating `--write` cannot replace them. |
| Context `partial` | Normal unfilled templates. | Add real facts progressively and recheck; unknowns can remain unknown. |

### Skill installation already exists

If count is 20 and you are not updating, use the existing pack. For incomplete/updated copies, ask Codex to compare source and installed folders first. Back up installed `li-*` folders **outside discovery directories**, preserving custom edits. Only then move that reviewed pack out of `.agents/skills` and reinstall. Preserve unrelated Skills; do not add a second user-wide copy to hide conflicts.

### If you moved the folder

Generated configuration contains absolute paths. Point Codex and Terminal at the new folder. Preserve `.linkedin-agent` and back up project `.codex/config.toml` before edits.

Ask Codex to inspect `.venv`, `.web-tools/browser.json` and the three project MCP entries. Adjust only affected launcher paths, preserve other settings, and regenerate the browser receipt if necessary. The helper can preview paths only before registration; with existing names, even preview refuses conflicts without changing files. Ask Codex to review the existing configuration and portable template instead. Moving a virtual environment can break entry points; choose a safe rebuild after inspecting it rather than copying environments blindly.

Rerun both MCP checks and restart Codex. Basic writing/context can work while optional tools are repaired.

## If You Get Completely Stuck

1. Stop and copy error text into Codex, excluding keys, cookies and confidential data.
2. Check `pwd`/`ls`. Ask Codex to diagnose the current setup before changes.
3. Make a private backup of `.linkedin-agent`, including voice, claims, imports and history. Do not delete it to repair tooling.
4. Re-run context `init` for missing templates; it preserves existing files. Review Skill conflicts before reinstalling.
5. Preserve optional configuration and inspect the failure. In a dedicated environment, locked Python/npm reinstallation can repair missing dependencies. npm's clean install replaces that package folder; do not touch another project's environment.
6. If necessary, clone into a **different new folder**, use the core path there and restore reviewed private context. Keep the old folder until the new one works.

Do not discard Git changes to fix setup. Never delete context/history without an explicit decision and a usable backup.

## Data and Privacy

**Local files:** `.linkedin-agent/` contains voice/profile context, claims, metrics, history, analytics and imported reader data. `.web-tools/` holds browser/health state; `.venv/` and `tools/web/node_modules/` hold optional packages. Core Python helpers run locally with no external detector APIs or telemetry.

**Codex:** pasted text and files it reads may be processed by its model/service according to your account/client settings. Local storage does not mean every Codex interaction stays on your computer. Share only what you are comfortable using there.

**Research:** public URLs/queries and necessary request details may go to the selected tool/site/provider. Keep inputs public/minimal. Do not send private profile context, internal claims, inbox material, secrets or customer details as research input. Imports still need factuality/public-permission review.

**Git:** the repository ignores `.linkedin-agent/`, generated `.agents/skills/li-*`, `.codex/config.toml`, `.web-tools/`, `.venv/`, Node packages and `.env` files. Ignoring prevents ordinary accidental additions; it is not encryption and cannot protect deliberately force-added or previously tracked files. Never commit personal context, imports, cookies, tokens or credentials. Keep backups private.

## Updating Later

From the project folder, check changes first:

```sh
git status --short
```

**Expected if clean:** no output. If filenames appear, review/save changes with Codex; do not overwrite them. Ignored private context does not appear, so back it up separately. A ZIP download is not a Git clone; use a separate fresh clone for Git updates.

**Only with a clean checkout and private backup**, request an update that refuses automatic merge commits:

```sh
git pull --ff-only
```

**Expected:** `Already up to date.` or fast-forward summary. If refused, ask Codex to explain the branch/changes; do not force it.

Read the updated README. Installed Skills are copies; updates do **not** update `.agents/skills` automatically. Use the reviewed backup/reinstall procedure. Re-run optional installs only if lockfiles changed and the environment is dedicated. Recheck relevant MCP verification/health afterward.

From the project folder, run automated checks:

```sh
python3 -m unittest discover -s tests -q
```

**Expected:** test count followed by `OK`. Optional-runtime checks may be skipped on core-only installs. `FAILED` needs investigation. Tests require Git history for licence comparison; counts can change as the project evolves.

### Optional: user-wide Skill installation

Only if you want these Skills in other projects, run **from this repository**:

```sh
python3 scripts/install_skills.py --dest "$HOME/.agents/skills"
```

**Expected:** 20 installed, unless existing folders conflict. `$HOME` is your user folder. Use one strategy to avoid duplicate packs. User-wide Skills still need `.linkedin-agent` context in the active project. No global install is required for the beginner path.

## Is Everything Working?

- [ ] `pwd`/`ls` identify the intended project.
- [ ] Python meets the core minimum.
- [ ] Installed count is 20; Codex applies a LinkedIn Skill in a new chat.
- [ ] Context init/status work; `partial` is fine during onboarding.
- [ ] Step 4 rewrite works without research or invented facts.
- [ ] Real imports can be shown, or separate fictional practice import works.
- [ ] Reader status describes coverage without claiming live access.
- [ ] Unittest finishes with `OK` in the Git clone.
- [ ] Scrapling/Playwright checks pass, if enabled.
- [ ] Health states are understood; disabled providers need not be enabled.
- [ ] You review and perform every LinkedIn action yourself.

**Validation scope:** commands were checked on macOS on 2026-10-02 in an isolated copy, including project-local and isolated user-wide installs, practice/prepared imports and optional setup/verification. Public cloning was checked separately from working-tree code. Desktop sign-in, OS installers and personalized model responses require human first-use checks. No Linux/Windows, paid Bright Data activation or unsupported social-source setup is claimed as tested.

## Where to Go Next

- [README](../README.md): Skills and workflows.
- [Architecture](../ARCHITECTURE.md): how components fit.
- [Security](../SECURITY.md): boundaries and residual risks.
- [Advanced web tooling](CODEX_WEB_TOOLING.md): versions/configuration.
- [Orchestration](ORCHESTRATION.md): routing/evidence/capability limits.
- [v1 release audit](V1_RELEASE_AUDIT.md): validated behavior and gaps.
- [One-page quickstart](QUICKSTART.md): shortest core route.
