#!/usr/bin/env bash
# vm-test-env.sh — Idempotent test-environment bootstrap for the OmniPlan MCP VM.
#
# Goal: ensure every supported OmniPlan version listed in the README's
# "Supported OmniPlan versions" matrix is present at a stable path inside the
# Tart VM, downloading + installing missing versions where the source URL is
# known.
#
# Idempotent: safe to run repeatedly. Skips versions already installed.
# Verifies bundle CFBundleShortVersionString matches the manifest entry.
#
# Run inside the VM (via tart-vm ssh), or directly on a Mac with the same
# /Applications layout. Requires no Apple ID or Mac App Store interaction.
#
# Usage:
#   tart-vm ssh <vm-name> 'bash -s' < scripts/vm-test-env.sh
#   # or, if /Volumes/My Shared Files/code is mounted:
#   tart-vm ssh <vm-name> 'bash "/Volumes/My Shared Files/code/scripts/vm-test-env.sh"'
#
# Exit codes:
#   0 — every manifest entry present at the expected path
#   1 — installation failed (download error, hdiutil failure, etc.)
#   2 — usage / environment error (missing tools, not on macOS, etc.)

set -euo pipefail

# ---- Manifest -----------------------------------------------------
# Each entry: BUNDLE_PATH | EXPECTED_VERSION | SOURCE | URL_OR_HINT
#   BUNDLE_PATH       — where the .app should live (always under /Applications)
#   EXPECTED_VERSION  — what `defaults read .../Info CFBundleShortVersionString`
#                       should return; pattern (regex). Use ".*" to skip check.
#   SOURCE            — one of: dmg-url, manual
#                         dmg-url → script downloads + installs from URL
#                         manual  → script verifies presence only; URL is a hint
#   URL_OR_HINT       — DMG URL for dmg-url; pointer text for manual
#
# Add a new version: append a row, run the script.
# Remove a version: delete the row; script won't touch existing installs.
MANIFEST=(
  "/Applications/OmniPlan.app|4.10.3 test|dmg-url|https://omnistaging.omnigroup.com/omniplan/releases/OmniPlan-4.x-v232.5.9-e7066d2251-Test.dmg"
  "/Applications/OmniPlan-4.10.2-baseline.app|4.10.2|manual|Pre-existing from L3 bake; if missing, install OmniPlan 4.10.2 from https://omnigroup.com/download/latest/omniplan/ then rename. The L3 image already has this app side-by-side."
)

# ---- Logging ------------------------------------------------------
RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; RESET=$'\033[0m'
log()   { printf '%s[vm-test-env]%s %s\n' "$BLUE" "$RESET" "$*"; }
ok()    { printf '%s[vm-test-env]%s %s\n' "$GREEN" "$RESET" "$*"; }
warn()  { printf '%s[vm-test-env]%s %s\n' "$YELLOW" "$RESET" "$*" >&2; }
err()   { printf '%s[vm-test-env]%s %s\n' "$RED" "$RESET" "$*" >&2; }

# ---- Pre-flight ---------------------------------------------------
if [[ "$(uname)" != "Darwin" ]]; then
  err "this script must run on macOS (the test VM)"
  exit 2
fi
for cmd in curl hdiutil defaults; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "missing required command: $cmd"
    exit 2
  fi
done

# ---- Per-entry handlers -------------------------------------------
verify_version() {
  local app_path="$1" expected_pattern="$2"
  if [[ "$expected_pattern" == ".*" ]]; then
    return 0
  fi
  local actual
  actual=$(defaults read "${app_path}/Contents/Info" CFBundleShortVersionString 2>/dev/null || echo "")
  if [[ "$actual" =~ $expected_pattern ]]; then
    ok "  version ok: ${app_path##*/} → ${actual}"
    return 0
  fi
  warn "  version mismatch: ${app_path##*/} reports '${actual}', expected pattern '${expected_pattern}'"
  return 1
}

install_dmg() {
  local app_path="$1" url="$2"
  local dmg
  dmg=$(mktemp -t omniplan-XXXXXX.dmg)
  trap 'rm -f "$dmg"' RETURN

  log "  downloading ${url##*/}..."
  if ! curl -fsSL -o "$dmg" "$url"; then
    err "  download failed: $url"
    return 1
  fi
  log "  size: $(du -h "$dmg" | awk '{print $1}')"

  log "  mounting DMG (auto-accepting EULA)..."
  local mount_output mount_point
  mount_output=$(yes | PAGER=cat hdiutil attach -nobrowse -readonly -noverify "$dmg" 2>&1) || true
  mount_point=$(echo "$mount_output" | awk '/Volumes/ {print $NF; exit}')
  if [[ -z "$mount_point" || ! -d "$mount_point" ]]; then
    err "  could not determine mount point from hdiutil output"
    echo "$mount_output" >&2
    return 1
  fi
  log "  mounted at $mount_point"

  local source_app
  source_app=$(find "$mount_point" -maxdepth 2 -name '*.app' -type d | head -1)
  if [[ -z "$source_app" ]]; then
    err "  no .app bundle found inside DMG at $mount_point"
    hdiutil detach "$mount_point" >/dev/null 2>&1 || true
    return 1
  fi
  log "  installing $source_app → $app_path"

  if [[ -d "$app_path" ]]; then
    sudo rm -rf "$app_path"
  fi
  if ! sudo cp -R "$source_app" "$app_path"; then
    err "  cp failed"
    hdiutil detach "$mount_point" >/dev/null 2>&1 || true
    return 1
  fi

  hdiutil detach "$mount_point" >/dev/null 2>&1 || true
  ok "  installed: $app_path"
}

# ---- Main loop ----------------------------------------------------
EXIT_CODE=0
for entry in "${MANIFEST[@]}"; do
  IFS='|' read -r APP_PATH VERSION SOURCE URL_OR_HINT <<<"$entry"
  log "checking $APP_PATH (expected $VERSION, source: $SOURCE)"

  if [[ -d "$APP_PATH" ]]; then
    if verify_version "$APP_PATH" "$VERSION"; then
      ok "  present"
      continue
    fi
    warn "  present but version mismatch — leaving as-is (manual review needed)"
    EXIT_CODE=1
    continue
  fi

  log "  not installed"
  case "$SOURCE" in
    dmg-url)
      if ! install_dmg "$APP_PATH" "$URL_OR_HINT"; then
        EXIT_CODE=1
      fi
      ;;
    manual)
      err "  missing and source is 'manual' — agent cannot auto-install"
      err "  hint: $URL_OR_HINT"
      EXIT_CODE=1
      ;;
    *)
      err "  unknown source kind: $SOURCE"
      EXIT_CODE=1
      ;;
  esac
done

if [[ $EXIT_CODE -eq 0 ]]; then
  ok "all manifest entries satisfied"
else
  err "one or more entries need manual attention; rerun after fixing"
fi
exit $EXIT_CODE
