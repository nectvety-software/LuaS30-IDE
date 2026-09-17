# LuaS30 Engine 1.14.0 — AI Agent Activity + Shell

- Added collapsible AI Activity / Reasoning Summary panel.
- Added explicit policy against raw/private chain-of-thought display.
- Added `luas30-summary` response protocol.
- Added `luas30-shell` JSON action protocol.
- Added Shell access modes: Disabled, Ask, Auto Safe.
- Added shell risk classification and destructive-command confirmation.
- Added project-scoped AI working-directory resolution.
- AI commands run in the same visible integrated Terminal.
- Added terminal command_started / command_finished lifecycle signals.
- Added AI command result capture and automatic agent continuation.
- Added six-turn agent loop limit.
- Added redaction/truncation of shell output before sending it back to AI providers.
- Shell permission remains session-only and is not persisted.
