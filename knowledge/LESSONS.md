# patch-factory cross-session lessons

Council-facing lessons live in `../docs/council/LESSONS.md` (numbered, hash-pinned).
Per-session wrong calls live in `../docs/review/SESSION-*.md`. The full historical list is
[archive/skills/MY-WRONG-CALLS-ON-PATCH-FACTORY.md](archive/skills/MY-WRONG-CALLS-ON-PATCH-FACTORY.md).
This file keeps only what fits in neither.

## 29 Sep 2026

1. **Knowledge moved into the repo.** Assistant skills and memory are no longer the record;
   this folder, `docs/review/` and `docs/council/LESSONS.md` are.
2. **Public API staleness.** `/repos/<r>/commits` returned a month-old page while
   `/repos/<r>/branches/main` was current. Read the branch, then its tree.
3. **Cloud Shell fills up.** 250 older items were moved to `~/work/pf-archive/` with a
   size and sha256 index. Scripts now self-clean on success (WORKING-AGREEMENT.md).

## Standing rules (short form; AGENTS.md is authoritative)

- BANNED and CONFIRM are lowercase substring rules. An exact-match filter once matched 0 of
  45 names and shipped six spoof patches.
- `-e`/`-d` bind to the nearest preceding `-p`; same-bundle `-d` wins.
- Provider age is advisory. Configured, applied and owner-approved are separate states.
- `list-patches -x -u` hides universal patches; a name check must include them.
- `channel: prerelease` on a provider with zero prereleases fails; resolve.sh falls back to
  stable. Compare the two command lines before blaming a parser.
- Launchers are never rerun after a PUSH phase; paste the RESULT instead.
