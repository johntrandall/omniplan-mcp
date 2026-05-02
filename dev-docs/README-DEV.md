# Developer notes — mcp-omniplan-jtr

The geekier half of the README. If you're trying to extend the MCP, ship a new tool, debug a tool, or audit how this thing actually works, start here.

## Architecture in one paragraph

Each tool is a thin Python wrapper around an omniJS string passed to `Application('OmniPlan').evaluateJavascript("…")` from JXA, via a single subprocess call to `osascript -l JavaScript`. The bridge wrapper in [`src/omniplan_mcp/jxa.py`](../src/omniplan_mcp/jxa.py) handles the JSON envelope, escapes Python-side strings for embedding into JS, and translates `osascript` errors into agent-friendly messages. Every public tool returns a JSON envelope describing the post-write state — read-after-write is the contract.

This bridge is settled. **Do not modify `jxa.py` without discussing first** — it is the only nontrivial plumbing in the codebase, and it is the original upstream contribution from `xiahan4956/omniplan-mcp` that we kept verbatim. The other ~86% of the codebase was rebuilt on top of it.

## Layout

```
src/omniplan_mcp/
├── jxa.py            # the bridge — DO NOT MODIFY without discussion
├── tasks.py          # 7 task-CRUD tools
├── dependencies.py   # 3 dependency tools
├── resources.py      # 5 resource + assignment tools
├── documents.py      # save_document, get_project_info, update_project
├── server.py         # FastMCP server registration
└── __main__.py       # CLI entry point

tests/
├── unit/             # pure-Python — runs in <1s, no OmniPlan needed
├── integration/      # contract tests — one OmniPlan call per assertion
├── workflow/         # multi-tool sequences (create→link→assign→save)
├── e2e/              # save .oplx, parse Actual.xml, cross-check
├── fixtures/         # baseline.oplx (minimal OmniPlan document)
├── vendor-docs-snapshot/  # snapshot of omni-automation.com class pages
└── manual/           # smoke.py — original sanity-check script

scripts/
├── pre-release-test.sh         # runs the integration suite in a VM
└── build-baseline-fixture.py   # generates tests/fixtures/baseline.oplx

dev-docs/
├── ROADMAP.md                  # tier 0 / 1 / 2 / 3 feature plan
├── testing-policy.md           # 4 test levels, cadence, vendor-docs lint
├── vm-provisioning.md          # how to build the omniplan-dev Tart VM
├── omnijs-persistence-gaps.md  # documented vendor-side gaps + sentinels
├── TODO.md                     # tracked follow-ups (e.g. OmniGroup replies)
└── README-DEV.md               # this file
```

## Reference material

- **omniJS API for OmniPlan**: <https://omni-automation.com/omniplan/> — canonical class reference. The bridge wraps `Application('OmniPlan').evaluateJavascript(...)` so every tool is a small omniJS snippet against this API.
- **Omni Automation JXA bridge**: <https://omni-automation.com/jxa-applescript.html> — describes the AppleEvent we use.
- **OmniPlan SDEF (AppleScript dictionary)**: `/Applications/OmniPlan.app/Contents/Resources/OmniPlan.sdef` (~1450 lines). Legacy surface but still authoritative for class/property names when omniJS docs are silent.

A snapshot of every relevant omniJS class page lives at [`tests/vendor-docs-snapshot/`](../tests/vendor-docs-snapshot/) — captured 2026-05-01, refreshable when OmniGroup updates the docs. The unit-level alignment lint [`tests/unit/test_vendor_docs_alignment.py`](../tests/unit/test_vendor_docs_alignment.py) asserts every JS identifier we ship appears in the snapshot.

## How to add a new tool

1. **Read the relevant vendor class page** at <https://omni-automation.com/omniplan/>. Don't guess at omniJS API. The most common bug class on this codebase is using SDEF AppleScript names that don't exist on the omniJS surface — the alignment lint catches it but only if you ran the lint before opening a PR.
2. **Pick the module.** Task-related → `tasks.py`. New domain → new module (~100 LOC threshold).
3. **Write the tool** as a Python `async def` with type hints. Use FastMCP's `@mcp.tool()` decorator. Wrap the omniJS string in triple-quotes; use the `_escape(value)` helper for any user input embedded into JS.
4. **Register it in `server.py`** if it's in a new module.
5. **Write integration tests** in `tests/integration/test_<feature>.py`. Prefix every task created during the test with `__test__` so the cleanup pass finds it. Use the `test_root` fixture to get a known parent.
6. **Run the alignment lint:** `pytest tests/unit/test_vendor_docs_alignment.py`. If it fails, refresh `tests/vendor-docs-snapshot/` to include the new identifiers, OR confirm you used the documented name (not the SDEF name).
7. **Run the integration test:** `pytest tests/integration/test_<feature>.py -v` — needs OmniPlan running with a document open.
8. **Add a row to the Tools table in `README.md`** and a CHANGELOG entry under `## [Unreleased]`.

## Running the tests

| Level | Command | OmniPlan needed? |
|---|---|---|
| unit | `pytest tests/unit/` | No |
| contract (integration) | `pytest tests/integration/` | Yes — front document open |
| workflow | `pytest tests/workflow/` | Yes |
| e2e (XML cross-check) | `pytest tests/e2e/` | Yes — saved document |
| pre-release (full sweep in VM) | `bash scripts/pre-release-test.sh` | Auto-managed (VM) |

See [`testing-policy.md`](testing-policy.md) for the full policy, including the VM-based pre-release runner and the vendor-docs alignment lint.

## Editable install for hacking

```bash
git clone https://github.com/johntrandall/omniplan-mcp.git
cd omniplan-mcp
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

Then either:
- Run the tests: `pytest tests/unit/`
- Run the MCP directly: `python -m omniplan_mcp` (it'll wait for stdio)
- Re-register the editable install with Claude:
  ```bash
  uv tool install --reinstall --from . mcp-omniplan-jtr
  claude mcp remove omniplan-local -s user
  claude mcp add -s user omniplan-local "$(which mcp-omniplan-jtr)"
  ```

## Lineage

This codebase started as a fork of [`xiahan4956/omniplan-mcp`](https://github.com/xiahan4956/omniplan-mcp) at commit `b235768`. The JXA bridge in [`jxa.py`](../src/omniplan_mcp/jxa.py) is verbatim from that work. Everything else (~86% of current LOC) was rebuilt: 13 new tools, 4 new modules, the test policy and lint, the VM runner, the documentation. Distribution under a distinct PyPI name (`mcp-omniplan-jtr`) reflects that the project is now substantially independent. MIT-licensed; the original author is credited in [`LICENSE`](../LICENSE).

## What we don't ship

- **macOS GUI app** — there isn't one. This is a stdio MCP server.
- **A way to launch OmniPlan** — agents can't open OmniPlan; the user does.
- **Multi-document workflows** — every tool operates on the front document. The `document_name` parameter exists but isn't agent-tested.
- **A bundled .oplx generator** — see the `omniplan-format` skill for that workflow.
