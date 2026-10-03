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

## 29 Sep 2026, afternoon

4. **Pinned controllers go first.** Packet N required main `1b8e42c3`, so it ran before the
   unrelated knowledge PR (#110) merged. Order packets that pin main ahead of others.
5. **"Merged" in chat is not merged.** Read `/pulls/N` for `merged: true` before acting on it.
6. **Save the reason before the log goes.** The Edge reason survived only because the job
   log was still in Cloud Shell `/tmp`. Copy reason lines into the archive the same day.

## 1 Oct 2026

7. **Pin from main, never from a PR head.** Packet Q v1 took ci.yml's expected blob from
   Dependabot #103's head; main had changed since #103's base, so the gate stopped it before any
   push. v2 pinned every before and after blob from main's own tree and ran clean.
8. **Dependabot `directory: "/"` skips composite actions.** #103 bumped five workflows and missed
   `.github/actions/preparing/action.yml`; Validate's action-ref contract caught the mismatch.
9. **The keepalive bot moves main on the 1st of each month.** It only rewrites `.keepalive`, but a
   controller pinned to main before it stops with MAIN_MOVED (final-handover-v1, 3 Oct). Repin and
   rerun; the per-file blob gates are what protect the content.

## Standing rules (short form; AGENTS.md is authoritative)

- BANNED and CONFIRM are lowercase substring rules. An exact-match filter once matched 0 of
  45 names and shipped six spoof patches.
- `-e`/`-d` bind to the nearest preceding `-p`; same-bundle `-d` wins.
- Provider age is advisory. Configured, applied and owner-approved are separate states.
- `list-patches -x -u` hides universal patches; a name check must include them.
- `channel: prerelease` on a provider with zero prereleases fails; resolve.sh falls back to
  stable. Compare the two command lines before blaming a parser.
- Launchers are never rerun after a PUSH phase; paste the RESULT instead.
