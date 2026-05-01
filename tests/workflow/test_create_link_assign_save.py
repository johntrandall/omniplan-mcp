"""Workflow test: full Gantt-driver lifecycle in one sequence.

This is the canonical multi-tool sequence the MCP exists to support:
1. Create two tasks under the test root
2. Add a finish-to-start dependency between them
3. Create a resource and assign it to the second task with 0.5 units
4. Save the document
5. Read each artifact back via the appropriate read tool
6. Assert all four side-effects are visible after a single round-trip

This catches bugs that contract-level tests miss because they only
exercise one tool at a time. If any tool's omniJS write doesn't
persist correctly when sandwiched between other writes, this test
goes RED.

The save step is gated on the document already having a path (i.e.
not Untitled). On a Tart VM with the baseline.oplx fixture loaded,
that's always true. On the host with an Untitled doc open, save is
skipped per the existing pattern.
"""
from __future__ import annotations

import json
import os

import pytest

from omniplan_mcp.dependencies import add_dependency, list_dependencies
from omniplan_mcp.documents import save_document
from omniplan_mcp.jxa import run_omnijs
from omniplan_mcp.resources import (
    assign_resource,
    create_resource,
    list_assignments,
)
from omniplan_mcp.tasks import create_task, get_task

pytestmark = pytest.mark.requires_omniplan


async def test_full_gantt_workflow(test_root: str) -> None:
    a_raw = await create_task(
        title="__test__wf_a", parent_id=test_root, effort_seconds=3600
    )
    a = json.loads(a_raw)
    b_raw = await create_task(
        title="__test__wf_b", parent_id=test_root, effort_seconds=7200
    )
    b = json.loads(b_raw)

    dep_raw = await add_dependency(
        predecessor_id=a["id"],
        successor_id=b["id"],
        kind="FS",
        lead_time_seconds=1800,
    )
    dep = json.loads(dep_raw)
    assert dep["kind"] == "FS"
    assert dep["lead_time_seconds"] == 1800

    r_raw = await create_resource(name="__test__wf_alice", type="staff")
    r = json.loads(r_raw)
    asg_raw = await assign_resource(
        task_id=b["id"], resource_id=r["id"], units=0.5
    )
    asg = json.loads(asg_raw)
    assert asg["resource_id"] == r["id"]

    document_path_check = await run_omnijs("return document.fileType;")
    if document_path_check is None:
        pytest.skip("Front document is unsaved; save_document would block.")
    save_result = json.loads(await save_document())
    assert save_result["saved"] is True

    deps = json.loads(await list_dependencies(task_id=b["id"]))
    assert any(
        d["predecessor_id"] == a["id"] and d["kind"] == "FS"
        for d in deps
    )
    assert any(d["lead_time_seconds"] == 1800 for d in deps)

    asgs = json.loads(await list_assignments(task_id=b["id"]))
    assert any(a_["resource_id"] == r["id"] for a_ in asgs)
    assigned = next(a_ for a_ in asgs if a_["resource_id"] == r["id"])
    assert assigned["units_assigned"] == 0.5

    fresh_b = json.loads(await get_task(task_id=b["id"]))
    assert fresh_b["effort_seconds"] == 7200
