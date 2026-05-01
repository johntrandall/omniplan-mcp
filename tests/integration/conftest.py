"""Integration test shared fixtures.

`__test__root` is the parent group every integration test writes under. It is
created on demand and cleaned up (along with every other `__test__*` task) at
the end of each test, regardless of pass/fail. Tests run sequentially because
osascript serialises through an `asyncio.Lock` and OmniPlan is GUI-stateful.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import pytest_asyncio

from omniplan_mcp.jxa import run_omnijs
from omniplan_mcp.tasks import create_task

TEST_PREFIX = "__test__"
ROOT_TITLE = f"{TEST_PREFIX}root"


async def _ensure_root() -> str:
    """Create or reuse the `__test__root` group at the document root, return its uniqueID."""
    script = f"""
const _proj = document.project;
const root = _proj.actual.rootTask;
for (let i = 0; i < root.subtasks.length; i++) {{
  if (root.subtasks[i].title === {json.dumps(ROOT_TITLE)}) {{
    return String(root.subtasks[i].uniqueID);
  }}
}}
const t = root.addSubtask();
t.title = {json.dumps(ROOT_TITLE)};
return String(t.uniqueID);
"""
    return await run_omnijs(script)


async def _delete_test_tasks() -> int:
    """Delete every task in the front document whose title starts with the test prefix.

    Returns the number of tasks removed. We delete depth-first so we never
    walk through a subtree we just removed.
    """
    script = f"""
const _proj = document.project;
const root = _proj.actual.rootTask;
const prefix = {json.dumps(TEST_PREFIX)};

function collect(task, out) {{
  for (let i = 0; i < task.subtasks.length; i++) {{
    collect(task.subtasks[i], out);
  }}
  if (task !== root && (task.title || '').indexOf(prefix) === 0) {{
    out.push(task);
  }}
}}

const victims = [];
collect(root, victims);
let removed = 0;
for (const t of victims) {{
  try {{ t.remove(); removed += 1; }} catch (e) {{}}
}}
return removed;
"""
    return await run_omnijs(script)


@pytest_asyncio.fixture
async def test_root() -> AsyncIterator[str]:
    """Yield the uniqueID of `__test__root`; clean up every `__test__*` task after."""
    root_id = await _ensure_root()
    try:
        yield root_id
    finally:
        await _delete_test_tasks()
