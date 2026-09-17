# Compact Bottom Panel 1.10.1

The integrated panel is now treated as an on-demand editor surface.

## Default behavior

On every application startup/restart:

```text
Console / Build / Problems / Terminal = hidden
```

The active panel type and preferred height may be remembered, but visibility is not
restored automatically.

This keeps maximum vertical space available for source code.

## Terminal toggle

```text
Ctrl+`       Toggle Terminal
Ctrl+J       Toggle Panel
Ctrl+Shift+Y Toggle Console
```

If Terminal is hidden, `Ctrl+`` opens the panel and focuses Terminal.

If Terminal is already the active visible panel, the same shortcut hides it.

## Close button

A close button is displayed at the top-right corner of the bottom panel, matching the
interaction style of VS Code.

Closing the panel means hide/collapse only. It does not terminate the running shell.

Use `Terminal -> Kill Terminal` when the shell process itself should be stopped.

## Compact panel height

Default reveal height:

```text
145 px
```

Minimum practical height:

```text
72 px
```

The splitter is easier to grab and can resize the panel. The preferred height is remembered
between panel open/close operations and sessions, but the panel still starts hidden.

## Scrollbars

Vertical and horizontal scrollbars are reduced to:

```text
7 px
```

This applies to editor pages, Explorer, Project Hub lists, terminal output and other Qt
scroll areas that use the global Studio theme.

## Project Hub

Welcome and Project Hub continue to hide all editor-only chrome. Returning to source code
does not automatically open the bottom panel on a fresh application startup.
