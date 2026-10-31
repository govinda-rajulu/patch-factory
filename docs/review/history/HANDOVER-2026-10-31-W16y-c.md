# Handover, 31 October 2026: W16y-b result and packet W16y-c

Start a new chat from the PATCH-FACTORY-BUILDS skill, then `knowledge/STATE.md`, then this file,
then [OPEN-WORK.md](../OPEN-WORK.md).

## Where things stand

- W16y-b merged as #281 (`27adc7b4`, tree `c761f1c6`), RESULT OK, after a first run stopped at
  push on a GitHub HTTP 500. Smokes: Telegram rahul9999xda 14 of 14 on 13.1.1, Facebook 102 of
  102, Prime Video 3 of 3, Amazon Music 5 of 5, ES File fallback 1 of 1.
- First live provider scans: ES File PASS; Amazon Music HOLD on 22 "hosts" that were code names
  (wrong call 118). ClamAV clean on both; VirusTotal had seen neither file (normal for new builds).
- First live pin check: Facebook and Instagram `PIN_STORE_UNKNOWN listing_unreadable`; plain
  HTTPS reads are refused, as feared in wrong call 115.
- Owner phone test, 31 Oct: the Telegram smoke build installs and signs in.
- Cleanup preview after the merge: 0 releases, 12 Pages records (token `d692c7fdca756e47`, not
  applied; retention apply starts 3 Nov with the owner's token).

## What W16y-c changes

1. Telegram is published from rahul9999xda after the merge (one publishing Batch Patch).
2. Provider scan: hosts come from http(s):// URLs, or bare names with a real public top-level
   domain and not a code root (`com.`, `androidx.`, `R.`...). Code file names, package names,
   resource references and obfuscated names are ignored. A bare host with an uncommon ending
   is missed unless it appears in a URL (recorded limit).
3. Pin check probe: `src/etc/pin_fetch.sh` sources the build's own `utils.sh` (setup skipped
   with `PF_UTILS_NO_SETUP=1`), starts the store helper lazily, and runs `get_apk` with
   `PF_PIN_CHECK_ONLY=1`, which returns after the variant row with the pinned version code is
   found and before any download page. Normal builds are unchanged when those variables are
   unset. Candidate `overrides.version_code` pins are included. OK needs the wrapper's exit 0
   and a captured release page showing the pin; exit 2 is MISSING; any other failure is
   UNKNOWN (review finding: a failed lookup could have read as OK). Manual and report-only; the
   controller dispatches it once after the merge.
4. Packet controller: transient push failures are retried twice (30 s, 90 s); rejections stop
   at once; before each retry the remote branch is read and an already-pushed head counts as OK.
5. One step less for the owner: the controller saves each scan smoke's `provider-scan.json`
   next to the smoke logs, and the owner probe (pf-p2) reads the newest Pin store check,
   Retention preview and Batch Patch runs every time (details, evidence artifacts within the
   probe's size budget, never test APKs; logs for the first two). The next combo's probe zip
   therefore carries the pin probe result, the retention token and the Telegram publish run.
6. Push retry never retries a client error (HTTP 400/401/403/404/413), only server or network
   failures.
7. Records: wrong calls 118 and 119, lessons, OPEN-WORK, STATE, this file.

## Not covered

- The pin probe through the store helper is proven only offline (no internet in the assistant
  sandbox); the post-merge run is its first live read.
- New-provider ready-PR orchestration, Council model swaps (read the Sunday 1 Nov probe first),
  W15g signing split, retention apply (owner, from 3 Nov), combined Facebook fallbacks: later
  packets.

## How this was built

Scoped lane agents (pin reader; push retry with rehearsals), the scan fix and records by the
assistant, the full local suite, fresh review agents, rehearsal matrix and a launcher test.
Engineering: Anthropic Claude models, Google Cloud Shell and GitHub; owner and architect:
Govindarajulu K.
