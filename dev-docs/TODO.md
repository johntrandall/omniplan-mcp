# omniplan-mcp — Open Loops

Living index of every outstanding item across the project. Updated 2026-05-03.
This is the **single source of truth for "what's left."** If you're picking
this project back up after a break, read this file first.

---

## Quick start for the next agent

You're inheriting `mcp-omniplan-jtr` — an MCP server that lets Claude
drive OmniPlan 4 on macOS via the omniJS bridge. Current state:

- **Public, MIT-licensed.** Repo: <https://github.com/johntrandall/omniplan-mcp>
- **Latest release:** v0.4.3 on PyPI as `mcp-omniplan-jtr` and on the
  Homebrew tap `johntrandall/tap`.
- **20 tools shipped** across tasks, dependencies, resources, project metadata.
- **Test count:** 69 passed, 0 skipped, 1 xfailed (sentinel watching for
  `task.moveTo` to land in the omniJS surface).
- **VM workflow ready:** `omniplan-dev` Tart VM cloneable from
  `umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:v2-licensed`
  (license activated, build SHA pinned). Pre-release runner exists at
  `scripts/pre-release-test.sh` but hasn't been exercised end-to-end.

**Pick up by item below.** Each item has: what's been done, what's the
next concrete action, what files/commits to look at, gotchas, and an
effort estimate. Items are numbered for stable cross-reference; ordering
within a section is by leverage / unblocking value.

**Before you start anything substantive:**
1. Read `dev-docs/README-DEV.md` for architecture, then `dev-docs/testing-policy.md` for the test setup.
2. Check `git log --oneline -20` for the most recent context.
3. Run `pytest tests/unit/` (under `~/dev/omniplan-mcp/.venv/bin/python`) to confirm the dev environment works.

---

## Pending — only the human can do these

### 1. License `omniplan-dev` VM — ✅ DONE 2026-05-03

**Status:** complete. License activated; baked into the L3 image as `:v2-licensed`.
Listed here for index completeness; future-you doesn't need to redo this.

### 2. Stale Gmail drafts (cleanup)

Four drafts to delete manually (no MCP tool exposes Gmail draft deletion):

- `r-5062780006882575297` (v6 — hard-wrapped paragraphs)
- `r5845501165816829184` (v7 — wrap fixed but pre-wording-tweak)
- `r-3969378564178274196` (v8 — mangled signature)
- `19de8a875e255773` (intermediate v8)

Canonical sent draft: `19de8ac646a26e16` (subject "OmniPlan in agentic
workflows…", sent 2026-05-02 to `omniplan@omnigroup.com`).

**Next action (human):** Search Gmail `to:omniplan@omnigroup.com is:draft`
and delete each. ~60 seconds.

**Effort:** trivial. **Blocks:** nothing. Cosmetic only.

### 3. Re-scope PyPI token

Currently the PyPI API token in 1Password vault `JRVIS Execution`,
item `PyPI - mcp-omniplan-jtr`, is scoped to "Entire account, all projects."
That was required for the first publish (project didn't exist yet).
Now that `mcp-omniplan-jtr` exists on PyPI, the token can be re-scoped
to that single project.

**Next action (human):**
1. Open <https://pypi.org/manage/account/token/>
2. Revoke the existing token
3. Create a new token scoped to "Project: mcp-omniplan-jtr"
4. Update the credential in 1Password (`op item edit "PyPI - mcp-omniplan-jtr" credential=<new-token>`)
5. Update the notes field to reflect the scope change

**Effort:** ~5 minutes. **Blocks:** nothing. Security hygiene only.

### 4. Run `pre-commit install` (one-time)

In `~/dev/omniplan-mcp/`:

```bash
pre-commit install
```

Activates the unit-test hook from `.pre-commit-config.yaml`. Without this,
the testing-policy claim "unit tests run pre-commit" is unenforced.

**Why an agent can't do this:** `pre-commit install` writes to `.git/hooks/`
which is local-machine-specific and shouldn't be in the repo. Each
contributor runs it once.

**Effort:** trivial. **Blocks:** nothing strict; without it the hook isn't
active so a typo could land in `main`. The CI / pre-release path catches
it eventually but later than ideal.

---

## Pending — waiting on external responses

### 5. OmniGroup reply — omniJS gaps email

**Sent:** 2026-05-01 (Gmail message ID `19de54f80526a865` to `omniplan@omnigroup.com`).
**Subject:** "OmniPlan 4.10.2 omniJS — two small documented gaps (task reparent, Decimal accessor)".

**Two questions asked:**

1. **Task reparent** — no documented omniJS method. Three failure paths verified:
   - Named methods (`moveTo`, `reparent`, `insertAfter`, etc.) all
     return `typeof === 'undefined'` on the Task prototype
   - `subtasks.push(...)` mutation is silently no-op (cross-call read shows unchanged)
   - `task.parent = newParent` assignment doesn't persist
2. **Decimal number-extraction** — no documented accessor on the
   `Decimal` class. Current workaround in `src/omniplan_mcp/resources.py`
   parses `String(Decimal.fromString("..."))` via regex
   `Decimal:\s*(-?[0-9.]+)` — works but is brittle.

**Auto-followup:** routine `trig_019hMu6Mpt1sAWwLhA64n5kQ` SHOULD fire
2026-05-22. ⚠️ **Verify this routine actually exists** — when queried
2026-05-02 the API returned 404. May need to recreate. Use
`RemoteTrigger action=list` to verify; if missing, recreate using
`trig_017ohvAoUstKoQEt81uuxDFy` as a template (search Gmail for
omniJS-gaps reply, draft status email to John, do not send).

**Possible outcomes & next steps:**

- **OmniGroup confirms `task.moveTo` is on roadmap** → revive
  `feat/move-task` from the `xfail(strict=True)` sentinel at
  `tests/integration/test_move_task.py`. The sentinel will go RED on its
  next pre-release run, alerting that the implementation can ship.
- **OmniGroup confirms a Decimal accessor or stable `toString` contract**
  → simplify the regex parser in `src/omniplan_mcp/resources.py` to use
  the documented path. Look for `decimalToFloat` in the omniJS string.
- **"Use SDEF AppleScript"** → decision point: build a parallel SDEF
  bridge in `src/omniplan_mcp/sdef.py`, or accept the gap and document.
- **No response after 4 weeks (by 2026-05-29)** → file a GitHub issue on
  this repo with the reproduction (so it has a permanent URL), or
  re-prompt politely after another month.

**Related precedent:** A prior email to `omniplan@omnigroup.com` (2026-02-11)
about the .oplx format spec went unanswered. Set expectations accordingly
— silence is more likely than a reply.

**Effort to act on a reply:** 30–60 min depending on which path lands.

### 6. OmniGroup reply — VM-license email

**Sent:** 2026-05-02. Gmail thread originating from draft `19de8ac646a26e16`.
**Subject:** "OmniPlan in agentic workflows — license for automated testing in VMs?"

**Asks:**

1. Is there a license tier that covers running OmniPlan inside a VM for
   automated testing (developer / open-source / automation)?
2. Does an OmniPlan license carry across an APFS clone?

**Auto-followup:** routine `trig_017ohvAoUstKoQEt81uuxDFy` fires 2026-05-23
13:00 UTC. Verified to exist. Searches Gmail for reply, drafts status
email to John (does not send). Manage at
<https://claude.ai/code/routines/trig_017ohvAoUstKoQEt81uuxDFy>.

**Effort to act on a reply:** 15 min if they say yes (apply license type).
Up to several hours if they want a more formal arrangement.

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
in the session). Likely transient host-side flakiness; retry with the
wrapper's longer wait window or restart the Tart launch daemon.

### 7a. Smoke-test the new L3 image (next session) — TOP PRIORITY

Verify `:v2-licensed` clones boot cleanly, retain the license, and
respond to AppleEvents. **This unblocks #8 (pre-release runner).**

**Procedure:**

```bash
# Free the bridge slot if anything else is running
tart-vm status
tart-vm stop omniplan-dev   # if running

# Recreate omniplan-dev from the new licensed image
tart-vm destroy omniplan-dev   # if exists locally
tart-vm start omniplan-dev --from "umbridge.tail486ac0.ts.net:5051/tart/macos-15.7-l3-omniplan:v2-licensed" --dir code:$HOME/dev/omniplan-mcp

# Verify license + AppleEvents work
tart-vm ssh omniplan-dev 'cat ~/.omniplan-mcp-baseline-build'   # expect: 232.5.0
tart-vm ssh omniplan-dev 'osascript -l JavaScript -e "Application(\"OmniPlan\").documents().length"'   # expect: a number, no -1712 timeout
```

**If networking is flaky:** the issue is Tart's DHCP / VM bridge timing,
not the image. Workaround: `sudo killall tart` then retry (clears bridge
state). Or restart the host Mac's Tart launch daemon.

**Once verified:** mark #7a complete; #8 is now unblocked.

**Effort:** 15 minutes once Tart networking cooperates.

### 8. Pre-release runner end-to-end

`scripts/pre-release-test.sh` exists but has never been run end-to-end
against a clean omniplan-dev. **Blocked on #7a smoke test.**

**What it does:** clones omniplan-dev → runs contract / workflow / e2e
tests with `pytest -m requires_omniplan` against the VirtioFS-mounted
source → captures junit.xml + crash logs → destroys the clone.

**First run will probably surface:**
- Tart wrapper quirks we haven't hit yet
- Timing assumptions in tests (some tests may be host-coupled and need
  longer waits in the VM)
- pytest plugin install issues inside the VM (the VM's Python venv may
  need re-creation since it was an old `.venv-vm`)

**Procedure:**

```bash
cd ~/dev/omniplan-mcp
bash scripts/pre-release-test.sh
# observe; fix what breaks; iterate
```

**Effort:** 1–3 hours for first green run. Expect 2–3 fix cycles.

---

## Outreach (handed to the daily outreach-sweep agent)

These items live in `~/dev/_outreach/omniplan-mcp/OUTREACH.md` and get
picked up by the daily `/outreach-sweep` agent. Listed here for index
completeness only — don't duplicate effort. **Don't act on these
directly unless explicitly asked.**

### 9. Demo asset (screen recording, not asciinema)

A 30-second recording of an agent driving OmniPlan end-to-end (create
tasks, link dependencies, assign resources, save) — required for Stage 3
announcements. Tool choice: macOS screen recording (Cmd+Shift+5) +
optional `gifski` (`brew install gifski`) for a small README-embeddable
GIF. Terminal-only asciinema would miss the visual Gantt redraw which
is the whole point.

**Suggested workflow:**
1. Open OmniPlan with a fresh blank document on host (not VM — easier
   to record both windows)
2. Start a fresh Claude Code session in iTerm
3. Position windows side-by-side
4. Cmd+Shift+5 → "Record selected portion" covering both windows
5. In Claude: "Create a task called 'Build', another called 'Test',
   link them so Test depends on Build, add a resource Alice and assign
   her at 50%, then save the document."
6. Stop recording. Trim with QuickTime. Convert to GIF with gifski.

**Output:** a ~2-3MB GIF or MP4 to embed in the README.

### 10. Stage 3 announcements

Reddit (r/ClaudeAI, r/OmniFocus equivalent), Hacker News (Show HN), the
Anthropic MCP registry, and a community submission to Tim Wood at
omni-automation.com. **All gated on #9.** Per-channel framings TBD by
the outreach agent — see `outreach-reddit`, `outreach-show-hn`,
`outreach-mcp-directory`, `outreach-awesome-list-pr` skills.

### 11. Full per-channel outreach plan

Five-bullet plan flagged at the bottom of OUTREACH.md: per-channel
framings, demo asset, success criteria, ICE/RICE scoring, retro slot.
**Outreach agent picks this up** via `/outreach-sweep` daily.

### 12. OUTREACH.md gate #9 is stale

OUTREACH.md gate row #9 currently reads "announce as a fork or wait for
upstream merge." Fork posture was dropped at v0.4.0; gate is moot. The
outreach agent should resolve this by deleting or rewriting the gate
entry. **Mentioning here so future-you doesn't mistake it for a real gate.**

---

## Strategic decisions (your call)

### 13. Tier 2 features

Per `dev-docs/ROADMAP.md`:

- **Resource leveling** — `level_document()`, `unlevel_document()`. Wraps
  `document.level()`. Probably 1-2 hours.
- **Baselines** — `create_baseline(name)`, `list_baselines()`,
  `compare_to_baseline(name)`. Project class exposes `baselineNames` +
  `baselineNamed(name)` (already used in `get_project_info`); needs a
  baseline-create method. Probably 4-6 hours.
- **Custom data fields** — `set_custom_data(task_id, key, value)`,
  `get_custom_data(task_id, key?)`. Task class exposes
  `customValue(forKey)` and `setCustomValue(forKey, to)`. High value
  for cross-system links (Plane work item ID, Linear issue ID, GitHub
  PR URL). Probably 2-3 hours.
- **Splits** — `split_task(task_id, at_date)`, `unsplit_task(task_id)`.
  Task class has `split` method. Probably 2 hours.
- **Slack queries** — read-only, extends `get_task` shape with
  `free_slack` and `total_slack`. Trivial — those properties are
  already on the Task class snapshot.
- **Export** — `export_document(format, path)` where format is
  png/pdf/csv. Wraps the SDEF `export` command. Probably 2-3 hours.

**Not blocked, not started.** Each could be a separate `@project` session.
If shipping in groups, "custom data + slack" is the highest-value pair
(both small, both unlock real workflow patterns).

### 14. Privacy: git history rewrite

Older commits in `johntrandall/omniplan-mcp` retain references to
`admin-technical/`, `~/dev/autocoder_v3/`, and `JRVIS` vault names.
Working tree is redacted (chore commit `7eb02b0`); history is not.

**To remove from history:** use `git filter-repo` (modern tool, replaces
`git-filter-branch`):

```bash
brew install git-filter-repo
cd ~/dev/omniplan-mcp
git filter-repo --replace-text <(echo 'admin-technical==>your-infra-docs')
# Add more replacements as needed
git push --force origin main
git push --force umbridge main
```

**Destructive consequences:**
- Commit SHAs change
- Existing clones detach (anyone who pulled the public repo would
  encounter "fatal: refusing to merge unrelated histories")
- Tags need to be re-pushed
- Open PR diffs go stale (we have none currently)

**Recommendation:** only do this if a privacy concern materializes.
The leaked terms are project names, not credentials. Reasonable people
might judge them not worth a destructive rewrite.

### 15. Stale README at `~/admin-technical/setup/macos/omniplan-local/`

May still point at upstream `xiahan4956/omniplan-mcp`. Should now point
at `mcp-omniplan-jtr` from PyPI.

**Next action:** read the file, update the install command from
`uv tool install --from "git+https://github.com/xiahan4956/omniplan-mcp.git"` 
to `uv tool install mcp-omniplan-jtr`. Update the "Tools" table count
from 6 to 20. Update the "Why this is interesting" framing.

**Effort:** 5 minutes. **Blocks:** nothing.

### 16. Behavioral matrix (referenced in OUTREACH.md)

OUTREACH.md says "Behavioral matrix: not yet written. Required pre-publication."
The definition of "behavioral matrix" in this context is unclear. Best
guesses (in decreasing order of likelihood):

1. **A markdown table of every tool × every documented OmniPlan behavior**
   — i.e. expanded "Tools" table. Already partially done in README.
2. **A test-coverage matrix mapping tools to test files** — useful as
   a gate before the demo recording.
3. **Something specific to John's outreach playbook** — could be in
   `outreach-reddit` or `outreach-show-hn` skill docs as a prereq.

**Action:** ask John what he means before the announcement push.
**Effort:** 0 to investigate; up to 2 hours if it turns out to be (1).

---

## Done in this session — index for posterity

Closed in this session, listed here for "where did that resolution land?"
lookups. Each item is a search target — `git log --grep=...` or
`git show <commit>` to get the diff.

- ✅ Drop fork posture, rename to `mcp-omniplan-jtr` (v0.4.0). Commit `47b6645`.
- ✅ Publish to PyPI (v0.4.0 / v0.4.1 / v0.4.2 / v0.4.3). See
  <https://pypi.org/project/mcp-omniplan-jtr/>.
- ✅ Homebrew tap formula (`johntrandall/tap/mcp-omniplan-jtr`,
  audit-clean). See <https://github.com/johntrandall/homebrew-tap/blob/main/Formula/mcp-omniplan-jtr.rb>.
- ✅ LICENSE added (MIT, dual copyright with xiahan4956 for `jxa.py`).
- ✅ README rewritten consumer-facing; `dev-docs/README-DEV.md` absorbs
  developer material.
- ✅ Vendor-docs alignment lint with regression sentinel; substring-leak
  fix; broader fragment-extraction pattern that catches `task.titl` typos
  on first commit. See `tests/unit/test_vendor_docs_alignment.py`.
- ✅ Timezone date-shift bugs fixed: `documents.py` @ v0.4.1,
  `tasks.py` @ v0.4.2 (both: `getUTC*` instead of local-time getters).
- ✅ `query_tasks` operator-precedence + TaskType normalization bugs
  (v0.4.3). Filter clauses now parenthesized; type filter uses same
  regex normalization as `taskToObj`.
- ✅ Test coverage for `list_documents`, `query_tasks`, `get_task`,
  `delete_task`, `update_task` field round-trips (title/note/completed/
  3-point). See `tests/integration/test_basic_endpoints.py` and
  `test_update_task_fields.py`.
- ✅ Strengthened `test_save_document_clears_modified_flag` and
  `test_get_project_info_shape` to cross-bridge round-trips (independent
  JXA SDEF reads, not just the response payload).
- ✅ Pre-commit hook config (`pre-commit install` still required by user
  once — see #4).
- ✅ Courtesy comment to `xiahan4956/omniplan-mcp` PRs #2–#11.
- ✅ Privacy redaction of working tree (admin-technical / autocoder_v3 /
  JRVIS). Commit `7eb02b0`.
- ✅ Cross-link to `oplx-tools` and `oplx-format` in README.
- ✅ Email v8 sent to OmniGroup re: VM testing license.
- ✅ OmniPlan 4 Pro license activated in `omniplan-dev` VM (2026-05-03).
- ✅ L3 VM image rebuilt as `:v2-licensed` and pushed to OCI registry.
  Smoke test deferred (Tart networking flake).
- ✅ Auto-followup routine `trig_017ohvAoUstKoQEt81uuxDFy` scheduled
  for 2026-05-23 (VM-license email reply check).
- ✅ Test count: 69 passed, 0 skipped, 1 xfailed (sentinel for
  `task.moveTo` gap).
