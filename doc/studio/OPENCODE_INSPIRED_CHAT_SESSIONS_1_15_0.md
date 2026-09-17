# OpenCode-inspired Chat Sessions & Tools — LuaS30 IDE 1.15.0

This update borrows workflow ideas from OpenCode without embedding or depending on OpenCode.

## Implemented now

- persistent project-scoped chat sessions;
- New / Sessions / Resume / Rename / Delete session UI;
- `/new`, `/sessions`, `/resume`, `/continue`, `/rename`, `/help` commands;
- optional API-key persistence in a dedicated local JSON store;
- read-only agent tools: `read`, `grep`, `glob`;
- existing structured `edit/write` flow through `luas30-edit`;
- existing visible terminal flow through `luas30-shell`;
- Ask / Edit automatically / Plan / Full access permission presets;
- atomic code writes and per-change backups.

## Edit automatically flow

```text
AI response
  -> parse luas30-edit
  -> AIChangeService.prepare()
  -> validate project-relative target and protected paths
  -> create PreparedChangeSet
  -> auto_apply=true
  -> CodeEditorView._apply_ai_changes()
  -> backup existing file
  -> atomic os.replace()
  -> update the already-open editor buffer
  -> refresh project index + Explorer
  -> return apply result to the agent
```

## Ask / Apply Code flow

```text
AI response
  -> parse luas30-edit
  -> prepare only (disk remains unchanged)
  -> CODE CHANGES card: Preparing...
  -> validated change set ready
  -> Review Changes / Apply Code enabled
  -> user presses Apply Code
  -> same atomic apply path as Edit automatically
```

The Apply button is intentionally disabled before successful preparation so a malformed or
unsafe proposal cannot race ahead of validation.

## Local JSON files

```text
%APPDATA%/LuaS30IDE/config/ai_providers.json
%APPDATA%/LuaS30IDE/config/ai_credentials.json
%APPDATA%/LuaS30IDE/config/ai_sessions.json
```

`ai_credentials.json` is plaintext local storage by explicit user choice and is never stored
inside the active project.

## Next OpenCode-inspired candidates

Good next additions, in order:

1. snapshot-based `/undo` and `/redo` that revert both chat turns and file changes;
2. `apply_patch` tool for multi-file diffs;
3. session fork and compact/summarize;
4. TODO/task tool with a visible task list;
5. LSP tool for definitions/references/hover/symbols;
6. configurable skills and custom commands;
7. MCP tool adapters;
8. web fetch/search permissions;
9. specialized subagents (build, plan, review, explore).
