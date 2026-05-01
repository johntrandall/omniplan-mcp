# omniplan-mcp Follow-ups

Living list of tracked follow-ups for this fork. One-line items, ordered by
expected check-back date. Move to ROADMAP when an item grows.

## Pending

### Check OmniGroup response — by 2026-05-22

**Expected by:** ~2-3 weeks after send.

**Email draft:** Gmail draft `r-9007395370526708366` (johntrandall@gmail.com →
omniplan@omnigroup.com). Subject: "OmniPlan 4.10.2 omniJS surface — persistence
+ opacity gaps observed". Drafted 2026-05-01, **not yet sent** — John needs to
review and click Send. Search Gmail for `in:drafts to:omniplan@omnigroup.com`
to find it. Label: `omniplan-mcp` (`Label_4591`).

**Why:** Asks whether the persistence gaps documented in
[`omnijs-persistence-gaps.md`](omnijs-persistence-gaps.md) are intentional
limitations, deprecations, or bugs. A response (positive or negative) unblocks
several Tier 1 items currently sitting at `xfail(strict=True)` sentinels.

**Possible outcomes & next steps:**

- **OmniGroup confirms an omniJS fix is shipping** → revive
  `feat/constraints` and `feat/move-task` from the xfail sentinels and ship
  the implementations.
- **OmniGroup says "use SDEF AppleScript for those"** → decide whether to
  build a parallel SDEF bridge in `src/omniplan_mcp/sdef.py` or keep the
  features as documented gaps.
- **No response after 4 weeks (by 2026-05-29)** → file a GitHub issue with
  reproductions and let it ride. Re-prompt politely after another month.

**Related precedent:** The `omniplan-format` skill notes a prior email to
`omniplan@omnigroup.com` (2026-02-11) about the .oplx format spec that went
unanswered. Set expectations accordingly.

## Done

(empty)
