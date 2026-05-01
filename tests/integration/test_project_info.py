"""Integration tests for `get_project_info` and `update_project`.

Verified omniJS surface (probed live 2026-05-01, OmniPlan 4.10.2):
  - `document.project.actual.startDate`  writable, persistent
  - `document.project.actual.endDate`    read-only (computed from tasks)
  - `document.name`                      read-only document name
  - SDEF JXA `documents()[0].path()`     for the file path

omniJS surface gaps treated as known-not-supported:
  - `proj.scenarios` and `proj.baselines` undefined — the response only
    advertises `["Actual"]`.
  - `actual.currency` writes don't persist across JXA boundaries —
    omitted from both read and write shape.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.documents import get_project_info, update_project

pytestmark = pytest.mark.requires_omniplan


async def test_get_project_info_shape() -> None:
    info = json.loads(await get_project_info())
    assert isinstance(info["name"], str) and info["name"]
    # path may be None for an untitled doc
    assert "path" in info
    assert info["scenarios"] == ["Actual"]
    # dates may legitimately be None on an empty doc; just verify the keys
    # are present and the value is None or a YYYY-MM-DD string.
    for key in ("start_date", "end_date"):
        assert key in info
        if info[key] is not None:
            assert len(info[key]) == 10 and info[key][4] == "-" and info[key][7] == "-"


async def test_update_project_start_date_persists() -> None:
    original = json.loads(await get_project_info())["start_date"]
    target = "2027-03-15"
    try:
        after = json.loads(await update_project(start_date=target))
        assert after["start_date"] == target
        # Cross-call read confirms persistence.
        fresh = json.loads(await get_project_info())
        assert fresh["start_date"] == target
    finally:
        if original is not None:
            await update_project(start_date=original)


async def test_update_project_rejects_empty_clear() -> None:
    with pytest.raises(ValueError, match="cannot be cleared"):
        await update_project(start_date="")


async def test_update_project_no_args_raises() -> None:
    with pytest.raises(ValueError, match="nothing to update"):
        await update_project()
