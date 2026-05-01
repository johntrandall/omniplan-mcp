"""Integration tests for `add_dependency`, `remove_dependency`, `list_dependencies`.

Verified omniJS surface (probed live against OmniPlan 4.10.2):
  - `task.addDependent(other) -> Dependency` (default kind: FinishStart)
  - `dep.kind = DependencyKind.{FinishStart|FinishFinish|StartStart|StartFinish}`
  - `dep.prerequisite.uniqueID`, `dep.dependent.uniqueID`
  - `dep.remove()`
  - `dep.leadTimeDuration` accepts `Duration.workSeconds(N)` on write
    and is read back via `dep.leadTimeDuration.workSeconds` — full
    round-trip per the documented Duration class.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.dependencies import (
    add_dependency,
    list_dependencies,
    remove_dependency,
)
from omniplan_mcp.tasks import create_task

pytestmark = pytest.mark.requires_omniplan


async def _make_pair(test_root: str, label: str) -> tuple[str, str]:
    a = json.loads(
        await create_task(
            title=f"__test__deps__{label}_a",
            parent_id=test_root,
            effort_seconds=3600,
        )
    )
    b = json.loads(
        await create_task(
            title=f"__test__deps__{label}_b",
            parent_id=test_root,
            effort_seconds=3600,
        )
    )
    return a["id"], b["id"]


async def test_add_finish_start_dependency(test_root: str) -> None:
    a_id, b_id = await _make_pair(test_root, "fs")
    payload = json.loads(await add_dependency(a_id, b_id, kind="FS"))
    assert payload == {
        "predecessor_id": a_id,
        "successor_id": b_id,
        "kind": "FS",
        "lead_time_seconds": 0,
    }


async def test_list_dependencies_includes_added_pair(test_root: str) -> None:
    a_id, b_id = await _make_pair(test_root, "list")
    await add_dependency(a_id, b_id, kind="FS")

    listed = json.loads(await list_dependencies(task_id=b_id))
    assert any(
        d["predecessor_id"] == a_id and d["successor_id"] == b_id and d["kind"] == "FS"
        for d in listed
    )


async def test_dependency_kinds_round_trip(test_root: str) -> None:
    """Each of the four kinds round-trips through list_dependencies."""
    pairs = []
    for kind in ("FS", "SS", "FF", "SF"):
        a_id, b_id = await _make_pair(test_root, f"kind_{kind}")
        await add_dependency(a_id, b_id, kind=kind)
        pairs.append((a_id, b_id, kind))

    listed = json.loads(await list_dependencies())
    for a_id, b_id, kind in pairs:
        assert any(
            d["predecessor_id"] == a_id
            and d["successor_id"] == b_id
            and d["kind"] == kind
            for d in listed
        ), f"{kind} dependency not found in list"


async def test_remove_dependency_returns_true_on_match(test_root: str) -> None:
    a_id, b_id = await _make_pair(test_root, "remove")
    await add_dependency(a_id, b_id, kind="FS")

    result = json.loads(await remove_dependency(a_id, b_id))
    assert result == {"removed": True}

    listed = json.loads(await list_dependencies(task_id=b_id))
    assert not any(d["predecessor_id"] == a_id for d in listed)


async def test_remove_dependency_returns_false_when_no_match(test_root: str) -> None:
    a_id, b_id = await _make_pair(test_root, "noop")
    # Never added — remove should be a no-op.
    result = json.loads(await remove_dependency(a_id, b_id))
    assert result == {"removed": False}


async def test_add_dependency_with_lead_time(test_root: str) -> None:
    """Lead time round-trips: written as Duration.workSeconds(N), read
    back via dep.leadTimeDuration.workSeconds (Number)."""
    a_id, b_id = await _make_pair(test_root, "lead")
    payload = json.loads(
        await add_dependency(a_id, b_id, kind="FS", lead_time_seconds=3600)
    )
    assert payload["lead_time_seconds"] == 3600

    listed = json.loads(await list_dependencies(task_id=b_id))
    matching = [
        d for d in listed if d["predecessor_id"] == a_id and d["successor_id"] == b_id
    ]
    assert len(matching) == 1
    assert matching[0]["lead_time_seconds"] == 3600


async def test_add_dependency_unknown_kind_rejected(test_root: str) -> None:
    a_id, b_id = await _make_pair(test_root, "bad_kind")
    with pytest.raises(ValueError, match="Unknown dependency kind"):
        await add_dependency(a_id, b_id, kind="bogus")
