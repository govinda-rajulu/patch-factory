# CCleaner (ccleaner)

Package: com.piriform.ccleaner
Source APK: https://www.apkmirror.com/uploads/?appcategory=ccleaner
Provider: mich111discord/MightyMichs-Patches (mich111discord, channel prerelease; bundle: the one .mpp asset of the newest release on that channel; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/mich111discord/MightyMichs-Patches)

## Patches
- Unlock Premium: added 2026-10-25 by owner request; opens CCleaner's paid features on the phone. New in bundle v1.12.0. The owner keeps it (W16l): CCleaner joins ADOPT.json paid_ok_targets and the owner accepts the account risk. The target is disabled since W16l (see Decision below).

Owner approved: Unlock Premium

Not built: the bundle's other 8 names for this package. The target is exclusive, so only the name above is applied (issue #252 lists all 9).

Removed (exclude list): Disable Telemetry. The W16l smoke (run 40216054895, CCleaner 26.08.0) failed on it:
"Failed to match the fingerprint: Fingerprint(definingClass=Lcom/avast/android/cleaner/tracking/TrackingManager;...)".
Owner, 25 Oct 2026: "its ok to remove that telemetry patch".

## Risks
- Unlock Premium is a client-side unlock of a paid feature; a CCleaner account can notice it. The owner accepts this.
- Unlock Premium is one day old (bundle v1.12.0, 25 Oct 2026); phone-test the first build.

## Decision
Owner request through "5. Add target" on 2026-10-25; merging the pull request is the approval.

Disabled 2026-10-25 (packet W16l): the second W16l smoke (run 40217711438) failed on Unlock Premium too:
"Failed to match the fingerprint: Fingerprint(definingClass=Lcom/avast/cleaner/billing/api/AclLicenseInfo;...)" on
CCleaner 26.08.0. The provider's own tracker has the same report for Disable Telemetry on 26.08.0 from a phone
(https://github.com/mich111discord/MightyMichs-Patches/issues/18, opened 25 Oct 2026 15:38 UTC), so bundle v1.12.0 does
not fit this CCleaner; the APK is not the cause. Nothing was ever published. Enable again ("5. Add target", action
enable) after a newer MightyMichs release fixes it; Unlock Premium stays chosen and owner approved.
