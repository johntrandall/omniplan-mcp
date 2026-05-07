"""Pre-flight environment check — runs first thanks to alphabetical
collection order ('test_environment' sorts before 'integration', 'unit',
'workflow', 'e2e').

Goal: when the test suite runs, the FIRST output the operator sees is a
clear summary of which OmniPlan versions are present in the test
environment, plus a hard fail with a pointer to `scripts/vm-test-env.sh`
if the canonical /Applications/OmniPlan.app is missing.

This file ships expected-version assertions for every entry in the
README's "Supported OmniPlan versions" matrix. When the matrix changes
(new version added, or one retired), update both the README and this
file in the same commit.
"""
from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

import pytest


# Mirror of the README "Supported OmniPlan versions" matrix.
# Each entry: (bundle_path, expected_short_version_substring, required)
#   required=True  → suite hard-fails if the bundle is missing
#   required=False → soft-warning only (e.g., side-by-side baselines for
#                    backward-compat regression testing — useful but not
#                    required for the suite to pass on the primary version)
EXPECTED_BUNDLES: list[tuple[Path, str, bool]] = [
    (Path("/Applications/OmniPlan.app"), "4.10.3", True),
    (Path("/Applications/OmniPlan-4.10.2-baseline.app"), "4.10.2", False),
]


def _read_short_version(bundle: Path) -> str | None:
    """Return CFBundleShortVersionString from the bundle's Info.plist, or
    None if the bundle is missing or unreadable."""
    info_plist = bundle / "Contents" / "Info.plist"
    if not info_plist.exists():
        return None
    try:
        with info_plist.open("rb") as f:
            plist = plistlib.load(f)
    except Exception:
        # Fall back to `defaults read` for unusual plist formats
        result = subprocess.run(
            ["defaults", "read", str(bundle / "Contents" / "Info"),
             "CFBundleShortVersionString"],
            capture_output=True, text=True, check=False,
        )
        return result.stdout.strip() or None
    return str(plist.get("CFBundleShortVersionString") or "") or None


@pytest.mark.parametrize(
    "bundle,expected,required",
    EXPECTED_BUNDLES,
    ids=lambda x: str(x) if isinstance(x, Path) else (str(x)[:20] if x else "_"),
)
def test_omniplan_version_matrix(bundle: Path, expected: str, required: bool) -> None:
    """For each entry in the README's supported-versions matrix, assert
    that the bundle exists at the expected path and reports a version
    that contains the expected substring.

    If a `required=True` bundle is missing, the test FAILS with a
    pointer at scripts/vm-test-env.sh. If a `required=False` bundle is
    missing, the test SKIPS with a note (back-compat testing is
    optional)."""
    actual = _read_short_version(bundle)
    if actual is None:
        msg = (
            f"missing bundle: {bundle}. Expected OmniPlan version "
            f"matching '{expected}'. Run scripts/vm-test-env.sh to "
            f"install missing versions, or update the test environment "
            f"manually. See dev-docs/test-environment.md."
        )
        if required:
            pytest.fail(msg)
        pytest.skip(msg)

    assert expected in actual, (
        f"{bundle.name} reports version {actual!r}; "
        f"matrix expected version containing {expected!r}. "
        f"This usually means the test VM has been bumped to a build "
        f"the supported-versions matrix doesn't yet cover. Update the "
        f"README matrix AND this file's EXPECTED_BUNDLES list in the "
        f"same commit."
    )
