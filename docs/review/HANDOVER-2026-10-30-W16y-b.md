# Handover, 30 October 2026: W16y-a result and packet W16y-b

Start a new chat from the PATCH-FACTORY-BUILDS skill, then `knowledge/STATE.md`, then this file,
then [OPEN-WORK.md](OPEN-WORK.md). Owner decisions of the day: [DECISIONS-2026-10-30.md](DECISIONS-2026-10-30.md).

## Where things stand

- W16y-a merged as #279 (`75fd6dae`, tree `801b1a96`), RESULT OK. Smokes: Facebook HushFacebook
  102 of 102, Prime Video hoo-dles, Amazon Music 26.36.1 (De-Vanced v1.6.2, 5 of 5 chosen
  patches; the 2.36.1 version bug is fixed upstream), ES File fallback stopped at the coverage
  floor (test build only, as designed). The cleanup preview listed 0 releases and 11 Pages
  records; it was not applied.
- Owner actions done on 30 Oct: secret scanning and push protection on, `TDL_BACKUP` deleted,
  merged CCleaner branch deleted, repo secret `VT_API_KEY` set.

## What W16y-b changes

1. Provider safety scan: Manual Patch input `scan` (nonpublishing only). `src/etc/provider_scan.py`
   compares the original and the patched APK (permissions added, new hosts against
   `provider_scan_allowlist.json`, new code red flags, new native libraries), runs ClamAV on the
   bundle and the patched APK, and looks up both sha256 values on VirusTotal (lookup only, no
   upload; the key is used only in that step). One `PROVIDER_SCAN ... verdict=PASS|HOLD|BLOCK`
   line; evidence `provider-scan.json` kept 30 days. Run name gains ` / scan`. Controllers can
   list `SMOKE_SCAN` entries (always advisory).
2. Needs you: a monthly watched-provider digest (UTC days 1 to 7 of each month, collapsed, no ids).
   HushTelegram, HushGram and HushFacebook become watch sources (`src/etc/extra-providers.json`).
   Nothing is adopted automatically.
3. Pin check probe (`pin-check.yml`, manual dispatch only, report-only): reads the store listing for targets with an exact build pin (Facebook and Instagram today), prints `PIN_STORE_OK`, `PIN_STORE_MISSING` or `PIN_STORE_UNKNOWN`, keeps evidence 30 days and never fails. Not scheduled yet (wrong call 115): the build reaches APKMirror through its browser helper, and plain reads were only tested against stubs. The controller dispatches it once after the merge; the weekly schedule follows with that evidence.
4. Patch age: `max_patch_age_days` is 180 for every target (preflight enforces it; Add app writes
   it). Status page and portal show an advisory warning past 180 days; builds are never blocked.
5. Council: the Sunday morning probe prints `MODEL_OK` or `MODEL_MISSING` per listed seat model.
   Seat changes remain pull requests.
6. Telegram survey (read-only): [TELEGRAM-SURVEY-2026-10-30.md](TELEGRAM-SURVEY-2026-10-30.md).
   Owner, 30 Oct evening: non-Hush for Telegram. rahul9999xda v1.17.0 is now primary on 13.1.1
   with 14 names; rushiranpise stays the fallback; HushTelegram goes on watch (its own fix for the
   sign-in error needs the owner's API ID at patch time). The packet's Telegram smoke build is the
   phone test.
7. Workflow YAML contract (`tests/workflow_yaml_contracts.py`) after wrong call 113.
8. Credits: ClamAV and VirusTotal in CREDITS.md.

Nothing is published or deleted by this packet.

## Wrong calls 112 to 117

Recorded in [KT-2026-10-28.md](KT-2026-10-28.md): 112 unescaped `%` in a pull request BODY; 113
an unparseable `manual-patch.yml` line from a lane, caught by parsing every workflow before the
commit; 114 Add app still writing a 60-day patch age that the new preflight rule refuses; 115 a
pin checker accepted on stub tests only, weekly and failing, although the build reaches APKMirror
through a browser helper (now a manual report-only probe); 116 a controller config whose
message string broke on a regex replacement, hidden by a rehearsal summary that showed only
exit codes (caught by reading the logs; compile gate and RESULT count added); 117 watch-only
provider rows leaking into selection checks once Telegram left Hush (caught by the full suite).

## Not built, not covered

- The new-provider ready-PR orchestration (discovery, scan smoke, green test build, ready pull
  request). Only the scan step exists.
- The pin checker and VirusTotal client were tested with stubs in the assistant sandbox (no
  internet there); the first real reads are the packet's scan smokes and the first scheduled runs.
- First runs to read: Council probe (Sunday 1 Nov), monthly digest (1 Nov), the post-merge pin
  check probe, retention preview (Monday 2 Nov). Retention apply needs the owner's token, from 3 Nov.

## How this was built

Four scoped lane agents (scan and credits; digest and watch sources; pin check, patch age and
Council lines; Telegram survey), integration and fixes by the assistant, the full local suite,
review agents on the final diff, the controller rehearsal matrix against the fake GitHub and a
launcher test with a fake home. Engineering: Anthropic Claude models, Google Cloud Shell and GitHub;
owner and architect: Govindarajulu K.
