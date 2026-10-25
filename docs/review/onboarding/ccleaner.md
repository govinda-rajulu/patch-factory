# CCleaner (ccleaner)

Package: com.piriform.ccleaner
Source APK: https://www.apkmirror.com/uploads/?appcategory=ccleaner
Provider: mich111discord/MightyMichs-Patches (mich111discord, channel prerelease; bundle: the one .mpp asset of the newest release on that channel; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/mich111discord/MightyMichs-Patches)

## Patches
- Disable Telemetry: added 2026-10-25 by owner request; stops CCleaner's usage tracking. New in bundle v1.12.0 (25 Oct 2026).
- Unlock Premium: added 2026-10-25 by owner request; opens CCleaner's paid features on the phone. New in bundle v1.12.0. The owner keeps it (W16l): CCleaner joins ADOPT.json paid_ok_targets and the owner accepts the account risk.

Owner approved: Unlock Premium

Not built: the bundle's other 7 names for this package. The target is exclusive, so only the two names above are applied (issue #252 lists all 9).

## Risks
- Unlock Premium is a client-side unlock of a paid feature; a CCleaner account can notice it. The owner accepts this.
- Both patches are one day old (bundle v1.12.0, 25 Oct 2026); the W16l smoke build is the first test.

## Decision
Owner request through "5. Add target" on 2026-10-25; merging the pull request is the approval.
