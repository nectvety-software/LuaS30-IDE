# Startup Screen Setting 1.9.8

LuaS30 Studio exposes one startup-screen preference under:

```text
Settings
└── Startup screen
```

Available values:

## Welcome

Opens the VS Code-style Welcome page first.

```text
Start
Recent
Project Storage summary
Workspace
Quick Start
```

## Project Hub

Opens the full managed-project screen first.

```text
Project search
New Project
Import
Open
Duplicate
Rename
Delete
Reveal
```

Internally this is the `projects` tool view. Its tab title is `Project Hub`.

## Empty Editor

Starts with the central editor workspace empty.

It does not open:

```text
source files
untitled files
Welcome
Project Hub
other restored tool tabs
main.lua
```

The current project, editor-group geometry, Explorer/Activity Bar preference and panel
layout may still be restored.

## Session format

The selected mode is stored in:

```json
{
  "startup": {
    "mode": "welcome",
    "restore_source_tabs": false
  }
}
```

Valid mode identifiers:

```text
welcome
project_hub
empty_editor
```

For backward compatibility, an older session containing only `show_start_page` is
migrated automatically:

```text
show_start_page = true  -> welcome
show_start_page = false -> empty_editor
```

## Source-file startup rule

All three modes preserve the 1.9.6 rule: application startup/restart never automatically
opens source or untitled documents.

## Single source of truth

The old Welcome-page checkbox was removed. Startup selection is controlled only from
Settings to avoid conflicting controls.
