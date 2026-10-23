# Packet controllers

How the assistant hands a packet to the owner, so a fresh chat does not have to rebuild the
tools. Added 10 Oct 2026 (packet H12) from the W9 to W12 controllers, which all ran RESULT OK.

| File | What it is |
| --- | --- |
| `packet.tmpl.py` | The controller. Fill the CONFIG block; the build step fills the TREE and BUNDLE placeholders. Phases: gate (with PRECHECKS; W15e: main may be past the base by plain bot commits touching no packet file, L071), clone, push, pr, validate (ADVISORY checks recorded, never blocking), smoke (`app` or `app/provider`; all dispatched at once, longest app first by `src/etc/build-minutes.json`, then watched together (W15c); SMOKE_ADVISORY entries record NOTE, never block), merge, close, pages, preview, cleanup (CLEANUP_APPLY), tidy (TIDY, W14: old release notes lose the repeated blocks; backup in the logs), mirror (MIRROR), t1 (RUN_T1). |
| `fake_gh.py` | A fake `gh` with a git-backed origin, for rehearsal. Knobs are listed at its top (W15b: `prs_as_issues`, a pull request in CLOSE). |
| `rehearse.sh` | Runs a built controller against `fake_gh.py` in a throwaway world. A fix on top of a pushed packet: set PARENT in the controller; rehearse with `PRIOR_TREE=<old tree> PRIOR_BRANCH=packet/<name>` (and `PRIOR_MOVED=1` for the stop case). W15e: `DRIFT=<path>` puts a bot commit on main before the run, `DRIFT_MAIL=<mail>` makes it a human one (must stop), `MID_DRIFT=<path>` adds a bot commit mid-run; W15f: `DRIFT_MERGE=<path>` puts a Rule merge (bot author, GitHub committer) on main. |
| `suite.sh` | Local copy of 3. Validate's offline steps. Run one instance at a time. |
| `pf-t1.py` | The all-flows test: `PF_MAIN=<full main sha> python3 pf-t1.py`. One nonpublishing Batch Patch of every enabled app, then 2. Check new patch, Provider, Nightly, Community, Tooling and Selection watch, then the status page. Nothing merged or deleted. Added in W13. |
| `render.cjs` | Headless render of `docs/index.html` (Playwright; set `PLAYWRIGHT_BROWSERS_PATH` if the browser lives elsewhere). |
| `build_ctl.py` | W15i: fills the template from a CONFIG file, the packet branch, BASE, BASE_TREE and PREREQ (usage in its first lines). |
| `owner-probes/pf-keys.py` | W15i: the owner's Cloud Shell probe: tests free AI keys live and saves only working ones as secrets, reads CodeQL alerts, runs morphe-desktop's list-versions to list the files it creates, dispatches a council probe and zips the logs. Rehearse new probes against fake APIs first. |

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
  and prints a COVERAGE line. Merging over a failed agent review is the owner's call (W11).
- After the merge it waits for the Pages deployment of the merge before the cleanup preview,
  or the token goes stale (W12: STOP, token mismatch; L049). Deletions stay the owner's
  command: the controller prints the apply line and never runs it.
