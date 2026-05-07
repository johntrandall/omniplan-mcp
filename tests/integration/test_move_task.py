"""Regression sentinel for the omniJS move-task gap.

History:

  - 2026-05-01: Initial probe (OmniPlan 4.10.2, build 232.5.0) found
    the Task class exposed no `move` / `moveTo` / `reparent` etc. — all
    documented mutating methods stopped at `addSubtask`, `remove`, etc.
    Filed OG ticket #3107771.
  - 2026-05-06: Ken Case (Omni) replied that `parent` accessor and
    `move` method were added to both Task and Resource. Test build
    posted at <https://omnistaging.omnigroup.com/omniplan/>.
  - 2026-05-07: Verified live against OmniPlan 4.10.3 test v232.5.9 in
    a persistent Tart VM (see `dev-docs/drafts/beta-v232.5.9-probe-results.md`).
    Confirmed signature: `task.move(newParent, index)` — BOTH args
    required, `uniqueID` preserved across the move.

Test policy: still `xfail(strict=True)` until the `move_task` MCP tool
ships — at that point, replace this sentinel with a real positive
integration test (create three tasks, move one, assert structure +
preserved id) and drop the xfail marker.

Reference: `dev-docs/ROADMAP.md` "Tier 1 — known omniJS gaps" section,
and the probe report linked above.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.requires_omniplan,
    pytest.mark.xfail(
        reason=(
            "Beta v232.5.9 of OmniPlan 4.10.3 verified the omniJS API: "
            "task.move(newParent, index) works and preserves uniqueID. "
            "Sentinel stays xfail-strict until the move_task MCP tool "
            "ships and this stub is replaced with a real integration test."
        ),
        strict=True,
    ),
]


def test_move_task_method_exists() -> None:
    """Sentinel: when the move_task tool ships, replace this with a
    real positive test and drop the xfail. See module docstring."""
    raise AssertionError("Stub — move_task MCP tool not yet implemented.")
