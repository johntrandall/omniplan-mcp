# Test Environment — `mcp-omniplan-jtr`

The test suite for `mcp-omniplan-jtr` runs against a real OmniPlan
process inside a Tart macOS VM. This doc describes what the VM needs
to contain, how to populate it, and how the suite enforces it.

## Why a VM (and not the host)

Running tests against the host's OmniPlan would:

1. Mutate whichever document the human happens to have open
2. Compete with the human's foreground use of OmniPlan
3. Couple test output to the host's specific document state

The Tart VM is a controlled environment: a known OmniPlan version, a
predictable scratch document, and license state that doesn't change
between test runs. License binding is preserved across `tart clone`
under default settings — see `dev-docs/beta-v232.5.9-probe-results.md`
and the `omni-licensing` skill — so cloning the VM for parallel CI
doesn't burn license seats.

## Multi-version layout

The same VM holds **multiple OmniPlan versions side-by-side** at
distinct `/Applications/OmniPlan-<X.Y.Z>.app` paths. This is
seat-efficient (one license registration per app, regardless of how
many versions are installed) and lets the suite run against any
version without re-bake.

Canonical layout:

| Path | Version | Purpose |
|---|---|---|
| `/Applications/OmniPlan.app` | Current (4.10.3 test as of 2026-05-07) | Default — what `Application('OmniPlan')` resolves to via LaunchServices |
| `/Applications/OmniPlan-4.10.2-baseline.app` | 4.10.2 | Backward-compat regression target |
| `/Applications/OmniPlan-<other>.app` | (future) | Add as new versions arrive — see "Adding a version" |

The README's "Supported OmniPlan versions" matrix is the public
record; this layout is the implementation.

**Single license seat regardless of count.** Per the empirical
license-binding finding: the receipt binds to the system identity
(IOPlatformUUID + serial), not to a specific app bundle. Two OmniPlan
binaries in one VM share one receipt; one seat consumed.

## Bootstrap script

`scripts/vm-test-env.sh` is idempotent — running it makes the VM
match the manifest at the top of the script, downloading + installing
any missing versions whose source URL is known.

```bash
# Inside the VM (via tart-vm ssh):
tart-vm ssh <vm-name> 'bash -s' < scripts/vm-test-env.sh

# Or, if the worktree is mounted at /Volumes/My Shared Files/code:
tart-vm ssh <vm-name> 'bash "/Volumes/My Shared Files/code/scripts/vm-test-env.sh"'
```

Manifest entry kinds:

- **`dmg-url`** — script downloads the DMG, mounts it (auto-accepts
  the EULA), copies the .app to the target path, ejects. Idempotent:
  skipped if the target path already exists with the expected version.
- **`manual`** — script verifies presence only; downloading isn't
  scriptable for that version (e.g., older builds Omni doesn't
  archive at a stable URL). The hint string in the manifest entry
  tells the operator where to source it.

The `dmg-url` path is fully unattended once the VM has network access.
The `manual` path requires a human (or a more elaborate scrape) to
populate the missing app.

## Adding a new OmniPlan version to the test matrix

Three places to update in the same commit:

1. **README "Supported OmniPlan versions" matrix** — new row with
   version, build, "verified" status, and date.
2. **`scripts/vm-test-env.sh` MANIFEST array** — new entry with the
   target path, expected version pattern, source kind, and URL.
3. **`tests/test_environment.py` EXPECTED_BUNDLES list** — same
   information, in pytest-parametrize-ready form. Pre-flight will
   check this entry on every run.

The release checklist (`dev-docs/release-checklist.md`) reminds you
to do all three when shipping a release that bumps the support matrix.

## Pre-flight in the test suite

`tests/test_environment.py` runs first (alphabetical collection
order: `test_environment` precedes `integration/`, `unit/`, etc.).
For each entry in `EXPECTED_BUNDLES`:

- If `required=True` and the bundle is missing → suite **fails** with
  a pointer at `scripts/vm-test-env.sh`.
- If `required=False` and the bundle is missing → suite **skips** the
  back-compat check with a note.
- If the bundle exists but reports a version outside the matrix →
  suite **fails** with a message saying to update the README and
  test_environment in the same commit.

This means agents picking up the project after a VM bake can run
`pytest tests/` and immediately see whether the environment matches
the public-facing matrix without having to read source.

## Why `defaults read` and not `mdls`

The pre-flight uses `plistlib` first, then falls back to `defaults
read` if the plist format is unusual. `mdls` (Spotlight metadata)
could also work but requires Spotlight to have indexed
`/Applications`, which doesn't always happen in fresh Tart clones.
`defaults read` works on any bundle regardless of indexing state.

## Troubleshooting

**"OmniPlan 4 is not running"** — the suite's parent conftest
(`tests/conftest.py`) skips all `requires_omniplan` tests if the
process isn't alive. Start OmniPlan in the VM and open a document.
The bootstrap script doesn't auto-launch — that's a deliberate
boundary (auto-launch could fight a human user; explicit launch is
the contract).

**Version mismatch** — if `test_omniplan_version_matrix` fails because
the actual version differs from the expected substring, either:
1. The VM was upgraded but the matrix wasn't (update README + test).
2. The VM was downgraded somehow (less common; check
   `~/.omniplan-mcp-baseline-build` if the L3 image bake recorded one).

**Receipt expired** — OmniPlan receipts have a ~7-day TTL. On day 8,
the next launch hits `register.omnigroup.com` to renew. If the VM
has no network, the renewal fails and OmniPlan falls back to trial
mode (which blocks the omniJS bridge). Restore network access; the
renewal happens automatically on next launch.
