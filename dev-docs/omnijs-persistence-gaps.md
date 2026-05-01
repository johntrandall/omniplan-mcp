# OmniPlan omniJS Surface Gaps

**Verified empirically against OmniPlan 4.10.2 (build 232.5.0) on macOS 15.7.3, 2026-05-01.**

This document catalogues every property/method on the omniJS surface that this fork
probed and found to be missing or inadequate under the standard
`Application('OmniPlan').evaluateJavascript(...)` bridge in `src/omniplan_mcp/jxa.py`.

After cross-referencing the canonical class docs at <https://omni-automation.com/omniplan/>
and probing every documented setter, the surface is much smaller than an earlier
draft of this doc claimed. **Most of the "persistence gaps" reported in earlier
drafts were us probing under SDEF AppleScript names that don't exist on the omniJS
classes.** The surviving gaps are limited to:

1. One missing method (task reparenting) — confirmed via three failed paths plus
   a saved-bundle XML inspection.
2. One read-side wart (`Decimal.toString` requires regex parsing) — there's no
   documented number-extraction accessor.

When OmniGroup ships a release that closes either gap, the corresponding
`pytest.mark.xfail(strict=True)` sentinel test goes RED.

---

## 1. Missing methods (no omniJS equivalent for SDEF operations)

| Operation | SDEF | omniJS | Branch / sentinel |
|---|---|---|---|
| Move task to new parent / sibling | `move` (NSMoveCommand) | none — no `moveTo` / `insertAfter` / `reparent` / `appendTo` / `prependTo` / `subtasks.push(...)` mutation / `task.parent = ...` assignment | `feat/move-task` — `tests/integration/test_move_task.py::test_move_task_method_exists` |

**How we verified:** three failure paths, all silent no-ops on the omniJS side.

```javascript
// (1) named methods — none exist on Task.prototype
typeof task.moveTo;       // 'undefined'
typeof task.reparent;     // 'undefined'
typeof task.insertAfter;  // 'undefined'

// (2) subtasks-array mutation — push returns ok, model unchanged
B.subtasks.push(C);              // returns truthy
A.subtasks.length;               // unchanged across calls
B.subtasks.map(t => t.title);    // does not include C

// (3) parent assignment — silent no-op on both names
D.parent = B;       // no throw
D.parentTask = B;   // no throw
typeof D.parent;    // 'undefined'  (still no parent accessor)
```

We also saved the document to a `.oplx` bundle and confirmed `Actual.xml` shows
the original parent in `<child-task idref="...">` after every probe — i.e. the
attempts never reach the underlying model.

The SDEF AppleScript bridge does expose a `move` command (NSMoveCommand) for
tasks. Reaching it requires a parallel JXA SDEF bridge separate from
`evaluateJavascript`, which is **out of scope for this fork**.

**Clone-and-replace doesn't substitute for a real move:** copying properties to
a new task and removing the old one would change `uniqueID`, silently breaking
every dependency, assignment, and ID reference made against the old task.

---

## 2. Read-side opacity workarounds

| Property / API | Returns | Workaround in this fork |
|---|---|---|
| `r.costPerUse` | `Decimal` | `String(d)` is `"[object Decimal: 100]"`. We regex `Decimal:\s*(-?[0-9.]+)` to recover the number. **Note:** `Decimal.fromString("100.00")` round-trips with trailing zeros collapsed, so `100.00` reads back as `100`. The documented `Decimal` class has `add` / `subtract` / `multiply` / `divide` / `compare` / `equals` / `toString` — no number-extraction accessor. |

`Duration` is **not** opaque. The documented accessors `workSeconds`,
`elapsedSeconds`, `elapsedDays`, `elapsed` (Boolean), and friends round-trip
correctly. An earlier draft of this doc claimed `Duration` was opaque — that was
us probing for a `.seconds` accessor (which doesn't exist) and never trying
`workSeconds` (which does). `add_dependency` / `list_dependencies` now round-trip
`lead_time_seconds` via `Duration.workSeconds`.

`actual.rootResource.schedule` is genuinely opaque on read in the omniJS surface
(no accessor returns the day/time-span structure), but writes are also unsupported,
so we deferred working-hours editing rather than shipping a half-feature.

---

## 3. Properties that actually round-trip (debunked claims)

These were reported as broken in earlier drafts of this doc and the README. Each
was re-probed under the **documented** omniJS class name and verified to
round-trip across separate `evaluateJavascript` calls:

| Earlier claim | Reality |
|---|---|
| `task.startConstraintDate` "value lost across calls" | Wrong name. Documented name is `task.startNoEarlierThanDate` (Date or null). Round-trips correctly. Tier 1 `update_task` now exposes it along with `startNoLaterThanDate` / `endNoEarlierThanDate` / `endNoLaterThanDate`. |
| `dep.leadTimeDuration` "Duration is opaque on read" | Wrong probe. `dep.leadTimeDuration.workSeconds` returns the integer seconds. Round-trips. |
| `assignment.units` "write doesn't persist" | Wrong name. Documented setter is `assignment.unitsAssigned` (Number, read/write). Round-trips. |
| `actual.currency` "same persistence trap" | Inconclusive. Write accepted inline, but the value does not persist across `evaluateJavascript` boundaries. May be a real gap — but we did not pursue it further because currency editing is low-value and we don't have a confident probe matrix yet. Currency is omitted from `update_project` rather than shipping a footgun. |
| `proj.scenarios` "undefined" | Wrong API. Documented enumeration is `proj.baselineNames` (Array of String), with `proj.baselineNamed(name)` for lookup. `get_project_info` now returns `scenarios: ["Actual", ...proj.baselineNames]`. |

**Methodology for the corrections:** read the canonical class docs at
<https://omni-automation.com/omniplan/{tasks,dependencies,assignments,projects,scenarios,duration}.html>;
probe each setter under the documented name; for date fields, control with
`task.manualStartDate` (known to round-trip) using identical input; cross-check
with the saved `.oplx` `Actual.xml` to confirm writes actually reach the
underlying model.

---

## What we asked OmniGroup

Email sent 2026-05-01 to `omniplan@omnigroup.com` (Gmail message ID
`19de54f80526a865`), subject "OmniPlan 4.10.2 omniJS — two small documented gaps
(task reparent, Decimal accessor)". Two questions:

1. Is task reparenting deliberately omitted from the omniJS Task class, or
   should we use a method we missed?
2. Is there a documented accessor on `Decimal` to extract a Number, or is
   `String(d)` parsing the supported path?

A status check is scheduled via the Anthropic Cloud routine
`trig_019hMu6Mpt1sAWwLhA64n5kQ` for 2026-05-22.

---

## Lessons (cross-cutting — captured for future work)

This doc went through ~9 wrong drafts before the surface settled. The mistakes
clustered into one anti-pattern: **probing under SDEF property names instead of
reading the documented omniJS class.** SDEF and omniJS are two surfaces with
overlapping but distinct vocabularies. Examples we tripped on:

| SDEF name | omniJS name | What we shipped after the fix |
|---|---|---|
| `start constraint date` | `startNoEarlierThanDate` | `update_task(start_no_earlier_than=...)` |
| `lead time` | `leadTimeDuration` (with `.workSeconds` accessor) | `add_dependency(lead_time_seconds=...)` round-trips |
| `units` | `unitsAssigned` (on Assignment) | `assign_resource(units=...)` round-trips |
| `scenarios` (collection of scenario) | `baselineNames` (Array of String) on Project | `get_project_info` returns real list |

The `troubleshooting-sanity` skill (in `~/.claude/skills/`) captures the broader
methodology that fell out of this episode: read the vendor's class docs first,
verify writes landed (don't infer from read failures), and isolate before
escalating bug claims.
