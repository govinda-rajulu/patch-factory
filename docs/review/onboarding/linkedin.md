# LinkedIn (linkedin)

Package: com.linkedin.android
Source APK: https://www.apkmirror.com/uploads/?appcategory=linkedin-linkedin
Provider: heyymichii/michii-patches (heyymichii, channel prerelease; bundle: the one .mpp asset of the newest release on that channel; licence: GPL-3.0, the LICENSE file at https://github.com/heyymichii/michii-patches/blob/dev/LICENSE, read 2026-10-08)

## Patches
- Material You: added 2026-10-20 by owner decision, 20 Oct 2026 (packet W15b; Selection watch #182 list; the adopt rule passes it too)
- Block tracking: added 2026-10-08 by owner request
- Disable double-tap like: added 2026-10-08 by owner request
- Download media: added 2026-10-08 by owner request
- Feed filters: added 2026-10-08 by owner request
- Hide Premium upsells: added 2026-10-08 by owner request
- Hide ads: added 2026-10-08 by owner request
- Hide promoted jobs: added 2026-10-08 by owner request
- Hide suggested posts: added 2026-10-08 by owner request
- Messaging: added 2026-10-08 by owner request
- Open links directly: added 2026-10-08 by owner request
- Sanitize share links: added 2026-10-08 by owner request

## Risks
- By their names the 12 patches (11 when this was written; Material You came later) hide content, block tracking or add downloads; none names a paid unlock ("Hide Premium upsells" hides the Premium adverts). The provider's own descriptions were not read for this record.
- Account risk from a re-signed LinkedIn app is unknown; test with a spare account first.

## Decision
Owner request through "5. Add target" on 2026-10-08; merging the pull request is the approval.

Disabled 2026-10-08 by owner request; releases stay published. Why: 1. Manual Patch run 37769337284 stopped with "needs SDK 32, device is 29". The provider lists only LinkedIn 4.1.1255.1 and 4.1.1258, and the version it picked needs Android 12L; the owner phone is Android 10. Enable again only with a provider that supports a LinkedIn version for SDK 29.

Enabled 2026-10-09 by owner request.
2026-10-09: enabled again with max_app_version 4.1.1255.1 (removed later: max_app_version is null today and the W16k picker chooses). The provider's newest listed version
(4.1.1258) needs Android 12L; APKMirror lists 4.1.1255.1 (the second listed version) as Android 10+
(owner, link in the session record). If the build still says "needs SDK", disable it again.
- Owner, 28 Oct 2026 (W16w D1, D2): channel latest (stable v1.1.1); the Michii Patches settings entry is missing on dev.3 with 4.1.1261 (upstream issue 12). Material You leaves the selection: stable v1.1.1 does not offer it (not a veto; it comes back when stable offers it). The old LinkedIn release goes (D3, cleanup --apps linkedin after the fresh build).
