# Omni Group team invite — operator procedure

**Audience:** John, manually running the four invites for `john+omni-development@johnrandall.com`.
**Purpose:** Document the exact click path on `accounts.omnigroup.com` so the invites are mechanical, not investigative.
**Source of truth:** Empirical observation 2026-05-07 by Claude session `0411dd3d-e2e2-45d5-899c-b6d86436f51f` via P1 browserless Playwright. Sign-in confirmed; invite form inspected; **no invites were submitted**.

## TL;DR

Sign into `accounts.omnigroup.com` as `johnrandall`. The dashboard's **Team Management** section lists the four per-app team licenses. Each license has its own **Manage Team** button that takes you to `/manage-team` for that license (selection is carried via `sessionStorage.teameditid`, NOT a query string — so the link path **must** be entered by clicking from the dashboard, not by visiting `/manage-team` directly). On `/manage-team`, paste the invitee's **email** into the textarea (not the Omni Account name), then click **Add Email**. Repeat 4× — once per license. Back-button between licenses; the dashboard re-renders with current seat counts.

## Verified facts (2026-05-07)

| Fact | How verified |
|---|---|
| 4 separate per-app team licenses, each Total: 3, Used: 1 (`johnrandall` only) | Read directly from dashboard — confirms the skill's seat math |
| All "Manage Team" links share the bare URL `/manage-team` | DOM inspection of the four `<a>` elements |
| License selection uses `sessionStorage.teameditid` (numeric license ID) | Observed `teameditid: "1199578"` set after clicking OmniFocus 4 Pro's button |
| Invite field is a `<textarea>` (not `<input>`), takes **email** addresses | DOM inspection: placeholder `max.geekery@omnigroup.com`, title `"Enter a single email to add, or paste in a list of email addresses, separated by a comma or line breaks."` |
| Multiple emails accepted: comma-separated or line-break-separated | Title attribute on the textarea + label "Enter as many emails as you'd like, separated by commas:" |
| Submit mechanism: **Add Email** button (with **Cancel** sibling) appears under the textarea once content is typed | Triggered the React input event programmatically; observed buttons mount in the previously-`display:none` wrapper |
| Sign-out is a `<div>` (not a button) in the top-right header next to the username | DOM inspection |

## Step-by-step

### 1. Sign in

1. Open `https://accounts.omnigroup.com/`.
2. Account Name: `johnrandall` (the account *username*, NOT the email).
3. Password: from 1Password vault `JK + VA`, item `Omni Group: Account (johnrandall)`.
4. Click **Sign In**.

You'll land on the dashboard at `https://accounts.omnigroup.com/`. The page is one long scroll containing five sections: Account, Password, Payment, App Access, **Team Management**, Legacy License Keys.

### 2. Locate Team Management

Scroll to the **Team Management** section (roughly mid-page). You'll see one row per team-licensed app. Currently, in alphabetical order:

- OmniGraffle 7 for Mac — Total seats: 3, Unused seats: 2
- OmniOutliner 6 Pro — Total seats: 3, Unused seats: 2
- OmniFocus 4 Pro — Total seats: 3, Unused seats: 2
- OmniPlan 4 Pro — Total seats: 3, Unused seats: 2

Each row has a **Manage Team** link.

### 3. Invite to one license

1. Click **Manage Team** on the FIRST license (e.g., OmniGraffle 7 for Mac).
2. The page navigates to `/manage-team` showing only that license. You'll see:
   - License heading (e.g., "OmniGraffle 7 for Mac")
   - "Total Seats: 3 / Used Seats: 1"
   - **Invite Users:** label with a textarea (placeholder `max.geekery@omnigroup.com`)
   - The current users table (just `johnrandall` / `john@johnrandall.com`)
   - A **Remove User(s)** button (disabled until you select a user — irrelevant for invites)
3. **Click into the textarea** and type or paste:
   ```
   john+omni-development@johnrandall.com
   ```
4. Two buttons appear directly under the textarea: **Cancel** and **Add Email**.
5. Click **Add Email**. (Behavior beyond this point is **not yet verified** — the click was deliberately NOT performed during research. Expected: an invitation email is sent to the entered address; the page may display a "pending" or "invited" status row in the Users table.)
6. Click **\<Back to Omni Accounts** in the top-left to return to the dashboard.

### 4. Repeat for the other three licenses

Repeat step 3 for each remaining license in any order:
- OmniOutliner 6 Pro
- OmniFocus 4 Pro
- OmniPlan 4 Pro

After all four invites, the Team Management section on the dashboard should show "Used seats: 2" / "Unused seats: 1" for each app — though this may only update after `john+omni-development` accepts the invite from `john@johnrandall.com`.

### 5. Sign out

Click **Sign out** in the top-right header (next to your username `johnrandall`). The page returns to the sign-in form; localStorage is cleared.

## Reassigning a seat (remove + re-invite)

Seats are reassignable directly from the same `/manage-team` page:

1. The Users table on `/manage-team` has a checkbox per row.
2. Check the row of the user you want to release (`john+omni-development@johnrandall.com`, or any other invitee).
3. Click **Remove User(s)** (which enables once at least one row is checked).
4. The seat moves back into the "Unused seats" pool.
5. Invite a different email via the textarea (same flow as a fresh invite).

The owner account (`johnrandall`) cannot be removed from its own team licenses — only invited users can. There is no admin-approval delay observable in the UI; remove + re-invite is two clicks plus typing.

**Not verified:** whether removing a user with an actively-running install immediately deactivates the app, revokes on next launch, or waits for the next 7-day receipt renewal. See `https://support.omnigroup.com/team-subscriptions/` for vendor-confirmed behavior.

## Open questions / behaviors NOT verified

These were not tested during research because doing so would have submitted a real invite or modified state:

1. **What clicking "Add Email" actually triggers** — best guess (from the label + Omni's documented team-licensing model) is that it sends an invitation email to the address. There may or may not be an additional confirmation step.
2. **Whether the invitee (`john+omni-development`) needs an existing Omni Account before being invited, or if the invite acts as both invitation + account creation prompt.** Per the omni-licensing skill, the recommended flow is to create the account first (in-app or via `accounts.omnigroup.com/register`), THEN invite. This avoids ambiguity.
3. **Whether the invite appears with a "pending" status row in the Users table immediately, or only after acceptance.**
4. **What email subject/body the invitee receives.** Worth keeping an eye on the `john@johnrandall.com` inbox after invites go out — the verification/invite emails arrive there since `+omni-development` is a Gmail alias.

## What to watch in `john@johnrandall.com` inbox

After clicking Add Email on each of the 4 licenses, expect up to 4 incoming emails (1 per license) addressed to `john+omni-development@johnrandall.com`, likely from `accounts@omnigroup.com` or similar. These contain the acceptance/registration link the invitee clicks to claim the seat.

## Anti-patterns reminder (from the omni-licensing skill)

- Do **NOT** invite the personal `johnrandall` account to its own team license — it's already the owner.
- Do **NOT** invite an arbitrary alias as a workaround for "1 seat used by John, 1 reserved for agent" — use the dedicated `john+omni-development@johnrandall.com` address per ADR-001.
- The team-license seats are per-app (4 separate pools of 3); there is **no** unified pool. Don't reason about "how many seats total."

## Screenshots

Captured during research, stored in the P1 browserless container's `.playwright-mcp/` output directory (NOT on the local Mac filesystem):
- `01-account-dashboard.png` — full dashboard after sign-in
- `02-manage-team-omniplan.png` — Manage Team page for OmniPlan 4 Pro (representative; all four are visually identical aside from the heading and seat counts)
- `03-manage-team-omnifocus.png` — Manage Team page for OmniFocus 4 Pro

If screenshots are needed locally, re-run the research procedure or extract them from the container.

## Provenance

- Session ID: `0411dd3d-e2e2-45d5-899c-b6d86436f51f`
- Date: 2026-05-07
- Browser: P1 pool browserless Playwright (umbridge container)
- Skill referenced: `omni-licensing` (`~/.claude/skills/omni-licensing/SKILL.md`)
- ADR referenced: ADR-001 Omni License Allocation (`~/dev/_areas/ADRs/ADR-001-omni-license-allocation.md`)
