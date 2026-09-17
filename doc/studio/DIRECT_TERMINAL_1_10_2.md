# Direct Terminal Input 1.10.2

LuaS30's integrated terminal now uses one terminal canvas for both shell output and command
entry.

## Before

Older releases used:

```text
terminal output
────────────────────────
small command textbox
```

This made the terminal behave like a log viewer plus form field rather than an IDE shell.

## 1.10.2

The terminal now behaves like:

```text
C:\...\project> dir
<output>

C:\...\project> python tools\build.py --project ...
<output>

C:\...\project> _
```

There is no separate `QLineEdit`.

## Editing boundary

Only text after the current prompt can be edited. Historical output can be selected and
copied but normal typing cannot overwrite it.

## Keyboard

```text
Enter       submit command
Up          previous history item
Down        next history item
Home        beginning of editable command
Ctrl+A      select editable command
Ctrl+V      paste
Ctrl+L      clear terminal
Ctrl+C      copy selected text; otherwise send ETX
```

## Command completion marker

LuaS30 keeps one persistent shell process. To know when a command has completed and to
refresh the working-directory prompt, it appends an internal completion marker after each
submitted command.

Windows:

```text
__LUAS30_DONE__:<errorlevel>:<current-directory>
```

POSIX:

```text
__LUAS30_DONE__:<status>:<current-directory>
```

The marker is consumed internally and is not shown to the user.

This also lets `cd` update the next prompt without restarting the shell.

## Terminal lifecycle

Hiding the bottom panel does not stop the shell. `Terminal -> Kill Terminal` still stops
the process explicitly.

Opening Terminal with `Ctrl+`` focuses the direct terminal surface immediately.
