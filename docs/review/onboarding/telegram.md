# Telegram (telegram)

Package: org.telegram.messenger
Source APK: APKMirror, per the target's `source` (unchanged).

**Current (W16h, 25 Oct 2026):** rushiranpise/morphe-patches is primary on 12.10.1 with 13 names in `src/patches/telegram-rushiranpise/include-patches` (Bypass channel restrictions and Unlock Premium among them); its exclusions are in `src/patches/telegram-rushiranpise/exclude-patches`. newuser7171 below is the fallback. The W16g sections below are history.
Provider: rushiranpise/morphe-patches (primary since W16h; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/rushiranpise/morphe-patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease).
Provider: newuser7171/telegram-morphe-patches- (fallback since W16h; licence: GPL-3.0, the LICENSE file at https://github.com/newuser7171/telegram-morphe-patches-; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). Names below come from the live list-patches run in Explore issue #235 (24 Oct 2026, 19 patches) and the community index (compatible 12.10.4).

Owner decision, 24 Oct 2026 (packet W16g): newest version and most patches wins. newuser7171 targets 12.10.4 with every rushiranpise Telegram patch plus `Bypass translation restrictions`; rushiranpise (12.10.1) stays as the fallback. Owner keeps Remove ads, Bypass translation restrictions, Download speed boost, Hide typing indicator and Unlock Premium.

Owner approved: Unlock Premium

## Patches

Exclusive target; the newuser7171 fallback's names are in `src/patches/telegram-newuser7171/include-patches` (W16h removed Bypass channel restrictions from this list):

- Anti-delete messages: default on; same as the rushiranpise build.
- Anti-disappearing media: default on; same as the rushiranpise build.
- Anti-screenshot notification: default on; same as the rushiranpise build.
- Bypass content restrictions: default on; same as the rushiranpise build.
- Bypass translation restrictions: default on; new on this provider, owner asked for it.
- Disable auto-update: default on; stops the in-app updater replacing the patched app.
- Disable channel switching: default on; same as the rushiranpise build.
- Download speed boost: default on; owner keeps it.
- Hide typing indicator: default on; owner keeps it.
- Remove ads: default on; ad removal.
- Unlock Premium: default on; owner approved (tested a premium patch for this app before).
- Use normal paste: default on; same as the rushiranpise build.
- Voice to music: default on; same as the rushiranpise build.

Left out of the fallback (its exclude-patches): `Bypass channel restrictions` (W16i: fails on 12.10.4, run 40108956377; excluded so the Selection rule cannot add it back, as PR #243 tried), `Bypass integrity check` (CONFIRM rule, held as before), `Fix Firebase after re-signing`, `Provide Original app certificate`, `Spoof app signature`, `Spoof install source` (all BANNED re-signing rules).

## Risks

- Telegram accounts are server-side; Premium unlock is client-side and may be ignored or noticed. The owner accepts this (tested before).
- Re-signed build: Telegram may refuse some features that check the signature; the re-signing patches stay off by rule.

## W16h (25 Oct 2026): rushiranpise primary again

The W16g smoke (run 40108956377) failed on 12.10.4: "Bypass channel restrictions" did not match
(`PhotoViewer` fingerprint). rushiranpise (12.10.1, 13 patches including Bypass channel restrictions
and Unlock Premium) is primary again. newuser7171 is the fallback without Bypass channel restrictions
(13 names: it adds Bypass translation restrictions).
