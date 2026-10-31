# Packet controllers

How the assistant hands a packet to the owner, so a fresh chat does not have to rebuild the
tools. Added 10 Oct 2026 (packet H12) from the W9 to W12 controllers, which all ran RESULT OK.

| File | What it is |
| --- | --- |
| `packet.tmpl.py` | The controller. Fill the CONFIG block; the build step fills the TREE and BUNDLE placeholders. Phases: gate (with PRECHECKS; W15e: main may be past the base by plain bot commits touching no packet file, L071), clone, push, pr, validate (ADVISORY checks recorded, never blocking), smoke (`app` or `app/provider`; all dispatched at once, longest app first by `src/etc/build-minutes.json`, then watched together (W15c); SMOKE_ADVISORY entries record NOTE, never block), merge, close, pages, preview, cleanup (CLEANUP_APPLY), tidy (TIDY, W14: old release notes lose the repeated blocks; backup in the logs), mirror (MIRROR), t1 (RUN_T1). |
| `fake_gh.py` | A fake `gh` with a git-backed origin, for rehearsal. Knobs are listed at its top (W15b: `prs_as_issues`, a pull request in CLOSE). |
| `rehearse.sh` | Runs a built controller against `fake_gh.py` in a throwaway world. A fix on top of a pushed packet: set PARENT in the controller; rehearse with `PRIOR_TREE=<old tree> PRIOR_BRANCH=packet/<name>` (and `PRIOR_MOVED=1` for the stop case). W15e: `DRIFT=<path>` puts a bot commit on main before the run, `DRIFT_MAIL=<mail>` makes it a human one (must stop), `MID_DRIFT=<path>` adds a bot commit mid-run; W15f: `DRIFT_MERGE=<path>` puts a Rule merge (bot author, GitHub committer) on main. |
| `suite.sh` | Local copy of 3. Validate's offline steps. Run one instance at a time. |
| `pf-t1.py` | The all-flows test: `PF_MAIN=<full main sha> python3 pf-t1.py`. One Batch Patch of every enabled app (publish off unless PF_T1_PUBLISH=1, or PF_T1_PUBLISH_APPS for chosen apps), then 2. Check new patch (it publishes apps whose provider or store changed, like its schedule), then Provider, Community, Tooling and Selection watch, 11. Rule merge, Nightly watch and Needs you (FLOWS in pf-t1.py), then it waits for Status page data. No packet cleanup or release deletion; Rule merge may merge an eligible Selection watch pull request or delete a stale adopt branch. Added in W13. |
| `render.cjs` | Headless render of `docs/index.html` (Playwright; set `PLAYWRIGHT_BROWSERS_PATH` if the browser lives elsewhere). |
| `build_ctl.py` | W15i: fills the template from a CONFIG file, the packet branch, BASE, BASE_TREE and PREREQ (usage in its first lines). |
| `owner-probes/pf-keys.py` | W15i: the owner's Cloud Shell probe: tests free AI keys live and saves only working ones as secrets, reads CodeQL alerts, runs morphe-desktop's list-versions to list the files it creates, dispatches a council probe and zips the logs. Rehearse new probes against fake APIs first. |
| `owner-probes/pf-sp.py` | W15g (31 Oct): read-only smoke probe: waits for the packet branch's Manual Patch runs, reads each Sign job result, and for a byte-compare refusal downloads the unsigned hand-off and lists directory, source-stamp and top-level META-INF entries. Found wrong call 120. |
| `owner-probes/pf-ip.py` | W15g (31 Oct): read-only issue and pull request collector: every issue, pull request, comment, review comment and label as JSONL, zipped (the 282-record audit input). |

## Building one

1. Owner uploads `git bundle --all` of live main. Verify its bytes and sha256 against the line
   he pastes, fetch it, and check the main commit's tree.
2. Make the packet on a branch whose parent tree is main's tree. Run `suite.sh` and `render.cjs`.
3. Bundle the packet: `git bundle create pf-X.bundle <prerequisite>..packet/X`, where the
   prerequisite is a commit the owner's clone has (any ancestor of main).
4. Copy `packet.tmpl.py`, set PACKET, BASE (full sha), BASE_TREE, PREREQ, WHEN, MESSAGE, TITLE,
   BODY, CHECKS, SMOKE, CLOSE. Replace the TREE placeholder with the packet tree id and the
   BUNDLE placeholder with the bundle in base64. Compile it, name it
   `pf-X-<first 8 of sha256>.py`.
5. Rehearse (W15i set, environment knobs of rehearse.sh): plain; `RERUN=1`; `DRIFT_MERGE=<a file the packet does not touch>`; `DRIFT=<file> DRIFT_MAIL=someone@example.com` (must STOP); `DRIFT=<a packet file>` (must STOP); a failed check; `PF_T1=run`. The happy path, a rerun after OK, and every stop you can provoke (main moved,
   a failed check, a failed or silent smoke build, a wrong merge tree, Pages never deploying).
   `rehearse.sh CONTROLLER.py REPO_DIR BASE_PARENT BASE_TREE '{"checks":{"Validate targets and scripts":"failure"}}'`
6. Hand over a direct download link and one if/then launcher that checks count, regular file,
   bytes and sha256 before `python3`. No backslashes, no `a && b || c`.

## Rules the controller keeps

- Every phase reads state first; a rerun after OK changes nothing. After a STOP it keeps the
  clone, the script and the logs, and says where. The owner pastes RESULT before any rerun.
- The packet commit is made on the owner box with fixed author and date, so its id is the
  same on every run; gates compare trees, not commit ids. Bot commits on main after the base
  are merged over when they touch no packet file; the merge tree must be the packet tree plus
  their files (W15e, L071). Any human commit on main still stops with MAIN_MOVED.
- Merge only when CHECKS pass, OPTIONAL checks that appear pass, and every SMOKE build works
  and prints a COVERAGE line; entries also in SMOKE_ADVISORY or SMOKE_KEEP_GOING are the
  exception: a failed one is a NOTE, its log kept, and the merge goes on (W16q, Amazon Music). Merging over a failed agent review is the owner's call (W11).
- After the merge it waits for the Pages deployment of the merge before the cleanup preview,
  or the token goes stale (W12: STOP, token mismatch; L049). With CLEANUP_APPLY = False the
  controller prints the apply line and never runs it; with True (W13 on, owner's choice per packet;
  the W16m controller, handed to the owner and not stored
  here, sets it) it applies that exact preview and keeps the receipt. PF_CLEANUP=keep skips it.
- W16n: WATCH_DISPATCH lists workflow files the controller dispatches once on main after the
  cleanup, without waiting; a done file per workflow stops a rerun from sending them twice. A green
  run closes that workflow's failing issue through Notify.

## One owner file: probe plus controller (W16q, 27 Oct 2026)

`build_combo.py PROBE.py pf-<packet>-<sha8>.py PACKET OUT` joins a read-only probe (for example
`owner-probes/pf-p2.py`) and a built controller into one owner file: it runs the probe (collect),
then the controller (do), streams both, and ends with one RESULT line. Inner scripts are embedded
with their sha256 and unpacked into `~/work/run-logs`, so the launcher still checks exactly one
`~/pf-<packet>-*.py`. The controller is kept on a STOP, so the same launcher resumes. One combo
runs at a time (a lock in `~/work/run-logs`; a second launcher stops at once), and any setup error
still ends in one RESULT line. Probe P2 never downloads `test-apk-*` artifacts (evidence only, 5 MB
cap) and prints CLUE lines, the log lines that name a cause. Tests: `tests/combo_contracts.py`.

W16v (27 Oct 2026) additions:

- **RESULT FINDINGS**: the packet merged and every step finished, but the all-flows test (T1) printed
  FINDING lines. Never RESULT OK; nothing to rerun; upload the zips and read pf-t1.out first.
- **Launcher log**: each launch writes a new `~/work/run-logs/pf-<packet>-nohup-<UTC stamp>.log`, so a
  second paste cannot wipe the live log; the combo lock stops the second run at once.
- **Cloud Shell limits** (Google quotas page): a session ends after 12 hours, and the VM ends after
  20 minutes with no one using the tab. Keep the tab open and touch it now and then. After a cut,
  paste the same launcher again: done files skip finished phases and T1 reuses runs it already dispatched.
- **Pages FAIL**: rerun the failed Pages run on main in GitHub Actions, then paste the same launcher.
- **Upload reading order**: probe zip `P2-RESULT.txt`, `case-review.json`, `icons/icons.json` and
  `icons/`; controller folder `RESULT.json`, `pf-t1.out`, then the `pf-t1-*` logs folder.

## Assistant sandbox notes (W16, 23 to 26 Oct 2026)

Things the assistant relearned in the W16 chat; read before building a controller.

- **Inputs.** The sandbox has no internet. Live state comes from public API reads through the
  assistant's web reader; code
  comes from the owner's `git bundle --all` (check bytes and sha256 against his pasted line, then
  `git clone` the bundle). A packet branch must sit on main's exact tree.
- **Long commands.** A single command that sleeps quietly for 20 seconds or more can lose its
  connection ("Failed to read sandbox RPC requests"). Background processes also seem to pause
  between calls. Start the suite detached (`setsid nohup flock /tmp/pf-suite.lock bash
  docs/review/controllers/suite.sh <tree> > log 2>&1 < /dev/null &`) and wait with a loop that
  prints a dot every 4 to 5 seconds and stops at the `SUITE` line. A full suite takes about 7 to 9
  minutes of that.
- **One suite at a time.** A suite run while review agents run tests in the same sandbox failed
  once (shared /tmp files) and passed alone (W16o, 26 Oct). Run the final suite after the agents finish.
- **Killing.** `pkill -f <pattern>` (and `kill $(pgrep -f <pattern>)`) also kills the calling shell
  when the pattern is in its own command line (it happened again on 26 Oct). Kill by process id. An orphaned `unittest` from a killed suite still holds
  `/tmp/pf-suite.lock`; find holders through `/proc/*/fd`.
- **Tests that are not in the obvious place.** Anchors pin warning texts (version_steps_contracts
  pins "Set max_app_version in src/targets.json." in check_sdk.sh); target counts come from
  `tests/target_counts.py` (a disabled app changes ENABLED, not TOTAL).
- **Rehearsal knobs used in W16k and W16l.** `smoke_winner` in the state JSON makes a named smoke
  win with another provider (must STOP, L098); `PRIOR_TREE` and `PRIOR_BRANCH` rehearse a fix on top
  of a pushed packet; `RERUN=1` proves a rerun publishes nothing twice (done files).
- **A fix after a STOP.** The pushed packet commit is deterministic (tree, parent, fixed author,
  WHEN, MESSAGE), so recompute its full sha with `git commit-tree` from the old controller's CONFIG,
  check it against the short sha the owner pasted, and set PARENT to it. Rebuild, rehearse with
  PRIOR_TREE, hand over a new launcher; the controller fast-forwards the branch and reuses the PR.
- **Smokes.** Name the provider for any app with a fallback (`instagram/piko`). A first build of a
  new provider bundle is the first real test: read the provider's open issues before blaming the
  APK (L100).
- **Cloud Shell.** It ends idle sessions and with them nohup jobs; every controller phase must be
  rerunnable. Publishing batches are dispatched and not waited for. Google's limits page (W16o
  round 4): "Non-interactive sessions are ended automatically after 40 minutes" and sessions are
  capped at 12 hours. Run long controllers in Cloud Shell's tmux, keep the tab open, and expect
  to rerun the same launcher after a cut (the script is kept on anything but RESULT OK or RESULT FINDINGS).
- **Working rules carried from the assistant's memory (26 Oct 2026).** Provider facts come from
  `src/community/bundles.json` or a live list-patches run, never from a web search; check every
  record against `docs/council/ONBOARD.md` before it ships; check the official Morphe bundle
  before any community provider. Packets never edit bot-written paths (baselines, bot reports).
  Names that leave a selection go to `exclude-patches`, so the Selection rule cannot add them
  back. A packet closes the issues it serves (CLOSE) and deletes its merged branch
  (DELETE_BRANCHES). `build_ctl.py` takes the packet worktree, not an older checkout. Exact bytes
  of a file on main come from the git blob API by sha (raw reads collapse whitespace and can be
  stale; about 16 KB of base64 per read). L061: never suppress a signal. The owner sends a Cloud
  Shell file to the chat with `cloudshell download <file>`, then attaches it. In the 23 to 26 Oct chat
  the assistant's memory and skill write tools twice reported success without saving: re-read after
  every write. About 1000 MB of
  Actions artifact zips sit in the owner's Cloud Shell home: he decides their fate later, so no
  cleanup command may delete them. Delegate searches and doc preparation to agents with a scope,
  sources, an output and a stop rule; the assistant still verifies, gates and merges.
