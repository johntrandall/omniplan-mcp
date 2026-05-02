"""Vendor-docs alignment lint.

Fails if any omniJS identifier our code reaches into is missing from a
checked-in snapshot of the vendor docs at https://omni-automation.com/omniplan/.

This is the lint that would have caught the May 1 doc-misreading episode
(commit f5e48fb): we were probing under SDEF names like `startConstraintDate`
and `assignment.units` that don't exist on the documented omniJS classes,
and the "facts" were never reachable in vendor-docs text.

Methodology:

1. Walk every Python source under `src/omniplan_mcp/` and extract every
   triple-quoted string fragment that gets passed into `run_omnijs(...)` or
   embedded as a JS template within `_RESOURCE_OBJ_HELPER` etc.
2. Inside those strings, find identifiers of the form
   ``(task|dep|assignment|r|actual|proj|doc|root|t|a|res|d)\\.(...)``
   and constants ``(Duration|DependencyKind|ResourceType|Decimal|Document|TaskType)\\.(...)``.
3. Strip allow-list entries (helper variables, project-internal names).
4. Concatenate every .md file under `tests/vendor-docs-snapshot/` and
   assert each remaining identifier appears verbatim.

Refresh the snapshot when OmniGroup updates the docs:

    rm -rf tests/vendor-docs-snapshot && \\
        python3 scripts/refresh-vendor-docs-snapshot.py   # (TODO: write)

Until that script exists, refresh manually by saving each page from
https://omni-automation.com/omniplan/ as a single .md (one per class) under
tests/vendor-docs-snapshot/.

The lint deliberately does NOT verify the *existence* of the vendor-docs
snapshot directory — when it's empty (e.g. fresh checkout, snapshot not yet
captured), the test SKIPS rather than fails. This keeps the lint quiet for
contributors who haven't snapshotted yet, but loud for CI/pre-release where
the snapshot is checked in.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src" / "omniplan_mcp"
SNAPSHOT_DIR = REPO_ROOT / "tests" / "vendor-docs-snapshot"
ALLOWLIST_FILE = REPO_ROOT / "tests" / "unit" / "vendor_docs_allowlist.txt"

OBJECT_PREFIXES = (
    "task",
    "t",
    "dep",
    "assignment",
    "r",
    "res",
    "actual",
    "proj",
    "doc",
    "root",
    "rootRes",
    "rootTask",
    "a",
    "d",
    "g",
    "m",
)

CONSTANT_PREFIXES = (
    "Duration",
    "DependencyKind",
    "ResourceType",
    "Decimal",
    "Document",
    "TaskType",
)

OBJ_PATTERN = re.compile(
    r"\b(?:" + "|".join(OBJECT_PREFIXES) + r")\.([A-Za-z_][A-Za-z_0-9]*)"
)
CONST_PATTERN = re.compile(
    r"\b(" + "|".join(CONSTANT_PREFIXES) + r")\.([A-Za-z_][A-Za-z_0-9]*)"
)

# Match every triple-quoted block in src/. Almost all such blocks in this
# codebase are JS templates passed to run_omnijs / run_jxa or returned
# from helper functions like `_task_to_obj()`. A narrower per-call-site
# pattern list (the previous form) had blind spots — taskToObj's body
# wasn't extracted because it lived inside `return _fmt_date() + """..."""`,
# which didn't match any of the named patterns. Catching every triple-quote
# is over-broad but safe: identifiers we extract that aren't real omniJS
# names (Python docstrings, etc.) still pass through the snapshot/allowlist
# filter, so over-extraction can only ADD allowlist entries, not skip
# real bugs.
JS_FRAGMENT_PATTERNS = [
    re.compile(r'f?"""(.*?)"""', re.DOTALL),
]


def _load_allowlist() -> set[str]:
    if not ALLOWLIST_FILE.exists():
        return set()
    return {
        line.strip()
        for line in ALLOWLIST_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def _extract_js_fragments() -> list[str]:
    fragments: list[str] = []
    for py_file in SRC_DIR.rglob("*.py"):
        text = py_file.read_text()
        for pattern in JS_FRAGMENT_PATTERNS:
            fragments.extend(pattern.findall(text))
    return fragments


def _extract_identifiers(fragments: list[str]) -> set[str]:
    found: set[str] = set()
    for frag in fragments:
        for match in OBJ_PATTERN.finditer(frag):
            found.add(match.group(1))
        for match in CONST_PATTERN.finditer(frag):
            found.add(f"{match.group(1)}.{match.group(2)}")
    return found


_BULLET_PATTERN = re.compile(r"^\s*[-*]\s+(?:`)?([A-Za-z_][A-Za-z_0-9.]*)(?:`)?\s*$")


def _snapshot_identifiers() -> set[str]:
    """Parse every markdown bullet in the snapshot dir into an exact-match
    set of identifiers.

    Snapshot files use markdown bullets like:
      - title
      - workSeconds
      - Duration.workSeconds
      - DependencyKind.FinishStart

    Returns the bare identifier (`title`) AND the dotted form
    (`Duration.workSeconds`) so both OBJ_PATTERN matches (just the
    property) and CONST_PATTERN matches (`Class.method`) can be checked
    against the snapshot.

    The previous implementation concatenated the snapshot as raw text and
    used substring search, which let a typo like `task.titl` pass because
    "titl" is a substring of "title". Exact set membership closes that
    gap.
    """
    if not SNAPSHOT_DIR.exists():
        return set()
    out: set[str] = set()
    for path in SNAPSHOT_DIR.rglob("*.md"):
        for line in path.read_text().splitlines():
            m = _BULLET_PATTERN.match(line)
            if not m:
                continue
            ident = m.group(1)
            out.add(ident)
            # If the snapshot lists a dotted form like `Duration.workSeconds`,
            # also expose the bare suffix (`workSeconds`) so OBJ_PATTERN
            # matches resolve.
            if "." in ident:
                out.add(ident.rsplit(".", 1)[1])
    return out


@pytest.fixture(scope="module")
def snapshot() -> set[str]:
    idents = _snapshot_identifiers()
    if not idents:
        pytest.skip(
            "No vendor-docs snapshot under tests/vendor-docs-snapshot/. "
            "Run scripts/refresh-vendor-docs-snapshot.py (or capture manually) "
            "before pre-release."
        )
    return idents


@pytest.fixture(scope="module")
def allowlist() -> set[str]:
    return _load_allowlist()


@pytest.fixture(scope="module")
def identifiers_in_use() -> set[str]:
    return _extract_identifiers(_extract_js_fragments())


def test_snapshot_loader_uses_exact_match_not_substring(snapshot: set[str]) -> None:
    """Regression for the substring-leak bug closed 2026-05-02.

    Previously the snapshot was joined as raw text and `identifier in
    snapshot` did substring search, so a typo like `task.titl` passed
    because `"titl" in "title"` is True. This test asserts the snapshot
    is now an exact-membership set: `title` is in, common prefixes are
    not.
    """
    assert "title" in snapshot
    assert "titl" not in snapshot, (
        "snapshot is not an exact-match set — substring leak regressed. "
        "A typo like `task.titl` would silently pass the alignment lint."
    )
    assert "not" not in snapshot, (
        "`note` should be in the snapshot, but `not` should not — "
        "exact membership regression."
    )


def test_every_omnijs_identifier_appears_in_vendor_docs(
    snapshot: set[str], allowlist: set[str], identifiers_in_use: set[str]
) -> None:
    missing: list[str] = []
    for identifier in sorted(identifiers_in_use):
        if identifier in allowlist:
            continue
        if identifier in snapshot:
            continue
        missing.append(identifier)

    assert not missing, (
        f"{len(missing)} omniJS identifier(s) used in src/omniplan_mcp/ "
        f"do not appear in tests/vendor-docs-snapshot/ or the allowlist:\n"
        + "\n".join(f"  {m}" for m in missing)
        + "\n\nFor each: either (a) confirm it's documented at "
        "https://omni-automation.com/omniplan/ and refresh the snapshot, "
        "or (b) add it to tests/unit/vendor_docs_allowlist.txt with a "
        "one-line reason. Or — most likely — you've used an SDEF name "
        "instead of the documented omniJS name (see commit f5e48fb)."
    )
