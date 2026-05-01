# OmniPlan omniJS Persistence Gaps

**Verified empirically against OmniPlan 4.10.2 (build 24G419) on macOS 15.7.3, 2026-05-01.**

This document catalogues every property/method on the omniJS surface that this fork
probed and found to behave incorrectly under the standard
`Application('OmniPlan').evaluateJavascript(...)` bridge that `src/omniplan_mcp/jxa.py`
uses. They fall into three categories:

1. **Persistence gaps** — write succeeds inline (within a single `evaluateJavascript`
   call) but the value vanishes on the next call.
2. **Read opacity** — value is set correctly and persists, but the read returns an
   opaque object with no accessor that exposes its content.
3. **Missing methods** — the SDEF AppleScript surface has the operation but the omniJS
   class surface lacks an equivalent method.

All three classes block features cleanly written against omniJS. Where a workaround
exists in another bridge (JXA SDEF specifiers via `app.documents()[0].project...`) it
is noted, but the workaround is intentionally **out of scope for this fork** — the
`jxa.py` bridge is settled and dedicated to omniJS.

When OmniGroup ships a release that closes any of these gaps, the corresponding
`pytest.mark.xfail(strict=True)` sentinel test goes RED, alerting us to revive the
implementation.

---

## 1. Persistence gaps (write inline, lost across calls)

The pattern: `obj.prop = value` succeeds without throwing, and reading `obj.prop`
later in the *same* `evaluateJavascript` call returns the value. But on the next
JXA invocation, `typeof obj.prop === 'undefined'` again. The control case
`task.manualStartDate` rules out a generic Date / serialization / evaluator-context
issue — manual dates persist correctly.

| Property / API | Class | Probed | Branch | Status |
|---|---|---|---|---|
| `task.startConstraintDate` | Task | 2026-05-01 | `feat/constraints` | xfail sentinel |
| `task.startBeforeDate` | Task | 2026-05-01 | `feat/constraints` | xfail sentinel |
| `task.endAfterDate` | Task | 2026-05-01 | `feat/constraints` | xfail sentinel |
| `task.endBeforeDate` | Task | 2026-05-01 | `feat/constraints` | xfail sentinel |
| `dep.leadTimeDuration` | Dependency | 2026-05-01 | `feat/dependencies` | accepted on write, returns `null` on read |
| `assignment.units` | Assignment | 2026-05-01 | `feat/resources` | accepted on write, returns `null` on read |
| `actual.currency` | Scenario | 2026-05-01 | `feat/project-info` | omitted from `update_project` |

**Hypothesis:** these properties have SDEF-bound setters (cocoa key prefix `script*`)
that the AppleScript bridge wires through, but the omniJS surface synthesizes them as
ad-hoc JS object properties at evaluation time. The assignment lands on the JS object,
not the underlying OmniPlan model, so it disappears with the JS context.

**Verification recipe (general):**

```javascript
// step 1, in one evaluateJavascript call:
const t = document.project.actual.rootTask.addSubtask();
t.title = '__probe__';
t.startConstraintDate = new Date(2027, 0, 1);
const id = String(t.uniqueID);
// returns id

// step 2, in a SECOND evaluateJavascript call:
const t = /* re-find by id via descendents() */;
typeof t.startConstraintDate;  // → 'undefined'   ← the bug
typeof t.manualStartDate;      // → 'object'      ← control case
```

---

## 2. Read opacity (writes persist, reads return opaque objects)

The value is set correctly and the underlying model retains it. But the omniJS
accessor returns an object with no exposed `.seconds` / `.value` / `.valueOf()` /
`Number()` / `JSON.stringify()` path that recovers the numeric content.

| Property / API | Returns | Workaround |
|---|---|---|
| `dep.leadTimeDuration` | `Duration` | none — `String()` is `"[object Duration]"` (no value) |
| `task.duration` | `Duration` | none |
| `r.costPerUse` | `Decimal` | partial — `String(d)` is `"[object Decimal: 100.00]"`; we regex out the number |
| `actual.rootResource.schedule` | (opaque) | none — full work-week schedule is unreachable |

**Note on `task.effort`:** unlike `task.duration`, `task.effort` *does* return as a
plain Number (verified). We don't know why these two diverge; they may have different
cocoa accessor implementations.

---

## 3. Missing methods (no omniJS equivalent for SDEF operations)

| Operation | SDEF | omniJS | Branch | Status |
|---|---|---|---|---|
| Move task to new parent / sibling | `move` (NSMoveCommand) | none — no `moveTo` / `insertAfter` / `reparent` / `appendTo` / `prependTo` | `feat/move-task` | xfail sentinel |
| Enumerate all scenarios | `<element type="scenario"/>` | none — `proj.scenarios` is undefined | `feat/project-info` | reported as `["Actual"]` only |

**Why we don't fall back to SDEF for `move_task`:** a direct probe of
`app.documents()[0].project.tasks()` returned references whose `.title()` accessor
failed in a fresh JXA session. Either the SDEF tasks collection is keyed by something
other than what we tried, or it's not safely reachable. Diagnosing further would
require building the parallel SDEF bridge — out of scope.

**Clone-and-replace doesn't work either:** copying properties into a new task and
removing the old one would change the task's `uniqueID`, silently breaking every
dependency, assignment, and ID reference made against the old task.

---

## Tools that exposed the gap during implementation

| Tool | Affected | How we shipped |
|---|---|---|
| `add_dependency` | `lead_time_seconds` | Accepts and writes via `Duration.workSeconds(N)`; `list_dependencies` returns `lead_time_seconds: null`. |
| `assign_resource` | `units` | Accepts and echoes the input; reads return null. |
| `update_project` | `currency`, working hours | Currency rejected from API surface. Working hours deferred. |
| `update_task` | constraint dates | `xfail` sentinel only; not on the public API. |
| `move_task` | (entire feature) | Not implemented; `xfail` sentinel only. |

---

## Sentinels (`pytest.mark.xfail(strict=True)`)

These tests go **RED** the day OmniGroup closes a gap. Reviving the corresponding
implementation should be the first step when that happens.

- `tests/integration/test_constraints.py::test_constraint_dates_persist_across_calls`
- `tests/integration/test_move_task.py::test_move_task_method_exists`

`lead_time_seconds`, `assignment.units`, and `currency` don't have dedicated
sentinels — they're documented in the relevant module docstrings, and re-running the
existing integration tests with their assertions tightened would surface a fix.

---

## What we'd need from OmniGroup

1. **Persist constraint dates through omniJS.** `task.startConstraintDate` etc. should
   either persist across `evaluateJavascript` calls (writes land on the model) or
   throw on assignment if they're truly read-only.
2. **Expose Duration / Decimal accessors.** A `.seconds` getter on `Duration` and a
   `.toFloat()` (or similar) on `Decimal` would unblock several round-trip reads.
3. **Add `task.moveTo(newParent, beforeSibling?)` or equivalent.** No outline editor
   without it.
4. **Fix `assignment.units` persistence.** Same shape as constraint dates.
5. **Expose `proj.scenarios` enumeration.** Even read-only would let us list and
   compare baselines properly.

Email sent to `omniplan@omnigroup.com` 2026-05-01 referencing this document. See
`dev-docs/TODO.md` for the response-check follow-up.
