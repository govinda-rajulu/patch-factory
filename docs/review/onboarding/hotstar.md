# JioHotstar (hotstar)

Package: in.startv.hotstar
Source APK: per src/build/helper/apps.json
Provider: durgesh0505/chiggi_morphe_patches (chiggi, channel latest; bundle: the one .mpp asset of the newest release on that channel; licence: the LICENSE file at https://github.com/durgesh0505/chiggi_morphe_patches)

## Patches
- Enable all codecs: added 2026-10-22 by the Selection watch adopt rule (src/patches/ADOPT.json): no BANNED, CONFIRM, hold or paid match in its name or index description

## Risks
- See the agent review on the pull request that adds this record.

## Decision
Selection watch adopt rule (src/patches/ADOPT.json) on 2026-10-22; 11. Rule merge merges the pull request only when every check, the Onboarding review and every test build are green.
2026-10-24 (packet W16g): owner excludes chiggi "Premium unlock" (a paid-tier UI unlock on an account app; Hotstar checks subscriptions on its servers). Listed in `src/patches/hotstar-chiggi/exclude-patches` so the Selection watch never adopts it.
