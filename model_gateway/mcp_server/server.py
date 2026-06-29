"""Model Gateway MCP Server — dynamic tool registration from config.json

All tools are defined in config.json under "capabilities". This server
reads them at startup and registers each as an MCP tool automatically.
To add a new tool, add a capability block to config.json — no Python code needed.

Security: API keys via env vars (ARK_API_KEY, OPENROUTER_API_KEY, etc.), never in config.
"""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Ensure the parent package is importable
for candidate in [
    Path(__file__).resolve().parent.parent.parent,
    Path(__file__).resolve().parent.parent,
]:
    _s = str(candidate)
    if _s not in sys.path:
        sys.path.insert(0, _s)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print(
        "ERROR: mcp Python SDK not installed.\n"
        "Run: pip install mcp",
        file=sys.stderr,
    )
    sys.exit(1)

from model_gateway.config import load as load_config, get_capability
from model_gateway.core import is_url, is_data_url, MIME_MAP
from model_gateway.client import ModelGatewayClient


# ── Thread pool ────────────────────────────────────────────────────────────
_executor = ThreadPoolExecutor(max_workers=3)


def _validate_image_args(capability: dict, arguments: dict) -> str | None:
    """Validate image arguments. Returns error message or None."""
    if not capability.get("accepts_images"):
        return None

    images = arguments.get("images", [])
    if not images:
        return "At least one image is required."

    for img in images:
        if is_url(img) or is_data_url(img):
            continue
        p = Path(img)
        if not p.exists():
            return f"Image not found: {img}"
        if not p.is_file():
            return f"Not a file: {img}"
        ext = p.suffix.lower()
        if ext not in MIME_MAP and ext:
            return f"Unsupported format: {ext}. Supported: {', '.join(MIME_MAP.keys())}"

    return None


def _format_usage(result: dict) -> str:
    """Format usage info with reasoning tokens if present."""
    usage = result.get("usage", {})
    parts = [
        f"**Model:** {result.get('model', '?')}",
        f"**Tokens:** {usage.get('total_tokens', '?')} total "
        f"({usage.get('prompt_tokens', '?')} prompt + "
        f"{usage.get('completion_tokens', '?')} completion)",
    ]
    if usage.get("reasoning_tokens"):
        parts.append(f"**Reasoning:** {usage['reasoning_tokens']} tokens")
    return " | ".join(parts)


# ── MCP Server ─────────────────────────────────────────────────────────────

class DynamicModelGateway:
    """MCP Server that reads tool definitions from config at startup."""

    def __init__(self, config: dict):
        self.cfg = config
        self.server = Server(config.get("server_name", "model-gateway"))
        self._tools: list[Tool] = []
        self._build()

    def _build(self):
        """Build tool list from config capabilities."""
        for cap in self.cfg.get("capabilities", []):
            schema = cap.get("input_schema", {})
            tool = Tool(
                name=cap["tool"],
                description=cap.get("description", ""),
                inputSchema=schema,
            )
            self._tools.append(tool)

        @self.server.list_tools()
        async def list_tools():
            return self._tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return await self._handle(name, arguments)

    async def _handle(self, name: str, arguments: dict) -> list[TextContent]:
        """Generic tool handler — routes by capability name."""
        cap = get_capability(self.cfg, name)
        if not cap:
            raise ValueError(f"Unknown tool: {name}")

        # Validate required fields from input_schema
        required = cap.get("input_schema", {}).get("required", [])
        for field in required:
            if field not in arguments or not arguments[field]:
                return [TextContent(
                    type="text",
                    text=f"Error: '{field}' is required for {name}."
                )]

        # Validate images if applicable
        img_error = _validate_image_args(cap, arguments)
        if img_error:
            return [TextContent(type="text", text=f"Error: {img_error}")]

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                _executor,
                _run_sync,
                self.cfg,
                cap,
                arguments,
            )
        except Exception as e:
            return [TextContent(type="text", text=f"API error: {e}")]

        output = result["text"]
        usage = result.get("usage", {})
        if usage:
            output += f"\n\n---\n{_format_usage(result)}"

        return [TextContent(type="text", text=output)]

    async def run(self):
        """Run the MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def _run_sync(config: dict, capability: dict, arguments: dict) -> dict:
    """Synchronous call wrapper for the thread pool."""
    client = ModelGatewayClient(config)
    return client.call(capability, arguments)


# ── Entry Point ─────────────────────────────────────────────────────────────

def main():
    """Entry point for `python -m model_gateway.mcp_server`."""
    cfg = load_config()

    gateway = DynamicModelGateway(cfg)

    try:
        asyncio.run(gateway.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal MCP server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
