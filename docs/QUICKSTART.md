# Quickstart: LinkedIn Intelligence Agent

For explanations and troubleshooting, use the [Beginner Setup Guide](BEGINNER_SETUP.md).
This is the tested **macOS core path**: local Codex, Git and Python 3.10+.
No Node, npm, research provider or LinkedIn credentials are required.

## 1. Check prerequisites

In Terminal, from any folder, check Python:

```sh
python3 --version
```

Expected: Python 3.10 or newer. Check Git:

```sh
git --version
```

Expected: a Git version. Use the full guide if a prerequisite is missing.

## 2. Download or open the project

From your chosen parent folder in Terminal:

```sh
git clone https://github.com/RiyDomingo/linkedin-intelligence-agent.git
```

Expected: a new project folder. Enter it from that same parent folder:

```sh
cd linkedin-intelligence-agent
```

Expected: no error. Already have the project? Skip cloning. Type `cd` and a space,
drag its folder from Finder into Terminal, then press Return.

## 3. Install Skills and context

Run each command from the project folder. Install the pack:

```sh
python3 scripts/install_skills.py --dest .agents/skills
```

Expected: 20 Skills installed. Existing folders are refused; see the full guide.
Create private templates:

```sh
python3 skills/li-context/scripts/context.py --root .linkedin-agent init
```

Expected: created files, or an empty created list on repeat. Check context:

```sh
python3 skills/li-context/scripts/context.py --root .linkedin-agent status
```

Expected: no missing files; `partial` while templates need your information.

## 4. Try Codex

Open this folder in local Codex and start a new chat. Restart the client if
newly installed Skills are not visible. Ask:

> Rewrite this LinkedIn post in a plain tone without adding facts or doing research:
> “I reviewed our checklist today. One step was unclear. I rewrote it.”

Expected: a usable draft, no LinkedIn action. Then ask:

> Set up my LinkedIn Intelligence Agent. Help me add my real voice, public bio and audience.

Supply three real writing samples. Use the full guide to
[add authorized LinkedIn information](BEGINNER_SETUP.md#give-the-agent-linkedin-information)
or try its separate fictional practice import.

**Import-based, not live account access.** The agent drafts and recommends;
you review, decide and perform every LinkedIn action yourself.
