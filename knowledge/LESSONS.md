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

## 6 Oct 2026

10. **A store page is a table; the first matching row wins.** Facebook 580 has 14 APKMirror
    variants and every build patched row 1 (armeabi-v7a). Filtering by arch alone still picks the
    wrong ARM64 row. Pin the version code and refuse anything else before patching.
11. **An upstream rename silently drops an exclusion.** `Alternative thumbnails` became `DeArrow`
    and the old `-d` matched nothing. Provider watch "removed" names that sit in an exclude list
    need a decision the same day.
12. **Read failed job logs with `gh run view --job ID --log-failed`.** `gh api .../jobs/ID/logs`
    saved nothing in the 6 Oct intake, so the Reddit reason was lost for a round.
13. **A patcher buffers every edit and writes only after every anchor passed.** The first packet R
    patcher wrote files before a later anchor failed (caught in the sandbox).
14. **Adding a target is a checklist the tests already hold.** 13 test files pin the target count;
    making them fail first found the two real gaps (portal identity map, fallback policy row).

15. **Trust lives in the gates, not in the store name.** A second store passing the same package,
    version, SDK and identity gates is no weaker than the first. One store lagging a version
    stopped Reddit for a month.
16. **Sort with `LC_ALL=C` before comparing lists.** The owner's Cloud Shell sorts
    `NOTICE.txt` after `logos/`, the sandbox before it; packet R r2 stopped on that alone.

## Standing rules (short form; AGENTS.md is authoritative)

- BANNED and CONFIRM are lowercase substring rules. An exact-match filter once matched 0 of
  45 names and shipped six spoof patches.
- `-e`/`-d` bind to the nearest preceding `-p`; same-bundle `-d` wins.
- Provider age is advisory. Configured, applied and owner-approved are separate states.
- `list-patches -x -u` hides universal patches; a name check must include them.
- `channel: prerelease` on a provider with zero prereleases fails; resolve.sh falls back to
  stable. Compare the two command lines before blaming a parser.
- Launchers are never rerun after a PUSH phase; paste the RESULT instead.
