# omniplan-mcp Roadmap

Forked from [xiahan4956/omniplan-mcp](https://github.com/xiahan4956/omniplan-mcp) at commit `b235768` on 2026-05-01.
Upstream ships 6 task-CRUD tools — useful but covers only ~20% of OmniPlan's omniJS API.
This fork extends coverage so Claude can drive a real Gantt: dependencies, resources, leveling, baselines, scheduling.

## Prerequisites for any feature work

1. **Read vendor docs first.** They live in `~/dev/zVendorDocs/OmniPlan/` (downloaded 2026-05-01):
   - `omni-automation-website-v4.10.2-2026-05-01/` — partial mirror of `omni-automation.com/omniplan/`. **Only 8 top-level pages were captured** (`index.md`, `big-picture.md`, `application.md`, `setup.md`, `tutorial.md`, `actions.md`, `conference-example.md`, `conference-fetch-example.md`). Deep API pages (Tasks, Dependencies, Resources, Documents) were **not** mirrored — fetch them online from `https://omni-automation.com/omniplan/` as needed.
   - `applescript-dictionary-v4.10.2-2026-05-01/` — SDEF + per-suite breakdowns. Authoritative for class/property names. **Use this when omniJS docs are missing.**
   - `reference-manual-mac-v4.5.5-2026-05-01/` — user manual (concept reference for inspectors, views, terminology).
2. **The bridge architecture is settled.** `osascript -l JavaScript` → `Application('OmniPlan').evaluateJavascript(...)` runs an omniJS string inside the running app and returns its value across the AppleEvent boundary. See `src/omniplan_mcp/jxa.py`. Don't touch this; it's the only nontrivial plumbing.
3. **Test environment.** OmniPlan must be running with `funding-pipeline.oplx` (or another scratch doc) open. macOS Automation TCC must be granted. Use marker-prefixed task names (`__test__*`) so the cleanup pass is unambiguous. See `Testing` section.

## Verified vs unverified API claims

The signatures below in `Tier 0`–`Tier 2` are **a mix of verified (from existing source/SDEF) and educated guesses (from omniJS conventions in other Omni apps)**. Before implementing any feature, **verify the actual signature in OmniPlan's omniJS Console** (Automation menu → Show Console — type `app.platformName` to confirm it's live; then probe the API: `app.frontDocument.project.rootTask.addSubtask` etc.). The Console returns live values and is the ground truth.

| Pattern | Source | Confidence |
|---|---|---|
| `task.addSubtask()` | `big-picture.md`, `conference-example.md` | **Verified** |
| `task.descendents()` | same | **Verified** |
| `scenario.taskNamed(name)` (note: on Scenario, **not** Document) | `big-picture.md` | **Verified** |
| `document.save()` | `conference-example.md` | **Verified** |
| `task.effort` / `task.effortDone` (Duration objects with `.seconds` property) | `src/omniplan_mcp/tasks.py` reads them | **Verified** for read; **unverified** for write |
| `task.title`, `task.note`, `task.manualStartDate`, `task.manualEndDate` | source code writes them | **Verified** |
| Dependency model: `prerequisite`, `dependent`, `dependency type`, `lead time`, `lead percentage` | `applescript-dictionary/omniplan-suite.md` (SDEF) | **Verified** for AppleScript; omniJS class/method names **unverified** |
| `dependency types: finishstart` (and presumably `startstart`, `finishfinish`, `startfinish`) | SDEF | **Verified** |
| `task.addDependent(other, DependencyKind.FinishStart, lag)` | **Educated guess** modeled on OmniFocus/OmniOutliner conventions | **UNVERIFIED — confirm in Console first** |
| `Duration.seconds(N)` constructor for setting effort | **Educated guess** | **UNVERIFIED — try `task.effort = N` (raw number) first** |
| `task.minEffortEstimate`, `expectedEffortEstimate`, `maxEffortEstimate` for three-point | **Educated guess** | **UNVERIFIED** |
| Constraint date properties (`startNoEarlierThan`, `mustStartOn`, etc.) | SDEF has constraint-date concept; omniJS names guessed | **UNVERIFIED** |

### Known API limitation

**`task.parent` does NOT exist in OmniPlan's omniJS API.** Source code at `src/omniplan_mcp/tasks.py` line 27 documents this — that's why `parent_id`, `outline_id`, and `depth` are computed via traversal of `rootTask.descendents()` rather than read from the task object. Any tool that needs to know a task's parent must walk down from `rootTask`, not up from the child.

### Terminology drift between omniJS and SDEF

**SDEF says `lead time` and `lead percentage`; the omniJS API may use either `lead*` or `lag*` or both.** Pick the right one by inspection — and once verified, name the Python parameter to match the omniJS name (e.g., `lead_time_seconds`), not a generic name like `lag_seconds`. This avoids a translation layer between the MCP surface and the underlying API.

Same caution applies to other terminology (`prerequisite`/`dependent` vs `predecessor`/`successor`, `effort` vs `duration` vs `work`). Match the omniJS names; don't invent new ones.

## Prioritized Feature TODO

Ordered by how badly each gap blocks "Claude as a Gantt-driver." Tier 0 must ship before this MCP is qualitatively useful for planning; Tier 1 makes it a real planning tool; Tier 2/3 are expert features.

### Tier 0 — Blocks usefulness (P0, ~3 days)

> **All API examples below are starting points, not specifications.** Confirm each in the omniJS Console (Automation → Show Console) before coding. See "Verified vs unverified API claims" above.

- [ ] **Effort/duration on `create_task`.** Add `effort_seconds: int | None`. Try `task.effort = N` (raw integer seconds — match how the existing read code treats `task.effort`) first; fall back to `Duration.seconds(N)` factory if the property is read-only or strongly typed. Optionally expose `min_effort_seconds`, `expected_effort_seconds`, `max_effort_seconds` for three-point estimation **if** the corresponding properties exist (probe in Console: `task.minEffortEstimate` etc. — name is unverified).
- [ ] **Effort/duration on `update_task`.** Same fields as above. Empty string clears.
- [ ] **Dependencies — create.** New tool `add_dependency(predecessor_id, successor_id, kind="FS"|"SS"|"FF"|"SF", lead_time_seconds=0)`. **Note the parameter is `lead_time_seconds`, matching SDEF terminology.** Try omniJS `task.addDependent(otherTask, DependencyKind.FinishStart, leadTimeSeconds)` first; if that signature doesn't exist, fall back to `new Dependency(...)` constructor or whatever the Console reveals. The SDEF `depend X upon Y` AppleScript command is the absolute fallback. Without this feature, the MCP outputs a list, not a Gantt.
- [ ] **Dependencies — remove.** `remove_dependency(predecessor_id, successor_id) -> {removed: bool}`. omniJS approach (unverified): iterate `task.dependents` (or `task.prerequisites`), find match by counterpart task ID, call `.remove()` on the dependency object.
- [ ] **Dependencies — list.** `list_dependencies(task_id?) -> [{predecessor_id, successor_id, kind, lead_time_seconds}]`. Property names on the dependency object are **unverified** — likely `prerequisiteTask` and `dependentTask` per SDEF, possibly `predecessor`/`successor` per common conventions. Confirm and conform to the omniJS names.
- [ ] **`find_task` by name.** `find_task(name: str, exact: bool = False) -> [{id, title, outline_id}]`. For `exact=True`: try `scenario.taskNamed(name)` (**Verified** location: on Scenario, not Document — `actual.taskNamed(...)` per `big-picture.md`). For `exact=False`: walk `rootTask.descendents()` and substring-match. Removes the "list → grep → use ID" pattern.
- [x] **`save_document() -> {saved, name, modified_before, modified_after}`.** Shipped on `feat/save-document`. **Autosave behavior — verified empirically (2026-05-01, OmniPlan 4.10.2):** OmniPlan does NOT autosave the front document on idle. After editing a task via MCP, polled `document.modified()` over a 10-second window: the flag stayed `true` throughout. Explicit save is therefore necessary to persist between UI File>Save commands and the quit-time save prompt. Implementation note: `document.save()` is synchronous-return but clears the `modified` flag ~500ms later, so the wrapper polls up to 2s before reporting `modified_after`.

### Tier 1 — Real planning tool (P1, ~3 days)

- [ ] **Constraint dates on `update_task`. BLOCKED — omniJS persistence gap.** Probed live against OmniPlan 4.10.2 on 2026-05-01 (branch `feat/constraints`). The omniJS Task object accepts writes to `startConstraintDate`, `startBeforeDate`, `endAfterDate`, `endBeforeDate` within a single `evaluateJavascript` call and reads them back **inline**. But the values **do not persist** across JXA call boundaries — the property reverts to `typeof === "undefined"` on the next call. The control case `task.manualStartDate` does persist, ruling out a generic Date / serialization issue. The accessors that *do* persist live on the SDEF AppleScript bridge (cocoa keys `scriptStartConstraintDate`, `scriptStartBeforeDate`, `scriptEndAfterDate`, `scriptEndBeforeDate`) — a different bridge from `Application.evaluateJavascript`. Implementing constraint dates therefore requires a parallel JXA bridge that talks SDEF specifiers, which is out of scope for the current fork (the `jxa.py` bridge is settled and dedicated to omniJS). Revisit when (a) Omni wires constraint dates through to omniJS persistently — `tests/integration/test_constraints.py` is an `xfail(strict=True)` sentinel that goes RED when this happens — or (b) we decide a parallel SDEF bridge is worth the lift.
- [ ] **`get_project_info()`** — returns `{name, start_date, end_date, currency, working_hours, scenarios[]}`.
- [ ] **`update_project(...)`** — start date, currency, default working hours.
- [ ] **`move_task(task_id, new_parent_id?, after_sibling_id?)`. BLOCKED — omniJS gap.** Probed live 2026-05-01 (branch `feat/move-task`). The omniJS Task class exposes `addSubtask`, `addPrerequisite`, `addDependent`, `addAssignment`, `descendents`, `clearResourceLeveledDate`, `customValue`, `setCustomValue`, `setCustomData`, `split`, `remove` — and no `move`/`insertAfter`/`insertBefore`/`reparent`/`appendTo`/`prependTo` equivalents. SDEF defines a `move` command for tasks (NSMoveCommand) but the JXA bridge to the task collection is fragile (`app.documents()[0].project.tasks()` returned references whose `.title()` accessor failed). Clone-and-replace would change uniqueIDs, breaking dependencies and assignments — not a viable workaround. `tests/integration/test_move_task.py` is an `xfail(strict=True)` sentinel.
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

- **Fixture doc:** runs against the **front document** of the running OmniPlan process. A checked-in `tests/fixtures/test-suite.oplx` is *not* shipped in v0.1.1 — `.oplx` is a bundle of XML members that requires either a generator or a manual GUI round-trip to bootstrap (see the `omniplan-format` skill). The marker isolation below is the actual safety net; the fixture would be a clean-room nicety. **Add later** when there's a generator or when test pollution becomes a real problem.
- **Pytest marker:** `@pytest.mark.requires_omniplan` — `tests/conftest.py` auto-skips the marked tests when OmniPlan 4 isn't running or the sandbox container is missing.
- **Per-test isolation:** `tests/integration/conftest.py` provides a `test_root` fixture that creates `__test__root` (a Group task) on demand under the document root and cleans up by deleting *every* `__test__*` task at teardown. Tests must prefix every task they create. No parallel tests (asyncio lock + GUI app makes parallelism dangerous).
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
