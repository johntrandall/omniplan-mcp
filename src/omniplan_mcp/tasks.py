import json
from typing import Optional
from omniplan_mcp.server import mcp
from omniplan_mcp.jxa import run_omnijs

def _doc_selector() -> str:
    """Returns JS expression to get the front document's root project."""
    return "const _proj = document.project;"


def _fmt_date() -> str:
    """JS helper to format dates as YYYY-MM-DD.

    Use UTC components — ISO date strings ('2027-04-12') parse as UTC
    midnight on write, so reading via local-time getters introduces a
    one-day skew west of UTC. Symptom prior to fix: writing 2027-04-12
    as a constraint date read back as 2027-04-11 in Eastern timezone.
    Same fix as documents.py applied 2026-05-02.
    """
    return """
function fmtDate(d) {
  if (!d) return null;
  var y = d.getUTCFullYear();
  var m = ('0' + (d.getUTCMonth() + 1)).slice(-2);
  var day = ('0' + d.getUTCDate()).slice(-2);
  return y + '-' + m + '-' + day;
}
"""


def _task_to_obj() -> str:
    """JS helper function to serialize a Task to a plain object.

    Note: 'parent_id', 'outline_id', and 'depth' are NOT set here — callers must inject them
    after traversal, because OmniPlan Automation does not expose a task.parent property.
    """
    return _fmt_date() + """
function toSeconds(v) {
  if (v === null || v === undefined) return 0;
  if (typeof v === 'number') return v;
  if (typeof v === 'object') {
    if (typeof v.seconds === 'number') return v.seconds;
    if (typeof v.value === 'number') return v.value;
  }
  var n = Number(v);
  return isNaN(n) ? 0 : n;
}

function taskToObj(task, summary) {
  if (summary) {
    return {
      title: task.title || '',
      type: String(task.type).replace(/.*TaskType:\\s*/, '').replace('TaskType.', '').replace(']', '').trim(),
      start_date: fmtDate(task.startDate),
      end_date: fmtDate(task.endDate),
    };
  }

  var effort = toSeconds(task.effort);
  var effortDone = toSeconds(task.effortDone);
  var completionPct = effort > 0 ? Math.round((effortDone / effort) * 100) : 0;

  var obj = {
    id: String(task.uniqueID),
    title: task.title || '',
    type: String(task.type).replace(/.*TaskType:\\s*/, '').replace('TaskType.', '').replace(']', '').trim(),
    completed: effortDone >= effort && effort > 0,
    start_date: fmtDate(task.startDate),
    end_date: fmtDate(task.endDate),
    depth: 0,
    parent_id: null,
    outline_id: null,
  };

  if (!summary) {
    obj.note = task.note || '';
    obj.completion_pct = completionPct;
    obj.manual_start_date = fmtDate(task.manualStartDate);
    obj.manual_end_date = fmtDate(task.manualEndDate);
    obj.effort_seconds = effort;
    obj.effort_done_seconds = effortDone;
    obj.start_no_earlier_than = fmtDate(task.startNoEarlierThanDate);
    obj.start_no_later_than = fmtDate(task.startNoLaterThanDate);
    obj.end_no_earlier_than = fmtDate(task.endNoEarlierThanDate);
    obj.end_no_later_than = fmtDate(task.endNoLaterThanDate);
  }

  return obj;
}
"""


@mcp.tool()
async def query_tasks(
    keyword: Optional[str] = None,
    task_type: Optional[str] = None,
    completed: Optional[bool] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    limit: Optional[int] = None,
    detail: Optional[str] = None,
) -> str:
    """Query tasks in an OmniPlan document with optional filters.

    Args:
        keyword: Filter by title or note containing this text (case-insensitive).
        task_type: One of: task, group, milestone, hammock.
        completed: True = completed only, False = incomplete only, None = all.
        due_before: ISO date string (e.g. 2025-12-31). Tasks ending before this date.
        due_after: ISO date string (e.g. 2025-01-01). Tasks ending after this date.
        limit: Maximum number of tasks to return. Returns all tasks if omitted.
        detail: 'summary' (default) returns core fields only; 'full' returns all fields.
    """
    doc_sel = _doc_selector()
    task_to_obj = _task_to_obj()

    filters = []
    if keyword:
        kw = json.dumps(keyword.lower())
        filters.append(f"(t.title || '').toLowerCase().includes({kw}) || (t.note || '').toLowerCase().includes({kw})")
    if task_type:
        # Use the same normalization taskToObj uses for the output `type`
        # field — see helper in _task_to_obj. The previous form
        # (`String(t.type).replace('TaskType.', '')`) never matched because
        # `String(t.type)` actually serializes as
        # `[object TaskType: TaskType.milestone]` and the unhandled prefix
        # / trailing bracket were left in.
        filters.append(
            f"String(t.type).replace(/.*TaskType:\\s*/, '').replace('TaskType.', '').replace(']', '').trim() === {json.dumps(task_type)}"
        )
    if completed is True:
        filters.append("(t.effortDone >= t.effort && t.effort > 0)")
    elif completed is False:
        filters.append("!(t.effortDone >= t.effort && t.effort > 0)")
    if due_before:
        filters.append(f"t.endDate && t.endDate < new Date({json.dumps(due_before)})")
    if due_after:
        filters.append(f"t.endDate && t.endDate > new Date({json.dumps(due_after)})")

    # Parenthesize each clause before joining with &&. The keyword filter
    # uses `||` internally; without explicit parens, JS operator precedence
    # (`&&` binds tighter than `||`) made the keyword's title-match alone
    # short-circuit any subsequent task_type / completed / date filter.
    filter_expr = " && ".join(f"({f})" for f in filters) if filters else "true"

    script = f"""
{doc_sel}
{task_to_obj}

var _rootUID = String(_proj.actual.rootTask.uniqueID);

function flatten(task, parentId, parentOutlineId) {{
  var results = [];
  for (var _i = 0; _i < task.subtasks.length; _i++) {{
    var child = task.subtasks[_i];
    var idx = String(_i + 1);
    var outlineId = parentOutlineId ? (parentOutlineId + '.' + idx) : idx;
    results.push({{raw: child, parentId: parentId, outlineId: outlineId}});
    results = results.concat(flatten(child, String(child.uniqueID), outlineId));
  }}
  return results;
}}

var root = _proj.actual.rootTask;
var allPairs = flatten(root, _rootUID, '');
var filtered = allPairs.filter(function(p) {{ var t = p.raw; return {filter_expr}; }});
var sliced = filtered{'' if limit is None else f'.slice(0, {limit})'};
var summary = {json.dumps(detail != 'full')};
return sliced.map(function(p) {{
  var obj = taskToObj(p.raw, summary);
  obj.outline_id = p.outlineId;
  if (!summary) {{
    obj.parent_id = (p.parentId === _rootUID) ? null : p.parentId;
  }}
  return obj;
}});
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def get_task(
    task_id: str,
) -> str:
    """Get full details of a single task by its unique ID.

    Args:
        task_id: The uniqueID of the task.
    """
    doc_sel = _doc_selector()
    task_to_obj = _task_to_obj()

    script = f"""
{doc_sel}
{task_to_obj}

var _rootUID = String(_proj.actual.rootTask.uniqueID);

function findById(task, id, parentId, outlineId) {{
  if (String(task.uniqueID) === id) return {{task: task, parentId: parentId, outlineId: outlineId}};
  for (var _i = 0; _i < task.subtasks.length; _i++) {{
    var child = task.subtasks[_i];
    var idx = String(_i + 1);
    var childOutlineId = outlineId ? (outlineId + '.' + idx) : idx;
    var found = findById(child, id, String(task.uniqueID), childOutlineId);
    if (found) return found;
  }}
  return null;
}}

var found = findById(_proj.actual.rootTask, {json.dumps(task_id)}, null, '');
if (!found) throw new Error('Task not found: {task_id}');
var obj = taskToObj(found.task);
obj.parent_id = (found.parentId === _rootUID || found.parentId === null) ? null : found.parentId;
obj.outline_id = found.outlineId || null;
return obj;
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def create_task(
    title: str,
    parent_id: Optional[str] = None,
    task_type: Optional[str] = None,
    note: Optional[str] = None,
    manual_start_date: Optional[str] = None,
    manual_end_date: Optional[str] = None,
    effort_seconds: Optional[int] = None,
    min_effort_seconds: Optional[int] = None,
    expected_effort_seconds: Optional[int] = None,
    max_effort_seconds: Optional[int] = None,
) -> str:
    """Create a new task in an OmniPlan document.

    Args:
        title: Task title.
        parent_id: uniqueID of the parent task. If omitted, adds to root.
        task_type: One of: task, group, milestone, hammock. Defaults to task.
        note: Optional task description.
        manual_start_date: ISO date string for manual start.
        manual_end_date: ISO date string for manual end.
        effort_seconds: Total effort in person-seconds (e.g. 14400 for 4h).
        min_effort_seconds: Three-point estimation minimum (person-seconds).
        expected_effort_seconds: Three-point estimation expected value.
        max_effort_seconds: Three-point estimation maximum.
    """
    doc_sel = _doc_selector()
    task_to_obj = _task_to_obj()

    set_type = f"newTask.type = TaskType.{task_type};" if task_type else ""
    set_note = f"newTask.note = {json.dumps(note)};" if note else ""
    set_start = f"newTask.manualStartDate = new Date({json.dumps(manual_start_date)});" if manual_start_date else ""
    set_end = f"newTask.manualEndDate = new Date({json.dumps(manual_end_date)});" if manual_end_date else ""
    set_effort = f"newTask.effort = {int(effort_seconds)};" if effort_seconds is not None else ""
    set_min_effort = f"newTask.minEffortEstimate = {int(min_effort_seconds)};" if min_effort_seconds is not None else ""
    set_expected_effort = f"newTask.expectedEffortEstimate = {int(expected_effort_seconds)};" if expected_effort_seconds is not None else ""
    set_max_effort = f"newTask.maxEffortEstimate = {int(max_effort_seconds)};" if max_effort_seconds is not None else ""

    script = f"""
{doc_sel}
{task_to_obj}

function findById(task, id, outlineId) {{
  if (String(task.uniqueID) === id) return {{task: task, outlineId: outlineId}};
  for (var _i = 0; _i < task.subtasks.length; _i++) {{
    var child = task.subtasks[_i];
    var idx = String(_i + 1);
    var childOutlineId = outlineId ? (outlineId + '.' + idx) : idx;
    var found = findById(child, id, childOutlineId);
    if (found) return found;
  }}
  return null;
}}

var parentId = {json.dumps(parent_id)};
var parentFound = parentId ? findById(_proj.actual.rootTask, parentId, '') : null;
var parent = parentFound ? parentFound.task : _proj.actual.rootTask;
if (parentId && !parentFound) throw new Error('Parent task not found: ' + parentId);
var parentOutlineId = parentFound ? parentFound.outlineId : '';

var newTask = parent.addSubtask();
newTask.title = {json.dumps(title)};
{set_type}
{set_note}
{set_start}
{set_end}
{set_effort}
{set_min_effort}
{set_expected_effort}
{set_max_effort}

var obj = taskToObj(newTask);
obj.parent_id = parentId;
var newTaskIndex = parent.subtasks.indexOf(newTask) + 1;
obj.outline_id = parentOutlineId ? (parentOutlineId + '.' + String(newTaskIndex)) : String(newTaskIndex);
return obj;
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def create_tasks(
    tasks: list[dict],
) -> str:
    """Create multiple tasks in a single JXA call.

    Performance: each `evaluateJavascript` round-trip is ~1-3s of
    osascript startup. Building 50 tasks via 50 calls to `create_task`
    is ~50-150s. This tool does the whole batch in one round-trip.

    Args:
        tasks: list of task specs. Each spec is a dict with the same
            fields `create_task` accepts:
              title (required), parent_id, task_type, note,
              manual_start_date, manual_end_date, effort_seconds,
              min_effort_seconds, expected_effort_seconds,
              max_effort_seconds.
            Plus one extra:
              parent_index — int, optional. References another task in
              the same batch by zero-based position. Must be less than
              the task's own index. At most one of `parent_id` and
              `parent_index` may be set; if neither is set, the task
              is added under the document root.

    Returns:
        JSON array of created-task shapes — same fields as `create_task`
        returns, in the order the inputs were given.

    Raises ValueError on invalid parent_index references or unknown
    parent_id, before any task is created.
    """
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list of dicts")
    if not tasks:
        return json.dumps([])

    normalized: list[dict] = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            raise ValueError(f"tasks[{i}] is not a dict")
        title = t.get("title")
        if not isinstance(title, str) or not title:
            raise ValueError(f"tasks[{i}].title is required and must be a non-empty string")
        parent_id = t.get("parent_id")
        parent_index = t.get("parent_index")
        if parent_id is not None and parent_index is not None:
            raise ValueError(f"tasks[{i}]: pass at most one of parent_id, parent_index")
        if parent_index is not None:
            if not isinstance(parent_index, int) or parent_index < 0 or parent_index >= i:
                raise ValueError(
                    f"tasks[{i}].parent_index must be an int in [0, {i}); got {parent_index!r}"
                )
        normalized.append({
            "title": title,
            "parent_id": parent_id,
            "parent_index": parent_index,
            "task_type": t.get("task_type"),
            "note": t.get("note"),
            "manual_start_date": t.get("manual_start_date"),
            "manual_end_date": t.get("manual_end_date"),
            "effort_seconds": t.get("effort_seconds"),
            "min_effort_seconds": t.get("min_effort_seconds"),
            "expected_effort_seconds": t.get("expected_effort_seconds"),
            "max_effort_seconds": t.get("max_effort_seconds"),
        })

    doc_sel = _doc_selector()
    task_to_obj = _task_to_obj()
    specs_js = json.dumps(normalized)

    script = f"""
{doc_sel}
{task_to_obj}

const _rootUID = String(_proj.actual.rootTask.uniqueID);
const specs = {specs_js};

function findById(task, id) {{
  if (String(task.uniqueID) === id) return task;
  for (let i = 0; i < task.subtasks.length; i++) {{
    const f = findById(task.subtasks[i], id);
    if (f) return f;
  }}
  return null;
}}

function fmtOutline(parentTask, parentOutlineId, childTask) {{
  const idx = parentTask.subtasks.indexOf(childTask) + 1;
  return parentOutlineId ? (parentOutlineId + '.' + idx) : String(idx);
}}

function outlineFor(task) {{
  if (String(task.uniqueID) === _rootUID) return '';
  const root = _proj.actual.rootTask;
  function walk(t, path) {{
    for (let i = 0; i < t.subtasks.length; i++) {{
      const child = t.subtasks[i];
      const seg = path ? (path + '.' + (i + 1)) : String(i + 1);
      if (String(child.uniqueID) === String(task.uniqueID)) return seg;
      const found = walk(child, seg);
      if (found) return found;
    }}
    return null;
  }}
  return walk(root, '') || '';
}}

const created = [];
const out = [];
for (let i = 0; i < specs.length; i++) {{
  const s = specs[i];
  let parent;
  let parentOutlineId = '';
  if (s.parent_id !== null && s.parent_id !== undefined) {{
    parent = findById(_proj.actual.rootTask, s.parent_id);
    if (!parent) throw new Error('tasks[' + i + ']: parent_id not found: ' + s.parent_id);
    parentOutlineId = outlineFor(parent);
  }} else if (s.parent_index !== null && s.parent_index !== undefined) {{
    parent = created[s.parent_index];
    parentOutlineId = outlineFor(parent);
  }} else {{
    parent = _proj.actual.rootTask;
  }}
  const t = parent.addSubtask();
  t.title = s.title;
  if (s.task_type) t.type = TaskType[s.task_type];
  if (s.note !== null && s.note !== undefined) t.note = s.note;
  if (s.manual_start_date) t.manualStartDate = new Date(s.manual_start_date);
  if (s.manual_end_date) t.manualEndDate = new Date(s.manual_end_date);
  if (s.effort_seconds !== null && s.effort_seconds !== undefined) t.effort = s.effort_seconds;
  if (s.min_effort_seconds !== null && s.min_effort_seconds !== undefined) t.minEffortEstimate = s.min_effort_seconds;
  if (s.expected_effort_seconds !== null && s.expected_effort_seconds !== undefined) t.expectedEffortEstimate = s.expected_effort_seconds;
  if (s.max_effort_seconds !== null && s.max_effort_seconds !== undefined) t.maxEffortEstimate = s.max_effort_seconds;
  created.push(t);
  const obj = taskToObj(t);
  obj.outline_id = fmtOutline(parent, parentOutlineId, t);
  obj.parent_id = (String(parent.uniqueID) === _rootUID) ? null : String(parent.uniqueID);
  out.push(obj);
}}
return out;
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def update_task(
    task_id: str,
    title: Optional[str] = None,
    note: Optional[str] = None,
    completed: Optional[bool] = None,
    manual_start_date: Optional[str] = None,
    manual_end_date: Optional[str] = None,
    effort_seconds: Optional[int] = None,
    min_effort_seconds: Optional[int] = None,
    expected_effort_seconds: Optional[int] = None,
    max_effort_seconds: Optional[int] = None,
    start_no_earlier_than: Optional[str] = None,
    start_no_later_than: Optional[str] = None,
    end_no_earlier_than: Optional[str] = None,
    end_no_later_than: Optional[str] = None,
) -> str:
    """Update an existing task. Only provided fields are changed.

    Args:
        task_id: The uniqueID of the task.
        title: New title.
        note: New note text.
        completed: True to mark complete, False to mark incomplete.
        manual_start_date: ISO date string, or empty string to clear.
        manual_end_date: ISO date string, or empty string to clear.
        effort_seconds: Total effort in person-seconds. Pass 0 to set to zero;
            None (omit) to leave unchanged.
        min_effort_seconds: Three-point estimation minimum (person-seconds).
        expected_effort_seconds: Three-point estimation expected value.
        max_effort_seconds: Three-point estimation maximum.
        start_no_earlier_than: ISO date string, or empty string to clear.
            Maps to `task.startNoEarlierThanDate`.
        start_no_later_than: ISO date string, or empty string to clear.
            Maps to `task.startNoLaterThanDate`.
        end_no_earlier_than: ISO date string, or empty string to clear.
            Maps to `task.endNoEarlierThanDate`.
        end_no_later_than: ISO date string, or empty string to clear.
            Maps to `task.endNoLaterThanDate`.
    """
    doc_sel = _doc_selector()
    task_to_obj = _task_to_obj()

    updates = []
    if title is not None:
        updates.append(f"task.title = {json.dumps(title)};")
    if note is not None:
        updates.append(f"task.note = {json.dumps(note)};")
    if completed is True:
        updates.append("if (task.effort > 0) { task.effortDone = task.effort; }")
    elif completed is False:
        updates.append("task.effortDone = 0;")
    if manual_start_date == "":
        updates.append("task.manualStartDate = null;")
    elif manual_start_date is not None:
        updates.append(f"task.manualStartDate = new Date({json.dumps(manual_start_date)});")
    if manual_end_date == "":
        updates.append("task.manualEndDate = null;")
    elif manual_end_date is not None:
        updates.append(f"task.manualEndDate = new Date({json.dumps(manual_end_date)});")
    if effort_seconds is not None:
        updates.append(f"task.effort = {int(effort_seconds)};")
    if min_effort_seconds is not None:
        updates.append(f"task.minEffortEstimate = {int(min_effort_seconds)};")
    if expected_effort_seconds is not None:
        updates.append(f"task.expectedEffortEstimate = {int(expected_effort_seconds)};")
    if max_effort_seconds is not None:
        updates.append(f"task.maxEffortEstimate = {int(max_effort_seconds)};")
    for param_value, omnijs_prop in (
        (start_no_earlier_than, "startNoEarlierThanDate"),
        (start_no_later_than, "startNoLaterThanDate"),
        (end_no_earlier_than, "endNoEarlierThanDate"),
        (end_no_later_than, "endNoLaterThanDate"),
    ):
        if param_value == "":
            updates.append(f"task.{omnijs_prop} = null;")
        elif param_value is not None:
            updates.append(f"task.{omnijs_prop} = new Date({json.dumps(param_value)});")

    if not updates:
        return json.dumps({"error": "No fields to update."})

    update_block = "\n".join(updates)

    script = f"""
{doc_sel}
{task_to_obj}

var _rootUID = String(_proj.actual.rootTask.uniqueID);

function findById(task, id, parentId, outlineId) {{
  if (String(task.uniqueID) === id) return {{task: task, parentId: parentId, outlineId: outlineId}};
  for (var _i = 0; _i < task.subtasks.length; _i++) {{
    var child = task.subtasks[_i];
    var idx = String(_i + 1);
    var childOutlineId = outlineId ? (outlineId + '.' + idx) : idx;
    var found = findById(child, id, String(task.uniqueID), childOutlineId);
    if (found) return found;
  }}
  return null;
}}

var found = findById(_proj.actual.rootTask, {json.dumps(task_id)}, null, '');
if (!found) throw new Error('Task not found: {task_id}');
var task = found.task;

{update_block}

var obj = taskToObj(task);
obj.parent_id = (found.parentId === _rootUID || found.parentId === null) ? null : found.parentId;
obj.outline_id = found.outlineId || null;
return obj;
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def find_task(
    name: str,
    exact: bool = False,
) -> str:
    """Look up tasks by title, returning lightweight identifiers.

    Removes the "list everything → grep → use ID" pattern when an agent
    knows the title but not the uniqueID.

    Args:
        name: Title to match. Case-insensitive substring match by default.
        exact: When True, only return tasks whose title equals `name`
            exactly (case-sensitive). When False, returns every descendant
            whose title contains `name` (case-insensitive).

    Returns:
        JSON array of `{"id", "title", "outline_id"}`. Empty array if
        nothing matches. Order matches outline traversal (depth-first,
        children in document order).
    """
    if exact:
        match_expr = f"(t.title || '') === {json.dumps(name)}"
    else:
        kw = json.dumps(name.lower())
        match_expr = f"((t.title || '').toLowerCase()).indexOf({kw}) >= 0"

    script = f"""
const _proj = document.project;
const root = _proj.actual.rootTask;

function walk(task, outlineId, hits) {{
  for (let i = 0; i < task.subtasks.length; i++) {{
    const t = task.subtasks[i];
    const idx = String(i + 1);
    const childOutlineId = outlineId ? (outlineId + '.' + idx) : idx;
    if ({match_expr}) {{
      hits.push({{
        id: String(t.uniqueID),
        title: t.title || '',
        outline_id: childOutlineId,
      }});
    }}
    walk(t, childOutlineId, hits);
  }}
}}

const hits = [];
walk(root, '', hits);
return hits;
"""
    result = await run_omnijs(script)
    return json.dumps(result)


@mcp.tool()
async def delete_task(
    task_id: str,
) -> str:
    """Delete a task by its unique ID.

    Args:
        task_id: The uniqueID of the task to delete.
    """
    doc_sel = _doc_selector()

    script = f"""
{doc_sel}

function findById(task, id) {{
  if (String(task.uniqueID) === id) return task;
  for (const child of task.subtasks) {{
    const found = findById(child, id);
    if (found) return found;
  }}
  return null;
}}

const task = findById(_proj.actual.rootTask, {json.dumps(task_id)});
if (!task) throw new Error('Task not found: {task_id}');
const title = task.title;
task.remove();
return {{ deleted: true, id: {json.dumps(task_id)}, title: title }};
"""
    result = await run_omnijs(script)
    return json.dumps(result)
