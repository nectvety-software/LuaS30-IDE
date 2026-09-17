# LuaS30 Engine 1.15.0 — AI Workbench v1

- Added AI access selector under the ChatAI prompt.
- Added Ask before changes, Edit automatically, Plan mode and Full access modes.
- Kept sensitive/dangerous shell commands confirmation-gated in Full access.
- Replaced inline provider drawer with a custom AI Provider Settings dialog.
- Added Test Connection, Apply and Save & Close provider actions.
- Added persisted non-secret provider feature toggles.
- Kept provider API keys session-only and non-persistent.
- Added `luas30-edit` model action protocol.
- Added project-root and secret-path validation for AI code changes.
- Added exact find/replace and full-file edit actions.
- Added VS Code-style AI Changes review tab with current/proposed panes.
- Added Apply Code and Reject controls.
- Added atomic file replacement and `.luas30/ai-backups` backups.
- Added automatic open-editor/project-index/Explorer refresh after AI edits.
- Expanded activity trace with code proposal/apply/reject events.
- Increased bounded agent continuation loop to eight turns.
