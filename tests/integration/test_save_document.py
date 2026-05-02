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
    """True when the front OmniPlan document has been saved at least once.

    Tries `path()` first, falls back to `file()` since `path()` throws
    "Can't convert types (-1700)" on saved docs in macOS 15+ even though
    the value exists. Same issue as the e2e helpers (commit f6aaa70).
    """
    script = """
const app = Application('OmniPlan');
const docs = app.documents();
if (docs.length === 0) {
  JSON.stringify({ ok: true, data: false });
} else {
  let saved = false;
  try { const p = docs[0].path(); if (p) saved = true; } catch (_) {}
  if (!saved) {
    try { const f = docs[0].file(); if (f) saved = true; } catch (_) {}
  }
  JSON.stringify({ ok: true, data: saved });
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

    # Independently confirm the doc IS dirty before save — catches the
    # bug class where save_document hard-codes its return without
    # actually exercising the underlying tool.
    pre = await run_jxa("""
const docs = Application('OmniPlan').documents();
JSON.stringify({ok: true, data: docs[0].modified() ? 'dirty' : 'clean'})
""")
    assert json.loads(pre).get("data") == "dirty", (
        "Pre-save: document not actually dirty after create_task — "
        "test setup or create_task itself is broken."
    )

    raw = await save_document()
    payload = json.loads(raw)

    assert payload["saved"] is True
    assert isinstance(payload["name"], str) and payload["name"]
    assert payload["modified_after"] is False

    # Independent post-save re-read of document.modified() via JXA — does
    # not trust the response from save_document. If save_document fakes
    # its return without actually saving, this assertion goes RED.
    post = await run_jxa("""
const docs = Application('OmniPlan').documents();
JSON.stringify({ok: true, data: docs[0].modified() ? 'dirty' : 'clean'})
""")
    assert json.loads(post).get("data") == "clean", (
        "Post-save: document.modified() is still true via independent "
        "JXA re-read. save_document either didn't actually save, or "
        "OmniPlan didn't accept the save."
    )


async def test_save_document_when_already_clean(test_root: str) -> None:
    """Save on a clean doc is a no-op but still returns saved: true."""
    # First save to flush whatever state is lying around.
    await save_document()

    raw = await save_document()
    payload = json.loads(raw)
    assert payload["saved"] is True
    assert payload["modified_after"] is False
