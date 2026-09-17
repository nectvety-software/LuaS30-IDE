# Project Hub Clean Layout 1.9.4

LuaS30 Studio separates project-management pages from source-editor chrome.

## Project Hub pages

These tabs use clean full-width mode:

```text
Welcome
Project Storage
```

When one of these tabs is active, Studio hides:

```text
Activity Bar
Explorer / Search sidebar
Find / Replace bar
Bottom Panel
  Console
  Build
  Problems
  Terminal
```

The Menu Bar, Workbench Bar, editor tab strip and Status Bar remain visible.

## Returning to editing

Opening or selecting a source editor exits Project Hub mode and restores the user's
previous editor layout.

For example:

```text
Editor state before Welcome:
Explorer = visible
Bottom Panel = visible / Terminal

Open Welcome:
Explorer = hidden
Bottom Panel = hidden
Activity Bar = hidden

Return to main.lua:
Explorer = visible
Bottom Panel = visible / Terminal
```

If the editor panel was hidden before entering Welcome, it remains hidden after return.

## Session behavior

Project Hub hiding is presentation-only. It must not overwrite:

```text
sidebar.visible
panel.visible
panel.active_key
splitter sizes
```

in the saved editor session.

This prevents opening/closing Studio on Welcome from permanently changing the layout of
the code editor.
