# OmniPlan 4.10.3 beta v232.5.9 — omniJS-gap probe results

**Date:** 2026-05-07
**Build under test:** OmniPlan 4.10.3 test, v232.5.9-e7066d2251
  ([omnistaging](https://omnistaging.omnigroup.com/omniplan/),
  released 2026-05-06 21:46 PDT)
**Source email:** OG ticket #3107771, Ken Case → John, 2026-05-06 17:05 PDT.
  Quote: *"Test builds with these Omni Automation improvements are now available."*
**Test environment:** Tart VM `omniplan-4.10.3-v232.5.9-beta` (cloned
  from `omniplan-dev`, persistent — see Licensing note below).
**Probe scripts:** `/tmp/omniplan-beta-probe.js` + `/tmp/omniplan-beta-runner.js`
  on the VM (also archived alongside this report at session close).

## TL;DR

The two omniJS gaps from OG #3107771 are **closed** in this beta.

| Gap | Status | Evidence |
|---|---|---|
| Task reparent (`task.move`) | ✅ verified — works, ID preserved | functional probe — see "Task.move" below |
| Resource reparent (`resource.move`) | ✅ accessor exists; functional test deferred | `Resource.prototype.move` present at depth 0 |
| `Decimal` value extraction | ✅ verified — direct `.toString()` returns numeric form | "Decimal" below |

## Task.move — Verified

**API shape:**
```js
task.move(newParent, index)   // BOTH args required
```
Calling `task.move(newParent)` (one arg) raises:
> `Error: Function Task.move argument "index" at index 1 requires a non-null value`

**Functional probe result (parentA → parentB):**
```
beforeMove: { childParentTitle: "PROBE-parentA", parentACount: 1, parentBCount: 0 }
afterMove:  { childParentTitle: "PROBE-parentB", parentACount: 0, parentBCount: 1,
              parentBContainsChild: true, childIdPreserved: true }
```

**Why this matters:** the long-standing reparent gap is what blocked the
`feat/move-task` work — every previous workaround (clone-and-replace,
`subtasks.push`, `task.parent =`) either silently no-op'd or broke
dependency/assignment references by changing `uniqueID`. This API
preserves `uniqueID`, so the existing dependency graph survives a move.

## Resource.move — accessor exists, functional test deferred

`Resource.prototype.move` is present (descriptor `accessor(get+set)` at
depth 0). I did not run a functional probe because the existing codebase
creates resources via `rootResource.addMember()` (members tree, not
`addChildResource`), and verifying Resource.move's signature is enough
follow-up to keep separate from this beta evaluation.

**Likely identical signature** (`resource.move(newParent, index)`) given
Ken's email said the same accessor + method were added to both classes,
but unverified.

## Decimal toString — Verified

Per Ken's correction, the right round-trip is **`Decimal.fromString(s).toString()`**
(not `String(d)`). Probe confirms:

```
Decimal.fromString("100.00").toString()   = "100"      // trailing zeros dropped
Decimal.fromString("100.50").toString()   = "100.5"    // trailing zero dropped
Decimal.fromString("-12.5").toString()    = "-12.5"
Decimal.fromString("0").toString()        = "0"
Decimal.fromString("1.5").add(Decimal.fromString("2.25")).toString() = "3.75"
String(Decimal.fromString("100.00"))      = "[object Decimal: 100]"   // legacy form, still present
```

**Implications for `src/omniplan_mcp/resources.py`:** The current regex
`String(d).match(/Decimal:\s*(-?[0-9.]+)/)` can be replaced with a
direct `d.toString()` and a `parseFloat(...)`. Trailing-zero behaviour
is unchanged ("100.50" → "100.5"), so any test that currently relies on
the regex output stays correct under the new path.

## Things still missing / weird

- **`Task.prototype.parent` is not visible to `Object.getOwnPropertyDescriptor`
  prototype walks** (depth -1 / "missing"), but reading `task.parent`
  on instances returns the parent task (or `null` for root). Treat it
  as a hidden accessor — it works.
- **`Task.prototype.containingProject`** still missing in this build
  (was missing before too — not part of this email exchange).
- **Resource creation API** uses `addMember()`, not `addChildResource` /
  `addSubresource`. Documented in `resources.py` but worth noting if
  Ken's email implied a parallel naming.
- **`task.uniqueID`** for the root task is the number `-1`. For real
  child tasks it's a positive integer (a number, not a string). Existing
  codebase already converts via `String(task.uniqueID)` everywhere.

## Next actions (queued, not done)

1. **Implement `move_task(task_id, new_parent_id, index=None)` MCP tool**
   in `tasks.py`. Find task + parent by `uniqueID`, call
   `t.move(parent, index ?? parent.subtasks.length)`. ~30 minutes.
2. **Flip the xfail sentinel** at `tests/integration/test_move_task.py`
   to a positive integration test once #1 lands.
3. **Functional probe for `resource.move`** to confirm signature parity
   with Task. ~15 minutes.
4. **Simplify Decimal parser** in `src/omniplan_mcp/resources.py` —
   replace the regex with a direct `Decimal.toString()` + `parseFloat`.
   ~10 minutes. Add a regression test for "100.50" → "100.5".
5. **Re-run the full test suite** in this VM with the beta, to surface
   any other breakages from the "addressed previous misspellings"
   release-note bullet (Omni said API names were renamed — we may have
   silent breakage in field accessors).

## Licensing note (per OG ticket #3108330)

Ken upgraded John's account to a 3-seat team license. He recommended
**persistent VM identity** over ephemeral clones because each new
hardware UUID triggers a fresh receipt registration. This VM
(`omniplan-4.10.3-v232.5.9-beta`) is therefore intended to live as a
long-running clone, not a throwaway. Do **not** destroy + re-clone
casually — it would burn license seats.

The existing `:v2-licensed` golden image was the source clone, so the
account credentials carried over; the beta install on top happened
in-place at `/Applications/OmniPlan.app` (baseline 4.10.2 preserved
side-by-side at `/Applications/OmniPlan-4.10.2-baseline.app` for
rollback).
