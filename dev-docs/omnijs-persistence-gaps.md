# OmniPlan omniJS Surface Gaps

**Originally verified against OmniPlan 4.10.2 (build 232.5.0) on macOS 15.7.3, 2026-05-01.**
**Both gaps closed in OmniPlan 4.10.3 (test build v232.5.9, 2026-05-06) — see "Status: closed in 4.10.3+" notes inline below.**

This document catalogues every property/method on the omniJS surface that this fork
probed and found to be missing or inadequate under the standard
`Application('OmniPlan').evaluateJavascript(...)` bridge in `src/omniplan_mcp/jxa.py`.

After cross-referencing the canonical class docs at <https://omni-automation.com/omniplan/>
and probing every documented setter, the surface is much smaller than an earlier
draft of this doc claimed. **Most of the "persistence gaps" reported in earlier
drafts were us probing under SDEF AppleScript names that don't exist on the omniJS
classes.** The surviving 4.10.2 gaps were limited to:

1. One missing method (task reparenting) — confirmed via three failed paths plus
   a saved-bundle XML inspection. **Closed in 4.10.3** — `task.move(parent, index)`
   and `resource.move(parent, index)` shipped per OG ticket #3107771. MCP surfaces
   them as `move_task` / `move_resource` (v0.4.5+).
2. One read-side wart (`Decimal.toString` requires regex parsing) — there's no
   documented number-extraction accessor. **Closed in 4.10.3 (clarification, not
   API change)** — Ken Case @ Omni confirmed `Decimal.fromString(s).toString()`
   returns the numeric form directly (`"100"`); only `String(d)` produces the
   `"[object Decimal: 100]"` wrapper. The regex workaround is retired in v0.4.5;
   the helper handles both shapes for backward-compat with 4.10.2.

The historical detail below is preserved as the empirical record that drove the
OmniGroup conversation (OG #3107771) and the v0.4.5 ship.

See `dev-docs/beta-v232.5.9-probe-results.md` for the full beta verification report.

---

## 1. Missing methods (no omniJS equivalent for SDEF operations) — CLOSED in 4.10.3

**Status: closed in OmniPlan 4.10.3 (build v232.5.7+, public release imminent).**
The MCP exposes the new API as `move_task` / `move_resource` from v0.4.5 onward.
On older builds those tools raise a clear "requires 4.10.3+" error.

The historical 4.10.2 gap (preserved for context):

| Operation | SDEF | omniJS in 4.10.2 | omniJS in 4.10.3 |
|---|---|---|---|
| Move task to new parent / sibling | `move` (NSMoveCommand) | none — no `moveTo` / `insertAfter` / `reparent` / `appendTo` / `prependTo` / `subtasks.push(...)` mutation / `task.parent = ...` assignment | **`task.move(newParent, index)`** — both args required; `uniqueID` preserved |
| Move resource within group hierarchy | `move` (NSMoveCommand) | (same gap) | **`resource.move(newParent, index)`** — same signature, signature parity verified |

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

## 2. Read-side opacity workarounds — Decimal CLOSED via clarification

**Status: Decimal closed in 4.10.3+ (the API was always there; the wart was that
we were calling it wrong).** Per Ken Case @ Omni (OG #3107771, 2026-05-06):
`Decimal.fromString(s).toString()` returns the numeric form directly. Only
`String(d)` (which goes through a different coercion path) produces the
`"[object Decimal: 100]"` wrapper that the regex was working around.

The MCP's `decimalToFloat` helper now uses the direct path with a backward-compat
fallback to the wrapper-form regex, in case 4.10.2's `toString()` returned the
wrapper form (untested on 4.10.2; the fallback covers both shapes).

| Property / API | Returns | Recovery |
|---|---|---|
| `r.costPerUse` | `Decimal` | `d.toString()` returns the numeric string directly on 4.10.3+. MCP helper falls back to regex extraction if `toString()` returns the wrapper form (4.10.2 behavior unverified). Trailing zeros are still dropped — `Decimal.fromString("100.00")` reads back as `"100"`, `"100.50"` reads back as `"100.5"` — by NSDecimalNumber design. The documented `Decimal` class has `add` / `subtract` / `multiply` / `divide` / `compare` / `equals` / `toString`; no separate number-extraction accessor exists or is planned (Decimal is `NSDecimalNumber` representation; lossy float round-trips are intentional). |

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
