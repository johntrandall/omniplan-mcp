"""Pytest configuration shared by every test layer.

Defines the `requires_omniplan` marker and an autouse skip hook: tests marked
this way only run if the OmniPlan 4 process is alive and its sandbox container
exists on disk. Unit tests never set the marker, so `pytest -m "not requires_omniplan"`
runs the full unit-only matrix without OmniPlan involvement.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

OMNIPLAN_CONTAINER = Path.home() / "Library" / "Containers" / "com.omnigroup.OmniPlan4"


def _omniplan_running() -> bool:
    pgrep = shutil.which("pgrep")
    if not pgrep:
        return False
    result = subprocess.run(
        [pgrep, "-x", "OmniPlan"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _omniplan_available() -> tuple[bool, str]:
    if not OMNIPLAN_CONTAINER.exists():
        return False, f"OmniPlan 4 sandbox not found at {OMNIPLAN_CONTAINER}"
    if not _omniplan_running():
        return False, "OmniPlan 4 is not running (start the app and open a document)"
    return True, ""


@pytest.fixture(scope="session")
def omniplan_available() -> bool:
    ok, _ = _omniplan_available()
    return ok


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    ok, reason = _omniplan_available()
    if ok:
        return
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "requires_omniplan" in item.keywords:
            item.add_marker(skip)
