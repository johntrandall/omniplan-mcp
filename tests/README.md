# Tests

Three layers, all under `pytest`:

| Layer | Where | Needs OmniPlan? | When it runs |
|---|---|---|---|
| Unit | `tests/unit/` | No | Always — fast, mocks `subprocess`. |
| Integration | `tests/integration/` | Yes (running, doc open, TCC granted) | Auto-skipped when OmniPlan isn't running. |
| Manual smoke | `tests/manual/smoke.py` | Yes | Run by hand: `python tests/manual/smoke.py`. Not collected by pytest. |

## Setup

```bash
pip install -e '.[dev]'
```

## Run

```bash
# Unit only — safe in CI, no OmniPlan needed.
pytest -m "not requires_omniplan"

# Everything — opens against your front OmniPlan document. Make sure
# nothing precious is open or that you trust the cleanup pass.
pytest

# Just integration tests against a live OmniPlan.
pytest tests/integration
```

## Test environment expectations

Integration tests run against the **front document** of the running OmniPlan
process. They do not require — and currently do not ship — a checked-in
fixture `.oplx`. Two reasons:

1. `.oplx` files are bundle directories with several XML members; round-tripping
   one as a binary blob through git is painful, and a generator-built fixture
   would be a separate engineering project (see `omniplan-format` skill).
2. The real safety net is **marker isolation**, not the fixture: every task
   created during a test is named `__test__<...>`, and the integration
   `conftest.py` deletes every task whose title starts with `__test__` after
   each test. Even if you run against your real planning doc, the cleanup pass
   only touches tasks the test owns.

A `__test__root` group task is created lazily on first use and reused across
the run. It survives the cleanup sweep (its title starts with the prefix, so it
is removed at the end of the session along with the children).

If you want a clean room, open a fresh `Untitled.oplx` in OmniPlan before
running the integration suite.

## Adding tests

```python
# tests/integration/test_my_feature.py
import json
import pytest
from omniplan_mcp.tasks import create_task

@pytest.mark.requires_omniplan
async def test_something(test_root):
    raw = await create_task(title="__test__my_feature", parent_id=test_root)
    task = json.loads(raw)
    assert task["title"] == "__test__my_feature"
    # cleanup happens automatically via the test_root fixture's finalizer.
```

Always prefix titles with `__test__` so the cleanup sweep finds them.
