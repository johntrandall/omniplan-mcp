"""Integration tests for effort/three-point-estimate fields on create/update.

Verified API surface (probed live against OmniPlan 4.10.2 on 2026-05-01):
  - `task.effort = N`               raw integer person-seconds
  - `task.minEffortEstimate = N`    same
  - `task.expectedEffortEstimate`   same
  - `task.maxEffortEstimate`        same

These properties read back as plain numbers, not Duration objects.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.tasks import create_task, update_task

pytestmark = pytest.mark.requires_omniplan


async def test_create_task_with_effort(test_root: str) -> None:
    raw = await create_task(
        title="__test__effort__create",
        parent_id=test_root,
        effort_seconds=14400,  # 4 hours
    )
    task = json.loads(raw)
    assert task["title"] == "__test__effort__create"
    assert task["effort_seconds"] == 14400


async def test_create_task_with_three_point_estimate(test_root: str) -> None:
    """Setting all three estimates causes OmniPlan to recompute effort via PERT.

    `effort = (min + 4*expected + max) / 6`. The explicit `effort_seconds`
    write is shadowed by the PERT calculation, which surfaces the underlying
    behaviour of the OmniPlan scheduling engine. Tools that want a literal
    effort value should not also pass three-point estimates.
    """
    min_s, expected_s, max_s = 7200, 14400, 28800
    raw = await create_task(
        title="__test__effort__three_point",
        parent_id=test_root,
        min_effort_seconds=min_s,
        expected_effort_seconds=expected_s,
        max_effort_seconds=max_s,
    )
    task = json.loads(raw)
    pert = (min_s + 4 * expected_s + max_s) // 6
    assert task["effort_seconds"] == pert  # 15600


async def test_update_task_changes_effort(test_root: str) -> None:
    raw = await create_task(
        title="__test__effort__update",
        parent_id=test_root,
        effort_seconds=3600,
    )
    task = json.loads(raw)
    assert task["effort_seconds"] == 3600

    raw2 = await update_task(task_id=task["id"], effort_seconds=7200)
    after = json.loads(raw2)
    assert after["effort_seconds"] == 7200


async def test_update_task_zero_effort(test_root: str) -> None:
    """Setting effort to 0 is allowed (e.g. for tasks held open as placeholders)."""
    raw = await create_task(
        title="__test__effort__zero",
        parent_id=test_root,
        effort_seconds=3600,
    )
    task = json.loads(raw)

    raw2 = await update_task(task_id=task["id"], effort_seconds=0)
    after = json.loads(raw2)
    assert after["effort_seconds"] == 0
