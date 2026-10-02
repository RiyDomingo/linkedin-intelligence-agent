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

## 5. Connect LinkedIn (optional account onboarding)

```sh
python3 tools/linkedin/setup.py --install --provision-browser --write
python3 tools/linkedin/manage.py --root .linkedin-agent enable
```

Restart Codex if needed, then ask: "Connect LinkedIn and build my professional
context from my profile and own posts." Sign in yourself in the dedicated browser
if requested. The connector can reuse an existing saved login. No password in chat.
See [requirements, actual validation and limitations](ACCOUNT_CONNECTOR.md).

The account connector reads only bounded own profile/posts/feed. It is third-party
browser automation, not an approved API. You perform every LinkedIn write action.

## Reusable professional context

After connecting LinkedIn, the agent builds private local professional memory.
Optionally add a resume/CV, professional bio, personal website or other professional
links now or later. Ask “What do you know about me?”, “Add my resume”, or “Correct my
current role.” Conflicts and sources remain visible; user corrections persist.
Most writing/context tasks reuse local memory and need no fresh account access.

See [the memory guide](PROFESSIONAL_MEMORY.md) for source management, privacy, export and reset.
