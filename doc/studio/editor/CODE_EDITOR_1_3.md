# LuaS30 Studio 1.3 — IDE-level Code Editor

Studio 1.3 upgrades the v1.2 editor into an IDE-style Lua workspace while keeping the VXP runtime/build system separate from the desktop UI.

## Features

### Lua / `engine.*` autocomplete
- `Ctrl+Space` forces completion.
- Typing `engine.` or `mre.` opens LuaS30 native API completion.
- Lua 5.1 keywords and standard library functions are included.
- Symbols from the current document and indexed project are included.

### Find / Replace
- `Ctrl+F`: Find.
- `Ctrl+H`: Replace.
- `F3`: next match.
- `Shift+F3`: previous match.
- Case-sensitive and whole-word modes.
- All matches are highlighted without replacing the editor document.

### Minimap
- Every source tab has a low-overhead minimap.
- The viewport is shown as a blue overlay.
- Clicking the minimap jumps to that approximate source line.
- It paints from the existing document; it does not create a second syntax document.

### Inline Lua diagnostics
- 350 ms debounced analysis while typing.
- Red wave underline for unmatched `end`/`until`, brackets, unterminated strings and multiline comments.
- Error line numbers are tinted red.
- Errors appear in the bottom `Problems` tab.

The inline analyzer is intentionally lightweight and dependency-free. The VXP build remains the final Lua/compiler validation.

### Go to Definition
- `F12` or the toolbar button.
- Indexes Lua function definitions, assigned functions and local declarations across the project.
- Opens the target file and jumps to the definition line.

### Project-wide search
- `Ctrl+Shift+F` opens project search.
- Search supports `*.lua` or semicolon-separated patterns such as `*.lua;*.json`.
- Case-sensitive and whole-word options.
- Runs in a worker thread so large searches do not freeze the editor.
- Double-click a result to open its exact line.

### Console / Build Log
The lower pane contains Console, Build Log and Problems. `Build VXP` and `Run Emulator` use `QProcess` so stdout/stderr appears inside Studio instead of a detached console window.

## Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+N | New file |
| Ctrl+O | Open file |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+Alt+S | Save All |
| Ctrl+F | Find |
| Ctrl+H | Replace |
| F3 | Find next |
| Shift+F3 | Find previous |
| Ctrl+Shift+F | Search project |
| Ctrl+Space | Autocomplete |
| F12 | Go to Definition |

## Files added in 1.3

```text
studio/app/editor/
├── completion.py
├── diagnostics.py
├── editor_pane.py
├── find_replace.py
├── minimap.py
├── project_index.py
└── project_search.py

studio/app/widgets/
└── bottom_panel.py
```
