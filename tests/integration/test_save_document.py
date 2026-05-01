"""Integration tests for `save_document`.

Empirical autosave finding (OmniPlan 4.10.2, probed live 2026-05-01):
  After editing a task via MCP, `document.modified()` stayed `true`
  for at least 10s. OmniPlan does NOT autosave on idle — explicit save
  is required to persist changes between UI File>Save and the quit-time
  save prompt. This makes save_document a real "commit now" tool, not
  cosmetic.

We do not close-and-reopen OmniPlan inside the test (that would lose
state in any other documents the user has open). Instead we verify:
  - calling save_document does not raise
  - it returns a payload with `saved: true` and the document name
  - `modified_after` is `false` after the save (the dirty flag cleared)

These tests require the front document to already have a save path.
On a fresh VM with only an Untitled doc, `document.save()` would pop
the Save As sheet and block the JXA call. The `_doc_has_path` helper
auto-skips when no saved doc is open.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from omniplan_mcp.documents import save_document
from omniplan_mcp.jxa import run_jxa
from omniplan_mcp.tasks import create_task

pytestmark = pytest.mark.requires_omniplan


def _front_doc_has_path() -> bool:
    """True when the front OmniPlan document has been saved at least once."""
    script = """
const app = Application('OmniPlan');
const docs = app.documents();
if (docs.length === 0) {
  JSON.stringify({ ok: true, data: false });
} else {
  let p = null;
  try { p = docs[0].path(); } catch (_) {}
  JSON.stringify({ ok: true, data: p ? true : false });
}
"""
    raw = asyncio.run(run_jxa(script))
    return json.loads(raw).get("data") is True


@pytest.fixture(autouse=True)
def _require_saved_document() -> None:
    if not _front_doc_has_path():
        pytest.skip(
            "front OmniPlan document is unsaved — `document.save()` would pop "
            "the Save As sheet and block the JXA call. Open a saved .oplx "
            "before running save_document tests."
        )


async def test_save_document_clears_modified_flag(test_root: str) -> None:
    # Make a change so the document is definitely dirty.
    await create_task(title="__test__save__make_dirty", parent_id=test_root)

    raw = await save_document()
    payload = json.loads(raw)

    assert payload["saved"] is True
    assert isinstance(payload["name"], str) and payload["name"]
    # If the doc is on a save-able backing (i.e. has been saved at least once),
    # the dirty flag clears. For brand-new "Untitled" docs, OmniPlan would
    # surface a save sheet and the flag may stay set; we don't run against
    # those in the test environment.
    assert payload["modified_after"] is False


async def test_save_document_when_already_clean(test_root: str) -> None:
    """Save on a clean doc is a no-op but still returns saved: true."""
    # First save to flush whatever state is lying around.
    await save_document()

    raw = await save_document()
    payload = json.loads(raw)
    assert payload["saved"] is True
    assert payload["modified_after"] is False
