# Clean Startup Tabs 1.9.6

LuaS30 Studio starts and restarts without automatically opening any source file.

## Startup behavior

The application can restore the current project and workspace layout, but source editor
documents are process-local.

```text
Application restart
      ↓
restore project
restore editor groups
restore tool tabs
restore Explorer / Activity Bar / panel state
      ↓
skip file tabs
skip untitled tabs
      ↓
open/focus Welcome
```

There is no automatic `main.lua` fallback.

## Session file

`workspace_session.json` continues to store workspace information, but v1.9.6 sanitizes
the editor-group tab list before writing it. Only tool tabs are retained for startup.

The startup section explicitly records:

```json
{
  "restore_source_tabs": false
}
```

Older session files that still contain `file` or `untitled` entries are safe: the restore
routine skips those entries, then the next session save rewrites the state without them.

## What remains persistent

```text
current project
group count and splitter sizes
tool tabs
active tool state
Explorer visibility
Activity Bar visibility
bottom panel visibility / active panel
window layout
Welcome startup preference
```

## Opening code

A file is opened only after an explicit user action such as:

```text
Explorer double-click
Search result
Open File
Go to Definition
project action that explicitly targets a file
```

Starting or restarting the IDE itself never opens a source document.
