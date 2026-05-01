"""Regression sentinel for the omniJS constraint-date persistence gap.

Probed live against OmniPlan 4.10.2 on 2026-05-01:

  - Setting `task.startConstraintDate = new Date(...)` (or `endBeforeDate`,
    `startBeforeDate`, `endAfterDate`) within a single `evaluateJavascript`
    call accepts the write and reads back inside that same call.
  - In a separate JXA call (the production code path: write in
    `update_task`, read in `get_task`), the value is GONE — the task's
    omniJS object reads `typeof === "undefined"` again.
  - `task.manualStartDate` (control case) DOES persist across JXA calls.

What's happening: omniJS is being permissive about adding ad-hoc JS
properties to the Task object. The actual cocoa setters
(`scriptStartConstraintDate`, `scriptStartBeforeDate`, etc., per the
`OmniPlan.sdef` accessors) live on the AppleScript bridge — a different
code path from `Application.evaluateJavascript`. Implementing constraint
dates therefore requires a parallel JXA bridge that talks SDEF
specifiers (`doc.project.tasks.whose({title: "..."}).startingConstraintDate
= ...`). That is intentionally out of scope for this fork; `jxa.py`
is settled.

Test policy: `xfail(strict=True)` — this guarantees the suite goes RED
the day Omni wires constraint dates through to omniJS persistently, at
which point we delete the xfail markers, revive the implementation
that was prototyped on this branch, and ship the feature.

Reference: `dev-docs/ROADMAP.md` "Tier 1 — known omniJS gaps" section.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.requires_omniplan,
    pytest.mark.xfail(
        reason=(
            "omniJS task.startConstraintDate / endBeforeDate / startBeforeDate / "
            "endAfterDate accept writes within a single evaluateJavascript call "
            "but do not persist across JXA boundaries — verified empirically on "
            "OmniPlan 4.10.2 (2026-05-01). Persistent setters live on the SDEF "
            "AppleScript bridge (scriptStartConstraintDate etc.), which would "
            "require a parallel non-omniJS bridge. Out of scope for this fork."
        ),
        strict=True,
    ),
]


def test_constraint_dates_persist_across_calls() -> None:
    """Sentinel: when this passes, omniJS persistence is fixed and we
    can revive the constraint-date implementation. See module docstring."""
    raise AssertionError("Stub — see module docstring for the unimplemented feature.")
