# Welcome / Project Hub 1.9.2

LuaS30 Studio now starts with a VS Code-style Welcome page backed by Project Storage.

## Default startup

For a new/cold workspace:

```text
Welcome
├── Start
│   ├── New Project
│   ├── Open Project Folder
│   ├── Import into Project Storage
│   └── Manage Project Storage
├── Recent
│   └── managed projects sorted by modified time
├── Project Storage
│   ├── storage path
│   ├── project count
│   ├── total size
│   └── projects with a VXP build
└── Workspace
    └── current project context
```

The Welcome tab is created at tab index 0 in editor group 0.

## Session restore

Session restore is not removed. Studio restores project, editor groups, files, tool tabs
and panel state first. The default checkbox `Show Welcome page on startup` then activates
Welcome.

If the checkbox is disabled, the previously active group/tab remains active after restore.

This means users can choose between:

```text
VS Code-like startup landing page
or
exact previous active editor restoration
```

without losing the restored tabs/groups.

## Project Storage

The Welcome page is a landing hub, while the existing `Project Storage` tool tab remains
the full project-management surface for duplicate, rename, delete, reveal and detailed
table management.

Importing from Welcome copies a valid external LuaS30 project into the managed storage
root and opens the imported project.

## UI policy

Controls use LuaS30's system font-icon layer. No emoji controls or bundled font files are
used.


## Behavior override in 1.9.8

The `Show Welcome page on startup` checkbox was removed. Startup destination is now
configured only in Settings using Welcome, Project Hub or Empty Editor.

See `STARTUP_SCREEN_1_9_8.md`.
