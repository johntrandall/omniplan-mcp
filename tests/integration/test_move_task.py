"""Integration tests for move_task — the omniJS task-reparent tool.

History:

  - 2026-05-01: Initial probe (OmniPlan 4.10.2, build 232.5.0) found no
    omniJS path to reparent a task; filed OG ticket #3107771.
  - 2026-05-06: Ken Case (Omni) replied that `parent` accessor and
    `move` method were added to both Task and Resource for the next
    release. Beta posted at <https://omnistaging.omnigroup.com/omniplan/>.
  - 2026-05-07: Verified the `task.move(newParent, index)` signature
    against OmniPlan 4.10.3 test v232.5.9; uniqueID preserved across
    the reparent. Implemented `move_task` MCP tool, wrote these tests.

Probe report: dev-docs/beta-v232.5.9-probe-results.md
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.dependencies import add_dependency, list_dependencies
from omniplan_mcp.tasks import (
    create_task,
    delete_task,
    get_task,
    move_task,
)

pytestmark = pytest.mark.requires_omniplan


async def _create(title: str, parent_id: str) -> dict:
    return json.loads(await create_task(title=title, parent_id=parent_id))


async def test_move_task_reparents_and_preserves_unique_id(test_root: str) -> None:
    """The core contract: a task moved between siblings keeps its uniqueID."""
    parent_a = await _create("__test__move_parent_a", test_root)
    parent_b = await _create("__test__move_parent_b", test_root)
    child = await _create("__test__move_child", parent_a["id"])

    result = json.loads(await move_task(task_id=child["id"], new_parent_id=parent_b["id"]))

    assert result["moved"] is True
    assert result["id"] == child["id"], "uniqueID must not change across move"
    assert result["new_parent_id"] == parent_b["id"]

    fresh = json.loads(await get_task(task_id=child["id"]))
    assert fresh["parent_id"] == parent_b["id"]
    assert fresh["title"] == "__test__move_child"


async def test_move_task_append_index_defaults_to_end(test_root: str) -> None:
    """Omitting `index` appends at the end of the new parent's subtasks."""
    parent_a = await _create("__test__move_idx_a", test_root)
    parent_b = await _create("__test__move_idx_b", test_root)
    sib1 = await _create("__test__move_idx_sib1", parent_b["id"])
    sib2 = await _create("__test__move_idx_sib2", parent_b["id"])
    moved = await _create("__test__move_idx_moved", parent_a["id"])

    result = json.loads(await move_task(task_id=moved["id"], new_parent_id=parent_b["id"]))
    assert result["index"] == 2, "default index should append at end (2 existing siblings → index 2)"

    # Cross-bridge sanity: the moved task is now the third child of parent_b.
    from omniplan_mcp.jxa import run_omnijs
    titles = await run_omnijs(f"""
const _proj = document.project;
function findById(t, id) {{
  if (String(t.uniqueID) === id) return t;
  for (const c of t.subtasks) {{ const f = findById(c, id); if (f) return f; }}
  return null;
}}
const p = findById(_proj.actual.rootTask, {json.dumps(parent_b["id"])});
return p.subtasks.map(s => s.title);
""")
    assert titles == ["__test__move_idx_sib1", "__test__move_idx_sib2", "__test__move_idx_moved"]
    # silence unused-var lints
    _ = (sib1, sib2)


async def test_move_task_explicit_index_inserts_at_position(test_root: str) -> None:
    """An explicit index slots the task into the right slice of subtasks."""
    parent_a = await _create("__test__move_pos_a", test_root)
    parent_b = await _create("__test__move_pos_b", test_root)
    await _create("__test__move_pos_sib1", parent_b["id"])
    await _create("__test__move_pos_sib2", parent_b["id"])
    moved = await _create("__test__move_pos_moved", parent_a["id"])

    result = json.loads(await move_task(
        task_id=moved["id"],
        new_parent_id=parent_b["id"],
        index=1,
    ))
    assert result["index"] == 1

    from omniplan_mcp.jxa import run_omnijs
    titles = await run_omnijs(f"""
const _proj = document.project;
function findById(t, id) {{
  if (String(t.uniqueID) === id) return t;
  for (const c of t.subtasks) {{ const f = findById(c, id); if (f) return f; }}
  return null;
}}
const p = findById(_proj.actual.rootTask, {json.dumps(parent_b["id"])});
return p.subtasks.map(s => s.title);
""")
    assert titles == [
        "__test__move_pos_sib1",
        "__test__move_pos_moved",
        "__test__move_pos_sib2",
    ]


async def test_move_task_to_root_when_new_parent_id_omitted(test_root: str) -> None:
    """Calling move_task without `new_parent_id` moves the task to the document root."""
    parent_a = await _create("__test__move_root_a", test_root)
    moved = await _create("__test__move_root_moved", parent_a["id"])

    result = json.loads(await move_task(task_id=moved["id"]))
    assert result["moved"] is True
    # rootTask.uniqueID is the OmniPlan root sentinel (-1 in the tested build);
    # we don't hard-code its value — just confirm the task is no longer under parent_a.
    fresh = json.loads(await get_task(task_id=moved["id"]))
    assert fresh["parent_id"] != parent_a["id"]


async def test_move_task_preserves_dependencies(test_root: str) -> None:
    """A dependency on a moved task survives the move (because uniqueID is preserved)."""
    parent_a = await _create("__test__move_dep_a", test_root)
    parent_b = await _create("__test__move_dep_b", test_root)
    predecessor = await _create("__test__move_dep_pred", test_root)
    successor = await _create("__test__move_dep_succ", parent_a["id"])

    await add_dependency(
        predecessor_id=predecessor["id"],
        successor_id=successor["id"],
    )
    deps_before = json.loads(await list_dependencies(task_id=successor["id"]))
    assert any(d["predecessor_id"] == predecessor["id"] for d in deps_before["predecessors"])

    await move_task(task_id=successor["id"], new_parent_id=parent_b["id"])

    deps_after = json.loads(await list_dependencies(task_id=successor["id"]))
    assert any(d["predecessor_id"] == predecessor["id"] for d in deps_after["predecessors"]), (
        "dependency must survive a move because uniqueID is preserved"
    )


async def test_move_task_into_self_rejected(test_root: str) -> None:
    """A task cannot be moved into itself."""
    parent = await _create("__test__move_self", test_root)
    with pytest.raises(Exception):  # JXA error surfaces as a Python-side exception
        await move_task(task_id=parent["id"], new_parent_id=parent["id"])


async def test_move_task_into_descendant_rejected(test_root: str) -> None:
    """A task cannot be moved under one of its own descendants (cycle)."""
    grand = await _create("__test__move_cycle_grand", test_root)
    parent = await _create("__test__move_cycle_parent", grand["id"])
    child = await _create("__test__move_cycle_child", parent["id"])

    with pytest.raises(Exception):
        await move_task(task_id=grand["id"], new_parent_id=child["id"])

    # Cleanup not strictly needed — conftest cleans __test__* — but assert the
    # tree is intact in case the move partially succeeded before erroring.
    fresh = json.loads(await get_task(task_id=grand["id"]))
    assert fresh["parent_id"] == test_root


async def test_move_task_unknown_id_rejected(test_root: str) -> None:
    """Moving a non-existent task surfaces a clear error."""
    with pytest.raises(Exception):
        await move_task(task_id="999999999", new_parent_id=test_root)
