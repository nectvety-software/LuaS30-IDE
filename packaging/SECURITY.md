# Packaging security notes

## MSI

- **Per-user install** under `%LOCALAPPDATA%\Programs\LuaS30 IDE` (no admin elevation).
- **Sourceless bytecode**: `studio/` and `tools/` ship as `.pyc` only (no plain `.py`).
- **Never packaged**: WiX binaries, `.env`, `*.pem` / `*.key`, `ai_credentials.json`, secret filenames, `.workbuddy-ai/`.
- **Secure property**: `AUTOLAUNCH` is marked `Secure="yes"` (not free-form from the UI).
- **Auto-launch** uses the hidden `LuaS30-IDE.vbs` launcher (argument characters `"` `&` `|` `<` `>` stripped).

## Runtime

- AI API keys are **Windows DPAPI**-encrypted when saved (`ai_credentials.json`).
- Config / venv / logs live in `%APPDATA%\LuaS30IDE`.
- Projects live in `Documents\LuaS30 Projects`.
- Launcher clears `PYTHONPATH` / `PYTHONHOME` / `PYTHONSTARTUP` before starting Python.

## What we do not claim

This is not code-signing with a commercial certificate, and DPAPI only protects keys for the same Windows user account.
