"""Isolate the agent host per test so suites stay deterministic on
machines with several workspaces. Tests set their own env where needed."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_host(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTS_HOST_DIR", str(tmp_path / "host"))
    monkeypatch.delenv("AGENTS_WORKSPACE", raising=False)
