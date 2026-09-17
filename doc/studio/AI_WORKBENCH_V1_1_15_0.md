# AI Workbench v1 — 1.15.0

## Purpose

AI Workbench v1 turns the existing LuaS30 ChatAI sidebar into an IDE agent surface similar
in workflow to modern coding assistants while keeping user-visible control over file and
shell changes.

The right sidebar remains separate from the center editor and the Compact Bottom Panel.

## Reasoning / activity display

LuaS30 does not display a provider's private raw chain-of-thought. The visible panel is:

```text
AI ACTIVITY · REASONING SUMMARY
```

It can show:

```text
context files/rules selected
high-level reasoning summary
code proposal summary
shell proposal / risk
shell execution result
apply/reject result
provider/tool errors
```

The model protocol uses a bounded `luas30-summary` block for this purpose.

## Access selector

The selector is placed directly below the chat text box:

```text
Ask before changes
Edit automatically
Plan mode
Full access
```

### Ask before changes

- code proposals open the `AI Changes` review surface;
- the user presses `Apply Code` or `Reject`;
- shell requests require the Run button;
- dangerous/sensitive shell commands receive an additional confirmation.

### Edit automatically

- validated code changes are applied automatically;
- shell requests still require user approval;
- backups are created for replaced files.

### Plan mode

- provider prompt explicitly disables `luas30-edit` and `luas30-shell` actions;
- the AI can still read the bounded codebase context and return a plan.

### Full access

- validated code changes are applied automatically;
- commands classified as `safe` or `project` can run in the visible Terminal automatically;
- commands classified as `sensitive` or `dangerous` are never silently executed and still
  require confirmation.

## Provider Settings

Open the gear button in ChatAI.

The custom frameless dialog provides:

```text
Provider
Model
Base URL
API key
Timeout
Allow AI shell requests
Allow AI code-change proposals
Show reasoning summary/activity trace
```

Supported provider transports remain:

```text
OpenAI
Anthropic
Google Gemini
OpenAI Compatible
Ollama Local
```

### Test Connection

`Test Connection` performs a minimal real provider request in a QThread so the Qt UI is
not blocked. The dialog shows `Connected` or the returned connection/API error.

### Apply

Writes non-secret provider settings and refreshes ChatAI without closing the dialog.

### Save & Close

Applies the settings and closes the dialog.

API keys can now optionally be saved to the user's local JSON credential file:

```text
%APPDATA%/LuaS30IDE/config/ai_credentials.json
```

The provider/model/base URL/timeout settings remain separate in `ai_providers.json`.
The credential JSON is outside project folders, is written atomically, and LuaS30 attempts
to restrict its filesystem permissions where supported. It is still plaintext local JSON,
so the Provider dialog labels this explicitly and lets the user remove a saved key by
unchecking the save option and applying the settings.

## Code edit protocol

The agent can emit:

```text
```luas30-edit
[{"path":"main.lua","find":"old","replace":"new","reason":"Fix logic"}]
```
```

or a full-file proposal:

```text
```luas30-edit
{"path":"src/module.lua","content":"-- complete file\n","reason":"Add module"}
```
```

The protocol is parsed separately from visible chat text.

## Project boundary

AI code edits are restricted to the open project root. LuaS30 rejects:

```text
absolute paths
../ traversal outside the project
.git / .hg / .svn
.venv / venv
node_modules
release
common credential/secret/private-key filenames
```

The active unsaved editor text is used as the review base when available, preventing the
review from silently ignoring what the developer currently sees in the editor.

## AI Changes tab

When an edit proposal is prepared, LuaS30 creates a normal tool tab:

```text
AI Changes
```

The view contains:

```text
changed-file list
CURRENT pane
PROPOSED pane
line-change highlighting
+/- line statistics
Reject
Apply Code
```

In `Ask before changes`, the diff tab opens automatically. Auto-edit modes prepare the
same validated change set but can apply it without stealing editor focus.

## Apply and backup

Existing files are copied to:

```text
<project>/.luas30/ai-backups/<timestamp>/<relative path>
```

before atomic replacement. New files do not need a source backup.

After application LuaS30 refreshes open editors, the project index and Explorer tree, then
reports the applied files back to the agent so it can request validation through the shell
if needed.

## Shell integration

AI shell commands continue to use the same visible Integrated Terminal as the user. The
agent cannot execute a hidden second shell.

Captured command output is bounded and common secret-bearing environment values are
redacted before the result is sent back to a remote provider.

## Security boundaries

The user-access selector changes confirmation behavior, not the project sandbox:

- code edits stay project-relative;
- sensitive/dangerous shell commands still ask;
- provider API keys are never written into project files; optional local JSON persistence is explicit;
- raw chain-of-thought is not requested or displayed;
- project secret files remain excluded from automatic context scanning.

## Persistent chat sessions

ChatAI now maintains project-scoped sessions in:

```text
%APPDATA%/LuaS30IDE/config/ai_sessions.json
```

The header Sessions button can create, resume, rename, and delete conversations. The active
session is restored per project. Internal tool results are retained for model continuity but
are not rendered as user-visible chat messages after a resume. Supported local commands are:

```text
/new
/clear
/sessions
/resume
/continue
/rename <name>
/help
```

## OpenCode-inspired read-only agent tools

The first tool layer adds project-confined `read`, `grep`, and `glob` calls through the
`luas30-tool` protocol. These tools are read-only and are available even in Plan mode. They
reject project traversal and common secret/generated paths. Existing LuaS30 capabilities map
roughly to OpenCode's edit/write and bash tools through `luas30-edit` and `luas30-shell`.

Future-compatible extension points are documented for apply-patch, LSP, todos, skills, web
fetch/search, MCP integrations, subagents, and snapshot-based undo/redo.
