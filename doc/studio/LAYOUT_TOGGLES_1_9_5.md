# Explorer and Activity Bar Toggles 1.9.5

LuaS30 Studio exposes persistent VS Code-like editor layout controls.

## Shortcuts

```text
Ctrl+B       Toggle Explorer / Primary Side Bar
Ctrl+Alt+A   Toggle Activity Bar
Ctrl+Shift+E Focus Explorer and make it visible
```

Two icon-only buttons are shown on the right side of the Workbench Bar. They execute the same QActions as the View menu and keyboard shortcuts.

## Welcome / Project Storage

Project Hub pages stay clean and physically hide Activity Bar and Explorer. That hiding is temporary and never overwrites user preferences. Returning to a source editor restores the prior state.

Explorer visibility is stored in `editor.sidebar.visible`. Activity Bar visibility is stored in `chrome.activity_bar_visible`.
