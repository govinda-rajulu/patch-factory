# Open work

Written by the closing block on 7 Sep 2026, from the repo rather than from memory. Every line
here is something not done, with what unblocks it. When a line stops being true, delete it.

## Only you can do these

1. **A second offline copy of the signing keystore.** One emailed archive is one deleted thread
   from losing every app in the set, and Truecaller charges phone verifications to re-establish.
   The drill is in `RECOVERY.md`. Fifteen minutes. This is the largest single risk in the project.
2. **Install a build on a phone.** Nothing has been installed since 16 Aug. `es-file` and
   `mx-player` first: they apply four resource-rewriting CONFIRM patches for the first time.
   Then `reddit`, whose hosts blocker ran for the first time on 6 Sep, where a bad blocklist
   entry looks like content failing to load.
3. **Decide the patches in `docs/review/DECISIONS-*.tsv`.** Generated and classified against
   `BANNED` and `CONFIRM`, but a patch reaching an APK on your accounts is your call, never a
   script's. Mark column 1 IN or OUT.

## Decided and closed, so nobody reopens them

- **`list-patches` must be run with `-x`.** morphe marks newer app versions EXPERIMENTAL and
  hides them without that flag. A dump taken without it made morphe's Reddit support look like it
  topped out at 2026.14.0 when it actually reaches 2026.35.0, the version this repo builds.
  `resolve.sh` has always passed `-x -u`; the one-off command that produced the dump had not.
  Every dump under `docs/review/` is now generated with `-x`. **Govind caught this from morphe's
  own README while I was about to write the wrong conclusion into this file.**
- **`morphe-desktop` stays unpinned.** `build.sh` takes its `latest` release on purpose, because
  new provider bundles routinely need a newer patcher. Pinning it freezes every provider.
  Recorded in `SECURITY.md` as the largest accepted supply-chain surface.
- **sonyliv and zee5 are out of scope**, removed 7 Sep. Both were Android-TV-only providers, and
  sonyliv also shipped a server-visible `Change app name` on a paid account.
- **`_attic` is kept, not cleaned.** An archive is unreferenced by design; the rule is in
  `src/etc/cleanup_guard.md` and `src/etc/orphans.sh` now warns instead of deleting.

## Open, and now unblocked

- **Wire morphe as a second Reddit provider.** Confirmed to support the version this repo builds.
  It needs an include list, which is a decision, not a script: `docs/review/DECISIONS-reddit-morphe.tsv`
  has every patch classified against `BANNED` and `CONFIRM`. Mark column 1, then add morphe as an
  `extra_bundles` entry on the `reddit` target with its own `patch_dir`. Note that `adobo` and
  morphe both ship a `Hide ads`-style patch, so watch the duplicate-name gate.

## Real, and not urgent

- **`src/build/utils.sh`** is unvendored upstream code from the FiorenMas template, sourced with
  `set +u` because it is not strict-mode safe, and `split_arch` builds its command with `eval`.
  Nothing untrusted reaches it, so this is debt rather than a hole. Splitting it into focused
  modules is a quiet afternoon, not a fix.
- **No reproducible-build check.** Two builds of the same input are not proven identical. Worth
  having, and the version an external audit proposed would not run: it called paths that do not
  exist here. Write it against `src/build/build.sh` if you want it.
- **No integration test on pull requests.** `main` is currently the test. This matters the day an
  agent opens PRs; until then it costs a runner per PR for little.
- **Three community providers considered and parked**: esfile/rushiranpise, photos/RookieEnough,
  instagram/Stylus. Each needs its own include list, which is a decision.
- **Docker images are digest-pinned now**, but nothing re-pins them when upstream ships. Dependabot
  covers actions, not these. Re-run the digest read by hand occasionally.

## Standing risks, per target

- Patch-age caps in force: 60 days on 13 target(s), 120 days on 1 target(s).
- A target whose winner ages out **stops building** unless it has a second candidate. Targets
  with only one candidate have no fallback: check the freshness table the closing block printed,
  and promote a working extra bundle to a candidate before a cap trips rather than after.
- `truecaller-combo` is the known one: its cap was raised to 120 days on 6 Sep because bufferk
  publishes rarely. That buys time, it does not fix the single point of failure.

## How to keep this file honest

Everything factual about the repo is generated: the README state block, the Pages catalog, the
target dropdown, `CREDITS.md` and the Obtainium import files, each with a `--check` gate in
**3. Validate**. This file is the one place allowed to hold opinion, so it is the one place that
can rot. Read it before planning a session, and delete what is no longer true.
