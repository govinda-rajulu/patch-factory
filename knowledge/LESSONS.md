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
17. **Size work to the seat, not the seat to the work.** Free tiers differ by more than ten times
    in request size (Groq 8000 tokens a minute, Gemini a million of context). Each seat has a
    budget and abstains above it; heavy work is split into parts that fit, never truncated.
18. **A remote asset fetch is optional per item.** One icon host serving WebP must not stop a
    packet: each tile passes the PNG gate or keeps its monogram, and the result names which.

19. **Free seats fail on format before they fail on judgement.** On the 7 Oct audit 6 of 8 seats
    gave no usable answer: broken or cut-off JSON, a 404 that stopped the seat, a too-small budget.
    Fix the transport (JSON mode, low reasoning, 404 falls through, one repair turn), not the prompt.
20. **A finding without a quote is a guess.** Audit seats invented lines ("no retry step") and
    generic advice. Findings now quote the file; a quote that is not there drops the finding.
21. **One standing issue per failing workflow.** 38 of 39 per-run failure issues were the same
    ci.yml story. Failures comment on one "Failing:" issue; the next green run closes it.

22. **Free tiers are shared by every job at once.** Eleven audit shards dispatched together made
    gemini busy on every part. Heavy jobs run one at a time, on a schedule, not in a burst.
23. **A fetch tool can truncate; count from the API, not from a page you read.** "Three shards
    posted nothing" was a truncated read; every run had succeeded and posted. Check counts twice.

24. **Stage removals before running the gates.** A moved file broke a test that copies the
    tracked file list until the deletion was staged; staged status also reports renames, so
    compare file sets with `git diff --name-only --no-renames`.
25. **Rehearse every controller against a fake GitHub, including the stop cases.** The V2
    rehearsal caught a rename in the file-set check before the owner ran it.
26. **A handover names what it could not cover.** Compacted chat context loses detail (wrong
    calls 1-5 of 6 Oct); say so in the record instead of filling the gap.

## 8 to 9 Oct 2026 (packets W2 to W5)

- Get the owner's `git bundle --all` of main first and run the whole suite (contracts, repair,
 portal, gates) plus a headless Pages render before any packet. A rehearsal without the suite
 proves nothing about the repository.
- Exercise every path a tool offers. `app.py` had add, disable, enable and remove; only add was
 tested, and disabling an app broke about 20 checks.
- Test a log filter on a real log. `gh run view --log-failed` does not label lines with the step
 name; grep the saved log for error words or a known start/end line instead.
- Check a record against the review's written rules before it ships (`docs/council/ONBOARD.md`).
- Patches that say "Any" version give the build nothing to choose; pin `max_app_version` from the
 store page (newest Android 10 build) until the build reads the store itself.
- Owner rules worth keeping: a failure stays listed until a later run of the same app works;
 keep each app's two newest builds and purge the rest; archive branches before deleting them.

## 9 Oct 2026, afternoon (packet W6)

- One vendor, two marker shapes: Prime Video's `libInit.so` is `release=NNN`, Amazon Music's
 is `4.6.14`. Classify each from its own `NATIVE_MEMBER_DIAGNOSTIC`, never from a sibling app.
- A per-workflow red light hides which app failed and clears on any other app's success. Key
 build status by app; keep the workflow red only for failures no app owns.

## 9 Oct 2026, evening (packet W7)

- One side effect per if/then, each with its own result line. Chaining push and PR in one `&&`
 test hides which one happened (wrong call 11).
- A hand-raised version pin is a symptom. Pick the newest the provider supports, step down
 from the phone cap, and keep pins only where a human chose an exact build.

## 9 Oct 2026, night (packet W8)

- A fake that always answers proves nothing about a real endpoint's shape. Rehearse log
 collection with the same command on one real finished run before shipping it.
- When one of two runs of the same commit fails in a third-party service step and the other
 passes, retry once, then gate on the pull-request run. Do not run both on packet branches.
- A tool on PATH in the sandbox may not be on PATH on the runner: use the reader that searches
 ANDROID_HOME.

## 9 Oct 2026, W8 results

- Pages deployment records are a list of past publishes, not content. Keep the newest 5; the
 rest go through `cleanup.py` with a receipt (L041).
- A run log repeats each step's script before its output. Filter the echoed block before you
 grep for a result, or the command reads as its own success (L042).

## 9 Oct 2026, late night (packet W10)

- A precondition in an API's docs is a test case: the fake must refuse the call the way the real
 service does (L043).
- Check watch output against the include lists. A name the build applies but the watch does not
 list means the listing is incomplete, not that the patch is gone (L044).

## 10 Oct 2026 (packet W11)

- Use the repository spelling GitHub returns; exact checks stay exact (L045).
- Before ranking providers, read every way the index links a patch to an app (L046).

## Standing rules (short form; AGENTS.md is authoritative)

- BANNED and CONFIRM are lowercase substring rules. An exact-match filter once matched 0 of
  45 names and shipped six spoof patches.
- `-e`/`-d` bind to the nearest preceding `-p`; same-bundle `-d` wins.
- Provider age is advisory. Configured, applied and owner-approved are separate states.
- `list-patches -x -u` hides universal patches; a name check must include them.
- `channel: prerelease` on a provider with zero prereleases fails; resolve.sh falls back to
  stable. Compare the two command lines before blaming a parser.
- Launchers are never rerun after a PUSH phase; paste the RESULT instead.
- The newest version a provider lists is not always the one with the most of our patches;
  choose by coverage, break ties by newest, and keep the old rule when the listing is in doubt (W12).
- Promise only what the packet ships. Cutting promised scope needs the owner's yes first (W12).
- Before a session ends, the tools it built go into the repo too (docs/review/controllers/, H12).
