"""Integration tests for `create_tasks` (bulk).

Single JXA call creates the whole batch — performance gain over
calling `create_task` N times. Per-task fields match `create_task`.
The extra `parent_index` field lets a later task in the batch parent
to an earlier one without needing the earlier one's uniqueID.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.tasks import create_tasks, find_task

pytestmark = pytest.mark.requires_omniplan


async def test_create_tasks_under_root_in_order(test_root: str) -> None:
    raw = await create_tasks(
        tasks=[
            {"title": "__test__bulk__a", "parent_id": test_root, "effort_seconds": 3600},
            {"title": "__test__bulk__b", "parent_id": test_root, "effort_seconds": 7200},
            {"title": "__test__bulk__c", "parent_id": test_root, "effort_seconds": 1800},
        ],
    )
    out = json.loads(raw)
    assert [t["title"] for t in out] == [
        "__test__bulk__a",
        "__test__bulk__b",
        "__test__bulk__c",
    ]
    assert [t["effort_seconds"] for t in out] == [3600, 7200, 1800]


async def test_create_tasks_with_intra_batch_parent_index(test_root: str) -> None:
    raw = await create_tasks(
        tasks=[
            {"title": "__test__bulk__group", "parent_id": test_root, "task_type": "group"},
            {"title": "__test__bulk__child_a", "parent_index": 0, "effort_seconds": 3600},
            {"title": "__test__bulk__child_b", "parent_index": 0, "effort_seconds": 3600},
        ],
    )
    out = json.loads(raw)
    parent_uid = out[0]["id"]
    assert out[1]["parent_id"] == parent_uid
    assert out[2]["parent_id"] == parent_uid

    found = json.loads(await find_task(name="__test__bulk__child_a", exact=True))
    assert len(found) == 1


async def test_create_tasks_rejects_invalid_parent_index(test_root: str) -> None:
    # parent_index must be < own index
    with pytest.raises(ValueError, match="parent_index"):
        await create_tasks(
            tasks=[
                {"title": "__test__bulk__bad_a", "parent_index": 1},
                {"title": "__test__bulk__bad_b", "parent_id": test_root},
            ],
        )


async def test_create_tasks_rejects_both_parent_specifiers(test_root: str) -> None:
    with pytest.raises(ValueError, match="at most one"):
        await create_tasks(
            tasks=[
                {"title": "__test__bulk__conflict", "parent_id": test_root, "parent_index": 0},
            ],
        )


async def test_create_tasks_empty_list_returns_empty(test_root: str) -> None:
    assert json.loads(await create_tasks(tasks=[])) == []
