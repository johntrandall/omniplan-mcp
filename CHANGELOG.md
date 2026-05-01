# Changelog

All notable changes to this fork of `omniplan-mcp`. Versioning follows
[Semantic Versioning](https://semver.org/); the upstream baseline is `v0.1.0`
(commit `b235768`).

## [Unreleased]

## [0.3.0] - 2026-05-01

Tier 1 of the fork roadmap (`dev-docs/ROADMAP.md`): adds
project-info, bulk task creation, resource CRUD + assignments, and
documents two omniJS surface gaps (constraints, move) as
`xfail(strict=True)` sentinels. Bumps the fork from 0.2.0 to 0.3.0.

Upstream PRs: [#6](https://github.com/xiahan4956/omniplan-mcp/pull/6),
[#7](https://github.com/xiahan4956/omniplan-mcp/pull/7), and the
resource module PR opened in this release.

Tool count: 13 → 19. New tools: `get_project_info`, `update_project`,
`create_tasks`, `list_resources`, `create_resource`, `delete_resource`,
`assign_resource`, `unassign_resource`.

### Added
- `list_resources`, `create_resource(name, type, email?, cost_per_use?)`,
  `delete_resource(resource_id)`, `assign_resource(task_id, resource_id,
  units?)`, `unassign_resource(task_id, resource_id)` in a new
  `src/omniplan_mcp/resources.py` module. ResourceType enum supports
  `staff` / `equipment` / `material` / `group`. `cost_per_use` is
  written through `Decimal.fromString(...)` per the omniJS contract;
  read back by parsing the Decimal toString.
- `create_tasks(tasks: list[dict])` — bulk task creation in a single
  JXA call. Each spec accepts the same fields as `create_task` plus a
  `parent_index` field for intra-batch parent references (a later task
  can parent to an earlier one without needing the earlier one's
  uniqueID). Performance: 50 tasks via 50 `create_task` calls is
  ~50–150s of osascript startup; via `create_tasks` it's ~1s.
- `get_project_info()` — returns `{name, path, start_date, end_date,
  scenarios}`. `path` is fetched via the JXA SDEF surface (omniJS
  doesn't expose it). `scenarios` only advertises `["Actual"]` because
  `proj.scenarios` is undefined in omniJS.
- `update_project(start_date)` — writes `actual.startDate`. Verified
  persistent across JXA calls.

### Test infrastructure
- `tests/integration/test_save_document.py` skips gracefully when the
  front document hasn't been saved yet (e.g. fresh Tart VM with only
  an Untitled doc) — `document.save()` would otherwise pop the Save As
  sheet and block the JXA call.

### Notes on omniJS gaps
- `actual.currency` accepts a write inline but doesn't persist across
  JXA boundaries (same trap as constraint dates) — deliberately omitted
  from `update_project` rather than shipping a footgun.
- Working hours / calendar — `actual.rootResource.schedule` exists but
  is opaque on read; deferred until we add a parallel SDEF bridge or
  Omni exposes accessors.
- `assignment.units` — write accepted, NOT persistent across JXA
  boundaries (same trap as `dep.leadTimeDuration`). `assign_resource`
  echoes the input value but `list_resources` doesn't expose a units
  field, since reads can't be trusted.
- Constraint dates and `move_task` — both blocked on omniJS persistence
  gaps; documented xfail sentinels in
  `tests/integration/test_constraints.py` and `test_move_task.py`.

## [0.2.0] - 2026-05-01

Tier 0 of the fork roadmap (`dev-docs/ROADMAP.md`): adds dependency
support, effort/three-point estimation, name-based lookup, and
explicit save. Bumps the fork from `0.1.1` to `0.2.0`. Upstream PRs:
[#2](https://github.com/xiahan4956/omniplan-mcp/pull/2),
[#3](https://github.com/xiahan4956/omniplan-mcp/pull/3),
[#4](https://github.com/xiahan4956/omniplan-mcp/pull/4),
[#5](https://github.com/xiahan4956/omniplan-mcp/pull/5).

### Added
- `save_document()` tool. OmniPlan does NOT autosave on idle (verified
  empirically — `document.modified` stays `true` for at least 10s after
  an edit). Explicit save is required to persist between UI File>Save
  commands and the quit-time save prompt. Returns
  `{saved, name, modified_before, modified_after}`. The wrapper polls
  the dirty flag for up to 2s after `document.save()` since the flag
  clears ~500ms after the synchronous return.
- `add_dependency(predecessor_id, successor_id, kind, lead_time_seconds)`,
  `remove_dependency(predecessor_id, successor_id)`,
  `list_dependencies(task_id=None)` tools (new module
  `src/omniplan_mcp/dependencies.py`). Supports all four DependencyKind
  values (FS / SS / FF / SF). **Known limitation:** `lead_time_seconds`
  is write-only — OmniPlan's omniJS `Duration` is opaque and exposes no
  read accessor, so `list_dependencies` returns `lead_time_seconds:
  null`. Documented in the module docstring and tests.
- `find_task(name, exact=False)` tool. Substring (case-insensitive) by
  default, exact match opt-in. Returns `[{id, title, outline_id}]`.
  Removes the "list everything → grep → use ID" pattern.
- `create_task` / `update_task` accept `effort_seconds`,
  `min_effort_seconds`, `expected_effort_seconds`, `max_effort_seconds`.
  Effort writes a raw integer to `task.effort` (verified live against
  OmniPlan 4.10.2). Setting all three estimates triggers OmniPlan's
  PERT recompute: `effort = (min + 4*expected + max) / 6` — documented
  in `tests/integration/test_effort.py`.
- `tests/` package: pytest layout (`unit/`, `integration/`, `manual/`,
  `fixtures/`), `requires_omniplan` marker that auto-skips when OmniPlan 4
  is not running, integration `test_root` fixture that creates `__test__root`
  on demand and cleans up every `__test__*` task after each test.
- `[project.optional-dependencies] dev` group with `pytest` and
  `pytest-asyncio`.
- Unit tests for the JXA envelope helpers in `tests/unit/test_jxa_escape.py`.
- Integration tests for effort fields in `tests/integration/test_effort.py`.

### Changed
- `test_tools.py` moved to `tests/manual/smoke.py`. Run with
  `python tests/manual/smoke.py`. Unchanged behaviour.
- ROADMAP: documented the front-document + marker-isolation testing
  approach (no checked-in `.oplx` fixture for now).

## [0.1.0] - upstream baseline

Forked from [xiahan4956/omniplan-mcp](https://github.com/xiahan4956/omniplan-mcp)
at commit `b235768` on 2026-05-01. Six task-CRUD tools:
`list_documents`, `query_tasks`, `get_task`, `create_task`, `update_task`,
`delete_task`.
