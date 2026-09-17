# Integrated Terminal and Console 1.9.3

LuaS30 Studio exposes the bottom panel in the same interaction style as VS Code:

```text
CONSOLE | BUILD | PROBLEMS | TERMINAL
```

## Shortcuts

```text
Ctrl+J        Toggle the complete bottom panel
Ctrl+Shift+Y  Toggle Console
Ctrl+`        Toggle Terminal
Ctrl+Shift+`  Start a new Terminal session
```

Selecting Console or Terminal while it is already the visible active panel hides the
bottom panel. Selecting it while another panel is active switches to it and keeps the
panel visible.

## Console

Console is the read-only LuaS30 Studio/runtime log. Existing Studio status messages,
emulator output and compatibility-tool output continue to use this surface.

The previous `output` object name remains as a source-level compatibility alias, so
existing Studio integrations do not break.

## Terminal

Terminal is backed by a real `QProcess` shell, not a simulated command box.

On Windows:

```text
%COMSPEC% /Q /K
```

is used, falling back to `cmd.exe`.

On non-Windows development hosts the current `SHELL` is used.

A newly-created shell uses the current LuaS30 project as its working directory and gets:

```text
LUAS30_ENGINE=1
LUAS30_PROJECT_ROOT=<current project>
```

Terminal supports command history with Up/Down, New, Kill and Clear.

## Workspace restore

The session stores:

```json
{
  "panel": {
    "visible": true,
    "active_key": "terminal",
    "active_index": 3,
    "vertical_sizes": [700, 220]
  }
}
```

`active_key` is preferred over numeric index so future panel-tab reordering does not
break restore. Older sessions containing only `active_index` are still accepted.

The Terminal process itself is not serialized. When a restored session has Terminal as
the visible active panel, LuaS30 starts a fresh shell in the current project directory.

## Startup behavior

The bottom panel is hidden for a new workspace, matching VS Code's default clean editor
layout. Build/run actions still open the panel automatically when output is needed.
