# Release Checklist — `mcp-omniplan-jtr`

**Use this every time you cut a release.** Auto-loaded by the
`release-mcp-omniplan` skill.

This is the project-specific checklist. The skill orchestrates which
generic skills (`publish-python-package`, `publish-homebrew-tap`,
`onprem-git`, `email-drafting`) apply to each step.

> **Origin**: this checklist exists because the v0.4.4 → v0.4.5 ship
> on 2026-05-07 surfaced ~6 things an agent needs to do beyond
> `uv publish` — version-tag the source repo, GitHub-release for the
> Homebrew tarball, bump the formula, refresh the README's
> supported-versions matrix and tools list, audit the persistence-gaps
> doc, and (if shipping in response to an OG support thread) reply on
> the thread. Doing them all from memory is a footgun.

## Pre-flight (before bumping the version)

- [ ] **All tests pass locally** in the beta VM:
  ```bash
  tart-vm ssh omniplan-4.10.3-v232.5.9-beta 'cd /tmp/code && /tmp/venv/bin/pytest tests/ -m requires_omniplan --tb=short'
  ```
  Target: 0 failed. (Skipped tests are pre-existing platform/env gates,
  not regressions.)
- [ ] **Unit suite passes locally**:
  ```bash
  ~/dev/omniplan-mcp/.venv/bin/python -m pytest tests/unit/ -q
  ```
- [ ] **Vendor-docs allowlist** at `tests/unit/vendor_docs_allowlist.txt`
  has been updated for any new omniJS identifiers introduced in this
  release. The lint goes RED on first commit if missing.

## Version + CHANGELOG

- [ ] **Bump `version`** in `pyproject.toml` (SemVer: patch for fixes,
  minor for new tools, major for breaking changes).
- [ ] **Add CHANGELOG entry** at the top of `CHANGELOG.md`, dated today.
  Cover: Added / Changed / Fixed / Tests / Compatibility / Notes.
  Mark each claim with **Verified** / **Observed** / **Inferred** per
  the confidence-tag protocol — do not state Inferred claims as
  Verified.
- [ ] If correcting a prior release's claim, add a **CHANGELOG correction**
  subsection naming what was wrong and how it was inferred-not-verified.

## Documentation refresh

- [ ] **README — Supported OmniPlan versions matrix** updated. The
  "Verified" column needs the date and build number for the version
  tested. If a new version was added, give it a new row; if an
  existing version was re-verified, update the date.
- [ ] **README — Tools table** lists every tool the MCP exposes,
  including any added in this release. Note version requirements
  inline (e.g. "Requires OmniPlan 4.10.3+").
- [ ] **README — Limitations** updated when a previously-listed
  limitation closes (cross-reference the version it landed in).
- [ ] **`dev-docs/omnijs-persistence-gaps.md`** audited against the
  release. When a previously-tracked gap closes, mark it CLOSED with
  the version + ticket reference; preserve the historical detail
  below the status line.
- [ ] **`dev-docs/TODO.md`** open-loops index updated — closed loops
  marked DONE, new loops added.
- [ ] If a vendor (Ken @ OmniGroup, etc.) is owed a reply on an open
  ticket, **note the draft URL** in the relevant TODO entry.

## Build + publish to PyPI

- [ ] `rm -rf dist build && uv build` — produces both
  `mcp_omniplan_jtr-X.Y.Z.tar.gz` and `…-py3-none-any.whl`.
- [ ] `op item get "PyPI - mcp-omniplan-jtr" --vault "JRVIS Execution"
  --fields credential` — token reachable. (Per
  `1password-credential-management` skill: ALWAYS via 1Password,
  never hardcoded.)
- [ ] `UV_PUBLISH_TOKEN=<token> uv publish` — push to PyPI.
- [ ] **Verify v live**:
  ```bash
  sleep 10  # CDN propagation
  curl -s "https://pypi.org/pypi/mcp-omniplan-jtr/json" | python3 -c \
    "import json,sys;d=json.load(sys.stdin);print(d['info']['version'])"
  ```
  Output should match the version you just bumped.

## git: tag + push

- [ ] **Merge worktree branch into main** (`git merge --ff-only` if
  no conflicts; otherwise rebase or open a PR).
- [ ] **Tag the release commit**: `git tag vX.Y.Z <commit-sha>`.
- [ ] **Push to on-prem first** (per `onprem-git` skill):
  `git push umbridge main vX.Y.Z`.
- [ ] **Push to public origin** (asks for explicit user approval —
  this is irreversible): `git push origin main vX.Y.Z`.
- [ ] **GitHub release** for the tag:
  ```bash
  gh release create vX.Y.Z --title "vX.Y.Z" --notes "<short notes>"
  ```
  GitHub auto-generates the source tarball at
  `https://github.com/johntrandall/omniplan-mcp/archive/refs/tags/vX.Y.Z.tar.gz`
  — Homebrew references this URL.

## Homebrew tap bump (`johntrandall/homebrew-tap`)

- [ ] **Compute the source tarball SHA**:
  ```bash
  curl -sL "https://github.com/johntrandall/omniplan-mcp/archive/refs/tags/vX.Y.Z.tar.gz" \
    | shasum -a 256 | awk '{print $1}'
  ```
- [ ] **Update `Formula/mcp-omniplan-jtr.rb`** in
  `/opt/homebrew/Library/Taps/johntrandall/homebrew-tap/`:
  - `url` → new tag tarball
  - `sha256` → just-computed value
  - Resource blocks (PyJWT, etc.) — diff against the new wheel's
    `requirements.txt` if dependencies changed
- [ ] **Validation cycle** (per `publish-homebrew-tap` skill):
  ```bash
  brew style johntrandall/tap/mcp-omniplan-jtr     # in tap dir; requires push first
  brew audit --strict johntrandall/tap/mcp-omniplan-jtr
  brew install johntrandall/tap/mcp-omniplan-jtr   # fresh install
  brew test johntrandall/tap/mcp-omniplan-jtr      # if formula has a test block
  ```
- [ ] **Push the tap update**:
  `git -C /opt/homebrew/Library/Taps/johntrandall/homebrew-tap push origin main`.

## Install-method smoke tests

Confirm all three install methods land the new version (per the
README's three Install snippets):

- [ ] **uv tool**: `uv tool upgrade mcp-omniplan-jtr` (or fresh
  install if not previously installed). Verify
  `mcp-omniplan-jtr --version` (or the equivalent) shows X.Y.Z.
- [ ] **pip**: `pip install --upgrade mcp-omniplan-jtr` in a fresh
  venv.
- [ ] **brew**: `brew update && brew upgrade johntrandall/tap/mcp-omniplan-jtr`.

If any of the three lag (Homebrew often does — the tap repo's main
must be pushed and `brew update` must have synced), document the lag
in the release notes rather than blocking on it.

## Vendor / community communication (when applicable)

- [ ] If this release closes a vendor support ticket (e.g. OG
  #3107771), **draft a reply on the existing thread** per the
  `email-drafting` skill (HTML body, JRVIS author framing, AI-Drafted
  label, direct compose URL surfaced to the user). **Do not send
  until PyPI is verified live and the user approves the draft.**
- [ ] If this release affects the Outreach announcement plan, update
  `~/dev/_outreach/projects/omniplan-mcp/OUTREACH.md`.

## Closeout

- [ ] **Mark prior version yanked on PyPI** (only if the prior version
  has a known regression). Default: leave both versions installable.
- [ ] **Tasks list** updated — mark release tasks completed, queue
  any follow-up work uncovered during the cycle.
- [ ] **Field report** for the release, if it was non-trivial (per
  `field-report` skill). Saves hours of context for the next
  release agent.

---

## Quick reference: version → action map

| Change kind | Version bump | Tag? | Homebrew? | Email? |
|---|---|---|---|---|
| Doc-only (README, CHANGELOG fixes) | none — push to main | optional | no | no |
| Bug fix (no API change) | patch (X.Y.Z+1) | yes | yes | only if related to open vendor ticket |
| New tool / new capability | minor (X.Y+1.0) | yes | yes | yes if vendor was involved |
| Breaking API change | major (X+1.0.0) | yes | yes | announcement to users |
| Backward-compat fix for a same-day release | patch | yes | yes | mention the supersession in release notes |
