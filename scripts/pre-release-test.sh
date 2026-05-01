#!/usr/bin/env bash
# Pre-release test runner — runs contract / workflow / e2e-live-xml tests
# inside the persistent omniplan-dev Tart VM. See dev-docs/testing-policy.md.
#
# Usage: scripts/pre-release-test.sh [-k pattern]
#
# Exits non-zero on any test failure. Collects junit.xml and any OmniPlan
# crash logs from the VM into ./pre-release-artifacts/.

set -euo pipefail

VM_NAME="omniplan-dev"
ARTIFACTS_DIR="$(pwd)/pre-release-artifacts"
PYTEST_ARGS="${PYTEST_ARGS:-}"
PYTEST_FILTER="${1:-}"

err() { printf 'pre-release-test: ERROR: %s\n' "$*" >&2; }
note() { printf 'pre-release-test: %s\n' "$*"; }

if [[ -n "${PYTEST_FILTER:-}" && "$PYTEST_FILTER" == "-k" ]]; then
  shift
  PYTEST_ARGS="-k $1 $PYTEST_ARGS"
fi

# Prereqs.
if ! command -v tart-vm >/dev/null 2>&1; then
  err "tart-vm not on PATH. See ~/.claude/skills/tart-vm-management/."
  exit 2
fi

# VM up?
if ! tart-vm status 2>/dev/null | grep -q "^${VM_NAME} "; then
  note "VM '${VM_NAME}' not running. Starting…"
  tart-vm start "${VM_NAME}" --dir code:"$(pwd)" \
    || { err "Could not start ${VM_NAME}. Build the L3 image first; see dev-docs/vm-provisioning.md."; exit 2; }
fi

# Build SHA drift check.
BASELINE_BUILD=$(tart-vm exec "${VM_NAME}" cat /Users/admin/.omniplan-mcp-baseline-build 2>/dev/null || echo "")
RUNNING_BUILD=$(tart-vm exec "${VM_NAME}" zsh -l -c 'defaults read /Applications/OmniPlan.app/Contents/Info CFBundleVersion' 2>/dev/null || echo "")
if [[ -n "$BASELINE_BUILD" && "$BASELINE_BUILD" != "$RUNNING_BUILD" ]]; then
  note "WARNING: OmniPlan build drift. baseline=${BASELINE_BUILD} running=${RUNNING_BUILD}"
  note "         Re-validate by rebuilding the L3 image, then re-running this script."
fi

mkdir -p "${ARTIFACTS_DIR}"

# Run the suite.
note "Running pytest in ${VM_NAME}…"
SUITE_OK=0
tart-vm exec "${VM_NAME}" zsh -l -c "
  cd '/Volumes/My Shared Files/code'
  python3 -m venv .venv-vm 2>/dev/null || true
  source .venv-vm/bin/activate
  pip install -e '.[dev]' >/dev/null 2>&1
  pytest -m requires_omniplan ${PYTEST_ARGS} --junit-xml=/tmp/junit.xml tests/
" || SUITE_OK=$?

# Pull artifacts.
tart-vm exec "${VM_NAME}" cat /tmp/junit.xml > "${ARTIFACTS_DIR}/junit.xml" 2>/dev/null || true
tart-vm exec "${VM_NAME}" zsh -l -c \
  'ls ~/Library/Logs/DiagnosticReports/*OmniPlan* 2>/dev/null | xargs -I {} cat {}' \
  > "${ARTIFACTS_DIR}/omniplan-crashes.log" 2>/dev/null || true

if [[ "$SUITE_OK" -ne 0 ]]; then
  err "Test suite failed. Artifacts in ${ARTIFACTS_DIR}"
  exit "$SUITE_OK"
fi

note "All pre-release tests passed. Artifacts in ${ARTIFACTS_DIR}"
