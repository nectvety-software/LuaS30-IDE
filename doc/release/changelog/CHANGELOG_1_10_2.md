# LuaS30 Engine 1.10.2 — Direct Integrated Terminal

- Removed the separate terminal command QLineEdit.
- Added `TerminalSurface`, a direct-edit QPlainTextEdit.
- Commands are typed directly after the cwd prompt.
- Protected terminal history from normal edits.
- Added Up/Down command history in the terminal surface.
- Added Home and Ctrl+A command-line navigation.
- Added Ctrl+L clear and Ctrl+C copy/ETX behavior.
- Added paste handling for the editable command region.
- Added internal command-completion marker handling.
- Prompt cwd updates after `cd`.
- Kept persistent shell behavior when the panel is hidden.
