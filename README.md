# omniplan-mcp

MCP server for [OmniPlan 4](https://www.omnigroup.com/omniplan) on macOS. Manage your project tasks with natural language via Claude or any MCP-compatible client.

> **This is johntrandall's active fork** of [xiahan4956/omniplan-mcp](https://github.com/xiahan4956/omniplan-mcp). Upstream ships 6 task-CRUD tools and is the right architectural foundation; this fork extends coverage so Claude can drive a full Gantt (dependencies, resources, leveling, baselines, scheduling). See [`dev-docs/ROADMAP.md`](dev-docs/ROADMAP.md) for the prioritized feature list and order of operations. PRs are sent upstream per the [`fix-upstream`](https://github.com/johntrandall) workflow; this fork is the daily driver until they land.

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

```bash
pip install git+https://github.com/xiahan4956/omniplan-mcp.git
```

Or clone and install in editable mode:

```bash
git clone https://github.com/xiahan4956/omniplan-mcp.git
cd omniplan-mcp
pip install -e .
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
| `update_task` | Update task fields (title, note, dates, completion, color, effort + 3-point estimate) |
| `find_task` | Look up tasks by title; returns `[{id, title, outline_id}]` (substring by default, exact opt-in) |
| `delete_task` | Delete a task by ID |
| `add_dependency` | Link two tasks (FS / SS / FF / SF, optional lead time) |
| `remove_dependency` | Remove the dependency between two tasks |
| `list_dependencies` | List dependencies in the document (or filtered to one task) |

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

## Example Prompts

> "Show me all incomplete tasks due this week in my project."

> "Create a milestone called 'Beta Launch' under the Deployment group."

> "Mark task 42 as complete and set its bar color to green."

> "What tasks are assigned the red color?"

## License

MIT
