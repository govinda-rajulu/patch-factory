# Packet W17a: W17 phase 0 (31 Oct 2026)

Base: main `b1c34e50` (W16z, #285). Owner brief: twelve items, approved 31 Oct ("go ahead").
Scheduled runs were left alone so they prove themselves (Check new patch tonight, Council probe
and monthly digest Sunday 1 Nov, retention preview Monday 2 Nov; retention apply from 3 Nov
with the owner's token).

## What changed

| # | Item | Result |
| --- | --- | --- |
| 1 | Pin check | Weekly, Wednesday 09:07 IST (`37 3 * * 3`), still report-only. |
| 2 | Artifact names | `build-evidence-<t>-<run>-<attempt>` and `provider-scan-<t>-<run>-<attempt>`; the controller downloads `provider-scan-<t>-<run>-*`. |
| 3 | Signature files | `is_signature_file()` follows apksig `V1SchemeSigner.isJarEntryDigestNeededInManifest`: case-sensitive `META-INF/` direct child; lowercased name `manifest.mf`, `*.sf/.rsa/.dsa/.ec` (an empty base such as `META-INF/.SF` counts) or `sig-*`. `meta-inf/x.sf` is an ordinary entry. |
| 4 | History scan | [HISTORY-SCAN.md](HISTORY-SCAN.md): 157 flagged rows, 0 real secrets or personal data. |
| 5 | Fallback attempts | Each build writes a bounded attempt table (candidate, result, reason; at most 1 + `PF_MAX_FALLBACKS` rows) to its job summary. Tests were written first. |
| 6 | Agent trials | [AGENT-TRIALS.md](AGENT-TRIALS.md): 49 of 56. Council seats not run (needs a workflow). |
| 7 | Records | This file. |
| 8 | 5S | 8 closed records moved to `history/` with links rewritten; 66 broken relative links fixed; history index complete; STATE 25 Oct sections moved verbatim to `knowledge/archive/STATE-2026-10-25.md`. |
| 9 | Content | 10 claims in living docs fixed after checking each against the code (cleanup covers `dev/`; dropped-patch limit `max(3, total // 4)`; MicroG ticked by default; Council scope and keys; receipts; signing-check timing; CODEOWNERS wording; Facebook needs Android 11). |
| 10 | Portal | Dark headline contrast 1.03:1 to 7.55:1; 375 px MicroG picker overflow fixed; 4 px spacing grid; sentence-case eyebrow. 12 logos and `microg.png` recompressed; six logos keep their bytes (adguard, mxplayer and telegram fell below 45 dB at 40 px; edge, hotstar and instagram would not shrink); Latin Manrope subset with the full font as `unicode-range` fallback. First load 433,819 to 320,021 bytes. |
| 11 | Prose | Humanizer pass on 8 living docs; one dropped fact restored (nine seats, eight providers); dashes removed from AGENTS.md and PROVIDERS.md. |
| 12 | Sustain | `knowledge/style/` (WRITING.md, UI.md, credits); Validate runs `doclinks.py --check` and `page_weight.py --check` (budget 350,000), which fail the run, and `prose_lint.py`, which only warns. |
| + | Code sweep | Five uncalled helpers removed; restore record in [history/REMOVED-2026-10.md](../history/REMOVED-2026-10.md). |

## W16z results (read 31 Oct)

- Merged as #285 (`b1c34e50`, tree `85a17889`), RESULT OK.
- Pin check run 41194578599 on `b1c34e50`: PIN_STORE_OK for facebook, facebook:derevanced and instagram.
- Repo setup: success. Feature requests #286 (W17 owner console) and #287 (Android Auto) filed with labels.
- Reddit #280 stays red on purpose: Morphe's bundle targets 2026.40.0, below the 2026.41.0 on the
  shelf, so the release contract refuses (PUBLISH_REFUSED). The guard is right; it clears when
  Morphe catches up.

## Car and Android Auto (on hold, owner will test)

- Head unit: Megatronix, Android 13, platform AB8163 (TS9 MAX), 4 GB RAM, 32 GB storage, 1280x720;
  ZLink installed; Wi-Fi and Bluetooth connected.
- MicroG RE no-icon arm64-v8a installed on the head unit without error. Our YT Music install failed
  there; the error text is not recorded yet.
- Phone: Micromax In Note 1, Android 10, not rooted.
- Morphe's own YT Music patch "Android Auto" ("Bypasses certificate checks and restores YouTube
  Music Home recommendations, Library collections, and podcasts in Android Auto") has been in
  `src/patches/ytmusic-morphe/exclude-patches` since 6 Oct. That came from an assistant rule about
  certificate-class patches (docs/review/YTMUSIC-2026-10-06.md), not from an owner decision.
- Installer options: KingInstaller (GPLv3, installs as the Play Store) is the candidate;
  AAEnabler (new, no licence, asks for an email and device registration) is skipped.
- Next, when the owner reports: the install error, then a ZLink Android Auto test. Options: the
  Morphe Android Auto patch plus a KingInstaller install on the phone, or a direct head-unit install.

## Wrong calls

- 125: I guessed the head unit was 32-bit only; arm64 MicroG installed fine.
- 126: the W16z #154 record ([w16z/SAFELINK-154.md](../w16z/SAFELINK-154.md)) did not note that
  `runLink` checks status links with the generic same-repo rule, not the run pattern. Low risk:
  those links are runs, pull requests and workflow pages of this repository. Found by trial T2.

- 127: while repairing links I called `scenario_tools_contracts.py` "never committed" and rewrote
  its line in a dated record. It is tracked at `w15g-close/scenarios/tests/`; the original link was
  right. Found by the records reviewer; the line is restored byte for byte.

## Review round (31 Oct)

Three laser-scoped reviewers (code and workflows; portal; records), every finding re-rated.
Fixed: the attempt summary is best-effort (an unwritable summary file could have failed a good
build); `doclinks.py` treats absolute and escaping links as broken; `page_weight.py` refuses a font
outside `docs/` and closes its files; two sentences the contracts pin were restored in RECOVERY.md
and SECURITY.md (the prose pass missed them); wrong call 127; the archived STATE block and the
moved OPEN-WORK heading are byte for byte again; the archive README gets a new line instead of an
edited one. Kept: `↗` in "View source" is in neither Manrope file, so it was already drawn by a
system font before W17a; recompressed logos move alpha by at most 8 of 255; links with a title
(`[a](b "t")`) are not parsed, and the repo has none; the scan's 567 commits are from the 54-ref
bundle (a plain clone shows fewer); the credit line with Google Cloud Shell and GitHub is the
owner's rule of 27 Oct.

## W16w 64 or 65

Git settles it. W16w fix 2 (`5772ee0`) changed 64 link destinations in
`history/OPEN-WORK-ARCHIVE-2026-10.md`, and all 64 were broken before it. W16y-a (`f4f2e6e`)
changed one more later, when its target moved. The record's "64 relative links ... broken" is
right; the 65 in the W16w fresh review cannot be reproduced from git. Dated records keep
their words.

## Owner request, 31 Oct evening: Remote for Android TV

Through **5. Add target** (owner run): id `remoteatv`, package `tech.simha.androidtvremote`,
provider `XBadFellaX/BadFella-Patches`, patch `Remote ATV ad-free` (6.1.0, build 45), source
`apkmirror-apk`. A local dry run of the same tool on `b1c34e50` ended APP_CHANGE OK. Notes: the
provider repository was created 30 Oct (one maintainer); the default channel is prerelease.
A logo comes in a later packet.

Credit: Anthropic Claude models, Google Cloud Shell and GitHub, for Govindarajulu K.
