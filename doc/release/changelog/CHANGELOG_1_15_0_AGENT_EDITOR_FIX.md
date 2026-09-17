# LuaS30 Engine 1.15.0 — AI Agent Editor Apply Fix

## Fixed

- AI providers that ignore the `luas30-edit` protocol and return a normal fenced source block can now be recovered into an edit proposal for the active project file.
- Generated source no longer has to remain only in the Chat transcript when the request clearly asks to create, fix, update, refactor, or otherwise modify code.
- `Ask before changes` keeps the recovered edit pending for review/apply.
- `Edit automatically` and `Full access` continue through the existing automatic apply pipeline, writing the project file and refreshing any open editor buffer.
- Explanation/review prompts are excluded from fallback recovery to avoid accidental file replacement.
- Tiny unrelated snippets are not treated as full-file replacements.

## Safety

- The existing project-root path restrictions, sensitive-file blocking, atomic writes, and `.luas30/ai-backups` backups remain in effect.
- Structured `luas30-edit` actions always take precedence over the compatibility fallback.
