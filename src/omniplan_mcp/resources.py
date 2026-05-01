"""Resource CRUD + task-resource assignments.

Verified omniJS surface (probed live 2026-05-01 against OmniPlan 4.10.2):

  - `actual.rootResource.addMember() -> Resource`
  - `r.name`, `r.email`, `r.type` — string/string/ResourceType, all persist
  - `r.type = ResourceType.{staff|equipment|material|group}`
  - `r.costPerUse = Decimal.fromString("100.00")` — write requires a
    Decimal, NOT a Number ("Property Resource.costPerUse requires a
    value of type Decimal" otherwise). On read, `r.costPerUse` is a
    Decimal object whose `String()` form is `"[object Decimal: 100]"`
    — we parse the trailing number.
  - `r.uniqueID` — string, stable
  - `r.remove()` — deletes
  - `task.addAssignment(resource) -> Assignment`
  - `task.assignments` — array of Assignment objects
  - `assignment.resource` — Resource ref
  - `assignment.remove()` — deletes the assignment

Known omniJS gap surfaced during probing — `assignment.units` does not
persist across JXA call boundaries (same trap as `dep.leadTimeDuration`
and `task.startConstraintDate`). Tools accept `units` on write but
return `null` on read.
"""
from __future__ import annotations

import json
from typing import Optional

from omniplan_mcp.jxa import run_omnijs
from omniplan_mcp.server import mcp

VALID_RESOURCE_TYPES = {"staff", "equipment", "material", "group"}


_RESOURCE_OBJ_HELPER = """
function decimalToFloat(d) {
  if (d === null || d === undefined) return null;
  if (typeof d === 'number') return d;
  // String(Decimal) is "[object Decimal: 100.00]"; pull the number.
  var m = String(d).match(/Decimal:\\s*(-?[0-9.]+)/);
  return m ? parseFloat(m[1]) : null;
}
function typeName(t) {
  // String(ResourceType.staff) is "[object ResourceType: staff]".
  var s = String(t);
  var m = s.match(/ResourceType:\\s*(\\w+)/);
  return m ? m[1] : 'unknown';
}
function resourceToObj(r) {
  return {
    id: String(r.uniqueID),
    name: r.name || '',
    type: typeName(r.type),
    email: r.email || null,
    cost_per_use: decimalToFloat(r.costPerUse),
  };
}
"""


def _validate_type(rtype: str) -> None:
    if rtype not in VALID_RESOURCE_TYPES:
        raise ValueError(
            f"Unknown resource type {rtype!r}. Expected one of: "
            f"{', '.join(sorted(VALID_RESOURCE_TYPES))}."
        )


@mcp.tool()
async def list_resources() -> str:
    """List all resources in the document.

    Returns:
        JSON array of `{id, name, type, email, cost_per_use}`. Walks
        the rootResource tree depth-first; group resources are flattened
        out (their leaf members appear individually).
    """
    script = f"""
{_RESOURCE_OBJ_HELPER}

const root = document.project.actual.rootResource;
const out = [];
function walk(g) {{
  for (let i = 0; i < g.members.length; i++) {{
    const m = g.members[i];
    out.push(resourceToObj(m));
    if (m.members && m.members.length) walk(m);
  }}
}}
walk(root);
return out;
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def create_resource(
    name: str,
    type: str = "staff",
    email: Optional[str] = None,
    cost_per_use: Optional[float] = None,
) -> str:
    """Create a new resource at the document's resource root.

    Args:
        name: Resource name.
        type: One of "staff" (default), "equipment", "material", "group".
        email: Optional email address (relevant mainly for staff).
        cost_per_use: Optional cost in the document's currency. Stored
            as a Decimal — writes go through `Decimal.fromString(...)`
            so float inputs round-trip without Number precision issues.

    Returns:
        JSON `{id, name, type, email, cost_per_use}` for the new resource.
    """
    _validate_type(type)
    set_email = (
        f"r.email = {json.dumps(email)};" if email is not None else ""
    )
    set_cost = (
        f"r.costPerUse = Decimal.fromString({json.dumps(format(cost_per_use, 'f'))});"
        if cost_per_use is not None
        else ""
    )

    script = f"""
{_RESOURCE_OBJ_HELPER}

const root = document.project.actual.rootResource;
const r = root.addMember();
r.name = {json.dumps(name)};
r.type = ResourceType.{type};
{set_email}
{set_cost}
return resourceToObj(r);
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def delete_resource(
    resource_id: str,
) -> str:
    """Delete a resource by uniqueID.

    Args:
        resource_id: uniqueID of the resource to delete.

    Returns:
        JSON `{deleted: bool, id, name}`. `deleted` is true when a
        matching resource was found and removed, false if not found.
        Removing a resource that is currently assigned to tasks
        succeeds — OmniPlan strips the assignments.
    """
    script = f"""
const root = document.project.actual.rootResource;
const target_id = {json.dumps(resource_id)};
function findRes(g) {{
  for (let i = 0; i < g.members.length; i++) {{
    const m = g.members[i];
    if (String(m.uniqueID) === target_id) return m;
    if (m.members && m.members.length) {{
      const sub = findRes(m); if (sub) return sub;
    }}
  }}
  return null;
}}
const r = findRes(root);
if (!r) {{
  return {{ deleted: false, id: target_id, name: null }};
}}
const name = r.name;
r.remove();
return {{ deleted: true, id: target_id, name: name }};
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def assign_resource(
    task_id: str,
    resource_id: str,
    units: Optional[float] = None,
) -> str:
    """Assign a resource to a task.

    Args:
        task_id: uniqueID of the task.
        resource_id: uniqueID of the resource.
        units: Optional fractional allocation (1.0 = 100% of a staff
            resource's working hours). The omniJS API accepts the write
            but the value does NOT persist across JXA boundaries (same
            trap as `dep.leadTimeDuration`). The returned shape reports
            `units: null` even when a value was passed in.

    Returns:
        JSON `{task_id, resource_id, units}`. `units` always echoes the
        value passed in — this is a write-only confirmation, not a true
        round-trip read.
    """
    set_units = (
        f"a.units = {float(units)};" if units is not None else ""
    )
    units_echo = "null" if units is None else f"{float(units)}"

    script = f"""
const target_task_id = {json.dumps(task_id)};
const target_res_id = {json.dumps(resource_id)};

function findTask(t, id) {{
  if (String(t.uniqueID) === id) return t;
  for (const c of t.subtasks) {{
    const f = findTask(c, id); if (f) return f;
  }}
  return null;
}}
function findRes(g, id) {{
  for (let i = 0; i < g.members.length; i++) {{
    const m = g.members[i];
    if (String(m.uniqueID) === id) return m;
    if (m.members && m.members.length) {{
      const sub = findRes(m, id); if (sub) return sub;
    }}
  }}
  return null;
}}
const actual = document.project.actual;
const task = findTask(actual.rootTask, target_task_id);
if (!task) throw new Error('Task not found: ' + target_task_id);
const res = findRes(actual.rootResource, target_res_id);
if (!res) throw new Error('Resource not found: ' + target_res_id);

const a = task.addAssignment(res);
{set_units}

return {{ task_id: target_task_id, resource_id: target_res_id, units: {units_echo} }};
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def unassign_resource(
    task_id: str,
    resource_id: str,
) -> str:
    """Remove a resource assignment from a task.

    Args:
        task_id: uniqueID of the task.
        resource_id: uniqueID of the resource.

    Returns:
        JSON `{removed: bool}`. True when a matching assignment was
        found and removed, false otherwise.
    """
    script = f"""
const target_task_id = {json.dumps(task_id)};
const target_res_id = {json.dumps(resource_id)};

function findTask(t, id) {{
  if (String(t.uniqueID) === id) return t;
  for (const c of t.subtasks) {{
    const f = findTask(c, id); if (f) return f;
  }}
  return null;
}}
const actual = document.project.actual;
const task = findTask(actual.rootTask, target_task_id);
if (!task) throw new Error('Task not found: ' + target_task_id);

let removed = false;
for (let i = 0; i < task.assignments.length; i++) {{
  const a = task.assignments[i];
  if (a.resource && String(a.resource.uniqueID) === target_res_id) {{
    a.remove();
    removed = true;
    break;
  }}
}}
return {{ removed: removed }};
"""
    result = await run_omnijs(script)
    return json.dumps(result)
