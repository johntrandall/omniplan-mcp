# Vendor docs snapshot

Manual snapshots of <https://omni-automation.com/omniplan/> class reference pages.
Captured 2026-05-01.

`tests/unit/test_vendor_docs_alignment.py` concatenates every `.md` in this
directory and asserts that every omniJS identifier our shipped code reaches
into appears verbatim somewhere here. The test SKIPS when this directory is
empty (e.g. fresh checkout, snapshot not yet captured).

To refresh: re-fetch each page from the upstream docs and replace the `.md`
file. Don't delete entries that are still in use; only the test result tells
you whether something is referenced.

Pages currently captured:

- `task.md` — Task class
- `dependency.md` — Dependency class + DependencyKind enum
- `resource.md` — Resource class + Assignment class + ResourceType enum
- `duration.md` — Duration class (instance + class functions)
- `project.md` — Project class
- `scenario.md` — Scenario class
- `document.md` — Document + PlanDocument classes
