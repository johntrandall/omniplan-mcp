# omniplan-mcp Testing Policy

> Adapted from a multi-domain testing-intelligence policy (L1–L8 levels, lifecycle gates, mocking strategies) and collapsed for a 1-domain, 1-external-system codebase. Verifier-pass corrections applied 2026-05-01.

## Core beliefs

1. **Tests are contracts, not afterthoughts.** A passing test is evidence the test passes, not that the code is correct. Ask: would a subtle bug survive this assertion?
2. **The right test at the right level.** If it can be proven by parsing a JXA envelope without OmniPlan, don't spawn OmniPlan.
3. **Domain boundaries are test boundaries.** Our one boundary is `Application('OmniPlan').evaluateJavascript(...)`. That boundary gets bilateral contract tests against documented omniJS class behaviour.
4. **Vendor-docs alignment is load-bearing.** This codebase's bug class *is* doc-misreading (commit `f5e48fb fix(docs+constraints): correct misread omniJS claims`). Every omniJS identifier we reach into must be traceable to <https://omni-automation.com/omniplan/>.
5. **OmniPlan is GUI-stateful.** Per-test marker cleanup (`__test__*`) handles task/resource isolation. Per-class app restart is reserved for documented failure modes, not the default.

## Levels

Four levels. No numbering — names alone suffice for a 1-domain codebase. Cadence in the right column.

| Level | What | Mocked | Cadence |
|---|---|---|---|
| **unit** | Pure-Python helpers (jxa.py escape, envelope parsing, parameter serialization, vendor-docs lint logic) | All I/O | every commit (pre-commit hook) |
| **contract** | Each tool wraps one omniJS API call. Test verifies the documented contract round-trips: write via tool → read back via tool → assert. | Nothing — real OmniPlan, real osascript | pre-release |
| **workflow** | Multi-tool sequences exercising a real user story (create_task → add_dependency → assign_resource → save → reopen → assert state survives close). | Nothing | pre-release |
| **e2e-live-xml** | Canonical write-paths for each tool category, plus a `.oplx` save → unzip → `Actual.xml` parse to confirm writes reached the underlying model, not just the JS context. | Nothing | pre-release |

**Why e2e-live-xml exists.** Constraint dates were once thought broken because writes appeared to land but didn't persist across `evaluateJavascript` calls (commit history pre-`f5e48fb`). The actual bug was probing under SDEF names; once corrected, the writes did reach the model. But the same failure mode could recur on a future omniJS API: a setter that succeeds in JS without reaching the model. The XML cross-check is the safety net for that bug class. **One canonical e2e-live-xml test per write tool, sampled — not every assertion gets the unzip+parse treatment.**

**Vendor-docs alignment** is enforced as a unit-level lint, not a separate level. See "Vendor-docs alignment" below.

**MCP transport (formerly L5).** Dropped. With one domain and one external system, a "full server, faked OmniPlan" tier duplicates `unit` (envelope parsing) plus `contract` (real round-trip). The MCP transport layer is FastMCP boilerplate; bugs there surface immediately on any contract test invoked through the real server. Add only if a specific MCP-client bug appears.

## What we don't test

Explicit non-coverage with rationale. Adding to this list requires a PR with rationale.

- **Concurrency.** osascript serializes via the `asyncio.Lock` in `jxa.py` and OmniPlan's run loop. Multi-client simultaneous writes are not exercised. Reason: agents are single-threaded in practice.
- **TCC denial path.** Tested manually on host, not in the VM (the VM image bakes in the grant).
- **Performance.** No assertions on per-call latency. osascript startup dominates (~1–3s); optimization is a separate concern.
- **Multi-document.** All tools accept an optional `document_name` but always operate on the front document in tests. No agent workflow needs multi-doc today.
- **Network/disk failure during save.** `document.save()` writes to local FS; we don't simulate full disk or permission errors.

## Vendor-docs alignment (unit-level lint)

A unit test (`tests/unit/test_vendor_docs_alignment.py`) parses every `omniJS` snippet inside the `omniplan_mcp` package, extracts identifiers of the form `task.X`, `dep.X`, `assignment.X`, `r.X`, `actual.X`, `proj.X`, `doc.X`, `Duration.X`, `DependencyKind.X`, `ResourceType.X`, `Decimal.X`, `Document.X`, and asserts each appears in a checked-in snapshot of the relevant page from <https://omni-automation.com/omniplan/>.

The snapshot lives at `tests/vendor-docs-snapshot/` (one .md per class, refreshed manually when OmniGroup updates the docs). The lint is `grep`-based, not parser-based — overaggressive, so a small allowlist (`tests/unit/vendor_docs_allowlist.txt`) covers the few legitimate identifiers that won't appear verbatim in vendor docs (e.g. local helper variables named `task` inside our omniJS strings).

This lint goes RED on the next commit that uses an undocumented or misnamed identifier. It would have caught the `startConstraintDate` / `assignment.units` / `proj.scenarios` mistakes that drove the May 1 corrections.

## Integration test reliability

The existing `tests/integration/conftest.py` `test_root` fixture handles per-test isolation:
1. Creates `__test__root` group on demand.
2. Yields its uniqueID to the test.
3. Cleans up by deleting every `__test__*` task and `__test__*` resource at teardown.

This is sufficient for the failure modes the suite has actually hit (test pollution, cross-test resource accumulation). **No per-class app restart by default.**

App restart is a one-off escalation pattern for tests that demonstrably need it — e.g. a test that exercises `document.save()` against an Untitled document, where OmniPlan's Save As sheet leaks into the next test. Such tests use a `requires_clean_omniplan` marker that triggers the ritual:

```
pkill -x OmniPlan ; sleep 2
defaults delete com.omnigroup.OmniPlan4 NSWindow.FrameAutosaveName 2>/dev/null
open tests/fixtures/baseline.oplx
poll Application('OmniPlan').documents().length === 1 with 10s timeout
```

If a test isn't marked, it runs against whatever OmniPlan state the prior test left behind, which is fine if `__test__*` cleanup did its job.

**xfail sentinels** stay as-is — `pytest.mark.xfail(strict=True)` for documented vendor gaps (currently `test_move_task.py`).

## VM execution

All `contract` / `workflow` / `e2e-live-xml` tests run inside a **persistent** Tart VM named `omniplan-dev`, NOT an ephemeral clone. Reasons:

- **OmniPlan license activation** is unverified across APFS clones (no precedent in our infrastructure for licensed Mac apps in cloned VMs). A persistent VM activates once and stays activated.
- **Focus stealing** — running OmniPlan on the host interrupts the developer.
- **Hermetic state** — the developer's host has Documents history, autorestore preferences, license, and TCC grants tied to their account; the VM is a known starting point.

The runner does not `tart-vm destroy` between runs. It SSHes into the running VM, runs the suite, collects logs.

### VM provisioning constraints (must be solved before first green run)

These constraints are documented for the future build of the L3 image and are not auto-resolved by the runner:

1. **TCC Automation grant cannot be written at L3 build time with SIP on.** Per ADR-048, TCC sqlite3 writes require SIP off, which is only true at L1/L2 build. The grant for `osascript → com.omnigroup.OmniPlan4` must therefore either:
   - Be added at L2 build time, with the bundle ID hardcoded (OmniPlan isn't installed at L2, but TCC rows can reference unresolved bundle IDs), OR
   - Be granted manually once after L3 build via System Settings → Privacy & Security → Automation, then preserved across clones via APFS CoW (per `tart-vm-management` "What survives cloning").

   The L3 build script must document which path it takes. Until either is wired up, expect first-launch TCC dialogs.

2. **OmniPlan license activation behaviour in cloned VMs is unverified.** Before relying on ephemeral clones, run a smoke test: clone L3, boot, attempt `evaluateJavascript`, see if a license dialog appears. If it does, ephemeral clones are off the table and the persistent-VM-only model is mandatory (which the runner already assumes).

3. **The `omniplan-dev` VM and `macos-15.7-l3-omniplan-mcp` image do not yet exist.** They are referenced by this policy as targets for the L3 build procedure. The build procedure (one-time, manual, interactive for license activation) is documented in `dev-docs/vm-provisioning.md` (TODO, not yet written).

### Test runner (`scripts/pre-release-test.sh`)

This script does not yet exist. Its specified shape:

1. Verify `omniplan-dev` VM is running (`tart list` includes it; if not, `tart-vm start omniplan-dev`).
2. Sync source via VirtioFS (handled at VM start time — VirtioFS mounts persist for the VM's life; for a pre-release gate this is fine since source is frozen at commit).
3. SSH in, run `pytest -m requires_omniplan tests/ --junit-xml=/tmp/junit.xml`.
4. Pull junit XML and any OmniPlan crash logs from `~/Library/Logs/DiagnosticReports/*OmniPlan*` back to host.
5. Print summary, exit non-zero on any failure.

Realistic runtime budget: 10 contract tests at 1–3s each + 5 workflow tests at 5–30s + 3 e2e-live-xml at 30–60s ≈ 4–10 minutes. Pre-release gate cadence makes this acceptable.

## Skepticism checks (for the reviewer)

When reviewing a test PR:

1. Would this test pass even if the omniJS write didn't reach the model? (If yes → add an `e2e-live-xml` cross-check.)
2. Would this test pass if the tool returned an empty dict? (If yes → assertions are too weak.)
3. Does the test reference the documented omniJS API by URL? (Should — ties verification to vendor docs.)
4. If the test fails, will the failure message tell me what broke?
5. Is this test resilient to test-order changes within its class?

## Anti-patterns

- **Tests that re-implement the tool.** Asserting the tool's omniJS string contains `task.effort = N` tests the implementation, not the contract. Test: did `get_task` return the new effort?
- **Tests that pass when OmniPlan is dead.** The `requires_omniplan` marker must verify OmniPlan is responding before yielding the fixture, not just that the process exists.
- **Tests with no negative assertions.** Every test should also assert what *shouldn't* be true.

## OmniPlan version drift procedure

OmniGroup ships OmniPlan updates a few times per year. The omniJS API is stable across point releases but has historically broken on major version bumps. To detect drift early:

1. The L3 VM image records the OmniPlan build SHA in `~/.omniplan-mcp-baseline-build` (set by the L3 build script).
2. Pre-release runner compares the running OmniPlan build SHA against the baseline. If they differ, the runner emits a warning (does not block).
3. On a confirmed drift (new OmniPlan version), rebuild the L3 image, re-run the full suite, and update the baseline only if all tests pass. If any test fails, file an issue with the failing assertion and the version bump as the inflection point.

This is a procedure, not a test level — drift detection itself is a one-line shell check.

## References

- Source testing-intelligence policy (multi-domain, L1–L8 levels) — internal reference, not redistributable.
- omniJS class docs: <https://omni-automation.com/omniplan/>
- OmniPlan SDEF: `/Applications/OmniPlan.app/Contents/Resources/OmniPlan.sdef`
- `omniplan-format` skill: `~/.claude/skills/omniplan-format/SKILL.md` — for `.oplx` XML structure
- `tart-vm-management` skill: `~/.claude/skills/tart-vm-management/SKILL.md` — VM lifecycle
- `troubleshooting-sanity` skill: `~/.claude/skills/troubleshooting-sanity/SKILL.md` — methodology that produced this policy
- ADR-048 (VM Image Layer Architecture, internal) — TCC and SIP constraints. Summary: writes to `TCC.db` via sqlite3 require SIP off; SIP is only off at L1/L2 build time. L3 inherits SIP-on, so TCC grants must be added at L2 to be present in L3 clones.
