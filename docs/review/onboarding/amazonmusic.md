# Amazon Music (amazonmusic)

Package: com.amazon.mp3
Source APK: https://www.apkmirror.com/uploads/?appcategory=amazon-music-discover-songs
Provider: RookieEnough/De-Vanced (rookieenough, channel prerelease; bundle: the one .mpp asset of the newest release on that channel; licence: GPL-3.0, the LICENSE file at https://github.com/RookieEnough/De-Vanced/blob/main/LICENSE, read 2026-10-08)

## Patches
- Skip ads: added 2026-10-08 by owner request
- Unlimited track skipping: added 2026-10-08 by owner request
- Prevent log upload: added 2026-10-08 by owner request
- Unlock Unlimited: added 2026-10-08 by owner request

## Risks
- "Unlock Unlimited" and "Unlimited track skipping" are paid-tier features that Amazon can check on its servers. The agent review on pull request #160 blocks them under rule 1.
- Excluded: "Rename shared permissions" (the provider says it can break features). Add it only if the build will not install.

## Decision
Owner request through "5. Add target" on 2026-10-08.
2026-10-08: the owner keeps "Unlock Unlimited" and "Unlimited track skipping" to test them with a throwaway Amazon account only, and merges over the review's block. If that account is warned or limited, remove both names with "5. Add target" before anyone signs in with a real account.
2026-10-09: max_app_version 26.34.0. The provider's patches say "Any" version, so the build had no
version to pick (Manual Patch run 37769298585: "no max_app_version to fall back on"). 26.34.0 is
APKMirror's newest, universal, Android 10+ (read 2026-10-09). Raise it by hand until the build
follows the store's newest Android 10 version itself (OPEN-WORK).
2026-10-10 (packet W13): the throwaway account was banned. As decided on 2026-10-08, "Unlock Unlimited" and "Unlimited track skipping" are removed before anyone signs in with a real account. Skip ads and Prevent log upload stay. The cause (patch or new account) is unknown; do not move the test to the main account without a fresh decision.
