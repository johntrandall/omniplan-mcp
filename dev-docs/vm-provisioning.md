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

Current state (probed in the running `omniplan-dev` VM):
- `osascript -l JavaScript` Automation grant: GRANTED (verified by an
  AppleEvent reaching OmniPlan — it doesn't time out at the TCC layer; it
  times out inside OmniPlan's own modal-dialog blocking).

Since the grant is already in place, this item is partially resolved. **What
to verify:** does the grant persist if we destroy `omniplan-dev` and re-clone
from the L3 image, or did it get added through some manual click on this
specific clone? Per ADR-048 "What survives cloning", TCC grants do survive
APFS clones. Confirmation requires a one-time test:

```bash
tart clone macos-15.7-l3-omniplan:v1-2026-05-01 omniplan-dev-test
tart-vm start omniplan-dev-test
tart-vm exec omniplan-dev-test zsh -l -c \
  'osascript -l JavaScript -e "Application(\"OmniPlan\").documents().length"'
# Should not produce a TCC dialog. If it does, the grant didn't survive
# cloning, and the L3 build must be patched to add it (via L2 with SIP off
# OR via manual approval baked in once before the L3 layer is captured).
tart-vm destroy omniplan-dev-test
```

### 3. License-across-clones smoke test

Same shape as item 2 — destroy and re-clone, confirm OmniPlan launches
without a license dialog. Cannot be done in trial mode; gated on item 1.

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
