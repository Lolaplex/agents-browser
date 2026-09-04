#!/usr/bin/env python3
"""Run all unit tests for agents-browser."""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from tests.test_unit import (
    test_merge_mcp_server_into_file,
    test_merge_zed_settings,
    test_find_browser_executable,
    test_cdp_client_default_headless,
    test_mcp_tools_registered,
)


class TestAgentsBrowser(unittest.TestCase):
    def test_sync_mcp(self):
        test_merge_mcp_server_into_file()

    def test_sync_zed(self):
        test_merge_zed_settings()

    def test_browser_executable_discovery(self):
        test_find_browser_executable()

    def test_headless_default(self):
        test_cdp_client_default_headless()

    def test_mcp_tools(self):
        test_mcp_tools_registered()

    def test_cli_version(self):
        from agents_browser.__main__ import main
        from agents_browser import __version__
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            try:
                main(["--version"])
            except SystemExit:
                pass
        out = f.getvalue()
        self.assertIn(__version__, out)


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAgentsBrowser)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    sys.exit(0 if res.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
