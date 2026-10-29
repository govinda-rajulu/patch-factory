# MX Player Pro (mxplayer)

Package: com.mxtech.videoplayer.pro
Source APK: per src/build/helper/apps.json
Provider: BlazeFTL/FTL-Patches (ftl, channel prerelease; bundle: the one .mpp asset of the newest release on that channel; licence: the LICENSE file at https://github.com/BlazeFTL/FTL-Patches); gitlab:82031658 (paresh, channel prerelease; bundle: the one .mpp asset of the newest release on that channel; licence: the LICENSE file at GitLab project 82031658)
Provider: mich111discord/MightyMichs-Patches (mich111discord, fallback only, built alone after ftl fails, `overrides.extra_bundles: []`; licence: GPL-3.0, the LICENSE file at https://github.com/mich111discord/MightyMichs-Patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). Release v1.12.0 lists MX Player Pro 1.93.4, the target ceiling. Owner, 28 Oct 2026: add it as the MX Player fallback (W16w decision D14).

## Patches
- Unlock MX Player Pro (mich111discord): the only package-specific patch of v1.12.0 for 1.93.4; the provider marks it experimental; fallback only (owner, 28 Oct 2026, D14)
- Hide top tiles: owner took it in the Needs you review file, 2026-10-25 (N-939b7b)
- Skip Splash Screen: added 2026-10-22 by the Selection watch adopt rule (src/patches/ADOPT.json): no BANNED, CONFIRM, hold or paid match in its name or index description

## Risks
- See the agent review on the pull request that adds this record.

## Decision
Selection watch adopt rule (src/patches/ADOPT.json) on 2026-10-22; 11. Rule merge merges the pull request only when every check, the Onboarding review and every test build are green.

W16x (29 Oct 2026): the first MightyMichs smoke (v1.12.0, MX Player 1.93.4, its only version) downloaded and verified the APK, then "Unlock MX Player Pro" failed its fingerprint (Lxo;.j1()Z). The fallback cannot build today; ftl stays primary. Recheck on the next MightyMichs release.
