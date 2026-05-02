"""Round-trip integration tests for the four endpoints flagged as
untested by the 2026-05-02 verifier pass: list_documents, query_tasks,
get_task, delete_task. Each test creates state under `__test__root`,
exercises the read or destructive path, and asserts behavior — not
just shape.

These tests would fail if any of the four tools returned a hard-coded
or echoed value rather than performing real work.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.documents import list_documents
from omniplan_mcp.tasks import (
    create_task,
    delete_task,
    get_task,
    query_tasks,
)

pytestmark = pytest.mark.requires_omniplan


async def test_list_documents_returns_at_least_one_when_omniplan_open() -> None:
    raw = await list_documents()
    docs = json.loads(raw)
    assert isinstance(docs, list)
    assert len(docs) >= 1, "OmniPlan must have a doc open for the test suite"
    assert all("name" in d for d in docs)
    assert all(isinstance(d["name"], str) and d["name"] for d in docs)


async def test_get_task_returns_full_shape_for_known_id(test_root: str) -> None:
    raw = await create_task(
        title="__test__get_task_shape",
        parent_id=test_root,
        effort_seconds=3600,
        note="probe",
    )
    created = json.loads(raw)
    fresh = json.loads(await get_task(task_id=created["id"]))

    assert fresh["id"] == created["id"]
    assert fresh["title"] == "__test__get_task_shape"
    assert fresh["note"] == "probe"
    assert fresh["effort_seconds"] == 3600

    expected_fields = {
        "id", "title", "type", "completed", "start_date", "end_date",
        "depth", "parent_id", "outline_id", "note", "completion_pct",
        "manual_start_date", "manual_end_date",
        "effort_seconds", "effort_done_seconds",
        "start_no_earlier_than", "start_no_later_than",
        "end_no_earlier_than", "end_no_later_than",
    }
    missing = expected_fields - set(fresh.keys())
    assert not missing, f"get_task output missing fields: {sorted(missing)}"


async def test_get_task_raises_on_unknown_id() -> None:
    with pytest.raises(RuntimeError):
        await get_task(task_id="999999999")


async def test_query_tasks_filters_by_keyword(test_root: str) -> None:
    await create_task(title="__test__query_unique_keyword_alpha", parent_id=test_root)
    await create_task(title="__test__query_unique_keyword_beta", parent_id=test_root)
    await create_task(title="__test__query_other_thing", parent_id=test_root)

    raw = await query_tasks(keyword="unique_keyword")
    matching = json.loads(raw)
    titles = [t["title"] for t in matching]

    assert "__test__query_unique_keyword_alpha" in titles
    assert "__test__query_unique_keyword_beta" in titles
    assert "__test__query_other_thing" not in titles


async def test_query_tasks_filters_by_completed(test_root: str) -> None:
    # Note: this MCP's "completed" model is `effortDone >= effort && effort > 0`,
    # so the test tasks must have non-zero effort to be markable complete.
    # Setting completed=True on a 0-effort task is a no-op by design.
    a_raw = await create_task(
        title="__test__query_completed_a", parent_id=test_root, effort_seconds=3600
    )
    b_raw = await create_task(
        title="__test__query_completed_b", parent_id=test_root, effort_seconds=3600
    )
    a = json.loads(a_raw)
    b = json.loads(b_raw)

    from omniplan_mcp.tasks import update_task
    await update_task(task_id=a["id"], completed=True)

    completed = json.loads(await query_tasks(keyword="__test__query_completed", completed=True))
    incomplete = json.loads(await query_tasks(keyword="__test__query_completed", completed=False))

    completed_titles = {t["title"] for t in completed}
    incomplete_titles = {t["title"] for t in incomplete}

    assert "__test__query_completed_a" in completed_titles
    assert "__test__query_completed_a" not in incomplete_titles
    assert "__test__query_completed_b" in incomplete_titles
    assert "__test__query_completed_b" not in completed_titles


async def test_query_tasks_filters_by_task_type(test_root: str) -> None:
    await create_task(title="__test__query_type_task", parent_id=test_root, task_type="task")
    await create_task(title="__test__query_type_milestone", parent_id=test_root, task_type="milestone")

    milestones = json.loads(await query_tasks(keyword="__test__query_type", task_type="milestone"))
    titles = {t["title"] for t in milestones}
    assert "__test__query_type_milestone" in titles
    assert "__test__query_type_task" not in titles


async def test_delete_task_removes_it(test_root: str) -> None:
    raw = await create_task(title="__test__delete_target", parent_id=test_root)
    target = json.loads(raw)

    pre = json.loads(await get_task(task_id=target["id"]))
    assert pre["title"] == "__test__delete_target"

    result = json.loads(await delete_task(task_id=target["id"]))
    assert result.get("deleted") is True or result.get("id") == target["id"]

    with pytest.raises(RuntimeError):
        await get_task(task_id=target["id"])


# Regression sentinels for the v0.4.3 query_tasks bugs. Both shipped in
# 0.4.0 and survived to 0.4.2 because the previous test suite never
# combined keyword with another filter, and never exercised task_type
# alone. If these tests go RED, one of two bugs has come back:
#
#   1. Filter clauses joined with `&&` but keyword filter contains `||`
#      internally; without per-clause parens, JS precedence makes
#      title-match short-circuit other filters. Fix: parenthesize each.
#   2. task_type filter compared `String(t.type)` (e.g.
#      `[object TaskType: TaskType.milestone]`) to bare type name and
#      never matched. Fix: apply same regex normalization taskToObj uses.


async def test_regression_query_tasks_combined_filters_use_AND_not_OR(test_root: str) -> None:
    """Operator-precedence regression — see v0.4.3 CHANGELOG.

    Setup: two tasks with the same keyword in their title, but only one
    is a milestone. Filtering keyword + task_type=milestone must return
    ONLY the milestone, not both.

    The pre-v0.4.3 bug returned both because the keyword filter used
    `||` internally and `&&` joining without parens let the title-match
    short-circuit the type check.
    """
    await create_task(title="__test__regr_combined_t", parent_id=test_root, task_type="task")
    await create_task(title="__test__regr_combined_m", parent_id=test_root, task_type="milestone")

    raw = await query_tasks(keyword="__test__regr_combined", task_type="milestone")
    matched_titles = {t["title"] for t in json.loads(raw)}

    assert matched_titles == {"__test__regr_combined_m"}, (
        f"query_tasks(keyword=K, task_type=milestone) returned {matched_titles!r}; "
        f"expected only the milestone. If 'task' appears, the operator-precedence "
        f"bug from v0.4.3 has regressed (filter clauses must each be parenthesized "
        f"before joining with &&)."
    )


async def test_regression_query_tasks_task_type_alone_normalizes(test_root: str) -> None:
    """TaskType normalization regression — see v0.4.3 CHANGELOG.

    Setup: create one task and one milestone with NO shared keyword.
    Filter by task_type=milestone WITHOUT a keyword. The filter must
    select only the milestone.

    The pre-v0.4.3 bug compared `String(t.type)` (which serializes as
    `[object TaskType: TaskType.X]`) to the bare task_type string,
    causing the filter to never match anything. The bug was masked
    when combined with other filters; this test isolates it.
    """
    await create_task(title="__test__regr_norm_thing", parent_id=test_root, task_type="task")
    await create_task(
        title="__test__regr_norm_marker", parent_id=test_root, task_type="milestone"
    )

    raw = await query_tasks(task_type="milestone")
    matched = json.loads(raw)
    matched_titles = {t["title"] for t in matched}

    assert "__test__regr_norm_marker" in matched_titles, (
        "query_tasks(task_type=milestone) excluded our milestone — "
        "the TaskType normalization bug from v0.4.3 has regressed. "
        "Filter must apply the same regex chain that taskToObj uses "
        "for output."
    )
    assert "__test__regr_norm_thing" not in matched_titles, (
        "query_tasks(task_type=milestone) included a non-milestone task — "
        "the filter is not actually excluding non-matching types."
    )
