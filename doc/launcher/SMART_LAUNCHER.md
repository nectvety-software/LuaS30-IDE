# LuaS30 IDE 1.4.2 — Smart Launcher

`run.bat` no longer runs `pip install --upgrade` on every launch.

## Normal startup

```bat
run.bat
```

The launcher reads `requirements-studio.txt` and checks the installed package
versions inside `%APPDATA%\LuaS30IDE\venv`.

- If every installed version already satisfies the declared range, **pip is not
  run and the launcher does not check the network**.
- If a package is missing or outside the supported range, auto mode tests for
  network access and updates only that required package.
- After an update the environment is checked again before Studio starts.

For the current requirement:

```text
PySide6>=6.7,<7
```

an installed PySide6 6.8.x or 6.9.x is accepted without reinstalling it.

## Offline mode

```bat
run.bat --offline
```

No dependency download is attempted. If the existing environment already meets
requirements, Studio starts normally. If a required package is missing or too
old/new, the launcher stops with a clear error instead of modifying the venv.

Auto mode also falls back to offline behavior when the network check fails.

## Other modes

```bat
run.bat --online
run.bat --deps-only
run.bat --force-deps
```

- `--online`: permit required downloads without the automatic connectivity probe.
- `--deps-only`: validate/update dependencies and exit without starting Studio.
- `--force-deps`: force `pip --upgrade` for declared requirements. This is mainly
  for repairing an environment; it is not used during ordinary startup.

## Logs

Persistent change history:

```text
%APPDATA%\LuaS30IDE\logs\dependency_changes.log
```

Current resolved dependency state:

```text
%APPDATA%\LuaS30IDE\config\dependency_state.json
```

General launcher log (now appended instead of overwritten):

```text
%APPDATA%\LuaS30IDE\logs\launcher.log
```

Only actual version changes are written as `INSTALLED` or `UPDATED` records in
the dependency change log. Failed update attempts and no-change repair attempts
are recorded separately.

## pip behavior

`ensurepip` runs only when the venv has no working pip installation. The launcher
no longer upgrades pip/setuptools/wheel on every start.
