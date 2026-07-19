#!/usr/bin/env python3
"""Start each project MCP over stdio and verify initialize/tools-list."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
SERVERS = {
    "edgartools": ROOT / "scripts" / "mcp" / "edgartools.sh",
    "arxiv": ROOT / "scripts" / "mcp" / "arxiv.sh",
}


async def inspect_server(name: str, timeout: float) -> dict[str, object]:
    params = StdioServerParameters(
        command="/bin/bash",
        args=[str(SERVERS[name])],
        cwd=str(ROOT),
        env=dict(os.environ),
    )

    async def run() -> dict[str, object]:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                initialize = await session.initialize()
                tools = await session.list_tools()
                return {
                    "server": name,
                    "protocol_version": initialize.protocolVersion,
                    "server_name": initialize.serverInfo.name,
                    "server_version": initialize.serverInfo.version,
                    "tools": [tool.name for tool in tools.tools],
                }

    return await asyncio.wait_for(run(), timeout=timeout)


async def async_main(names: list[str], timeout: float) -> int:
    results = []
    for name in names:
        try:
            results.append(await inspect_server(name, timeout))
        except Exception as exc:  # pragma: no cover - diagnostic entry point
            results.append(
                {
                    "server": name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if any("error" in result for result in results) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "servers",
        nargs="*",
        choices=sorted(SERVERS),
        default=None,
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)
    if not args.servers:
        args.servers = sorted(SERVERS)
    return args


def main() -> int:
    args = parse_args()
    return asyncio.run(async_main(args.servers, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
