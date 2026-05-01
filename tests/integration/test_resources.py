"""Integration tests for resource CRUD and assignments.

Verified omniJS surface (probed live 2026-05-01, OmniPlan 4.10.2):

  - actual.rootResource.addMember() returns a Resource
  - r.name / r.email / r.type / r.uniqueID — persistent, readable
  - r.costPerUse — write requires Decimal.fromString; reads back as
    Decimal object (opaque, but its toString includes the number, so we
    parse it).
  - task.addAssignment(resource) returns an Assignment
  - task.assignments — array; assignment.resource has uniqueID
  - assignment.remove() works
  - assignment.units — write accepted, NOT persistent across JXA calls
    (same trap as dep.leadTimeDuration). Tools accept and echo, but
    return null on read.

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
