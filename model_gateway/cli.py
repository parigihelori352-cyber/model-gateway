"""CLI entry point — unified command-line interface for all capabilities"""
import argparse
import json
import sys
from pathlib import Path

from .config import load, save, get_capability
from .client import ModelGatewayClient


def _make_client_and_cap(tool_name: str) -> tuple[ModelGatewayClient, dict]:
    """Create client and find capability by tool name."""
    cfg = load()
    cap = get_capability(cfg, tool_name)
    if not cap:
        print(f"Error: capability '{tool_name}' not found in config.json", file=sys.stderr)
        sys.exit(1)
    return ModelGatewayClient(cfg), cap


def _print_result(result: dict, json_mode: bool):
    """Print result in text or JSON format."""
    if json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["text"])


def _run_tool(tool_name: str, args: argparse.Namespace):
    """Generic tool runner — converts argparse args to dict, calls client."""
    client, cap = _make_client_and_cap(tool_name)

    # Build arguments dict from argparse namespace, excluding None values
    arguments = {}
    for key, value in vars(args).items():
        if value is not None and key not in ("command", "json", "stdin"):
            arguments[key] = value

    result = client.call(cap, arguments)
    _print_result(result, args.json)


# ── Subcommand handlers ─────────────────────────────────────────────────────

def cmd_vision(args):
    _run_tool("vision_ask", args)


def cmd_plan(args):
    _run_tool("gpt_plan", args)


def cmd_review(args):
    # If argument is a file path, read it
    if not getattr(args, 'stdin', False):
        path = Path(args.code)
        if path.exists() and path.is_file():
            args.code = path.read_text(encoding="utf-8")
    _run_tool("gpt_review", args)


def cmd_decide(args):
    # Normalize: criteria may come as list or comma-separated string
    if args.criteria and len(args.criteria) == 1 and "," in args.criteria[0]:
        args.criteria = [c.strip() for c in args.criteria[0].split(",")]
    _run_tool("gpt_decide", args)


def cmd_workflow(args):
    _run_tool("gpt_design_workflow", args)


def cmd_translate(args):
    _run_tool("gpt_translate", args)


def cmd_config(args):
    """Config management."""
    cfg = load()
    if args.action == "list":
        safe = {k: v for k, v in cfg.items() if k != "providers"}
        # Show providers without keys
        safe["providers"] = {
            name: {"base_url": p.get("base_url", ""), "api_key_env": p.get("api_key_env", "")}
            for name, p in cfg.get("providers", {}).items()
        }
        print(json.dumps(safe, indent=2, ensure_ascii=False))
    elif args.action == "get":
        val = cfg.get(args.key, "(not set)")
        print(val)
    elif args.action == "set":
        cfg[args.key] = args.value
        save(cfg)
        print(f"Set {args.key} = {args.value}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="mg",
        description="Model Gateway — config-driven multi-model CLI & MCP Server",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # === vision ===
    v = subparsers.add_parser("vision", help="Analyze images with a vision model")
    v.add_argument("images", nargs="*", default=[], help="Image paths or URLs")
    v.add_argument("prompt", help="Question about the image(s)")
    v.add_argument("-p", "--provider", default=None, help="Provider override (ark, openrouter)")
    v.add_argument("-m", "--model", default=None, help="Model override")
    v.add_argument("--max-tokens", type=int, default=None)
    v.add_argument("--json", action="store_true")

    # === plan ===
    p = subparsers.add_parser("plan", help="Design an implementation plan")
    p.add_argument("task", help="Task description")
    p.add_argument("-c", "--context", default=None, help="Project background")
    p.add_argument("-b", "--budget", default="medium", choices=["low", "medium", "high"])
    p.add_argument("-r", "--reasoning-effort", default="medium", choices=["low", "medium", "high"])
    p.add_argument("--provider", default=None)
    p.add_argument("-m", "--model", default=None)
    p.add_argument("--json", action="store_true")

    # === review ===
    r = subparsers.add_parser("review", help="Deep code review")
    r.add_argument("code", help="Code to review, or a file path")
    r.add_argument("-f", "--focus", default="general",
                   choices=["security", "correctness", "architecture", "general"])
    r.add_argument("-r", "--reasoning-effort", default="medium", choices=["low", "medium", "high"])
    r.add_argument("--provider", default=None)
    r.add_argument("-m", "--model", default=None)
    r.add_argument("--stdin", action="store_true", help="Read code from stdin")
    r.add_argument("--json", action="store_true")

    # === decide ===
    d = subparsers.add_parser("decide", help="Multi-option trade-off analysis")
    d.add_argument("options", nargs="+", help="Option descriptions (at least 2)")
    d.add_argument("--criteria", nargs="*", default=None, help="Evaluation dimensions")
    d.add_argument("--constraints", default=None, help="Additional constraints")
    d.add_argument("-r", "--reasoning-effort", default="medium", choices=["low", "medium", "high"])
    d.add_argument("--provider", default=None)
    d.add_argument("-m", "--model", default=None)
    d.add_argument("--json", action="store_true")

    # === workflow ===
    w = subparsers.add_parser("workflow", help="Design a Claude Code workflow script")
    w.add_argument("task_description", help="Full task description to orchestrate")
    w.add_argument("-f", "--files-involved", nargs="*", default=None, help="Files/dirs involved")
    w.add_argument("-q", "--quality-requirement", default="standard",
                   choices=["quick", "standard", "exhaustive"])
    w.add_argument("-r", "--reasoning-effort", default="high", choices=["low", "medium", "high"])
    w.add_argument("--provider", default=None)
    w.add_argument("-m", "--model", default=None)
    w.add_argument("--json", action="store_true")

    # === translate ===
    t = subparsers.add_parser("translate", help="Translate text between languages")
    t.add_argument("text", help="Text to translate")
    t.add_argument("target_lang", help="Target language, e.g. Chinese, English")
    t.add_argument("-s", "--source-lang", default=None, help="Source language (auto-detect)")
    t.add_argument("--provider", default=None)
    t.add_argument("-m", "--model", default=None)
    t.add_argument("--json", action="store_true")

    # === config ===
    c = subparsers.add_parser("config", help="Manage configuration")
    c.add_argument("action", choices=["list", "get", "set"])
    c.add_argument("key", nargs="?", default=None)
    c.add_argument("value", nargs="?", default=None)

    args = parser.parse_args()

    handlers = {
        "vision": cmd_vision,
        "plan": cmd_plan,
        "review": cmd_review,
        "decide": cmd_decide,
        "workflow": cmd_workflow,
        "translate": cmd_translate,
        "config": cmd_config,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
