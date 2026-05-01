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
   `(task|dep|assignment|r|actual|proj|doc|root|t|a|res|d)\.([A-Za-z_][A-Za-z_0-9]*)`
   and constants `(Duration|DependencyKind|ResourceType|Decimal|Document|TaskType)\.([A-Za-z_][A-Za-z_0-9]*)`.
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

JS_FRAGMENT_PATTERNS = [
    re.compile(r'run_omnijs\s*\(\s*"""(.*?)"""', re.DOTALL),
    re.compile(r'run_omnijs\s*\(\s*f?"""(.*?)"""', re.DOTALL),
    re.compile(r"run_omnijs\s*\(\s*\"(.*?)\"\)", re.DOTALL),
    re.compile(r'_RESOURCE_OBJ_HELPER\s*=\s*"""(.*?)"""', re.DOTALL),
    re.compile(r'_TASK_TO_OBJ_FRAGMENT\s*=\s*"""(.*?)"""', re.DOTALL),
    re.compile(r"script\s*=\s*f?\"\"\"(.*?)\"\"\"", re.DOTALL),
    re.compile(r"wrapped\s*=\s*f?\"\"\"(.*?)\"\"\"", re.DOTALL),
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


def _snapshot_text() -> str:
    if not SNAPSHOT_DIR.exists():
        return ""
    parts = [p.read_text() for p in SNAPSHOT_DIR.rglob("*.md")]
    return "\n".join(parts)


@pytest.fixture(scope="module")
def snapshot() -> str:
    text = _snapshot_text()
    if not text:
        pytest.skip(
            "No vendor-docs snapshot under tests/vendor-docs-snapshot/. "
            "Run scripts/refresh-vendor-docs-snapshot.py (or capture manually) "
            "before pre-release."
        )
    return text


@pytest.fixture(scope="module")
def allowlist() -> set[str]:
    return _load_allowlist()


@pytest.fixture(scope="module")
def identifiers_in_use() -> set[str]:
    return _extract_identifiers(_extract_js_fragments())


def test_every_omnijs_identifier_appears_in_vendor_docs(
    snapshot: str, allowlist: set[str], identifiers_in_use: set[str]
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
