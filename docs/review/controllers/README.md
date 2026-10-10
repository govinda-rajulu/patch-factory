# Packet controllers

How the assistant hands a packet to the owner, so a fresh chat does not have to rebuild the
tools. Added 10 Oct 2026 (packet H12) from the W9 to W12 controllers, which all ran RESULT OK.

| File | What it is |
| --- | --- |
| `packet.tmpl.py` | The controller. Fill the CONFIG block; the build step fills the TREE and BUNDLE placeholders. Phases: gate (with PRECHECKS), clone, push, pr, validate (ADVISORY checks recorded, never blocking), smoke (`app` or `app/provider`), merge, close, pages, preview, cleanup (CLEANUP_APPLY), t1 (RUN_T1). |
| `fake_gh.py` | A fake `gh` with a git-backed origin, for rehearsal. Knobs are listed at its top. |
| `rehearse.sh` | Runs a built controller against `fake_gh.py` in a throwaway world. |
| `suite.sh` | Local copy of 3. Validate's offline steps. Run one instance at a time. |
| `pf-t1.py` | The all-flows test: `PF_MAIN=<full main sha> python3 pf-t1.py`. One nonpublishing Batch Patch of every enabled app, then 2. Check new patch, Provider, Nightly, Community, Tooling and Selection watch, then the status page. Nothing merged or deleted. Added in W13. |
| `render.cjs` | Headless render of `docs/index.html` (Playwright; set `PLAYWRIGHT_BROWSERS_PATH` if the browser lives elsewhere). |

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
5. Rehearse: the happy path, a rerun after OK, and every stop you can provoke (main moved,
   a failed check, a failed or silent smoke build, a wrong merge tree, Pages never deploying).
   `rehearse.sh CONTROLLER.py REPO_DIR BASE_PARENT BASE_TREE '{"checks":{"Validate targets and scripts":"failure"}}'`
6. Hand over a direct download link and one if/then launcher that checks count, regular file,
   bytes and sha256 before `python3`. No backslashes, no `a && b || c`.

## Rules the controller keeps

- Every phase reads state first; a rerun after OK changes nothing. After a STOP it keeps the
  clone, the script and the logs, and says where. The owner pastes RESULT before any rerun.
- The packet commit is made on the owner box with fixed author and date, so its id is the
  same on every run; gates compare trees, not commit ids.
- Merge only when CHECKS pass, OPTIONAL checks that appear pass, and every SMOKE build works
  and prints a COVERAGE line. Merging over a failed agent review is the owner's call (W11).
- After the merge it waits for the Pages deployment of the merge before the cleanup preview,
  or the token goes stale (W12: STOP, token mismatch; L049). Deletions stay the owner's
  command: the controller prints the apply line and never runs it.
