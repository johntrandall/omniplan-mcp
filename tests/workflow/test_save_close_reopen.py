"""Workflow test: save → reopen survives.

The most paranoid check: a write reaches disk and survives a close/reopen
cycle. This is what catches the "writes don't reach the model" bug class
without dropping into XML inspection.

Methodology:
1. Create a task with a constraint date
2. Save the document
3. Capture document.path() via JXA SDEF
4. Close the document
5. Reopen the document via JXA SDEF
6. Re-find the task by uniqueID and assert the constraint date round-tripped

This is workflow-level rather than e2e-live-xml because it exercises the
public read path; e2e-live-xml goes one step further and parses the XML
directly.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from omniplan_mcp.documents import save_document
from omniplan_mcp.jxa import run_jxa, run_omnijs
from omniplan_mcp.tasks import create_task, get_task, update_task

pytestmark = pytest.mark.requires_omniplan

TARGET_DATE = "2027-04-12"


async def _front_document_path() -> str | None:
    raw = await run_jxa("""
const app = Application('OmniPlan');
const docs = app.documents();
if (docs.length === 0) { 'null' }
else {
  let s = 'null';
  try { const p = docs[0].path(); if (p) s = String(p); } catch(_) {}
  if (s === 'null') {
    try { const f = docs[0].file(); if (f) s = String(f); } catch(_) {}
  }
  s
}
""")
    return None if raw.strip() == "null" else raw.strip()


async def _close_and_reopen(path: str) -> None:
    """Close every open document, then reopen the one at `path`."""
    await run_jxa(f"""
const app = Application('OmniPlan');
const docs = app.documents();
for (let i = 0; i < docs.length; i++) {{ docs[i].close({{saving: 'no'}}); }}
'closed'
""")
    await asyncio.sleep(1)
    await run_jxa(f"""
const app = Application('OmniPlan');
app.open(Path({json.dumps(path)}));
'opened'
""")
    for _ in range(20):
        ready = await run_jxa(
            "Application('OmniPlan').documents().length > 0 ? 'yes' : 'no'"
        )
        if ready.strip() == "yes":
            return
        await asyncio.sleep(0.5)
    raise AssertionError("Document did not reopen within 10s")


async def test_constraint_date_survives_close_reopen(test_root: str) -> None:
    path = await _front_document_path()
    if path is None:
        pytest.skip(
            "Front document is unsaved; this test requires a saved document "
            "(e.g. tests/fixtures/baseline.oplx loaded in OmniPlan)."
        )

    raw = await create_task(title="__test__reopen_probe", parent_id=test_root)
    task = json.loads(raw)
    await update_task(task_id=task["id"], start_no_earlier_than=TARGET_DATE)

    pre_save = json.loads(await get_task(task_id=task["id"]))
    pre_constraint = pre_save["start_no_earlier_than"]
    assert pre_constraint is not None

    await save_document()
    await _close_and_reopen(path)

    post = json.loads(await get_task(task_id=task["id"]))
    assert post["start_no_earlier_than"] == pre_constraint, (
        f"Constraint date did not survive close/reopen: "
        f"pre={pre_constraint!r}, post={post['start_no_earlier_than']!r}"
    )
