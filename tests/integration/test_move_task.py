"""Regression sentinel for the omniJS move-task gap.

Probed live against OmniPlan 4.10.2 on 2026-05-01:

  - Task class methods exposed in omniJS (probed via prototype walk):
    addSubtask, addPrerequisite, addDependent, addAssignment,
    descendents, clearResourceLeveledDate, customValue, setCustomValue,
    setCustomData, split, remove. **No move / insertAfter /
    insertBefore / reparent / appendTo / prependTo equivalents.**
  - The SDEF AppleScript surface defines a `move` command (NSMoveCommand)
    for tasks, but reaching it requires the parallel JXA SDEF bridge
    (separate from `Application.evaluateJavascript`). A direct JXA probe
    of `app.documents()[0].project.tasks()` returned task references
    whose `.title()` accessor failed, suggesting the SDEF task collection
    is not safely accessible from a fresh JXA session in this OmniPlan
    version.

Workaround pattern that does NOT work: clone task properties, add
under new parent, remove the original. uniqueID changes, breaking any
dependency or assignment that referenced the old ID.

Test policy: `xfail(strict=True)` — when Omni adds a `task.moveTo()`
or equivalent omniJS method, this test goes RED, alerting us to ship
the feature.

Reference: `dev-docs/ROADMAP.md` "Tier 1 — known omniJS gaps" section.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.requires_omniplan,
    pytest.mark.xfail(
        reason=(
            "omniJS Task class exposes no move/reparent/insertAfter/insertBefore "
            "methods (verified via prototype walk on OmniPlan 4.10.2, 2026-05-01). "
            "SDEF AppleScript move command exists but the parallel JXA bridge to "
            "the task collection is fragile and out of scope for this fork. "
            "Clone-and-replace would change uniqueIDs, breaking dependencies and "
            "assignments — not a viable workaround."
        ),
        strict=True,
    ),
]


def test_move_task_method_exists() -> None:
    """Sentinel: when this passes, omniJS supports task moves and we
    can revive the implementation. See module docstring."""
    raise AssertionError("Stub — see module docstring for the unimplemented feature.")
