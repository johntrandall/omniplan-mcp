"""Resource CRUD + task-resource assignments.

Verified omniJS surface (per the documented Assignment / Resource classes
at https://omni-automation.com/omniplan/ and probed live 2026-05-01
against OmniPlan 4.10.2):

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
  - `assignment.unitsAssigned` — Number, read/write. The earlier
    session probed the wrong property name (`units`) and concluded
    persistence was broken; using the documented `unitsAssigned`
    accessor round-trips cleanly.
  - `assignment.remove()` — deletes the assignment
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
  // Per Ken Case @ Omni (OG #3107771, 2026-05-06): `d.toString()` returns
  // the numeric form directly. `String(d)` goes through a different path
  // that produces "[object Decimal: 100]" — that's what the previous
  // regex was working around. Verified against OmniPlan 4.10.3 v232.5.9
  // (Decimal.fromString("100.00").toString() === "100"; trailing zeros
  // dropped, "100.50" → "100.5").
  var s = d.toString();
  var f = parseFloat(s);
  return isNaN(f) ? null : f;
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
async def move_resource(
    resource_id: str,
    new_parent_id: Optional[str] = None,
    index: Optional[int] = None,
) -> str:
    """Reparent a resource without changing its uniqueID.

    Wraps the omniJS `resource.move(newParent, index)` method introduced
    in OmniPlan 4.10.3 (build v232.5.9, 2026-05-06). Both omniJS args
    are required at the API level; this tool fills in `index` with
    `newParent.members.length` (append at end) when omitted.

    Because uniqueID is preserved across the move, assignments that
    reference the moved resource stay intact — no clone-and-rebuild.

    Args:
        resource_id: uniqueID of the resource to move.
        new_parent_id: uniqueID of the destination group resource. If
            omitted, the resource is moved under the document's
            rootResource.
        index: 0-based position in `new_parent.members`. If omitted,
            appended at the end.

    Returns:
        JSON `{moved: true, id, new_parent_id, index}` where `id` is
        the unchanged uniqueID and `new_parent_id` is the resolved
        parent's uniqueID.
    """
    new_parent_arg = json.dumps(new_parent_id)
    index_arg = "null" if index is None else str(int(index))

    script = f"""
const root = document.project.actual.rootResource;

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

const targetId = {json.dumps(resource_id)};
const res = findRes(root, targetId);
if (!res) throw new Error('Resource not found: ' + targetId);

const newParentId = {new_parent_arg};
let newParent;
if (newParentId === null) {{
  newParent = root;
}} else {{
  newParent = findRes(root, newParentId);
  if (!newParent) throw new Error('New parent resource not found: ' + newParentId);
}}

if (newParent === res) {{
  throw new Error('Cannot move a resource into itself');
}}
let cursor = newParent;
while (cursor) {{
  if (cursor === res) throw new Error('Cannot move a resource into one of its own descendants');
  cursor = cursor.parent;
}}

let idx = {index_arg};
if (idx === null) idx = newParent.members.length;
if (idx < 0 || idx > newParent.members.length) {{
  throw new Error('index out of range: ' + idx + ' (newParent has '
                   + newParent.members.length + ' members)');
}}

res.move(newParent, idx);

return {{
  moved: true,
  id: String(res.uniqueID),
  new_parent_id: String(newParent.uniqueID),
  index: idx,
}};
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
            resource's working hours). Maps to the documented
            `assignment.unitsAssigned` accessor (Number, read/write).
            Round-trips cleanly across JXA call boundaries.

    Returns:
        JSON `{task_id, resource_id, units}`. `units` is read back from
        `assignment.unitsAssigned` after the write — a true round-trip.
        When `units` is omitted on input, the returned value reflects
        whatever default OmniPlan applied (typically 1.0).
    """
    set_units = (
        f"a.unitsAssigned = {float(units)};" if units is not None else ""
    )

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

return {{
  task_id: target_task_id,
  resource_id: target_res_id,
  units: a.unitsAssigned,
}};
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def list_assignments(task_id: str) -> str:
    """List the resource assignments on a task.

    Args:
        task_id: uniqueID of the task.

    Returns:
        JSON array of `{resource_id, resource_name, units_assigned}`
        for each assignment on the task. Empty array if the task has
        no assignments. Reads `assignment.unitsAssigned` directly per
        the documented Assignment class.
    """
    script = f"""
const target_task_id = {json.dumps(task_id)};

function findTask(t, id) {{
  if (String(t.uniqueID) === id) return t;
  for (const c of t.subtasks) {{
    const f = findTask(c, id); if (f) return f;
  }}
  return null;
}}

const task = findTask(document.project.actual.rootTask, target_task_id);
if (!task) throw new Error('Task not found: ' + target_task_id);

const out = [];
for (let i = 0; i < task.assignments.length; i++) {{
  const a = task.assignments[i];
  if (!a.resource) continue;
  out.push({{
    resource_id: String(a.resource.uniqueID),
    resource_name: a.resource.name || '',
    units_assigned: a.unitsAssigned,
  }});
}}
return out;
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
