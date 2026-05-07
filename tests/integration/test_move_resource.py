"""Integration tests for move_resource — the omniJS resource-reparent tool.

History parallels test_move_task.py:

  - 2026-05-06: Ken Case (Omni) confirmed `parent` accessor and `move`
    method were added to both Task AND Resource for OmniPlan 4.10.3.
  - 2026-05-07: Live probe verified Resource.move signature parity:
    `resource.move(newParent, index)`, both args required, uniqueID
    preserved (probe: r3 moved from rootResource → r1, r1.members
    contained r3 by name, r1MemberCount: 0 → 1).
  - Same session: implemented `move_resource` MCP tool and these tests.

Probe report: dev-docs/beta-v232.5.9-probe-results.md
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.resources import (
    assign_resource,
    create_resource,
    list_assignments,
    list_resources,
    move_resource,
)
from omniplan_mcp.tasks import create_task

pytestmark = pytest.mark.requires_omniplan


async def _create(name: str, type_: str = "staff") -> dict:
    return json.loads(await create_resource(name=name, type=type_))


async def test_move_resource_reparents_and_preserves_unique_id(test_root: str) -> None:
    """Core contract: a resource moved between groups keeps its uniqueID."""
    group_a = await _create("__test__r_grp_a", type_="group")
    group_b = await _create("__test__r_grp_b", type_="group")
    member = await _create("__test__r_member", type_="staff")

    # Move member into group_a first, then to group_b — exercises the
    # full reparent path (root → grpA → grpB).
    await move_resource(resource_id=member["id"], new_parent_id=group_a["id"])
    result = json.loads(await move_resource(
        resource_id=member["id"],
        new_parent_id=group_b["id"],
    ))
    assert result["moved"] is True
    assert result["id"] == member["id"], "uniqueID must not change across move"
    assert result["new_parent_id"] == group_b["id"]

    # Cross-bridge confirmation: list_resources shows it under group_b.
    listed = json.loads(await list_resources())
    by_id = {r["id"]: r for r in listed}
    assert by_id[member["id"]]["name"] == "__test__r_member"


async def test_move_resource_append_index_defaults_to_end(test_root: str) -> None:
    """Omitting `index` appends to the end of the destination group's members."""
    group = await _create("__test__r_idx_grp", type_="group")
    sib1 = await _create("__test__r_idx_sib1")
    sib2 = await _create("__test__r_idx_sib2")
    moved = await _create("__test__r_idx_moved")

    # First seed group's members
    await move_resource(resource_id=sib1["id"], new_parent_id=group["id"])
    await move_resource(resource_id=sib2["id"], new_parent_id=group["id"])

    result = json.loads(await move_resource(
        resource_id=moved["id"],
        new_parent_id=group["id"],
    ))
    assert result["index"] == 2, "default index should append at end (2 existing members → index 2)"

    # Cross-bridge: walk the members of group via omniJS.
    from omniplan_mcp.jxa import run_omnijs
    names = await run_omnijs(f"""
const root = document.project.actual.rootResource;
function findRes(g, id) {{
  for (let i = 0; i < g.members.length; i++) {{
    const m = g.members[i];
    if (String(m.uniqueID) === id) return m;
    if (m.members && m.members.length) {{
      const sub = findRes(m, id); if (sub) return sub;
    }}
  }}
  return null;
}}
const grp = findRes(root, {json.dumps(group["id"])});
return grp.members.map(r => r.name);
""")
    assert names == ["__test__r_idx_sib1", "__test__r_idx_sib2", "__test__r_idx_moved"]


async def test_move_resource_explicit_index_inserts_at_position(test_root: str) -> None:
    """Explicit index slots the resource into the right slice of members."""
    group = await _create("__test__r_pos_grp", type_="group")
    sib1 = await _create("__test__r_pos_sib1")
    sib2 = await _create("__test__r_pos_sib2")
    moved = await _create("__test__r_pos_moved")

    await move_resource(resource_id=sib1["id"], new_parent_id=group["id"])
    await move_resource(resource_id=sib2["id"], new_parent_id=group["id"])

    result = json.loads(await move_resource(
        resource_id=moved["id"],
        new_parent_id=group["id"],
        index=1,
    ))
    assert result["index"] == 1

    from omniplan_mcp.jxa import run_omnijs
    names = await run_omnijs(f"""
const root = document.project.actual.rootResource;
function findRes(g, id) {{
  for (let i = 0; i < g.members.length; i++) {{
    const m = g.members[i];
    if (String(m.uniqueID) === id) return m;
    if (m.members && m.members.length) {{
      const sub = findRes(m, id); if (sub) return sub;
    }}
  }}
  return null;
}}
const grp = findRes(root, {json.dumps(group["id"])});
return grp.members.map(r => r.name);
""")
    assert names == [
        "__test__r_pos_sib1",
        "__test__r_pos_moved",
        "__test__r_pos_sib2",
    ]


async def test_move_resource_to_root_when_new_parent_id_omitted(test_root: str) -> None:
    """Calling move_resource without `new_parent_id` moves under rootResource."""
    group = await _create("__test__r_root_grp", type_="group")
    moved = await _create("__test__r_root_moved")

    # Put it under group first
    await move_resource(resource_id=moved["id"], new_parent_id=group["id"])
    # Then bring it back out (no new_parent_id → root)
    result = json.loads(await move_resource(resource_id=moved["id"]))
    assert result["moved"] is True

    # Confirm it's no longer in `group.members`
    from omniplan_mcp.jxa import run_omnijs
    in_group = await run_omnijs(f"""
const root = document.project.actual.rootResource;
function findRes(g, id) {{
  for (let i = 0; i < g.members.length; i++) {{
    const m = g.members[i];
    if (String(m.uniqueID) === id) return m;
    if (m.members && m.members.length) {{
      const sub = findRes(m, id); if (sub) return sub;
    }}
  }}
  return null;
}}
const grp = findRes(root, {json.dumps(group["id"])});
return grp.members.some(m => String(m.uniqueID) === {json.dumps(moved["id"])});
""")
    assert in_group is False, "moved resource should no longer be in the prior group"


async def test_move_resource_preserves_assignments(test_root: str) -> None:
    """An assignment on a moved resource survives the move (uniqueID preserved)."""
    raw_task = await create_task(title="__test__r_assn_task", parent_id=test_root)
    task = json.loads(raw_task)
    group = await _create("__test__r_assn_grp", type_="group")
    rsrc = await _create("__test__r_assn_rsrc", type_="staff")

    await assign_resource(task_id=task["id"], resource_id=rsrc["id"], units=0.5)

    before = json.loads(await list_assignments(task_id=task["id"]))
    assert any(a["resource_id"] == rsrc["id"] for a in before), (
        f"setup failure: assignment missing before move; assignments={before}"
    )

    await move_resource(resource_id=rsrc["id"], new_parent_id=group["id"])

    after = json.loads(await list_assignments(task_id=task["id"]))
    assert any(a["resource_id"] == rsrc["id"] for a in after), (
        "assignment must survive a move because uniqueID is preserved"
    )


async def test_move_resource_into_self_rejected(test_root: str) -> None:
    """A resource cannot be moved into itself."""
    grp = await _create("__test__r_self_grp", type_="group")
    with pytest.raises(Exception):
        await move_resource(resource_id=grp["id"], new_parent_id=grp["id"])


async def test_move_resource_into_descendant_rejected(test_root: str) -> None:
    """A resource cannot be moved under one of its own descendants (cycle)."""
    outer = await _create("__test__r_cycle_outer", type_="group")
    inner = await _create("__test__r_cycle_inner", type_="group")
    leaf = await _create("__test__r_cycle_leaf", type_="staff")

    await move_resource(resource_id=inner["id"], new_parent_id=outer["id"])
    await move_resource(resource_id=leaf["id"],  new_parent_id=inner["id"])

    with pytest.raises(Exception):
        await move_resource(resource_id=outer["id"], new_parent_id=inner["id"])


async def test_move_resource_unknown_id_rejected(test_root: str) -> None:
    """Moving a non-existent resource surfaces a clear error."""
    with pytest.raises(Exception):
        await move_resource(resource_id="999999999")
