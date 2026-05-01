# omniplan-mcp Follow-ups

Living list of tracked follow-ups for this fork. One-line items, ordered by
expected check-back date. Move to ROADMAP when an item grows.

## Pending

### Check OmniGroup response — by 2026-05-22

**Expected by:** ~3 weeks after send.

**Email sent:** Gmail message ID `19de54f80526a865` (johntrandall@gmail.com →
omniplan@omnigroup.com). Subject: "OmniPlan 4.10.2 omniJS — two small
documented gaps (task reparent, Decimal accessor)". **Sent 2026-05-01.**
Find via `to:omniplan@omnigroup.com` in Gmail.

**Important context:** an earlier round of drafting reported 8 omniJS issues,
but on doc re-read, 6 of those turned out to be us using SDEF property names
instead of the documented omniJS names. The sent email contains only the
two items that survived independent verification:

1. **Task reparent** — no documented omniJS method, and three failure-paths
   verified (named methods, `subtasks` array mutation, `.parent` assignment).
2. **Decimal number-extraction** — no documented accessor; we currently parse
   `String(Decimal.fromString("..."))` via regex, which works but feels
   brittle.

**Automated follow-up:** Anthropic Cloud routine `trig_019hMu6Mpt1sAWwLhA64n5kQ`
fires 2026-05-22 09:00 ET / 13:00 UTC. The agent will search Gmail for a
response, summarize against the two questions above, and draft (not send) a
status email to John. Manage at:
https://claude.ai/code/routines/trig_019hMu6Mpt1sAWwLhA64n5kQ

**Possible outcomes & next steps:**

- **OmniGroup confirms `task.moveTo` is on the roadmap or names a method
  we missed** → revive `feat/move-task` from the `xfail(strict=True)`
  sentinel at `tests/integration/test_move_task.py` and ship the
  implementation.
- **OmniGroup confirms a Decimal accessor or stable toString contract** →
  simplify the regex parser in `src/omniplan_mcp/resources.py`
  (`decimalToFloat`) to use the documented path.
- **OmniGroup says "use SDEF AppleScript"** → decide whether to build a
  parallel SDEF bridge in `src/omniplan_mcp/sdef.py`, or accept the gap.
- **No response after 4 weeks (by 2026-05-29)** → file a GitHub issue with
  reproductions for a permanent URL, or let it ride. Re-prompt politely
  after another month.

**Related precedent:** The `omniplan-format` skill notes a prior email to
`omniplan@omnigroup.com` (2026-02-11) about the .oplx format spec that went
unanswered. Set expectations accordingly.

## Done

(empty)
