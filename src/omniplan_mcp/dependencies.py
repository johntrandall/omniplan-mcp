"""Task-dependency tools.

Verified omniJS surface (per the documented Duration class at
https://omni-automation.com/omniplan/duration.html and probed live
against OmniPlan 4.10.2):

  - `task.addDependent(other) -> Dependency` — creates a dependency with
    `kind = DependencyKind.FinishStart` by default. Set `dep.kind = ...`
    to change after construction.
  - `DependencyKind` enum values: `FinishStart`, `FinishFinish`,
    `StartStart`, `StartFinish`. Their `String()` form is
    `"[object DependencyKind: FinishStart]"` etc. — we parse the trailing
    name to map back to the wire shorthand (FS / FF / SS / SF).
  - `task.dependents` (array of Dependency where this task is the
    prerequisite), `task.prerequisites` (this task is the dependent).
  - `dep.prerequisite`, `dep.dependent` — Task references with `uniqueID`.
  - `dep.remove()` — deletes the dependency from both endpoints.
  - `dep.leadTimeDuration` — read/write a `Duration` object. Build for
    write via `Duration.workSeconds(N)`. Read the value back via
    `dep.leadTimeDuration.workSeconds` (Number, read-only) — pairs
    symmetrically with the write side. Earlier sessions wrongly thought
    Duration was opaque; the documented accessors (`workSeconds`,
    `elapsed`, `elapsedSeconds`, etc.) round-trip cleanly.
"""
from __future__ import annotations

import json
from typing import Optional

from omniplan_mcp.jxa import run_omnijs
from omniplan_mcp.server import mcp

KIND_TO_OMNIJS: dict[str, str] = {
    "FS": "FinishStart",
    "SS": "StartStart",
    "FF": "FinishFinish",
    "SF": "StartFinish",
}
OMNIJS_TO_KIND: dict[str, str] = {v: k for k, v in KIND_TO_OMNIJS.items()}


def _validate_kind(kind: str) -> str:
    if kind not in KIND_TO_OMNIJS:
        raise ValueError(
            f"Unknown dependency kind {kind!r}. Expected one of: "
            f"{', '.join(sorted(KIND_TO_OMNIJS))}."
        )
    return KIND_TO_OMNIJS[kind]


_KIND_PARSER_JS = """
function parseKind(k) {
  // String(DependencyKind.FinishStart) -> "[object DependencyKind: FinishStart]".
  // Pull the trailing name and map it back to the wire shorthand.
  var s = String(k);
  var m = s.match(/DependencyKind:\\s*(\\w+)/);
  if (!m) return null;
  switch (m[1]) {
    case 'FinishStart':  return 'FS';
    case 'StartStart':   return 'SS';
    case 'FinishFinish': return 'FF';
    case 'StartFinish':  return 'SF';
    default:             return null;
  }
}
"""


@mcp.tool()
async def add_dependency(
    predecessor_id: str,
    successor_id: str,
    kind: str = "FS",
    lead_time_seconds: int = 0,
) -> str:
    """Add a dependency from predecessor to successor.

    Args:
        predecessor_id: uniqueID of the prerequisite task.
        successor_id: uniqueID of the dependent task.
        kind: One of "FS" (finish-to-start, default), "SS", "FF", "SF".
        lead_time_seconds: Lead time before the successor can start, in
            work-seconds. Defaults to 0. Negative values are not supported
            here; if you need lag in the other direction, model it as a
            different dependency kind.

    Returns:
        JSON `{predecessor_id, successor_id, kind, lead_time_seconds}`.
        `lead_time_seconds` is read back via
        `dep.leadTimeDuration.workSeconds` after the write — a true
        round-trip, not an echo. When no Duration is set on the
        dependency (e.g. lead_time_seconds=0), the field is reported as
        `0` rather than `null`.
    """
    omnijs_kind = _validate_kind(kind)
    lead = max(0, int(lead_time_seconds))

    set_lead = (
        f"dep.leadTimeDuration = Duration.workSeconds({lead});"
        if lead > 0
        else ""
    )

    script = f"""
const _proj = document.project;
const root = _proj.actual.rootTask;

function findById(task, id) {{
  if (String(task.uniqueID) === id) return task;
  for (let i = 0; i < task.subtasks.length; i++) {{
    const found = findById(task.subtasks[i], id);
    if (found) return found;
  }}
  return null;
}}

const pre = findById(root, {json.dumps(predecessor_id)});
if (!pre) throw new Error('Predecessor task not found: ' + {json.dumps(predecessor_id)});
const suc = findById(root, {json.dumps(successor_id)});
if (!suc) throw new Error('Successor task not found: ' + {json.dumps(successor_id)});

const dep = pre.addDependent(suc);
dep.kind = DependencyKind.{omnijs_kind};
{set_lead}

// When no Duration is set on the dependency, leadTimeDuration is null;
// surface that as 0 (semantically equivalent — no lead time).
const ltd = dep.leadTimeDuration;
return {{
  predecessor_id: String(pre.uniqueID),
  successor_id: String(suc.uniqueID),
  kind: {json.dumps(kind)},
  lead_time_seconds: ltd ? ltd.workSeconds : 0,
}};
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def remove_dependency(
    predecessor_id: str,
    successor_id: str,
) -> str:
    """Remove the dependency between two tasks.

    Args:
        predecessor_id: uniqueID of the prerequisite task.
        successor_id: uniqueID of the dependent task.

    Returns:
        JSON `{"removed": true}` if a matching dependency was found and
        removed, `{"removed": false}` if no such dependency existed.
    """
    script = f"""
const _proj = document.project;
const root = _proj.actual.rootTask;

function findById(task, id) {{
  if (String(task.uniqueID) === id) return task;
  for (let i = 0; i < task.subtasks.length; i++) {{
    const found = findById(task.subtasks[i], id);
    if (found) return found;
  }}
  return null;
}}

const pre = findById(root, {json.dumps(predecessor_id)});
if (!pre) throw new Error('Predecessor task not found: ' + {json.dumps(predecessor_id)});
const sucId = {json.dumps(successor_id)};

let removed = false;
for (let i = 0; i < pre.dependents.length; i++) {{
  const dep = pre.dependents[i];
  if (dep.dependent && String(dep.dependent.uniqueID) === sucId) {{
    dep.remove();
    removed = true;
    break;
  }}
}}
return {{ removed: removed }};
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def list_dependencies(
    task_id: Optional[str] = None,
) -> str:
    """List dependencies in the document.

    Args:
        task_id: Optional uniqueID. If provided, only dependencies where
            the task is the predecessor or successor are returned. If
            omitted, every dependency in the document is returned.

    Returns:
        JSON array of `{"predecessor_id", "successor_id", "kind",
        "lead_time_seconds"}`. `lead_time_seconds` is read from
        `dep.leadTimeDuration.workSeconds`; it is `null` only when no
        lead-time Duration is set on the dependency.
    """
    filter_clause = (
        f"if (preId !== {json.dumps(task_id)} && sucId !== {json.dumps(task_id)}) continue;"
        if task_id
        else ""
    )

    script = f"""
const _proj = document.project;
const root = _proj.actual.rootTask;

{_KIND_PARSER_JS}

const all = [root].concat(root.descendents());
const seen = new Set();
const out = [];
for (const t of all) {{
  for (let i = 0; i < t.dependents.length; i++) {{
    const dep = t.dependents[i];
    if (!dep.prerequisite || !dep.dependent) continue;
    const preId = String(dep.prerequisite.uniqueID);
    const sucId = String(dep.dependent.uniqueID);
    {filter_clause}
    const key = preId + '->' + sucId;
    if (seen.has(key)) continue;
    seen.add(key);
    // When no Duration is set, leadTimeDuration is null; surface as 0.
    const ltd = dep.leadTimeDuration;
    out.push({{
      predecessor_id: preId,
      successor_id: sucId,
      kind: parseKind(dep.kind) || 'FS',
      lead_time_seconds: ltd ? ltd.workSeconds : 0,
    }});
  }}
}}
return out;
"""
    result = await run_omnijs(script)
    return json.dumps(result)
