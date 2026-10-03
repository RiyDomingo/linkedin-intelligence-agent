# Quickstart: LinkedIn Intelligence Agent

For explanations and troubleshooting, use the [Beginner Setup Guide](BEGINNER_SETUP.md).
This is the tested **macOS core path**: local Codex, Git and Python 3.10+.
Core writing needs no Node, npm, research provider or LinkedIn login. For account
onboarding, also follow Step 5: the isolated connector requires uv and Python 3.12
and you sign in manually in its dedicated browser. See [connector setup](ACCOUNT_CONNECTOR.md).

## Recommended: ask Codex to set it up

Download or clone the repository, open its folder in Codex desktop, and paste:

> Set up LinkedIn Intelligence Agent for me. Check prerequisites, run the installation
> and configuration, and guide me through onboarding. Handle the commands yourself
> and pause only when you need my login, approval or decisions.

Codex can check the existing setup, install the 20 Skills, create private local
context, configure the optional connector and browser, and guide you through your
first brief. You normally do not need to run Terminal commands or edit configuration
files yourself. If a prerequisite or permission is unavailable, Codex should explain
the specific blocker and the smallest step needed to continue.

You still sign in to LinkedIn and complete verification yourself, confirm or correct
what the agent learned, and choose your goals and important audiences. Approve
installation permissions if your client requests them. Never put a password in chat.

For help getting the folder open, use the [Beginner Setup Guide](BEGINNER_SETUP.md).
The numbered commands below are the manual alternative and troubleshooting path;
Codex can execute them for you. Optional public research setup is separate.

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

Expected: a usable draft, no LinkedIn action.

For guided first-run onboarding, ask “Set up my LinkedIn Intelligence Agent.”
Codex offers account connection or the no-account path, optional sources, a review,
and the two missing strategic choices, then gives your first brief. Progress
survives interrupted chats. See [Onboarding](ONBOARDING.md).

For account-based onboarding, continue to Step 5. Codex can use your own observed
posts to propose voice traits, with uncertainty clearly labelled. You do not need
to paste your profile or posts when that connection succeeds.

If you prefer the local-only path, ask Codex to help add your real voice, public bio
and audience. Supply representative writing samples,
[authorized LinkedIn information](BEGINNER_SETUP.md#give-the-agent-linkedin-information),
or try the full guide's separate fictional practice import.

## 5. Connect LinkedIn (optional account onboarding)

```sh
python3 tools/linkedin/setup.py --install --provision-browser --write
python3 tools/linkedin/manage.py --root .linkedin-agent enable
```

Restart Codex if needed, then ask: "Connect LinkedIn and build my professional
context from my profile and own posts." Sign in yourself in the dedicated browser
if requested. The connector can reuse an existing saved login. No password in chat.
Sign-in in another browser tab does not connect this gateway. There is no separate
application to launch: continue working in this project's Codex chat.
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

## Returning to the agent

Open the same project in Codex and ask for Brief me, Create, Discover, Engage, or
Review & Plan. Completed setup is reused; offline context tasks remain available.
“Rerun setup review” reopens review without deleting memory or authentication.
See [the five workflows](WORKFLOWS.md).
