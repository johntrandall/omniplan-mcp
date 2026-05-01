"""Pure-Python smoke tests for the JXA helpers.

These do not need OmniPlan; they exercise the JSON-string escaping and the
envelope-parsing branches in `jxa.py`.
"""
from __future__ import annotations

import asyncio

import pytest

from omniplan_mcp.jxa import _escape, _friendly_error, run_omnijs


def test_escape_quotes_basic_strings() -> None:
    assert _escape("hello") == '"hello"'


def test_escape_handles_quotes_and_newlines() -> None:
    out = _escape('he said "hi"\n')
    # Round-trips through JSON, so the result is a valid JSON literal.
    import json

    assert json.loads(out) == 'he said "hi"\n'


def test_friendly_error_translates_not_running() -> None:
    msg = _friendly_error("Error: OmniPlan is not running.")
    assert "OmniPlan is not running" in msg


def test_friendly_error_translates_tcc_denial() -> None:
    msg = _friendly_error("Not authorized to send Apple events to OmniPlan. (-1743)")
    assert "Privacy & Security" in msg


def test_friendly_error_falls_through_for_unknown() -> None:
    msg = _friendly_error("some other osascript failure")
    assert "JXA error" in msg


def test_run_omnijs_raises_on_malformed_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_jxa(_script: str, timeout: float = 0) -> str:
        return "not-json"

    monkeypatch.setattr("omniplan_mcp.jxa.run_jxa", fake_run_jxa)

    with pytest.raises(RuntimeError, match="malformed JSON"):
        asyncio.run(run_omnijs("return 1"))


def test_run_omnijs_raises_on_error_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_jxa(_script: str, timeout: float = 0) -> str:
        return '{"ok": false, "error": "boom"}'

    monkeypatch.setattr("omniplan_mcp.jxa.run_jxa", fake_run_jxa)

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_omnijs("throw new Error('boom')"))


def test_run_omnijs_returns_data_on_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_jxa(_script: str, timeout: float = 0) -> str:
        return '{"ok": true, "data": [1, 2, 3]}'

    monkeypatch.setattr("omniplan_mcp.jxa.run_jxa", fake_run_jxa)

    assert asyncio.run(run_omnijs("return [1,2,3]")) == [1, 2, 3]
