# omniplan-mcp Roadmap

Forked from [xiahan4956/omniplan-mcp](https://github.com/xiahan4956/omniplan-mcp) at commit `b235768` on 2026-05-01.
Upstream ships 6 task-CRUD tools — useful but covers only ~20% of OmniPlan's omniJS API.
This fork extends coverage so Claude can drive a real Gantt: dependencies, resources, leveling, baselines, scheduling.

## Prerequisites for any feature work

1. **Read vendor docs first.** They live in `~/dev/zVendorDocs/OmniPlan/` (downloaded 2026-05-01):
   - `omni-automation-website-v4.10.2-2026-05-01/` — full omniJS API reference
   - `applescript-dictionary-v4.10.2-2026-05-01/` — SDEF (legacy AppleScript surface)
   - `reference-manual-mac-v4.5.5-2026-05-01/` — user manual (concept reference)
2. **The bridge architecture is settled.** `osascript -l JavaScript` → `Application('OmniPlan').evaluateJavascript(...)` runs an omniJS string inside the running app and returns its value across the AppleEvent boundary. See `src/omniplan_mcp/jxa.py`. Don't touch this; it's the only nontrivial plumbing.
3. **Test environment.** OmniPlan must be running with `funding-pipeline.oplx` (or another scratch doc) open. macOS Automation TCC must be granted. Use marker-prefixed task names (`__test__*`) so the cleanup pass is unambiguous. See `Testing` section.

## Prioritized Feature TODO

Ordered by how badly each gap blocks "Claude as a Gantt-driver." Tier 0 must ship before this MCP is qualitatively useful for planning; Tier 1 makes it a real planning tool; Tier 2/3 are expert features.

### Tier 0 — Blocks usefulness (P0, ~3 days)

- [ ] **Effort/duration on `create_task`.** Add `effort_seconds` (and optionally `min_effort_seconds`, `expected_effort_seconds`, `max_effort_seconds` for three-point estimation). Currently every task defaults to 8h with no override.
- [ ] **Effort/duration on `update_task`.** Same fields. Empty string clears.
- [ ] **Dependencies — create.** New tool `add_dependency(predecessor_id, successor_id, kind="FS"|"SS"|"FF"|"SF", lag_seconds=0)`. omniJS API: `task.addDependent(otherTask, DependencyKind.FinishStart, lag)`. Without this, output is a list, not a Gantt.
- [ ] **Dependencies — remove.** `remove_dependency(predecessor_id, successor_id)`. omniJS: iterate `task.dependents`, find match, `.remove()`.
- [ ] **Dependencies — list.** `list_dependencies(task_id?)` returns `[{predecessor_id, successor_id, kind, lag_seconds}]`. If no `task_id`, returns the whole document.
- [ ] **`find_task` by name.** `find_task(name, exact=False) -> [{id, title, outline_id}]`. Wraps omniJS `document.taskNamed(name)` plus a regex/substring fallback. Removes the "list → grep → use ID" pattern.
- [ ] **`save_document(document_name?)`.** Verify autosave behavior first — OmniPlan 4 may or may not autosave depending on file scheme (local vs iCloud). Ship explicit save regardless for "commit now" semantics.

### Tier 1 — Real planning tool (P1, ~3 days)

- [ ] **Constraint dates on `update_task`.** Add `start_no_earlier_than`, `start_no_later_than`, `end_no_earlier_than`, `end_no_later_than`, `must_start_on`, `must_end_on`. ISO date strings; empty clears. Critical for "this is locked because external dependency."
- [ ] **`get_project_info()`** — returns `{name, start_date, end_date, currency, working_hours, scenarios[]}`.
- [ ] **`update_project(...)`** — start date, currency, default working hours.
- [ ] **`move_task(task_id, new_parent_id?, after_sibling_id?)`** — restructure outline mid-session.
- [ ] **`create_tasks(tasks: [...])`** — bulk create in a single JXA call. Performance matters for project scaffolding (50 tasks × 2s shell-out = 100s otherwise).
- [ ] **Resources — basic CRUD.** `list_resources()`, `create_resource(name, type, units?, cost_per_hour?)`, `delete_resource(id)`.
- [ ] **Assignments.** `assign_resource(task_id, resource_id, units=1.0)`, `unassign_resource(task_id, resource_id)`.

### Tier 2 — Expert features (P2, ~3 days)

- [ ] **Resource leveling.** `level_document()`, `unlevel_document()`. Wraps `document.level()`.
- [ ] **Baselines.** `create_baseline(name)`, `list_baselines()`, `compare_to_baseline(name)`.
- [ ] **Custom data.** `set_custom_data(task_id, key, value)`, `get_custom_data(task_id, key?)`. High value for cross-system links (Plane work item ID, Linear issue ID, GitHub PR URL).
- [ ] **Splits.** `split_task(task_id, at_date)`, `unsplit_task(task_id)`.
- [ ] **Slack queries (read-only).** Already returnable from `get_task` if we add `free_slack`, `total_slack` to the output shape.
- [ ] **Export.** `export_document(format="png"|"pdf"|"csv", path)`.

### Tier 3 — Polish

- [ ] **Multi-document.** Add `document_name` param to all tools. Currently always operates on front document.
- [ ] **`describe_task()` / `describe_project()`** — return JSON schema of all settable fields. Lets Claude discover capabilities without docs lookup.
- [ ] **`run_omniautomation(script)` escape hatch.** Run arbitrary omniJS string for unforeseen needs. Gated behind a flag (default off) for safety.
- [ ] **MCP resources.** Expose `.oplx` files as MCP resources for inspection.

## Cross-cutting concerns

- **Read-after-write consistency.** Every write tool returns the post-write state. Already done in v0.1.0 — preserve.
- **Idempotency.** `create_task` with same title twice creates two tasks. Don't add "find or create" semantics; let the agent decide.
- **Error envelopes.** v0.1.0 has friendly errors for TCC denial and "not running." Extend to: file is read-only, document not saved, task in baseline (immutable), scheduling conflict, resource over-allocation.
- **Concurrency.** `asyncio.Lock` already serializes osascript calls. Verify behavior when human edits in GUI simultaneously — OmniPlan should serialize but worth an explicit test.
- **Performance.** Each call is ~1-3s of `osascript` startup + JXA → omniJS hop. For bulk ops this matters a lot. Bulk `create_tasks` and bulk `update_tasks` are the obvious wins.

## Testing environment

OmniPlan is a Mac GUI app — must be running, document open, TCC granted, state persists across runs. Three layers:

### 1. Unit tests (`tests/unit/`)

Pure Python. Mock `subprocess.create_subprocess_exec`. Test envelope parsing, parameter serialization, error message translation. Fast, CI-runnable. No OmniPlan needed. **Limited value** — real bugs are in the omniJS strings, not the wrapper.

```python
# tests/unit/test_jxa_envelope.py
async def test_omnijs_parses_ok_envelope():
    with mock_osascript_returning('{"ok": true, "data": [1,2,3]}'):
        result = await run_omnijs("return [1,2,3]")
        assert result == [1, 2, 3]

async def test_omnijs_raises_on_error_envelope():
    with mock_osascript_returning('{"ok": false, "error": "boom"}'):
        with pytest.raises(RuntimeError, match="boom"):
            await run_omnijs("throw new Error('boom')")
```

### 2. Integration tests (`tests/integration/`)

Real OmniPlan, real `osascript`, against a checked-in scratch doc.

- **Fixture doc:** `tests/fixtures/test-suite.oplx` — minimal document with one parent task `__test__root` that all tests write under.
- **Pytest marker:** `@pytest.mark.requires_omniplan` — `conftest.py` skips with reason if OmniPlan isn't running.
- **Per-test isolation:** create-marker-then-cleanup pattern. Every test creates tasks named `__test__<test_name>__<n>`; teardown deletes everything starting with `__test__`. No parallel tests (asyncio lock + GUI app makes parallelism dangerous).
- **What real bugs this catches:** typos in omniJS property names, deprecated API calls, OmniPlan version drift (4.10.2 vs future), edge cases in scheduling behavior.

```python
# tests/integration/test_dependencies.py
@pytest.mark.requires_omniplan
async def test_add_finish_start_dependency():
    a = await create_task(title="__test__deps__pred", effort_seconds=3600)
    b = await create_task(title="__test__deps__succ", effort_seconds=3600)
    await add_dependency(a["id"], b["id"], kind="FS")
    deps = await list_dependencies(b["id"])
    assert any(d["predecessor_id"] == a["id"] and d["kind"] == "FS" for d in deps)
```

### 3. End-to-end smoke (`tests/e2e/`)

Manual scripts plus a checklist doc. Run before each release:
1. Fresh OmniPlan launch, fresh `funding-pipeline.oplx` (git-restored).
2. Fresh Claude Code session.
3. Drive a real planning scenario from a transcript: create 10 tasks, link 5 dependencies, set efforts, level resources, baseline, save.
4. Diff the resulting `.oplx` against expected-state. Catches "feels different" UX regressions.

### CI

GitHub Actions macOS runners can't easily provide a GUI session with OmniPlan + TCC. Two options:

- **(a) Self-hosted Mac runner** with OmniPlan installed and TCC granted. Heavy. Defer until tier 2.
- **(b) Unit tests in CI; integration tests gated on local pre-push hook.** Pragmatic. Use this until `(a)` is justified.

## Order of operations

### Phase 0 — Fork hygiene (today, in this repo)

1. Created `dev-docs/ROADMAP.md` (this file).
2. Updated `README.md` to mark this as a fork, link to vendor docs, link to ROADMAP.
3. Add `pytest`, `pytest-asyncio`, and a minimal `tests/conftest.py` skeleton.
4. Move `test_tools.py` → `tests/manual/smoke.py` (preserve, don't delete).
5. Add `CHANGELOG.md` starting at "0.1.1 — fork".

### Phase 1 — Tier 0 features (week 1)

Branch per feature, PR upstream as you go. Order:
1. `feat/effort-on-create-update` — adds duration support. Single smallest unit.
2. `feat/find-task` — pure-add, no behavior change to existing tools.
3. `feat/dependencies` — biggest single improvement. Ships add/remove/list together.
4. `feat/save-document` — verify autosave behavior first; ship anyway.

After Tier 0, smoke test against `funding-pipeline.oplx` end-to-end. If qualitative gain over upstream is real, merge to `main` of our fork and tag `v0.2.0`. Update the `omniplan-local` MCP install in `~/admin-technical/setup/macos/omniplan-local/README.md` to point at our fork.

### Phase 2 — Tier 1 features (week 2)

1. `feat/constraints`
2. `feat/project-info`
3. `feat/move-task`
4. `feat/bulk-create`
5. `feat/resources` (CRUD + assignments together)

### Phase 3 — Tier 2 features (week 3)

1. `feat/leveling`
2. `feat/baselines`
3. `feat/custom-data`
4. `feat/splits-and-slack`
5. `feat/export`

### Phase 4 — Productionize

- Write ADR in `~/admin-technical/ADRs/` documenting the fork decision and trajectory.
- Update `~/admin-technical/inventories/MCP-Server-Inventory.md` with new tool count.
- Decide: maintain fork indefinitely, or push for full upstream merge. Upstream is 2★, MIT, last-commit 2026-03-14 — likely accepts PRs but slow. Strategy: open PR per feature, run from fork in the meantime.

## Style and conventions

- **omniJS snippets stay in Python triple-quoted strings**, not separate `.js` files. Easier to grep, easier to template params. Use `{_escape(value)}` (already in `jxa.py`) for user input.
- **One tool, one omniJS call.** No tool should fan out to multiple `evaluateJavascript` invocations — that defeats the bridge's transactional behavior.
- **Return shape consistency.** Every write tool returns the post-write state of the affected entity. Every list tool returns `[{...}]`. Every singleton tool returns `{...}` or null.
- **Type hints everywhere.** FastMCP uses them for the JSON schema.
- **No comments explaining what code does.** Comments only for non-obvious *why* (e.g., a workaround for a specific omniJS quirk with the SHA of when it was discovered).
