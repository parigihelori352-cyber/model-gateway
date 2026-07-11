# model-gateway

`model-gateway` is a small MCP server and command-line tool that routes named tasks to the language models you choose. Define a tool once in JSON, then use it from an MCP client or the terminal—without writing a separate Python integration for every task.

API keys are read from environment variables and are never stored in the repository.

## Quick start

Requirements: Python 3.10 or later and an API key for the provider you choose.

```bash
git clone https://github.com/parigihelori352-cyber/model-gateway.git
cd model-gateway
python -m pip install -e .
mg config init
```

`mg config init` creates `config.json` in the directory where you run it. It is ignored by Git, so it is safe to customize locally. The included starter configuration uses the OpenAI-compatible API:

```bash
# PowerShell
$env:OPENAI_API_KEY = "your-key"

# macOS / Linux
export OPENAI_API_KEY="your-key"
```

Then start the MCP server:

```bash
python -m model_gateway.mcp_server
```

For Claude Code, add this entry to your MCP settings. Replace the example path with the folder you cloned:

```json
{
  "mcpServers": {
    "model-gateway": {
      "command": "python",
      "args": ["-m", "model_gateway.mcp_server"],
      "cwd": "C:/path/to/model-gateway",
      "env": {
        "OPENAI_API_KEY": "your-key"
      }
    }
  }
}
```

Use forward slashes on Windows in this JSON. Alternatively, set `MODEL_GATEWAY_CONFIG` to an absolute path to use a configuration file stored elsewhere.

## Configuration

Start from [`config.example.json`](config.example.json). Each item in `capabilities` becomes an MCP tool at server startup.

```json
{
  "tool": "summarize_release_notes",
  "description": "Summarize release notes for a non-technical reader.",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "system_prompt": "Write a clear short summary for a non-technical reader.",
  "input_schema": {
    "type": "object",
    "properties": {
      "text": { "type": "string", "description": "Release notes to summarize." }
    },
    "required": ["text"]
  }
}
```

Providers must expose an OpenAI-compatible chat-completions API. The configuration supports OpenAI and OpenRouter out of the box; add another provider by setting its `base_url` and the name of its key environment variable. Do not put a real API key in `config.json`, examples, screenshots, or commits.

## Command line

The project includes task-oriented commands for configurations that define the matching capability names:

```bash
mg config path
mg config list
mg review path/to/file.py --focus security
mg review placeholder --stdin < path/to/file.py
```

For a custom configuration, use the dynamic MCP tools. The CLI command names `vision`, `plan`, `review`, `decide`, `workflow`, and `translate` require capabilities named `vision_ask`, `gpt_plan`, `gpt_review`, `gpt_decide`, `gpt_design_workflow`, and `gpt_translate` respectively.

## How paths are resolved

Configuration is located in this order: an explicit path supplied by code, `MODEL_GATEWAY_CONFIG`, `config.json` in the current working directory, then `config.json` in the editable project checkout. Run `mg config path` to see the file that will be used.

## Status and limitations

This is an early project. Model identifiers and provider-specific reasoning parameters vary by provider; verify those values in the provider's current documentation before relying on them in production. Keep the server process and its environment private because they contain access to your API keys.

## License

MIT
