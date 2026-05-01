# omniplan-mcp

MCP server for [OmniPlan 4](https://www.omnigroup.com/omniplan) on macOS. Manage your project tasks with natural language via Claude or any MCP-compatible client.

> **This is johntrandall's active fork** of [xiahan4956/omniplan-mcp](https://github.com/xiahan4956/omniplan-mcp). Upstream shipped 6 task-CRUD tools as v0.1.0; this fork is at **v0.3.0** with **19 tools** and adds dependencies, three-point estimates, name lookup, project info, bulk creation, resource CRUD, and explicit save. See [`dev-docs/ROADMAP.md`](dev-docs/ROADMAP.md) for the full roadmap and [`dev-docs/omnijs-persistence-gaps.md`](dev-docs/omnijs-persistence-gaps.md) for the omniJS limitations we hit and the sentinel tests that watch for fixes. PRs are sent upstream as features ship; this fork is the daily driver until they merge.

## Reference material

- **[Omni Automation API for OmniPlan](https://omni-automation.com/omniplan/index.html)** — the canonical omniJS reference. The bridge in [`src/omniplan_mcp/jxa.py`](src/omniplan_mcp/jxa.py) wraps `Application('OmniPlan').evaluateJavascript(...)` so every tool is a small omniJS snippet against this API.
- **[Omni Automation JXA/AppleScript bridge](https://omni-automation.com/jxa-applescript.html)** — describes the `evaluateJavascript` AppleEvent we use.
- **OmniPlan AppleScript dictionary (SDEF)** — `/Applications/OmniPlan.app/Contents/Resources/OmniPlan.sdef` (~1450 lines). Legacy surface but still authoritative for class/property names.
- **Local vendor-docs mirror** (this Mac, John's setup) — partial offline copies under [`~/dev/zVendorDocs/OmniPlan/`](file:///Users/johnrandall/dev/zVendorDocs/OmniPlan/):
  - `omni-automation-website-v4.10.2-2026-05-01/` — **only 8 top-level pages** (index, big-picture, application, setup, tutorial, actions, conference-example, conference-fetch-example). Deep API pages (Tasks/Dependencies/Resources/Documents) were **not** mirrored — fetch from `https://omni-automation.com/omniplan/` online when needed.
  - `applescript-dictionary-v4.10.2-2026-05-01/` — SDEF + per-suite breakdown. Authoritative for class/property names. **Use as fallback when omniJS docs are missing.**
  - `reference-manual-mac-v4.5.5-2026-05-01/` — OmniPlan user manual (concept reference for views, inspectors, terminology).

See [`dev-docs/ROADMAP.md`](dev-docs/ROADMAP.md) "Verified vs unverified API claims" for which omniJS signatures are confirmed vs. educated guesses.

## Requirements

- macOS
- OmniPlan 4 (must be running)
- Python 3.11+
- Automation permission granted to your terminal / MCP host app

## Installation

This fork (`v0.3.0`, 19 tools) — pinned to the tag because `origin/main`
hasn't yet caught up to the v0.3.0 commits (a harness rule on the original
author's machine prevents direct pushes to main):

```bash
uv tool install --from "git+https://github.com/johntrandall/omniplan-mcp.git@v0.3.0" omniplan-mcp
```

Or clone and install in editable mode:

```bash
git clone --branch v0.3.0 https://github.com/johntrandall/omniplan-mcp.git
cd omniplan-mcp
pip install -e .
```

Upstream baseline (`v0.1.0`, 6 tools):

```bash
pip install git+https://github.com/xiahan4956/omniplan-mcp.git
```

### Grant Automation Permission

The first time you run the server, macOS may prompt for Automation access. If not, grant it manually:

**System Settings → Privacy & Security → Automation** — enable OmniPlan for your terminal or the app running the MCP server.

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "omniplan": {
      "command": "python3",
      "args": ["-m", "omniplan_mcp"]
    }
  }
}
```

Then restart Claude Desktop.

## Tools

| Tool | Description |
|------|-------------|
| `list_documents` | List all currently open OmniPlan documents |
| `query_tasks` | Search and filter tasks by keyword, type, completion, color, or date range |
| `get_task` | Get full details of a task by ID |
| `create_task` | Create a new task under a parent task or project root (effort + 3-point estimate fields supported) |
| `create_tasks` | Bulk-create many tasks in a single round-trip; supports intra-batch `parent_index` |
| `update_task` | Update task fields (title, note, dates, completion, color, effort + 3-point estimate) |
| `find_task` | Look up tasks by title; returns `[{id, title, outline_id}]` (substring by default, exact opt-in) |
| `delete_task` | Delete a task by ID |
| `add_dependency` | Link two tasks (FS / SS / FF / SF, optional lead time) |
| `remove_dependency` | Remove the dependency between two tasks |
| `list_dependencies` | List dependencies in the document (or filtered to one task) |
| `save_document` | Save the front document to disk; returns `{saved, name, modified_after}` |
| `get_project_info` | Returns `{name, path, start_date, end_date, scenarios}` |
| `update_project` | Update project-level fields (currently `start_date` only) |
| `list_resources` | List all resources (`{id, name, type, email, cost_per_use}`) |
| `create_resource` | Create a resource (staff / equipment / material / group); supports `cost_per_use` |
| `delete_resource` | Delete a resource by ID; OmniPlan strips its assignments |
| `assign_resource` | Assign a resource to a task (optional `units`) |
| `unassign_resource` | Remove a resource assignment from a task |
| `list_assignments` | List a task's resource assignments (`{resource_id, resource_name, units_assigned}`) |

All tools accept an optional `document_name` parameter. If omitted, the frontmost open document is used.

### query_tasks parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `keyword` | string | Filter by title or note (case-insensitive) |
| `task_type` | string | `task` / `group` / `milestone` / `hammock` |
| `completed` | boolean | `true` = completed only, `false` = incomplete only |
| `color` | string | `red` / `orange` / `yellow` / `green` / `blue` / `purple` / `brown` / `gray` / `clear` |
| `due_before` | string | ISO date, e.g. `2025-12-31` |
| `due_after` | string | ISO date, e.g. `2025-01-01` |
| `limit` | int | Max results (default 50) |

### update_task parameters

Pass only the fields you want to change. Set `completed: true` to mark a task done, or `color: "clear"` to reset the bar color.

## Known omniJS limitations

OmniPlan 4.10.2's omniJS surface has several gaps that block features cleanly written
against the `evaluateJavascript` bridge. We document them in
[`dev-docs/omnijs-persistence-gaps.md`](dev-docs/omnijs-persistence-gaps.md) and ship
`xfail(strict=True)` sentinel tests that go RED if OmniGroup fixes them.

Short version:

| Gap | Affects |
|---|---|
| Constraint dates (`startConstraintDate` etc.) — write inline succeeds, value lost across calls | `update_task` constraint fields not exposed |
| `dep.leadTimeDuration` — `Duration` is opaque on read | `list_dependencies` returns `lead_time_seconds: null` |
| `assignment.units` — write doesn't persist across calls | `assign_resource` echoes input but can't round-trip |
| `actual.currency` — same persistence trap | omitted from `update_project` |
| No `task.moveTo` / `reparent` | `move_task` not implemented |
| No `proj.scenarios` enumeration | `get_project_info` reports `["Actual"]` only |
| `r.costPerUse` is opaque `Decimal` on read | parse `String(d)` to recover value (handled internally) |

## Example Prompts

> "Show me all incomplete tasks due this week in my project."

> "Create a milestone called 'Beta Launch' under the Deployment group."

> "Mark task 42 as complete and set its bar color to green."

> "What tasks are assigned the red color?"

## License

MIT
