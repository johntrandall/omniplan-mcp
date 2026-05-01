"""Integration tests for `find_task`.

Verifies the substring (default) and exact match modes against a freshly
populated set of marker-prefixed tasks. The cleanup pass in `test_root`
removes them after the test.
"""
from __future__ import annotations

import json

import pytest

from omniplan_mcp.tasks import create_task, find_task

pytestmark = pytest.mark.requires_omniplan


async def test_find_task_substring_returns_all_matches(test_root: str) -> None:
    for suffix in ("a", "b", "c"):
        await create_task(title=f"__test__find_{suffix}", parent_id=test_root)

    hits = json.loads(await find_task(name="__test__find"))
    titles = {h["title"] for h in hits}
    assert {"__test__find_a", "__test__find_b", "__test__find_c"}.issubset(titles)


async def test_find_task_substring_is_case_insensitive(test_root: str) -> None:
    await create_task(title="__test__FindCase", parent_id=test_root)

    hits = json.loads(await find_task(name="findcase"))
    assert any(h["title"] == "__test__FindCase" for h in hits)


async def test_find_task_exact_match_only_matches_full_title(test_root: str) -> None:
    await create_task(title="__test__exact", parent_id=test_root)
    await create_task(title="__test__exact_extra", parent_id=test_root)

    exact = json.loads(await find_task(name="__test__exact", exact=True))
    titles = [h["title"] for h in exact]
    assert titles == ["__test__exact"]


async def test_find_task_returns_empty_when_no_match(test_root: str) -> None:
    hits = json.loads(await find_task(name="__test__never_created_xyzzy"))
    assert hits == []


async def test_find_task_includes_id_and_outline_id(test_root: str) -> None:
    raw = await create_task(title="__test__find_outline", parent_id=test_root)
    created = json.loads(raw)

    hits = json.loads(await find_task(name="__test__find_outline", exact=True))
    assert len(hits) == 1
    hit = hits[0]
    assert hit["id"] == created["id"]
    # outline_id is "<root_index>.<child_index>"; both pieces are positive
    # ints, so the string contains a dot.
    assert "." in hit["outline_id"]
