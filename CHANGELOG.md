# Changelog

All notable changes to this fork of `omniplan-mcp`. Versioning follows
[Semantic Versioning](https://semver.org/); the upstream baseline is `v0.1.0`
(commit `b235768`).

## [Unreleased]

### Added
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
