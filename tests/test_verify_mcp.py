from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_mcp  # noqa: E402


class VerifyMcpArgumentTests(unittest.TestCase):
    def test_no_server_arguments_selects_every_server(self) -> None:
        self.assertTrue(
            hasattr(verify_mcp, "parse_args"),
            "verify_mcp must expose a testable argument parser",
        )
        args = verify_mcp.parse_args([])
        self.assertEqual(args.servers, ["arxiv", "edgartools"])


if __name__ == "__main__":
    unittest.main()
