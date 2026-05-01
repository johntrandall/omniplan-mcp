# omniplan-mcp Roadmap

Forked from [xiahan4956/omniplan-mcp](https://github.com/xiahan4956/omniplan-mcp) at commit `b235768` on 2026-05-01.
Upstream ships 6 task-CRUD tools — useful but covers only ~20% of OmniPlan's omniJS API.
This fork extends coverage so Claude can drive a real Gantt: dependencies, resources, leveling, baselines, scheduling.

## Current status

- **v0.3.0** tagged 2026-05-01 (Tier 1 of this roadmap).
- **19 tools** registered (upstream baseline: 6).
- **44 tests** collected: 8 unit + 36 integration. On the omniplan-dev Tart
  VM (untitled doc): 40 pass, 2 skip (`save_document` tests gated on
  `document.path`), 2 `xfail(strict=True)` sentinels for omniJS gaps. On
  the host with a saved doc open: 42 pass, 0 skip, 2 xfail.

| Tier | Status | Date |
|---|---|---|
| Tier 0 | Shipped — `v0.2.0` | 2026-05-01 |
| Tier 1 | Shipped (with two BLOCKED items, sentinels in place) — `v0.3.0` | 2026-05-01 |
| Tier 2 | Not started | — |
| Tier 3 | Not started | — |

**See [`omnijs-persistence-gaps.md`](omnijs-persistence-gaps.md) for the full catalogue of probed omniJS limitations and the sentinel tests that watch for fixes.**

## Prerequisites for any feature work

1. **Read vendor docs first.** They live in `~/dev/zVendorDocs/OmniPlan/` (downloaded 2026-05-01):
   - `omni-automation-website-v4.10.2-2026-05-01/` — partial mirror of `omni-automation.com/omniplan/`. **Only 8 top-level pages were captured** (`index.md`, `big-picture.md`, `application.md`, `setup.md`, `tutorial.md`, `actions.md`, `conference-example.md`, `conference-fetch-example.md`). Deep API pages (Tasks, Dependencies, Resources, Documents) were **not** mirrored — fetch them online from `https://omni-automation.com/omniplan/` as needed.
   - `applescript-dictionary-v4.10.2-2026-05-01/` — SDEF + per-suite breakdowns. Authoritative for class/property names. **Use this when omniJS docs are missing.**
   - `reference-manual-mac-v4.5.5-2026-05-01/` — user manual (concept reference for inspectors, views, terminology).
2. **The bridge architecture is settled.** `osascript -l JavaScript` → `Application('OmniPlan').evaluateJavascript(...)` runs an omniJS string inside the running app and returns its value across the AppleEvent boundary. See `src/omniplan_mcp/jxa.py`. Don't touch this; it's the only nontrivial plumbing.
3. **Test environment.** OmniPlan must be running with `funding-pipeline.oplx` (or another scratch doc) open. macOS Automation TCC must be granted. Use marker-prefixed task names (`__test__*`) so the cleanup pass is unambiguous. See `Testing` section.

## Verified API surface (probed live 2026-05-01, OmniPlan 4.10.2)

Everything below is verified against the running app. For the things we tried and
found to be missing or broken, see [`omnijs-persistence-gaps.md`](omnijs-persistence-gaps.md).

| Pattern | Status |
|---|---|
| `task.addSubtask()`, `task.descendents()`, `task.subtasks` | ✓ |
| `task.effort = N` (raw integer person-seconds — NOT a Duration) | ✓ |
| `task.minEffortEstimate`, `expectedEffortEstimate`, `maxEffortEstimate` | ✓ persistent. Setting all three triggers PERT recompute of `effort = (min + 4·expected + max) / 6` |
| `task.title`, `task.note`, `task.manualStartDate`, `task.manualEndDate` | ✓ |
| `task.remove()` | ✓ — used in source |
| `task.split(...)` | probed-only — exists on the prototype but not exercised by any current tool |
| `task.addDependent(other) -> Dependency` (then `dep.kind = DependencyKind.X` separately) | ✓ |
| `DependencyKind.{FinishStart, FinishFinish, StartStart, StartFinish}` | ✓ |
| `dep.prerequisite`, `dep.dependent`, `dep.kind`, `dep.remove()` | ✓ |
| `task.dependents`, `task.prerequisites` (arrays of Dependency) | ✓ |
| `actual.taskNamed(name)` (on Scenario, not Document; returns `null` on miss) | probed-only — `find_task` uses `descendents()` traversal because it also needs the outline path, but `taskNamed` is verified to exist and behave as documented |
| `document.save()` (no args) | ✓ — async-clears the dirty flag ~500ms later |
| `document.modified()` (JXA SDEF) | ✓ |
| `documents()[0].path()` (JXA SDEF, omniJS doesn't expose `document.path`) | ✓ |
| `actual.startDate = new Date(...)` | ✓ persistent |
| `actual.rootResource.addMember()` → Resource | ✓ |
| `r.name`, `r.email`, `r.type`, `r.uniqueID` | ✓ persistent |
| `r.costPerUse = Decimal.fromString("100.00")` (NOT a Number) | ✓ on write; opaque on read (parse `String(d)`) |
| `ResourceType.{staff, equipment, material, group}` | ✓ |
| `task.addAssignment(resource) -> Assignment`, `assignment.resource`, `assignment.remove()` | ✓ |

### Known omniJS API limitations

- **`task.parent` does NOT exist.** Documented in `src/omniplan_mcp/tasks.py` line 27. Parent IDs are computed via traversal of `rootTask.descendents()`, not read off the task.
- **Persistence gaps** (write inline, lost across calls): `task.startConstraintDate`/`startBeforeDate`/`endAfterDate`/`endBeforeDate`, `dep.leadTimeDuration`, `assignment.units`, `actual.currency`. See gaps doc.
- **Read-opaque objects**: `Duration` (no `.seconds` accessor), `Decimal` (parse `toString` for the value), `actual.rootResource.schedule` (fully opaque).
- **Missing methods**: no `task.moveTo` / `insertAfter` / `reparent`. No `proj.scenarios` enumeration.

### Terminology

We match the omniJS / SDEF names, not invented translations. SDEF says `lead time` and `lead percentage`; we use `lead_time_seconds`. SDEF says `prerequisite`/`dependent`; we use `predecessor_id`/`successor_id` only at the wire level (the underlying property is `prerequisite`/`dependent`).

## Prioritized Feature TODO

Ordered by how badly each gap blocks "Claude as a Gantt-driver." Tier 0 must ship before this MCP is qualitatively useful for planning; Tier 1 makes it a real planning tool; Tier 2/3 are expert features.

### Tier 0 — Shipped in v0.2.0

- [x] **`create_task` / `update_task` accept `effort_seconds`** plus the three-point estimate fields (`min_effort_seconds`, `expected_effort_seconds`, `max_effort_seconds`). `task.effort = N` is a raw integer in person-seconds; setting all three estimates triggers PERT recompute of `effort`. (PR #2.)
- [x] **`add_dependency` / `remove_dependency` / `list_dependencies`** — supports FS / SS / FF / SF kinds. `lead_time_seconds` is write-only; see persistence gaps doc. (PR #4, branch `feat/dependencies`.)
- [x] **`find_task(name, exact=False)`** — case-insensitive substring or exact-match lookup. (PR #3.)
- [x] **`save_document()`** — autosave verified absent (`document.modified()` stays `true` for ≥10s after an edit). (Branch `feat/save-document`.)

### Tier 1 — Shipped in v0.3.0 (with two BLOCKED items)

- [ ] **Constraint dates on `update_task`.** BLOCKED — `xfail(strict=True)` sentinel at `tests/integration/test_constraints.py`. See [`omnijs-persistence-gaps.md`](omnijs-persistence-gaps.md) §1 for the failure mode and what we'd need from OmniGroup.
- [x] **`get_project_info()`** (PR #6) — returns `{name, path, start_date, end_date, scenarios}`. `currency` and `working_hours` deferred (write doesn't persist; schedule object is opaque).
- [x] **`update_project(start_date)`** (PR #6) — `actual.startDate` write verified persistent. Currency rejected from API.
- [ ] **`move_task`.** BLOCKED — `xfail(strict=True)` sentinel at `tests/integration/test_move_task.py`. omniJS Task class exposes no move/reparent/insertAfter/insertBefore methods. See gaps doc §3.
- [x] **`create_tasks(tasks: list[dict])`** (PR #7) — bulk creation in a single JXA call. Adds `parent_index` field for intra-batch parent references.
- [x] **Resource CRUD.** `list_resources`, `create_resource(name, type, email?, cost_per_use?)`, `delete_resource(id)` (PR #8).
- [x] **Assignments.** `assign_resource(task_id, resource_id, units?)`, `unassign_resource(task_id, resource_id)` (PR #8). `units` is write-only; see gaps doc.

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
