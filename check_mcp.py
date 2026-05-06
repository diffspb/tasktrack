#!/usr/bin/env python3
"""
TaskTrack MCP server diagnostic tool.

Usage:
    python check_mcp.py                                    # localhost:8000, no auth
    python check_mcp.py --url https://tasktrack.busypage.ru/mcp/sse
    python check_mcp.py --url http://localhost:8000/mcp/sse --key my-secret-key
    python check_mcp.py --url http://localhost:8000/mcp/sse --call get_task --args '{"task_id":"..."}'
"""

import argparse
import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client


# ── ANSI colours ──────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
GREEN = "\033[32m"
CYAN  = "\033[36m"
YELLOW = "\033[33m"
RED   = "\033[31m"
BLUE  = "\033[34m"


def h1(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'━' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'━' * 60}{RESET}")


def h2(text: str) -> None:
    print(f"\n{BOLD}{BLUE}▸ {text}{RESET}")


def ok(text: str) -> None:
    print(f"  {GREEN}✓{RESET}  {text}")


def item(label: str, value: Any) -> None:
    val_str = json.dumps(value, ensure_ascii=False, indent=None) if not isinstance(value, str) else value
    print(f"  {DIM}│{RESET}  {BOLD}{label}{RESET}: {val_str}")


def warn(text: str) -> None:
    print(f"  {YELLOW}⚠{RESET}  {text}")


def err(text: str) -> None:
    print(f"  {RED}✗{RESET}  {text}", file=sys.stderr)


# ── Formatting helpers ─────────────────────────────────────────────────────────

def _fmt_tool(t) -> None:
    print(f"  {GREEN}•{RESET} {BOLD}{t.name}{RESET}")
    if t.description:
        lines = t.description.strip().splitlines()
        print(f"    {DIM}{lines[0]}{RESET}")
    props = getattr(t.inputSchema, "get", lambda k, d=None: None)("properties") or {}
    if isinstance(t.inputSchema, dict):
        props = t.inputSchema.get("properties", {})
    if props:
        params = ", ".join(
            f"{k}{'?' if k not in (t.inputSchema.get('required') or []) else ''}"
            for k in props
        )
        print(f"    {DIM}params: {params}{RESET}")


def _fmt_resource(r) -> None:
    print(f"  {GREEN}•{RESET} {BOLD}{r.uri}{RESET}")
    if getattr(r, "name", None):
        print(f"    {DIM}{r.name}{RESET}")


def _fmt_prompt(p) -> None:
    print(f"  {GREEN}•{RESET} {BOLD}{p.name}{RESET}")
    if getattr(p, "description", None):
        print(f"    {DIM}{p.description}{RESET}")


# ── Main ───────────────────────────────────────────────────────────────────────

async def run(url: str, api_key: str | None, call: str | None, call_args: dict) -> int:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    h1(f"TaskTrack MCP — {url}")
    print(f"  auth: {'Bearer ***' if api_key else 'none (dev mode)'}")

    try:
        async with sse_client(url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                ok("Connected and initialised")

                caps = session.get_server_capabilities()
                if caps:
                    item("server capabilities", {
                        "tools": caps.tools is not None,
                        "resources": caps.resources is not None,
                        "prompts": caps.prompts is not None,
                    })

                # ── list_tools ────────────────────────────────────────────────
                h2("list_tools")
                try:
                    result = await session.list_tools()
                    tools = result.tools
                    ok(f"{len(tools)} tool(s) registered")
                    for t in tools:
                        _fmt_tool(t)
                except Exception as e:
                    err(f"list_tools failed: {e}")

                # ── list_resources ────────────────────────────────────────────
                h2("list_resources")
                try:
                    result = await session.list_resources()
                    resources = result.resources
                    if resources:
                        ok(f"{len(resources)} resource(s)")
                        for r in resources:
                            _fmt_resource(r)
                    else:
                        warn("No resources registered")
                except Exception as e:
                    err(f"list_resources failed: {e}")

                # ── list_prompts ──────────────────────────────────────────────
                h2("list_prompts")
                try:
                    result = await session.list_prompts()
                    prompts = result.prompts
                    if prompts:
                        ok(f"{len(prompts)} prompt(s)")
                        for p in prompts:
                            _fmt_prompt(p)
                    else:
                        warn("No prompts registered")
                except Exception as e:
                    err(f"list_prompts failed: {e}")

                # ── optional tool call ────────────────────────────────────────
                if call:
                    h2(f"call_tool: {call}")
                    try:
                        result = await session.call_tool(call, call_args)
                        print(f"  isError: {result.isError}")
                        for content in result.content:
                            if hasattr(content, "text"):
                                try:
                                    parsed = json.loads(content.text)
                                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                                except json.JSONDecodeError:
                                    print(content.text)
                    except Exception as e:
                        err(f"call_tool failed: {e}")

    except Exception as e:
        err(f"Connection failed: {e}")
        print(file=sys.stderr)
        print(f"  Make sure the server is running and the URL is correct.", file=sys.stderr)
        print(f"  Start dev server:  cd backend && make dev", file=sys.stderr)
        return 1

    print(f"\n{GREEN}{BOLD}Done.{RESET}\n")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TaskTrack MCP server diagnostic tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000/mcp/sse",
        help="MCP SSE endpoint URL (default: http://localhost:8000/mcp/sse)",
    )
    parser.add_argument(
        "--key",
        metavar="API_KEY",
        default=None,
        help="Bearer API key (MCP_AGENTS mode); omit for dev mode",
    )
    parser.add_argument(
        "--call",
        metavar="TOOL_NAME",
        default=None,
        help="Optional: call a specific tool after the standard checks",
    )
    parser.add_argument(
        "--args",
        metavar="JSON",
        default="{}",
        help="JSON arguments for --call (default: {})",
    )
    args = parser.parse_args()

    try:
        call_args = json.loads(args.args)
    except json.JSONDecodeError as e:
        print(f"Error parsing --args: {e}", file=sys.stderr)
        sys.exit(1)

    exit_code = asyncio.run(run(args.url, args.key, args.call, call_args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
