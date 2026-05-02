"""Coverage gap closed (verifier #2 finding 2026-05-02): the previous
suite only exercised `update_task` for `effort_seconds`, `manual_start_date`,
and the four constraint dates. This file adds round-trip coverage for
the remaining fields: title, note, completed (toggle and inverse),
and the three-point estimates on UPDATE (not just create).

Each test creates a task, updates one field, reads back via get_task,
asserts the field round-tripped. Catches the bug class where
update_task echoes the input dict without actually writing.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.tasks import create_task, get_task, update_task

pytestmark = pytest.mark.requires_omniplan


async def test_update_task_title_round_trips(test_root: str) -> None:
    raw = await create_task(title="__test__upd_title_orig", parent_id=test_root)
    task = json.loads(raw)
    new_title = "__test__upd_title_renamed"

    await update_task(task_id=task["id"], title=new_title)

    fresh = json.loads(await get_task(task_id=task["id"]))
    assert fresh["title"] == new_title


async def test_update_task_note_round_trips(test_root: str) -> None:
    raw = await create_task(title="__test__upd_note", parent_id=test_root, note="initial")
    task = json.loads(raw)

    await update_task(task_id=task["id"], note="rewritten note text")

    fresh = json.loads(await get_task(task_id=task["id"]))
    assert fresh["note"] == "rewritten note text"


async def test_update_task_completion_toggles(test_root: str) -> None:
    """Completion is `effortDone >= effort && effort > 0` in this MCP.
    Setting completed=True on a non-zero effort task fills effortDone;
    completed=False resets effortDone. Round-trip both transitions.
    """
    raw = await create_task(
        title="__test__upd_completion", parent_id=test_root, effort_seconds=3600
    )
    task = json.loads(raw)
    initial = json.loads(await get_task(task_id=task["id"]))
    assert initial["completed"] is False, "fresh task should start incomplete"

    await update_task(task_id=task["id"], completed=True)
    after_complete = json.loads(await get_task(task_id=task["id"]))
    assert after_complete["completed"] is True
    assert after_complete["effort_done_seconds"] == 3600
    assert after_complete["completion_pct"] == 100

    await update_task(task_id=task["id"], completed=False)
    after_uncomplete = json.loads(await get_task(task_id=task["id"]))
    assert after_uncomplete["completed"] is False
    assert after_uncomplete["effort_done_seconds"] == 0
    assert after_uncomplete["completion_pct"] == 0


async def test_update_task_three_point_estimate_on_update(test_root: str) -> None:
    """Three-point estimates (min/expected/max) are settable on UPDATE,
    not just on create. PERT recomputes effort = (min + 4*expected + max) / 6.
    """
    raw = await create_task(
        title="__test__upd_3point", parent_id=test_root, effort_seconds=7200
    )
    task = json.loads(raw)

    # Apply 3-point estimate via update.
    await update_task(
        task_id=task["id"],
        min_effort_seconds=3600,
        expected_effort_seconds=7200,
        max_effort_seconds=21600,
    )

    fresh = json.loads(await get_task(task_id=task["id"]))
    expected_pert = (3600 + 4 * 7200 + 21600) // 6  # 9000
    assert fresh["effort_seconds"] == expected_pert, (
        f"PERT recompute: expected effort=(min + 4*expected + max)/6={expected_pert}, "
        f"got {fresh['effort_seconds']}. Either update_task didn't write the 3-point "
        f"fields, or OmniPlan stopped doing PERT recompute."
    )
