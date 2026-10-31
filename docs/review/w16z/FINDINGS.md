# W16z findings (31 Oct 2026)

Inputs: owner bundle of main `572d7d2b` (8267589 bytes, sha256 `6fd5efbb...c4fc`); collect zip from
`pf-p2` and `pf-ip` at that commit (10404081 bytes, `3a77c60e...e444`: 284 issues, 126 pull requests,
528 comments, 11 labels, pin-check run 41158386985 with evidence, status.json); Reddit job logs
(36814 bytes, `eff2f22e...f921`).

## Pin probe: `PIN_STORE_MISSING` was the probe (wrong call 122)

- Run 41158386985 printed MISSING for `facebook`, `facebook:derevanced` and `instagram`
  (`version_code_not_listed`). Its own captured release pages carry all three pins:
  `475817393`, `475019344`, `385811006`, each as `<span class="colorLightBlack">CODE</span>` in the
  variant row, with no "version code" label.
- `get_apk`'s pin-only branch (`src/build/utils.sh`) wanted a label within 40 characters before the
  code; `variant_pick.py` (the build) matches the code as a whole word. The fixtures in
  `tests/pin_check_contracts.py` carried `versionCode 123456`, a shape real pages do not have, so every
  test passed (L115 again).
- Fix: the pin-only branch uses the build's `\bCODE\b` rule. A fixture cut from the real Facebook
  page (`tests/fixtures/apkmirror-facebook-584-rows.html`) runs through `get_apk`: the pin returns 0,
  a neighbour code and a prefix return 2. The old code fails this test (negative control). Replayed on
  the three captured pages: 3 of 3 found (0 of 3 before). Builds were never affected.
- Review round 1 (LOW, kept): the probe accepts the pinned code in any variant row, while the build
  also filters by chip, screen and Android version. Fine for "is the pin still listed"; if the probe
  must prove "the pin is still buildable", require the picked row to carry the code.
- Review round 1 replay: the whole offline path (`pin_fetch_main` plus `_check_wrapped_target`) on the
  three captured pages gives `PIN_STORE_OK` for all three; main gives MISSING for all three.
- Next: the controller dispatches the pin check once after the merge; the weekly schedule follows
  only when that run reads OK.

## Reddit #280: the release guard is right, the failure issue said too little

- Check new patch, 30 Oct (run 41103704066) and 31 Oct (41174318367): Plan chose `winner=morphe
  app=2026.40.0`; the patch built and passed identity; "Releasing APK files" stopped with
  `PUBLISH_REFUSED reddit: app 2026.40.0 is older than the published 2026.41.0`. Morphe's current
  bundle targets 2026.40.0; the shelf has 2026.41.0 (27 to 29 Oct). The downgrade guard did its job.
- The poll is date based (`src/etc/poll.sh`): the newer bundle date asks for a build every run until
  Morphe supports a version at or above the shelf. Each run costs about 3 minutes and stays red; the
  signal is kept on purpose (L061).
- The failure issue said "No failing step recorded" although the job record names step 27/30 as
  failed (cause not proven: the notifier filter is correct on the job record read later). W16z: the
  issue now quotes up to three failure annotations (`::error::` lines), sanitised, so the reason
  shows; an unreadable annotation list is one line, never a missing report. Workflow gains
  `checks: read` (notify and its caller).
- Review round 1: the check run id is read from the job's `check_run_url` (equal to the job id
  today, but documented separately); bare URLs in a reason are removed (GitHub would link them).
- Open: if the step stays unnamed on the next real failure, probe the jobs API timing before any fix.

## Test APK retention (wrong call 124)

The 31 Oct question "keep test APKs 7 days or 2 to 3" came from the 30 Oct storage snapshot. The code
has kept `test-apk-*`, `patch-output-*` and `signed-output-*` for 1 day since W16y-a (30 Oct). The
owner answered 2 days; 1 day stays (shorter, and phone tests use Releases). Retention prose in
`RECOVERY.md` and `src/etc/cleanup.py` now matches the code: 3 releases per app (plus the newest
primary when all 3 are fallbacks), a 7-day age guard, 3 Pages records.

## Probe tooling (wrong call 123)

`gh api repos/.../actions/jobs/ID/logs` refuses log text with terminal colour codes (empty file);
`gh run view RUN --job ID --log` reads it (the same read `pf-p2` uses). Noted in
`docs/review/controllers/README.md`.

## UI pass (owner, 31 Oct: same link twice, lines breaking, cleanups)

Headless audit (Playwright, 360 px and 1280 px, real status.json, a release list rebuilt from the 49
build tags): no link repeated inside a card or section, no page-level duplicate, no horizontal scroll,
no page errors. Fixed: the "App shelf" tab broke into two lines on phones; group counts ("2 apps")
broke; the Freshness row broke inside "last built ..." (it now breaks only at the separator, and says
"bundle N days old"); five Watch cards repeated their own name in the description ("Selection
watch: drops ..." under "10. Selection watch"); a same-version rebuild said "1.0 -> 1.0" (now
"same version, rebuilt"), a first release said "unknown -> 1.0" (now "first release on this shelf").
With W16z's planned changes: one Freshness row, one `N patches` fold, CCleaner "Coming soon" with its
icon and no release line, one "Open Needs you" link with the reply words.

Credit: Anthropic Claude models, for Govindarajulu K.
