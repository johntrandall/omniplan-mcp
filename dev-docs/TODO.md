# omniplan-mcp — Open Loops

Living index of every outstanding item across the project. Updated 2026-05-03.
Move to `ROADMAP.md` when an item grows beyond a one-paragraph TODO.

> Single source of truth for "what's left." If you're picking this project
> back up after a break, read this file first.

---

## Pending — only the human can do these

### 1. License `omniplan-dev` VM (in flight)

OmniPlan 4 Pro license activated in the `omniplan-dev` VM via Screen Sharing
on 2026-05-03. AppleEvents now respond cleanly (no more trial-dialog
`-1712` hang). License file location TBD — probed in this turn; results in
session memory.

**Next:** rebuild L3 image with the activated license baked in (see #7).

### 2. Stale Gmail drafts (cleanup)

Four drafts to delete manually (no MCP tool exposes Gmail draft deletion):

- `r-5062780006882575297` (v6 — hard-wrapped paragraphs)
- `r5845501165816829184` (v7 — wrap fixed but pre-wording-tweak)
- `r-3969378564178274196` (v8 — mangled signature)
- `19de8a875e255773` (intermediate v8)

Canonical draft `19de8ac646a26e16` was sent 2026-05-02. Search Gmail
`to:omniplan@omnigroup.com is:draft` to find them.

### 3. Re-scope PyPI token

Currently `PyPI - mcp-omniplan-jtr` token in `JRVIS Execution` 1Password
vault is scoped to "Entire account, all projects" — required for first
publish. Re-scope to project-only at <https://pypi.org/manage/account/token/>
when convenient. Update the 1Password notes when done.

### 4. Run `pre-commit install` (one-time)

In `~/dev/omniplan-mcp/`:

```bash
pre-commit install
```

Activates the unit-test hook from `.pre-commit-config.yaml`. Without this,
the testing-policy claim "unit tests run pre-commit" is unenforced.

---

## Pending — waiting on external responses

### 5. OmniGroup reply — omniJS gaps email

**Sent:** 2026-05-01 (Gmail message ID `19de54f80526a865` to `omniplan@omnigroup.com`).
**Subject:** "OmniPlan 4.10.2 omniJS — two small documented gaps (task reparent, Decimal accessor)".

**Two questions asked:**

1. Task reparent — no documented omniJS method. Three failure paths verified.
2. Decimal number-extraction — no documented accessor; current workaround
   parses `String(Decimal.fromString("..."))` via regex.

**Auto-followup:** routine `trig_019hMu6Mpt1sAWwLhA64n5kQ` SHOULD fire
2026-05-22. ⚠️ Verify this routine actually exists — when queried on
2026-05-02 the API returned 404. May need to recreate.

**If no response by 2026-05-29 (4 weeks):** decide whether to file a GitHub
issue with reproductions, or re-prompt politely.

**Possible outcomes & next steps:**

- OmniGroup confirms `task.moveTo` is on roadmap → revive `feat/move-task`
  from the `xfail(strict=True)` sentinel at `tests/integration/test_move_task.py`.
- OmniGroup confirms a Decimal accessor → simplify the regex parser in
  `src/omniplan_mcp/resources.py` `decimalToFloat`.
- "Use SDEF AppleScript" → decide whether to build a parallel SDEF bridge
  in `src/omniplan_mcp/sdef.py`.

**Related precedent:** A prior email to `omniplan@omnigroup.com` (2026-02-11)
about the .oplx format spec went unanswered. Set expectations accordingly.

### 6. OmniGroup reply — VM-license email

**Sent:** 2026-05-02 (Gmail thread starting from draft `19de8ac646a26e16`).
**Subject:** "OmniPlan in agentic workflows — license for automated testing in VMs?"

**Asks:**

1. Is there a license tier that covers running OmniPlan inside a VM for
   automated testing (developer / open-source / automation)?
2. Does an OmniPlan license carry across an APFS clone?

**Auto-followup:** routine `trig_017ohvAoUstKoQEt81uuxDFy` fires 2026-05-23
13:00 UTC. Verified to exist. Searches Gmail for reply, drafts status
email to John (does not send). Manage at
<https://claude.ai/code/routines/trig_017ohvAoUstKoQEt81uuxDFy>.

---

## Blocked — gated on the above

### 7. L3 VM image rebuild — ✅ DONE 2026-05-03 (smoke test deferred)

Pushed to OCI: `umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:v2-licensed`
(SHA `e7d89a9b3198e7c4149b989f56a11b471404be5a4a27dccab53fe86222314705`).

Baked-in changes:
- OmniPlan 4 Pro license activated
- `com.omnigroup.OmniPlan4 NSQuitAlwaysKeepsWindows = false`
- Global `NSQuitAlwaysKeepsWindows = false`
- `~/.omniplan-mcp-baseline-build` records OmniPlan build `232.5.0`

Labels: `omniplan-build=232.5.0` and `license=pro`.

LaunchAgents inspected: only `com.cua.computer-server.plist` and
`org.cirruslabs.tart-guest-agent.plist` are present — neither auto-launches
OmniPlan. The earlier "auto-launch at boot" symptom was macOS state
restoration, fixed by `NSQuitAlwaysKeepsWindows = false`.

**Smoke test deferred:** a fresh clone of `:v2-licensed` failed to get
a DHCP lease on the Tart bridge (same issue intermittently hit earlier
in the session). Likely transient; retry with the wrapper's longer wait
window or stop other VMs first. The image push itself succeeded; the
content is in the registry.

### 7a. Smoke-test the new L3 image (next session)

Verify `:v2-licensed` clones boot cleanly, retain the license, and
respond to AppleEvents. Procedure:

```bash
tart-vm stop omniplan-dev   # free the bridge slot
tart-vm start l3-smoke --from "umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:v2-licensed"
tart-vm ssh l3-smoke 'osascript -l JavaScript -e "Application(\"OmniPlan\").documents().length"'
# Expect: a number, no -1712 timeout, no trial dialog
tart-vm destroy l3-smoke
tart-vm start omniplan-dev   # restore working state
```

If clones reliably get an IP and respond cleanly, the L3 image is
verified end-to-end and the pre-release runner (#8) becomes runnable.

### 8. Pre-release runner end-to-end

`scripts/pre-release-test.sh` exists but has never been run end-to-end
against a clean omniplan-dev. Blocked on #7. Will exercise:
contract / workflow / e2e tests inside the VM, with VirtioFS-mounted source.

---

## Outreach (handed to the daily outreach-sweep agent)

These items live in `~/dev/_outreach/omniplan-mcp/OUTREACH.md` and get
picked up by the daily `/outreach-sweep` agent. Listed here for index
completeness only — don't duplicate effort.

### 9. Demo asset (screen recording, not asciinema)

A 30-second recording of an agent driving OmniPlan end-to-end (create
tasks, link dependencies, assign resources, save) — required for Stage 3
announcements. Tool choice: macOS screen recording (Cmd+Shift+5) +
optional `gifski` for a small README-embeddable GIF. Terminal-only
asciinema would miss the visual Gantt redraw.

### 10. Stage 3 announcements

Reddit (r/ClaudeAI, r/OmniFocus equivalent), Hacker News (Show HN), the
Anthropic MCP registry, and a community submission to Tim Wood at
omni-automation.com. All gated on #9. Per-channel framings TBD by the
outreach agent.

### 11. Full per-channel outreach plan

Five-bullet plan flagged at the bottom of OUTREACH.md: per-channel
framings, demo asset, success criteria, ICE/RICE scoring, retro slot.
Outreach agent picks this up.

### 12. OUTREACH.md gate #9 is stale

Currently reads "announce as a fork or wait for upstream merge." Fork
posture was dropped at v0.4.0; gate is moot. Resolve by deleting or
rewriting the gate entry.

---

## Strategic decisions (your call)

### 13. Tier 2 features

Per `dev-docs/ROADMAP.md`:

- Resource leveling (`level_document()`, `unlevel_document()`)
- Baselines (`create_baseline`, `list_baselines`, `compare_to_baseline`)
- Custom data fields (`set_custom_data`, `get_custom_data`)
- Splits (`split_task`, `unsplit_task`)
- Slack queries (read-only, extends `get_task` shape)
- Export (`export_document(format, path)`)

Not blocked, not started. Each could be a separate `@project` session.

### 14. Privacy: git history rewrite

Older commits in `johntrandall/omniplan-mcp` retain references to
`admin-technical/`, `~/dev/autocoder_v3/`, and `JRVIS` vault names.
Working tree is redacted (chore commit `7eb02b0`); history is not.
A `git filter-repo` rewrite + force-push would scrub it. Destructive —
existing clones detach.

### 15. Stale README at `~/admin-technical/setup/macos/omniplan-local/`

May still point at upstream `xiahan4956/omniplan-mcp`. Should now point
at `mcp-omniplan-jtr` from PyPI. Five-minute fix; not blocked.

### 16. Behavioral matrix (referenced in OUTREACH.md)

OUTREACH.md says "Behavioral matrix: not yet written. Required pre-publication."
Definition of "behavioral matrix" in this context is unclear. Could be:

- A markdown table of every tool × every documented OmniPlan behavior
- A test-coverage matrix mapping tools to test files
- Something else specific to John's outreach playbook

Resolve before Stage 3 announcements if it's a real prerequisite.

---

## Done in this session — index for posterity

Closed in this session, listed here for "where did that resolution land?"
lookups:

- ✅ Drop fork posture, rename to `mcp-omniplan-jtr` (v0.4.0)
- ✅ Publish to PyPI (v0.4.0 / v0.4.1 / v0.4.2 / v0.4.3)
- ✅ Homebrew tap formula (`johntrandall/tap/mcp-omniplan-jtr`, audit-clean)
- ✅ LICENSE added (MIT, dual copyright with xiahan4956 for jxa.py)
- ✅ README rewritten consumer-facing; dev-docs/README-DEV.md absorbs developer material
- ✅ Vendor-docs alignment lint with regression sentinel; substring-leak fix
- ✅ Timezone date-shift bugs (documents.py @ v0.4.1, tasks.py @ v0.4.2)
- ✅ `query_tasks` operator-precedence + TaskType normalization bugs (v0.4.3)
- ✅ Test coverage for `list_documents`, `query_tasks`, `get_task`,
  `delete_task`, plus `update_task` field round-trips (title/note/completed/3-point)
- ✅ Pre-commit hook config (`pre-commit install` still required by user once — see #4)
- ✅ Courtesy comment to `xiahan4956/omniplan-mcp` PRs #2–#11
- ✅ Privacy redaction of working tree (admin-technical / autocoder_v3 / JRVIS)
- ✅ Cross-link to `oplx-tools` and `oplx-format` in README
- ✅ Email v8 sent to OmniGroup re: VM testing license
- ✅ OmniPlan 4 Pro license activated in `omniplan-dev` VM (2026-05-03)
- ✅ Test count: 69 passed, 0 skipped, 1 xfailed (sentinel for `task.moveTo` gap)
