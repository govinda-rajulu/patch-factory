# Telegram (telegram)

Package: org.telegram.messenger
Source APK: APKMirror, per the target's `source` (unchanged).
Provider: newuser7171/telegram-morphe-patches- (licence: the upstream repository LICENSE file; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). Names below come from the live list-patches run in Explore issue #235 (24 Oct 2026, 19 patches) and the community index (compatible 12.10.4).

Owner decision, 24 Oct 2026 (packet W16g): newest version and most patches wins. newuser7171 targets 12.10.4 with every rushiranpise Telegram patch plus `Bypass translation restrictions`; rushiranpise (12.10.1) stays as the fallback. Owner keeps Remove ads, Bypass translation restrictions, Download speed boost, Hide typing indicator and Unlock Premium.

Owner approved: Unlock Premium

## Patches

Exclusive target; names in `src/patches/telegram-newuser7171/include-patches`:

- Anti-delete messages: default on; same as the rushiranpise build.
- Anti-disappearing media: default on; same as the rushiranpise build.
- Anti-screenshot notification: default on; same as the rushiranpise build.
- Bypass channel restrictions: default on; same as the rushiranpise build.
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

Left out (exclude-patches): `Bypass integrity check` (CONFIRM rule, held as before), `Fix Firebase after re-signing`, `Provide Original app certificate`, `Spoof app signature`, `Spoof install source` (all BANNED re-signing rules).

## Risks

- Telegram accounts are server-side; Premium unlock is client-side and may be ignored or noticed. The owner accepts this (tested before).
- Re-signed build: Telegram may refuse some features that check the signature; the re-signing patches stay off by rule.
