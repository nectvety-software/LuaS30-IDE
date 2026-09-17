# AI Workbench 1.11.0

## Layout

```text
Activity | Explorer/Search | Editor Groups        | Chat AI
Bar      |                 |----------------------|
         |                 | Compact Bottom Panel |
```

The Compact Bottom Panel exists only below the center editor and never spans beneath
Explorer or ChatAI.

## Tab context menu

Right-click any source/tool tab:

```text
Close
Close Others
────────────
Close All Tabs
```

Close All Tabs reaches every editor group. Modified source files keep Save / Discard /
Cancel confirmation.

## Chat AI

Toggle ChatAI with:

```text
Ctrl+Alt+I
View -> Toggle Chat AI
Activity Bar -> Chat AI
Workbench layout icon -> Chat AI
```

Providers:

```text
OpenAI
Anthropic
Google Gemini
OpenAI Compatible
Ollama Local
```

Provider/model/base URL preferences are stored globally. API keys are never persisted.

Environment variables:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
LUAS30_AI_API_KEY
```

The provider drawer also accepts a session-only key.

## Codebase context

Automatic context reads:

```text
project directory tree
active editor
query-relevant source files
SKILLS.md
SKILL.md
PROMPT.md
engine doc/ai/SKILL.md
engine doc/ai/PROMPT.md
```

Instruction documents are separated from ordinary source context. Code files are reference
data, while SKILL(S)/PROMPT files are the agent instructions.

Excluded from AI context include common secrets (`.env`, credentials/secrets JSON,
private-key filenames) and generated/vendor-heavy folders such as build, release, venv,
node_modules and VCS directories.

Limits:

```text
tree              <= 450 entries
instruction docs  ~36K chars total
relevant sources  <= 8 files / ~50K chars
active editor     <= ~12K chars
chat history      latest 12 turns
```

## Provider transport

LuaS30 uses Python standard-library HTTP transport, so no additional AI SDK package is
required. OpenAI uses the Responses API; Anthropic uses Messages; Gemini uses
generateContent; OpenAI-compatible servers use `/chat/completions`; Ollama uses `/api/chat`.
