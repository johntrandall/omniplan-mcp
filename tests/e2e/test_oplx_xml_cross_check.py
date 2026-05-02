"""e2e-live-xml: write via tool, save, parse Actual.xml, assert.

This is the safety net for the bug class that drove the May 1 corrections:
an omniJS setter that succeeds in the JS context but doesn't reach the
underlying OmniPlan model. The contract-level tests can't catch that
class — they read back via the same omniJS API surface and report a
self-consistent lie. The XML cross-check parses the saved bundle's
`Actual.xml` directly.

One canonical write path is exercised per major write tool. We don't
unzip-and-parse on every assertion — that would be expensive — but we
do it for at least one happy-path per category: tasks, dependencies,
resources/assignments.

Methodology:
1. Use the public tools to create state (task, dependency, assignment)
2. `save_document()`
3. Resolve `document.path()` via JXA SDEF
4. Open the bundle directory, parse `Actual.xml`
5. Assert the new task's `<task id="..."><title>` element exists
   AND its `<effort>` matches what we set
   AND the dependency exists as a `<prerequisite-task>`
   AND the assignment exists as `<assignment idref=...>`

OmniPlan saves `.oplx` as a directory bundle by default (UTI
com.omnigroup.omniplan2.planfile). If the user has saved it as the zipped
form (planfile-zip), we unzip first.
"""
from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from omniplan_mcp.dependencies import add_dependency
from omniplan_mcp.documents import save_document
from omniplan_mcp.jxa import run_jxa
from omniplan_mcp.resources import assign_resource, create_resource
from omniplan_mcp.tasks import create_task

pytestmark = pytest.mark.requires_omniplan

NS = "{http://www.omnigroup.com/namespace/OmniPlan/v2}"


async def _front_document_path() -> str | None:
    raw = await run_jxa("""
const docs = Application('OmniPlan').documents();
if (docs.length === 0) { 'null' }
else {
  let s = 'null';
  try { const p = docs[0].path(); if (p) s = String(p); } catch(_) {}
  if (s === 'null') {
    try { const f = docs[0].file(); if (f) s = String(f); } catch(_) {}
  }
  s
}
""")
    s = raw.strip()
    return None if s == "null" else s


def _read_actual_xml(oplx_path: Path, tmp_path: Path) -> ET.ElementTree:
    """Return the parsed Actual.xml from the .oplx bundle (dir or zip)."""
    if oplx_path.is_dir():
        actual = oplx_path / "Actual.xml"
        return ET.parse(actual)
    if oplx_path.is_file() and zipfile.is_zipfile(oplx_path):
        extract_dir = tmp_path / "unzipped"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(oplx_path) as zf:
            zf.extractall(extract_dir)
        actual = extract_dir / "Actual.xml"
        return ET.parse(actual)
    raise AssertionError(f"Path is neither a bundle dir nor a zip: {oplx_path}")


async def test_create_task_landing_in_actual_xml(
    test_root: str, tmp_path: Path
) -> None:
    raw = await create_task(
        title="__test__xml_t",
        parent_id=test_root,
        effort_seconds=14400,
    )
    task = json.loads(raw)

    path = await _front_document_path()
    if path is None:
        pytest.skip("Front document is unsaved; cannot cross-check XML.")

    await save_document()

    tree = _read_actual_xml(Path(path), tmp_path)
    titles = [
        e.text
        for e in tree.iter(f"{NS}title")
        if e.text and e.text.startswith("__test__xml_t")
    ]
    assert "__test__xml_t" in titles, (
        "Task created via create_task() did not appear in Actual.xml after save. "
        f"Titles in XML: {titles!r}. This is the omniJS-write-not-reaching-model "
        "bug class — investigate."
    )

    for task_el in tree.iter(f"{NS}task"):
        title_el = task_el.find(f"{NS}title")
        if title_el is None or title_el.text != "__test__xml_t":
            continue
        effort_el = task_el.find(f"{NS}effort")
        assert effort_el is not None and effort_el.text == "14400", (
            f"Effort did not round-trip to XML: got element={effort_el!r}"
        )
        return
    pytest.fail("Task element not found by title walk (unexpected).")


async def test_dependency_landing_in_actual_xml(
    test_root: str, tmp_path: Path
) -> None:
    a = json.loads(await create_task(title="__test__xml_dep_a", parent_id=test_root))
    b = json.loads(await create_task(title="__test__xml_dep_b", parent_id=test_root))
    await add_dependency(predecessor_id=a["id"], successor_id=b["id"], kind="FS")

    path = await _front_document_path()
    if path is None:
        pytest.skip("Front document is unsaved; cannot cross-check XML.")

    await save_document()

    tree = _read_actual_xml(Path(path), tmp_path)

    # XML stores task ids as 't<omniJS_uniqueID>'; the prerequisite-task's
    # idref must point at exactly task `a`, not just any task.
    expected_predecessor_idref = f"t{a['id']}"

    for task_el in tree.iter(f"{NS}task"):
        title_el = task_el.find(f"{NS}title")
        if title_el is not None and title_el.text == "__test__xml_dep_b":
            prereqs = task_el.findall(f"{NS}prerequisite-task")
            assert prereqs, (
                "Dependency wrote via add_dependency() did not appear as "
                "<prerequisite-task> on the successor in Actual.xml."
            )
            idrefs = [p.get("idref") for p in prereqs]
            assert expected_predecessor_idref in idrefs, (
                f"Dependency's <prerequisite-task> idref={idrefs!r} but "
                f"add_dependency() was called with predecessor_id={a['id']!r} "
                f"(expected idref={expected_predecessor_idref!r}). The "
                f"dependency was wired to the wrong predecessor."
            )
            kinds = [p.get("kind") for p in prereqs if p.get("idref") == expected_predecessor_idref]
            # FS (Finish-to-Start) is the OmniPlan default; XML omits the
            # `kind` attribute when it's FS. None or "FS" both indicate FS.
            assert kinds and all(k in (None, "FS") for k in kinds), (
                f"Dependency kind in XML is {kinds!r}, expected None (default FS) or 'FS'."
            )
            return
    pytest.fail("Successor task not found in XML.")


async def test_assignment_landing_in_actual_xml(
    test_root: str, tmp_path: Path
) -> None:
    t = json.loads(await create_task(title="__test__xml_asg_t", parent_id=test_root))
    r = json.loads(await create_resource(name="__test__xml_asg_r", type="staff"))
    await assign_resource(task_id=t["id"], resource_id=r["id"], units=0.75)

    path = await _front_document_path()
    if path is None:
        pytest.skip("Front document is unsaved; cannot cross-check XML.")

    await save_document()

    tree = _read_actual_xml(Path(path), tmp_path)

    for task_el in tree.iter(f"{NS}task"):
        title_el = task_el.find(f"{NS}title")
        if title_el is not None and title_el.text == "__test__xml_asg_t":
            assignments = task_el.findall(f"{NS}assignment")
            assert assignments, (
                "Assignment via assign_resource() did not appear as "
                "<assignment> on the task in Actual.xml."
            )
            return
    pytest.fail("Task with assignment not found in XML.")
