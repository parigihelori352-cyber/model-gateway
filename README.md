# model-gateway — Define MCP Tools in JSON, Not Python

**One MCP server, any model, any role. Add a new LLM-powered tool in 5 minutes by writing a JSON block — zero Python code.**

## Why

Every MCP server follows the same pattern: define a tool schema, write a handler, call an LLM, return the result. The only thing that changes between tools is the **system prompt, model, and input schema**. So why write Python for each one?

model-gateway separates the *what* from the *how*:

```
config.json  ←──  WHAT: providers, models, tools, system prompts (you edit this)
    │
    ▼
server.py    ←──  HOW: MCP protocol, API routing, multimodal encoding (never touch this)
    │
    ▼
Claude Code  ←──  sees N tools, each powered by a different model
```

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Set API keys (or put them in ~/.claude/settings.json → env)
export OPENROUTER_API_KEY="sk-or-v1-xxx"

# 3. Define a tool — add this to config.json → capabilities:
# {
#   "tool": "my_summarizer",
#   "description": "Summarize text concisely",
#   "provider": "openrouter",
#   "model": "openai/gpt-4o-mini",
#   "system_prompt": "Summarize the text. Output only the summary.",
#   "input_schema": {
#     "type": "object",
#     "properties": {
#       "text": { "type": "string", "description": "Text to summarize" }
#     },
#     "required": ["text"]
#   }
# }

# 4. Restart Claude Code — my_summarizer appears automatically.
```

## How It Works

### Providers (API backends)

Configure once in `config.json` → `providers`. Each provider knows its `base_url` and which env var holds the key:

| Provider | Env Var | Used for |
|----------|---------|----------|
| OpenRouter | `OPENROUTER_API_KEY` | GPT-5.4, Gemini, Claude… (any model on OpenRouter) |
| OpenAI | `OPENAI_API_KEY` | Direct GPT-4o access |
| Ark (Volcano) | `ARK_API_KEY` | Doubao vision models |

Add a new provider in one JSON block — no code needed.

### Tools (capabilities)

Every tool is a JSON object with:

| Field | Purpose |
|-------|---------|
| `tool` | MCP tool name (snake_case) |
| `description` | Shown to Claude Code |
| `provider` | Which provider to route through |
| `model` | Model ID (OpenRouter format, e.g. `openai/gpt-5.4`) |
| `system_prompt` | The role prompt — this IS the tool's behavior |
| `input_schema` | JSON Schema — defines what arguments the tool accepts |
| `accepts_images` | (optional) Enable multimodal image analysis |
| `reasoning` | (optional) Enable reasoning tokens + effort control |

### Example: Build a code reviewer in 1 minute

```json
{
  "tool": "code_reviewer",
  "description": "Review code for bugs and improvements",
  "provider": "openrouter",
  "model": "openai/gpt-5.4",
  "system_prompt": "You are a senior code reviewer. Find bugs, edge cases, and suggest improvements. Be specific — reference line numbers.",
  "reasoning": { "enabled": true, "default_effort": "medium" },
  "input_schema": {
    "type": "object",
    "properties": {
      "code": { "type": "string", "description": "Code to review" },
      "language": { "type": "string", "description": "Programming language" }
    },
    "required": ["code"]
  }
}
```

Restart Claude Code. Done. `code_reviewer` is now an MCP tool powered by GPT-5.4 with reasoning.

## Built-in Tools

These come pre-configured as examples — delete or modify them freely:

| Tool | Default Model | Purpose |
|------|---------------|---------|
| `vision_ask` | Doubao Seed 2.1 Pro | Multimodal image analysis |
| `gpt_plan` | GPT-5.4 | Architecture & implementation planning |
| `gpt_review` | GPT-5.4 | Deep code review (security/correctness/architecture) |
| `gpt_decide` | GPT-5.4 | Multi-option trade-off analysis |
| `gpt_design_workflow` | GPT-5.4 | Claude Code Workflow script generation |
| `gpt_translate` | Gemini 2.5 Flash | High-quality translation |

## CLI

All tools are also available from the command line:

```bash
# Vision analysis
mg vision photo.jpg "Describe this image in detail"

# Architecture planning (GPT-5.4 + reasoning)
mg plan "Design a microservice saga pattern" --budget high

# Deep code review
mg review auth.py --focus security

# Trade-off analysis
mg decide "Redis Cluster" "Sentinel" "Cloud managed" --criteria "perf,cost,ops"

# Workflow script generation
mg workflow "Migrate auth to JWT with zero downtime" --quality exhaustive

# Translation
mg translate "Hello world" Chinese
```

## Claude Code Integration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "model-gateway": {
      "command": "python",
      "args": ["-m", "model_gateway.mcp_server"],
      "cwd": "/path/to/model-gateway"
    }
  }
}
```

## Security

- **No API keys in config.** All keys come from environment variables. `config.json` only stores `api_key_env` references.
- **`.gitignore` excludes `config.json`** — your tool definitions stay local.
- **`save()` strips keys.** The config manager writes only `api_key_env` references, never resolved keys.

## Design Philosophy

- **Config is the API.** The shape of a tool IS its definition. No indirection.
- **No code for new tools.** If you can write a system prompt, you can build an MCP tool.
- **Zero overhead.** The framework does nothing but route and serialize. Your prompts do the work.
- **Vendor freedom.** Swap between OpenRouter, OpenAI, Ark, or your own provider — tools stay identical.

## License

MIT
