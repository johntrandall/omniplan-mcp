# mcp-omniplan-jtr

**Drive [OmniPlan 4](https://www.omnigroup.com/omniplan) on macOS from Claude (or any MCP-compatible LLM agent) using natural language.**

Tell an agent "create a milestone called Beta Launch under the Deployment group, link it after the QA-complete task, and assign it to Alice." It does. The Gantt redraws.

20 tools across tasks, dependencies, resources, assignments, and project metadata. MIT-licensed. macOS only.

> **Lineage:** this build is *inspired by* [`xiahan4956/omniplan-mcp`](https://github.com/xiahan4956/omniplan-mcp) (MIT) — the original `jxa.py` bridge is reused under MIT. The rest of the codebase was rebuilt from scratch (~86% of current LOC). It's distributed under a distinct PyPI name (`mcp-omniplan-jtr`) so as not to take the original author's namespace. See [`CHANGELOG.md`](CHANGELOG.md) for what changed.

## What it does

| You say | The agent calls | OmniPlan reflects |
|---|---|---|
| "Show me incomplete tasks due this week" | `query_tasks(due_before=…, completed=false)` | filters the outline |
| "Create a 4-hour task 'Refactor login' under Auth" | `create_task(parent_id, effort_seconds=14400)` | new row in the Gantt |
| "Link 'Refactor login' before 'Run E2E'" | `add_dependency(predecessor_id, successor_id, kind="FS")` | dependency arrow drawn |
| "Assign Alice at 50%" | `assign_resource(task_id, resource_id, units=0.5)` | assignment chip on the bar |
| "Mark Beta Launch as a milestone, color green" | `update_task(type="milestone", color="green")` | diamond marker, green |
| "Save the document" | `save_document()` | written to disk |

## Requirements

- macOS (any recent version)
- OmniPlan 4 — installed and running with a document open. See "Supported OmniPlan versions" below for the matrix
- Python 3.11+
- Automation permission granted to your terminal / MCP host app (System Settings → Privacy & Security → Automation → enable OmniPlan)

### Supported OmniPlan versions

This MCP is verified against the following builds. "Verified" = full pytest integration suite passes against that build inside a Tart macOS VM with OmniPlan running.

| OmniPlan version | Build | All tools? | Verified | Notes |
|---|---|---|---|---|
| **4.10.3 test** | v232.5.9 (`e7066d2251`) | ✅ All 22 tools | 2026-05-07 | Test build from <https://omnistaging.omnigroup.com/omniplan/>. Adds `task.move` / `resource.move` per OG ticket #3107771 |
| **4.10.2** | 232.5.0 | ✅ Except `move_task` / `move_resource` | 2026-05-01 | Public release. The two move tools raise a clear "requires 4.10.3+" error; everything else works including all reads, writes, dependencies, resource assignments, and `cost_per_use` |
| 4.10.0–4.10.1 | (older 4.10.x patch builds) | Likely yes for non-move tools | Inferred (untested) | Should work — same omniJS surface as 4.10.2 for the tools we use, but not empirically verified |
| 4.9.x and older | — | Unknown | Untested | Not part of the supported matrix |

**Reporting a version compatibility issue:** if you find a build where a tool fails that the matrix says should work, please file an issue with the build number (visible in `OmniPlan → About OmniPlan`) and the tool name.

## Install

Pick whichever you prefer:

```bash
# 1. Homebrew tap (Python deps bundled in an isolated venv; only python@3.13 comes from brew)
brew tap johntrandall/tap
brew install mcp-omniplan-jtr
```

```bash
# 2. uv tool (recommended for the MCP ecosystem; installs from PyPI)
uv tool install mcp-omniplan-jtr
```

```bash
# 3. pip (if you don't have uv)
pip install mcp-omniplan-jtr
```

All three install the `mcp-omniplan-jtr` command. Register it as an MCP server with whichever client you use:

### Claude Code (CLI)

```bash
claude mcp add -s user omniplan-local mcp-omniplan-jtr
```

Then restart Claude Code.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "omniplan-local": {
      "command": "mcp-omniplan-jtr"
    }
  }
}
```

Then restart Claude Desktop.

### First call — Automation permission

The first time the agent calls a tool, macOS may prompt for Automation access. Approve OmniPlan automation for your terminal or the app running the MCP server. If the prompt was missed, grant it manually:

**System Settings → Privacy & Security → Automation** — enable OmniPlan for your terminal or MCP host.

If denied, every tool returns a clear error: `"macOS blocked Automation access to OmniPlan. Grant permission in System Settings > Privacy & Security > Automation."`

## Tools

| Tool | What it does |
|---|---|
| `list_documents` | List all currently open OmniPlan documents |
| `query_tasks` | Search and filter tasks by keyword, type, completion, color, or date range |
| `find_task` | Look up tasks by title; substring by default, exact opt-in |
| `get_task` | Get full details of a task by ID |
| `create_task` | Create a new task under a parent task or project root |
| `create_tasks` | Bulk-create many tasks in a single round-trip; supports intra-batch parent references |
| `update_task` | Update title, note, dates, completion, color, effort, three-point estimates, constraint dates |
| `move_task` | Reparent a task while preserving its uniqueID (so dependencies and assignments survive). Requires OmniPlan 4.10.3+ |
| `delete_task` | Delete a task by ID |
| `add_dependency` | Link two tasks (FS / SS / FF / SF, optional lead time) |
| `remove_dependency` | Remove the dependency between two tasks |
| `list_dependencies` | List dependencies in the document (or filtered to one task) |
| `save_document` | Save the front document to disk |
| `get_project_info` | Project metadata: name, path, dates, scenarios |
| `update_project` | Update project-level fields (currently start date) |
| `list_resources` | List all resources |
| `create_resource` | Create a resource (staff / equipment / material / group) |
| `move_resource` | Reparent a resource (across the resource group hierarchy) while preserving its uniqueID. Requires OmniPlan 4.10.3+ |
| `delete_resource` | Delete a resource by ID |
| `assign_resource` | Assign a resource to a task with optional units fraction |
| `unassign_resource` | Remove a resource assignment from a task |
| `list_assignments` | List a task's resource assignments |

All tools accept an optional `document_name` parameter. If omitted, the frontmost open document is used.

## Example prompts

> "Show me all incomplete tasks due this week in my project."

> "Create a milestone called 'Beta Launch' under the Deployment group, dependent on 'QA-complete', and assign it to Alice at 50%."

> "Mark task 42 as complete and set its bar color to green."

> "What tasks are assigned the red color?"

> "List every resource and how much they're allocated across the project."

## Limitations

OmniPlan's omniJS surface has a few small gaps. Most tools work transparently; these are the documented edges:

- **Task / Resource reparenting requires OmniPlan 4.10.3+** — earlier builds had no omniJS path to reparent without changing uniqueID. Ken Case @ Omni shipped `task.move` and `resource.move` in May 2026 (OG ticket #3107771); the MCP wraps both as `move_task` / `move_resource`. On 4.10.2 those tools raise a clear "requires 4.10.3+" error; the rest of the MCP works on 4.10.2 unchanged.
- **Resource working hours** are not editable through this MCP — `actual.rootResource.schedule` is opaque on the omniJS surface.
- **Project currency** (`actual.currency`) is not exposed for the same reason — writes via omniJS don't persist across calls. Cost values themselves work; just not the currency unit.
- **OmniPlan must be running** with a document open. The MCP doesn't launch OmniPlan or open documents for you.

For the full release-by-release history including verification status for each finding, see [CHANGELOG.md](CHANGELOG.md).

For the full catalogue (and the mitigations), see [`dev-docs/omnijs-persistence-gaps.md`](dev-docs/omnijs-persistence-gaps.md).

## For developers

If you want to extend, hack on, or contribute to this MCP:

- **Architecture & internals:** [`dev-docs/README-DEV.md`](dev-docs/README-DEV.md)
- **Roadmap & feature tiers:** [`dev-docs/ROADMAP.md`](dev-docs/ROADMAP.md)
- **Testing policy:** [`dev-docs/testing-policy.md`](dev-docs/testing-policy.md)
- **VM provisioning for the pre-release test runner:** [`dev-docs/vm-provisioning.md`](dev-docs/vm-provisioning.md)

## Related projects

Sibling OmniPlan tooling in the same workflow:

- [`oplx-tools`](https://github.com/johntrandall/oplx-tools) — Python toolkit for OmniPlan `.oplx` documents: generate, lint, parse. Useful when you want to build a Gantt from a database or CI pipeline rather than the GUI.
- [`oplx-format`](https://github.com/johntrandall/oplx-format) — Community-maintained file-format specification for `.oplx` documents (verified against OmniPlan 4.10.2). Reference doc that informed both `oplx-tools` and the e2e XML cross-checks in this MCP's test suite.

## License

MIT. See [`LICENSE`](LICENSE).
