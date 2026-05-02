# Changelog

All notable changes to `mcp-omniplan-jtr`. Versioning follows
[Semantic Versioning](https://semver.org/).

The project started as a fork of
[`xiahan4956/omniplan-mcp`](https://github.com/xiahan4956/omniplan-mcp) at
commit `b235768` (their `v0.1.0`). After Tier 0/1 work landed, ~86% of LOC
was new and the JXA bridge in `src/omniplan_mcp/jxa.py` was the only
significant remaining upstream code (kept verbatim under MIT). At v0.4.0 the
distribution was renamed to `mcp-omniplan-jtr` and the project posture
changed from "fork" to "build inspired by". See `LICENSE` for attribution.

## [0.4.1] - 2026-05-02

### Fixed
- `get_project_info` and any other date round-trip path through
  `documents.py` now uses `getUTCFullYear/Month/Date` instead of
  local-time getters. Writing an ISO date string parses as UTC
  midnight, so reading via local-time getters introduced a one-day
  skew west of UTC. The pre-existing `test_update_project_start_date_persists`
  flake was the visible symptom; the bug applied to every date read
  on a timezone-shifted host.
- `tests/e2e/test_oplx_xml_cross_check.py` and
  `tests/workflow/test_save_close_reopen.py` `_front_document_path()`
  helper: tries `path()` first, falls back to `file()` if path()
  raises `Can't convert types (-1700)`. The error happens with some
  saved documents on macOS 15+ where the SDEF coercion of NSURL to
  POSIX path fails. The production `get_project_info` already wraps
  in try/catch; the test helpers were missing that defensive cast.

### Added
- Homebrew tap formula at `johntrandall/tap/mcp-omniplan-jtr` —
  resource-bundled Python venv with all 36 transitive PyPI deps. Three
  install paths now documented in README: brew tap / uv tool / pip.

## [0.4.0] - 2026-05-02

### Changed (BREAKING)
- **Renamed PyPI distribution from `omniplan-mcp` to `mcp-omniplan-jtr`.**
  The CLI command renamed from `omniplan-mcp` to `mcp-omniplan-jtr`; users
  re-registering with Claude Code or Claude Desktop must update their MCP
  config. The Python import name (`omniplan_mcp`) is unchanged — visible
  only to developers extending the package.
- **Lineage reframed from "fork" to "inspired by"** in the README, since
  ~86% of current LOC is new and the project's direction is now
  independent from upstream. Original author still credited in `LICENSE`.
- **Removed `upstream` git remote** and dropped fork-style PR-upstreaming
  workflow. Subsequent feature work is committed directly to `main`.
- **Added `LICENSE`** (MIT) with dual copyright — John Randall for the
  current project and xiahan4956 for the original `jxa.py` bridge that
  remains in the codebase.
- **Project metadata** (`description`, `license`, `authors`, `classifiers`,
  URLs) populated in `pyproject.toml` for PyPI publication.

### Docs
- **README rewritten as consumer-facing** — install instructions, what-it-
  does table, example prompts. Geekier content moved to
  `dev-docs/README-DEV.md`.
- **`dev-docs/README-DEV.md` added** — architecture, tool-extension recipe,
  vendor-docs reference, editable-install workflow, lineage notes.
- **Redacted private-host paths and project-specific filenames from
  `dev-docs/ROADMAP.md`** — local vendor-docs mirror references replaced
  with the canonical public URL at <https://omni-automation.com/omniplan/>.

## [Unreleased]

### Added
- `update_task` accepts `start_no_earlier_than`, `start_no_later_than`,
  `end_no_earlier_than`, and `end_no_later_than` (ISO date strings, or
  empty string to clear). `get_task` surfaces them under the same names.
  Maps to the documented omniJS `task.startNoEarlierThanDate` /
  `startNoLaterThanDate` / `endNoEarlierThanDate` / `endNoLaterThanDate`
  setters. Round-trip verified live in
  `tests/integration/test_constraints.py` (4 tests, all passing).
  Earlier drafts of this fork's docs marked constraint dates as
  "BLOCKED — value lost across calls"; that was us probing under SDEF
  property names (`startConstraintDate` etc.) that don't exist on the
  omniJS Task class. The documented names work as expected.
- `list_assignments(task_id) -> [{resource_id, resource_name,
  units_assigned}]` — exposes per-task assignment info that
  `list_resources` doesn't cover.

### Fixed
- `list_dependencies` and `add_dependency` now round-trip
  `lead_time_seconds` via the documented `Duration.workSeconds`
  accessor instead of returning `null` / echoing the input. The
  previous session wrongly concluded `Duration` was opaque on read; the
  documented Duration class exposes `workSeconds`, `elapsedSeconds`,
  `elapsed`, and friends. Module docstring and tests updated.
- `assign_resource` now writes via the documented
  `assignment.unitsAssigned` (Number, read/write) instead of the
  non-existent `assignment.units`. The value is read back after the
  write — a true round-trip, not an echo.
- `get_project_info` now enumerates baselines via
  `proj.baselineNames`, returning
  `scenarios: ["Actual", ...proj.baselineNames]` instead of the
  hard-coded `["Actual"]`. The documented Project class exposes
  `baselineNames` (Array of String) plus `baselineNamed(name)`.

### Docs
- Rewrote `dev-docs/omnijs-persistence-gaps.md` from scratch. Earlier
  drafts asserted ~6 "persistence gaps" as facts; on doc re-read those
  were us probing under SDEF AppleScript names (`startConstraintDate`,
  `assignment.units`, etc.) that the omniJS classes don't expose under
  those names. The corrected doc lists only the surviving gaps: missing
  `task.moveTo` / reparenting (verified by three failed paths plus
  saved-bundle XML cross-check), and the `Decimal.toString` regex parse
  workaround. README "Known omniJS limitations" table aligned. ROADMAP
  Tier 1 status updated — constraints flipped from BLOCKED to shipped.

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
