# AI Agent Activity and Shell Control 1.14.0

## Visible reasoning summary

ChatAI now contains a collapsible panel:

```text
AI ACTIVITY · REASONING SUMMARY
```

This panel is intentionally a **high-level reasoning/activity summary**, not the model's
private raw chain-of-thought. It can display:

```text
Context          tree/rules/source files loaded
Rules            SKILLS.md / SKILL.md / PROMPT.md used
Files            relevant code files selected
Reasoning summary concise plan/conclusion supplied by the model
Shell proposal   command + risk classification
Shell running    visible command sent to Terminal
Shell result     exit code + working directory
AI error         provider/tool errors
```

Provider prompts explicitly request a concise `luas30-summary` block and prohibit private
chain-of-thought disclosure.

## Shell control

ChatAI can request one shell command per turn using:

```text
```luas30-shell
{"command":"python tools/validate_x.py","cwd":"project","reason":"Run validation"}
```
```

The marker is removed from normal chat rendering and converted into a Shell Request card.

### Permission modes

```text
Disabled
Ask before running
Auto-run safe commands
```

`Ask before running` is the default. No provider can silently turn this into Auto mode.
The permission is intentionally not persisted across sessions.

`Auto-run safe commands` only auto-runs inspection-oriented commands. Commands classified
as project-mutating, sensitive or dangerous remain manual.

Examples of dangerous patterns include destructive delete/reset/format commands. A manual
Run click for a dangerous command requires a second confirmation dialog.

## Visible integrated Terminal

AI commands use the same `IntegratedTerminal` as the user:

```text
ChatAI -> Shell Request -> Compact Bottom Panel / TERMINAL
```

The Terminal emits command lifecycle signals:

```text
command_started(command, origin)
command_finished(command, exit_code, cwd, output, origin)
```

The origin is `ai` for agent-controlled commands, so normal user terminal activity is not
fed back into ChatAI automatically.

## Agent continuation

After a shell command finishes:

1. Terminal stays visible and contains the complete local output.
2. ChatAI receives a bounded copy of the result.
3. Common secret-bearing environment values are redacted from the copy sent to the model.
4. ChatAI automatically continues the original task.
5. The loop is limited to six model turns per user request.

This prevents unlimited self-triggering shell loops.

## Working directory boundary

`cwd="project"` runs in the current project root. Relative subdirectories are allowed.
If an AI response requests a working directory outside the project, LuaS30 ignores that
path and uses the project root instead.

The shell command itself is still a real user-shell command; therefore manual approval
remains important for mutating commands.
