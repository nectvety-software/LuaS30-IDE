# AI Agent

> **Language:** English · [Tiếng Việt](../vi/AI-Agent.md)

LuaS30 Studio ships **ChatAI** in the right sidebar — an agent-style workspace that
can read the codebase, propose file edits, and run commands in the terminal the user
can actually see.

## Mandatory preflight

Any AI agent that creates, scaffolds, imports, migrates, generates or substantially
modifies a LuaS30 project **must** read these two files, **in this order**:

```text
1. doc/ai/SKILL.md
2. doc/ai/PROMPT.md
```

It must then inspect the current source/config relevant to the requested target. Do
**not** create a project from memory, old chat context, generic MRE knowledge, or an
older LuaS30 version.

Minimum preflight for a new project:

```text
doc/ai/SKILL.md
doc/ai/PROMPT.md
VERSION
README.md
doc/INDEX.md
profiles/<selected-target>.json
templates/basic/
```

If the exact target profile does not exist:

```text
profiles/generic-vxp-qvga.json
templates/device_probe/
sdk/luas30/include/ls30/
sdk/luas30/src/abi_resolver.c
```

Then either use the conservative generic profile and **clearly mark hardware
compatibility as untested**, or add a dedicated target profile/adapter first,
validate it, then scaffold the application.

Agent entry point: [`doc/ai/README.md`](../../doc/ai/README.md).

## Providers

Supported transports:

```text
OpenAI
Anthropic
Google Gemini
OpenAI Compatible
Ollama Local
```

**AI Provider Settings** is a frameless modal with: Provider, Model, Base URL, API
key, Timeout, Allow shell requests, Allow code-change proposals, Show reasoning
summary/activity trace.

Buttons: **Test Connection**, **Apply**, **Save & Close**, **Cancel**.

`Test Connection` performs a minimal real request in a QThread so the UI is not
blocked, and reports `Connected` or the returned connection/API error.

API keys are **session-only by default**. If the user opts to save one, it is written
to:

```text
%APPDATA%/LuaS30IDE/config/ai_credentials.json
```

This is **plaintext** JSON outside project folders, written atomically, with
filesystem permissions restricted where the OS supports it. The dialog states this
explicitly and lets the user remove a saved key by unchecking the option and applying.
Provider/model/base URL/timeout settings live separately in `ai_providers.json`.

## Access modes

The selector sits directly below the chat text box:

| Mode | Behaviour |
|---|---|
| **Ask before changes** | edit proposals open the `AI Changes` tab for review; the user presses `Apply Code` or `Reject`. Shell requests need the Run button |
| **Edit automatically** | validated changes are applied automatically; shell **still** needs approval; replaced files are backed up |
| **Plan mode** | the prompt disables `luas30-edit` and `luas30-shell` entirely; the AI still reads context and returns a plan |
| **Full access** | validated changes are applied automatically; commands classified `safe`/`project` run automatically in the visible Terminal |

> Commands classified `sensitive` or `dangerous` are **never** run silently — even in
> Full access they still require confirmation.

The selector changes **confirmation behaviour**, not the **sandbox**.

## Activity and reasoning display

LuaS30 does **not** display a provider's raw chain-of-thought. The panel shows:

```text
AI ACTIVITY · REASONING SUMMARY
```

It can contain: context files/rules selected, high-level reasoning summary, code
proposal summary, shell proposal with risk level, shell execution result,
apply/reject result, provider/tool errors. The model uses a bounded `luas30-summary`
block for this purpose.

## Protocols

| Protocol | Role |
|---|---|
| `luas30-edit` | propose in-project file edits (a `find`/`replace` patch, or a full-file `content` proposal) |
| `luas30-shell` | propose a command for the visible Terminal |
| `luas30-tool` | read-only tools: `read`, `grep`, `glob` |
| `luas30-summary` | bounded high-level activity/reasoning summary |

`luas30-edit` as a patch:

````text
```luas30-edit
[{"path":"main.lua","find":"old","replace":"new","reason":"Fix logic"}]
```
````

As a full file:

````text
```luas30-edit
{"path":"src/module.lua","content":"-- complete file\n","reason":"Add module"}
```
````

The protocol is parsed **separately** from the visible chat text.

## AI Changes

When an edit proposal is prepared, LuaS30 creates an ordinary tool tab:

```text
AI Changes
```

The tab contains: the changed-file list, a `CURRENT` pane, a `PROPOSED` pane,
line-change highlighting, +/− line statistics, and `Reject` / `Apply Code` buttons.

In `Ask before changes` the diff tab opens automatically. Auto modes prepare the same
validated change set but can apply it without stealing editor focus.

If the editor holds unsaved text, **that text** is used as the review base — so the
review cannot silently ignore what the developer currently sees.

### Apply and backup

Overwritten files are copied to:

```text
<project>/.luas30/ai-backups/<timestamp>/<relative path>
```

before atomic replacement. New files need no source backup. After applying, LuaS30
refreshes editors, the project index and the Explorer tree, then reports the applied
files back to the agent.

## Project boundary

AI code edits are confined to the open project root. LuaS30 rejects:

```text
absolute paths
../ traversal outside the project
.git / .hg / .svn
.venv / venv
node_modules
release
common credential / secret / private-key filenames
```

## Shell integration

AI-proposed commands run in the **same Integrated Terminal** the user sees. The agent
cannot open a hidden second shell. Captured output is size-bounded and common
secret-bearing environment values are redacted before the result is sent to a remote
provider.

Command classification:

| Level | Behaviour |
|---|---|
| `safe` | read-only, may auto-run in Full access |
| `project` | in-project work, may auto-run in Full access |
| `sensitive` | always asks |
| `dangerous` | always asks, with additional confirmation |

## Chat sessions

ChatAI keeps project-scoped sessions in:

```text
%APPDATA%/LuaS30IDE/config/ai_sessions.json
```

The header Sessions button can create, resume, rename and delete conversations. The
active session is restored per project. Internal tool results are retained for model
continuity but are not rendered as visible chat messages after a resume.

Supported local commands:

```text
/new
/clear
/sessions
/resume
/continue
/rename <name>
/help
```

## UI design and asset tools

Beyond code read/write tools, the agent has two design tools that share
`design_store` / `lua_export` / `items.COMPONENTS` with the UI Designer (the schema is
not duplicated):

- **`ui_design`** — `catalog`, `screens`, `get` to read; `add_screen`,
  `rename_screen`, `delete_screen`, `set_screen`, `add_item`, `update_item`,
  `remove_item`, `export` to write.
- **`asset`** — `list` and `make` (generates PNG, 9 kinds).

Writes are gated by `allow_write` (i.e. the edit policy is not `disabled`). Snapping
is 4px, components are clamped inside 240×320, and default asset colours come from
`lua_export` (**content** colours, not IDE colours).

Tool names are a **single source** (`TOOL_NAMES` in `ai_agent_protocol.py`), used
both for parse-time filtering and for the prompt. Adding a tool without registering it
there makes the tool block be dropped **silently** (0 actions, no error).

## Automatic context

ChatAI reads the project structure, the active/relevant source, the project's and the
engine's `SKILLS.md` / `SKILL.md` / `PROMPT.md`, and excludes common secret files such
as `.env`, credentials and private keys.

> **Trap worth knowing:** instruction documents are truncated by a character limit
> when the context is built. If important content sits at the end of an over-long
> file, it may **never reach the model**. The current limits are 64,000 characters per
> file and 160,000 total, and the truncation notice reports how many characters were
> dropped. `tools/validate_ai_context.py` guards this.

See also [`doc/studio/AI_WORKBENCH_V1_1_15_0.md`](../../doc/studio/AI_WORKBENCH_V1_1_15_0.md),
[`doc/studio/AI_AGENT_SHELL_1_14_0.md`](../../doc/studio/AI_AGENT_SHELL_1_14_0.md) and
[`doc/studio/AI_DESIGN_TOOLS.md`](../../doc/studio/AI_DESIGN_TOOLS.md).
