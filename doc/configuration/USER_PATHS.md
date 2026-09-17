# LuaS30 IDE 1.4.1 — User paths

LuaS30 keeps the engine installation separate from per-user data and projects.

## AppData

On Windows, `run.bat` and the Studio automatically create:

```text
%APPDATA%\LuaS30IDE\
├── config\
│   └── studio.ini
├── logs\
│   ├── launcher.log
│   └── environment.json
├── cache\
├── temp\
├── backups\
└── venv\
```

The Python virtual environment is stored in AppData rather than inside the
engine install directory. This allows the engine folder to remain effectively
read-only during normal use.

## Projects

Every project created with **New Project** is placed automatically under the
user's actual Windows Documents folder:

```text
Documents\LuaS30IDE\<project_name>\
```

Example:

```text
C:\Users\Hop\Documents\LuaS30IDE\MiniFarm\
```

The Studio resolves the Windows Documents folder rather than assuming a fixed
English path, so redirected Documents folders are supported.

The GUI now asks only for a project name. It no longer asks the user to choose
an arbitrary destination directory.

## Command-line project creation

```bat
new_project.bat MiniFarm
```

creates:

```text
Documents\LuaS30IDE\MiniFarm\
```

## Optional overrides

For portable or test environments these variables can override the defaults:

```text
LUAS30_APPDATA
LUAS30_DOCUMENTS
LUAS30_PROJECTS
```
