# omniplan-dev VM Provisioning

How to build and maintain the persistent Tart VM that runs the pre-release
test suite. Referenced by [`testing-policy.md`](testing-policy.md). Read that
first for the why.

> **Status (2026-05-01):** L3 image (`macos-15.7-l3-omniplan:v1-2026-05-01`)
> exists in the OCI registry. OmniPlan 4.10.2 build 232.5.0 is installed.
> Open items below.

## What's already built

| Item | State | Where |
|---|---|---|
| L0 vanilla macOS 15.6 | Done | `local: macos-15.6-l0-vanilla` |
| L2 dev base (15.7) | Done | OCI: `umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l2-dev:v1-20260501` |
| L3 OmniPlan image | Done | OCI: `umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:v1-2026-05-01` |
| `omniplan-dev` running VM | Up | local clone of the L3 image |
| OmniPlan 4.10.2 build 232.5.0 | Installed | `/Applications/OmniPlan.app` in the VM |

## Open items

These must be resolved before the pre-release runner produces reliable
results. Each is a one-paragraph blocker per the verifier review.

### 1. License activation in the VM

OmniPlan in the VM is currently in trial mode. Trial mode runs but periodically
pops a "Buy now" or "Continue trial" sheet that blocks `evaluateJavascript`
calls (matches the `AppleEvent timed out (-1712)` symptom we've seen).

**Path forward (gated on OmniGroup reply):** see
`drafts/omnigroup-vm-license-email.md` for the licensing inquiry. Until they
respond and we either acquire a usable license or confirm trial mode behaves
predictably under automation, the runner cannot rely on the VM's OmniPlan.

**Workaround for now:** kill OmniPlan and relaunch before each test class.
This won't always work — the trial dialog may fire mid-test. Document the
flake in test failure messages and retry once.

### 2. TCC Automation grant timing (verifier #2 finding)

Per ADR-048, `kTCCServiceAppleEvents` rows can be written to `TCC.db` via
`sqlite3` only while SIP is off. SIP is off only during the L1→L2 build pass;
L2 re-enables SIP, and the L3 build inherits that.

**Status:** The TCC Automation grant IS in place in both the persistent
`omniplan-dev` VM and a fresh clone of the L3 image (smoke-tested
2026-05-01 via `tart-vm start tcc-smoke-test --from macos-15.7-l3-omniplan`,
then destroyed). AppleEvents reach OmniPlan in both VMs.

The grant was therefore baked in at L3 build time (manual approval before
the layer was captured), and per ADR-048 "What survives cloning", it
persists across APFS clones. **Item 2 resolved.**

Caveat: in the smoke test, the AppleEvent still timed out (-1712) inside
OmniPlan even though it reached the app. That hang is item 1 (license),
not TCC. The grant works; the app is stuck.

### 3. License-across-clones smoke test

**Status:** Could NOT be completed without a license. The fresh L3 clone
exhibited the same OmniPlan hang as the persistent VM (auto-launched at
boot — see "Auto-launch at boot" below — in headless trial-mode state
that doesn't respond to AppleEvents). Without a license to install, the
question of whether activation survives APFS cloning is moot.

**Gated on item 1** (OmniGroup license reply). Once we have a license:
1. Activate it in the persistent `omniplan-dev` VM.
2. Stop the VM, push the layer with the activated license:
   `tart push omniplan-dev umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:v2-licensed`.
3. `tart clone …:v2-licensed license-smoke-test`.
4. Start the clone, attempt `evaluateJavascript`, observe whether OmniPlan
   prompts for activation.

### 4. Auto-launch at boot (discovered during smoke test)

In the fresh L3 clone, OmniPlan was running (PID 788) immediately after
boot, with no window visible and no documents open — and unresponsive
to AppleEvents. The L3 image as built has either:
- A LaunchAgent that starts OmniPlan at login, OR
- macOS's "Reopen windows when logging back in" pref enabled.

Headless launch + trial-mode dialog (which probably IS rendered, just not
visible because the window has zero size or is positioned off-screen) is
what produces the documented hang.

**Fix when we rebuild the L3 image** (see "Building the L3 image" step 8):
```bash
tart-vm exec build-l3-omniplan-… zsh -l -c \
  'defaults write com.omnigroup.OmniPlan4 NSQuitAlwaysKeepsWindows -bool false'
# Also disable the system-wide auto-restore preference to be safe:
tart-vm exec build-l3-omniplan-… zsh -l -c \
  'defaults write -g NSQuitAlwaysKeepsWindows -bool false'
```
And remove any LaunchAgent that auto-launches OmniPlan if one exists at
`~/Library/LaunchAgents/com.omnigroup.*.plist`.

## Building the L3 image (when next needed)

You won't need to do this often — the L3 image is stable across OmniPlan
point releases. Re-build when:
- OmniPlan ships a major version bump.
- The L2 dev base is rebuilt.
- A test discovers that some VM-side dependency is missing.

### Procedure

1. **Verify L2 is current.** `tart pull umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l2-dev:latest`.

2. **Clone L2 into a build VM.** `tart clone macos-15.7-l2-dev build-l3-omniplan-$(date +%Y%m%d)`.

3. **Start the build VM.** `tart-vm start build-l3-omniplan-…`.

4. **Install OmniPlan.** Via Homebrew Cask (recommended — keeps the install reproducible):
   ```bash
   tart-vm exec build-l3-omniplan-… zsh -l -c "brew install --cask omniplan"
   ```
   Or the DMG path if you need a specific build:
   ```bash
   curl -L -o /tmp/op.dmg https://downloads.omnigroup.com/software/MacOSX/10.16/OmniPlan-4.10.2.dmg
   tart-vm-copy …
   ```

5. **Activate the license** (interactive — requires John). SSH into the VM,
   `open -a OmniPlan`, paste the license from 1Password (`OmniPlan - License`
   in JRVIS Personal). The license file lands at
   `~/Library/Application Support/Omni Group/Software Licenses/`.

   (If we get a VM-friendly license per the OmniGroup email, this step
   simplifies — paste a different license; otherwise it's whatever standalone
   license OmniGroup says we can use.)

6. **Verify the Automation TCC grant is in place.** First time only,
   approve the prompt:
   ```bash
   tart-vm exec build-l3-omniplan-… zsh -l -c \
     'osascript -e "tell application \"OmniPlan\" to activate"'
   # Approve the TCC dialog when it appears (System Settings → Privacy
   # & Security → Automation if the popup didn't appear).
   ```
   The grant is now baked into TCC.db and survives cloning per ADR-048.

7. **Bake the baseline build SHA.**
   ```bash
   tart-vm exec build-l3-omniplan-… zsh -l -c \
     'defaults read /Applications/OmniPlan.app/Contents/Info CFBundleVersion \
        > ~/.omniplan-mcp-baseline-build'
   ```

8. **Set OmniPlan to NOT auto-restore documents on launch.** This makes the
   per-test ritual deterministic:
   ```bash
   tart-vm exec build-l3-omniplan-… zsh -l -c \
     'defaults write com.omnigroup.OmniPlan4 NSQuitAlwaysKeepsWindows -bool false'
   ```

9. **Stop the VM, push the layer.**
   ```bash
   tart-vm stop build-l3-omniplan-…
   TAG="v$(date +%Y-%m-%d)"
   tart push build-l3-omniplan-… \
     "umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:${TAG}"
   tart push build-l3-omniplan-… \
     "umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:latest"
   ```

10. **Re-create `omniplan-dev` from the new image.**
    ```bash
    tart delete omniplan-dev
    tart clone "umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:${TAG}" omniplan-dev
    tart-vm start omniplan-dev --dir code:$HOME/dev/omniplan-mcp
    ```

11. **Verify with the smoke test:**
    ```bash
    bash scripts/pre-release-test.sh -k workflow
    ```

## Persistent vs ephemeral mode

Per the testing policy, the runner uses the **persistent** `omniplan-dev` VM,
NOT ephemeral clones. Two reasons:

- License activation across APFS clones is unverified (item 3).
- VirtioFS mount is set at VM start time; for a pre-release gate where
  source is frozen at commit anyway, the persistent model is sufficient.

If items 1 and 3 resolve cleanly (license survives clones), we may revisit
the ephemeral pattern for parallel test runs. Until then: one persistent VM.

## Known issues

- **OmniPlan stuck UI.** OmniPlan occasionally enters a state where AppleEvents
  reach the app but never return (`AppleEvent timed out -1712`). Recovery:
  `pkill -9 -x OmniPlan; open -a OmniPlan`. Probable cause: trial-mode dialog
  or unfinished autosave. Resolution: gated on item 1.
- **Trial-mode dialog interrupts automation.** Same root cause; gated on
  item 1.

## References

- `~/.claude/skills/tart-vm-management/SKILL.md` — VM lifecycle + naming
- `~/admin-technical/ADRs/ADR-048-VM-Image-Layer-Architecture.md` — TCC + SIP constraints
- `dev-docs/testing-policy.md` — why the VM exists at all
- `dev-docs/drafts/omnigroup-vm-license-email.md` — pending licensing inquiry
