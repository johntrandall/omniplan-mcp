"""Integration tests for resource CRUD and assignments.

Verified omniJS surface (per the documented Assignment / Resource
classes at https://omni-automation.com/omniplan/ and probed live
2026-05-01, OmniPlan 4.10.2):

  - actual.rootResource.addMember() returns a Resource
  - r.name / r.email / r.type / r.uniqueID — persistent, readable
  - r.costPerUse — write requires Decimal.fromString; reads back as
    Decimal object (opaque, but its toString includes the number, so we
    parse it).
  - task.addAssignment(resource) returns an Assignment
  - task.assignments — array; assignment.resource has uniqueID
  - assignment.remove() works
  - assignment.unitsAssigned (NOT `units`) — Number, read/write,
    round-trips. The earlier session probed the wrong property name;
    the documented accessor is `unitsAssigned`.

Tests use the `__test__` prefix so the integration conftest cleans up
both tasks and resources at teardown.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.resources import (
    assign_resource,
    create_resource,
    delete_resource,
    list_assignments,
    list_resources,
    unassign_resource,
)
from omniplan_mcp.tasks import create_task

pytestmark = pytest.mark.requires_omniplan


async def test_create_resource_round_trip(test_root: str) -> None:
    raw = await create_resource(
        name="__test__rsrc_alice",
        type="staff",
        email="alice@example.com",
        cost_per_use=125.50,
    )
    r = json.loads(raw)
    assert r["name"] == "__test__rsrc_alice"
    assert r["type"] == "staff"
    assert r["email"] == "alice@example.com"
    assert r["cost_per_use"] == 125.50
    assert isinstance(r["id"], str) and r["id"]

    # Re-read via list_resources to confirm the create actually persisted
    # (not just echoed the input). Catches a class of bug where the tool
    # appears to succeed but writes nothing.
    listed = json.loads(await list_resources())
    found = next((res for res in listed if res["id"] == r["id"]), None)
    assert found is not None, (
        f"create_resource returned id={r['id']!r} but list_resources "
        f"doesn't see it — write didn't persist."
    )
    assert found["name"] == "__test__rsrc_alice"
    assert found["type"] == "staff"
    assert found["email"] == "alice@example.com"
    assert found["cost_per_use"] == 125.50


async def test_list_resources_includes_created(test_root: str) -> None:
    a = json.loads(await create_resource(name="__test__rsrc_list_a", type="staff"))
    b = json.loads(await create_resource(name="__test__rsrc_list_b", type="equipment"))

    listed = json.loads(await list_resources())
    by_id = {r["id"]: r for r in listed}
    assert a["id"] in by_id and by_id[a["id"]]["type"] == "staff"
    assert b["id"] in by_id and by_id[b["id"]]["type"] == "equipment"


async def test_delete_resource_removes_it(test_root: str) -> None:
    r = json.loads(await create_resource(name="__test__rsrc_del", type="staff"))
    result = json.loads(await delete_resource(resource_id=r["id"]))
    assert result == {"deleted": True, "id": r["id"], "name": "__test__rsrc_del"}

    listed = json.loads(await list_resources())
    assert all(it["id"] != r["id"] for it in listed)


async def test_delete_resource_returns_false_when_missing(test_root: str) -> None:
    result = json.loads(await delete_resource(resource_id="999999999"))
    assert result["deleted"] is False


async def test_create_resource_unknown_type_rejected(test_root: str) -> None:
    with pytest.raises(ValueError, match="Unknown resource type"):
        await create_resource(name="__test__rsrc_bad", type="bogus")


async def test_assign_and_unassign_resource(test_root: str) -> None:
    r = json.loads(await create_resource(name="__test__rsrc_assignee", type="staff"))
    t = json.loads(
        await create_task(
            title="__test__rsrc_assignment_task",
            parent_id=test_root,
            effort_seconds=3600,
        )
    )

    assigned = json.loads(
        await assign_resource(task_id=t["id"], resource_id=r["id"], units=0.5)
    )
    # `units` now round-trips via assignment.unitsAssigned (true read).
    assert assigned == {"task_id": t["id"], "resource_id": r["id"], "units": 0.5}

    removed = json.loads(await unassign_resource(task_id=t["id"], resource_id=r["id"]))
    assert removed == {"removed": True}


async def test_unassign_returns_false_when_no_assignment(test_root: str) -> None:
    r = json.loads(await create_resource(name="__test__rsrc_noassign", type="staff"))
    t = json.loads(
        await create_task(title="__test__rsrc_noassign_task", parent_id=test_root, effort_seconds=3600)
    )
    result = json.loads(await unassign_resource(task_id=t["id"], resource_id=r["id"]))
    assert result == {"removed": False}


async def test_list_assignments(test_root: str) -> None:
    """Two assignments at different unitsAssigned values round-trip."""
    r1 = json.loads(await create_resource(name="__test__rsrc_la_one", type="staff"))
    r2 = json.loads(await create_resource(name="__test__rsrc_la_two", type="staff"))
    t = json.loads(
        await create_task(
            title="__test__rsrc_la_task",
            parent_id=test_root,
            effort_seconds=3600,
        )
    )

    await assign_resource(task_id=t["id"], resource_id=r1["id"], units=0.25)
    await assign_resource(task_id=t["id"], resource_id=r2["id"], units=0.75)

    listed = json.loads(await list_assignments(task_id=t["id"]))
    by_id = {a["resource_id"]: a for a in listed}
    assert r1["id"] in by_id
    assert r2["id"] in by_id
    assert by_id[r1["id"]]["resource_name"] == "__test__rsrc_la_one"
    assert by_id[r1["id"]]["units_assigned"] == 0.25
    assert by_id[r2["id"]]["resource_name"] == "__test__rsrc_la_two"
    assert by_id[r2["id"]]["units_assigned"] == 0.75


async def test_list_assignments_empty(test_root: str) -> None:
    t = json.loads(
        await create_task(
            title="__test__rsrc_la_empty_task",
            parent_id=test_root,
            effort_seconds=3600,
        )
    )
    listed = json.loads(await list_assignments(task_id=t["id"]))
    assert listed == []
