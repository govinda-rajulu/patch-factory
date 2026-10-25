# Google Photos (photos)

Package: com.google.android.apps.photos (installed as app.morphe.android.apps.photos, beside the system Photos)
Source APK: the target's current source mapping (unchanged).
Provider: rushiranpise/morphe-patches (primary; licence: GPL-3.0, the LICENSE file (blob f288702d) at https://github.com/rushiranpise/morphe-patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). Names: src/patches/gg-photos/include-patches.
Provider: Akash-Sriram/morphe-google-photos (extra since W16j; licence: none declared, the GitHub licence API returns null for the repository on 25 Oct 2026, so its terms are unknown; the owner took it anyway (N-1a216b) and already gave it AMOLED dark theme on 20 Oct (owner E1, ADOPT.json reserved); bundle: the one `.mpp` asset of the newest release including pre-releases; channel: prerelease).

## Patches
- AMOLED dark theme: Akash-Sriram, owner took the provider except Custom Morphe branding and Official package name (N-1a216b, 2026-10-25)
- DCIM & backup control: Akash-Sriram, owner took the provider except Custom Morphe branding and Official package name (N-1a216b, 2026-10-25)
- Flag manager & Toolkit: Akash-Sriram, owner took the provider except Custom Morphe branding and Official package name (N-1a216b, 2026-10-25)
- Media engine & AI fixes: Akash-Sriram, owner took the provider except Custom Morphe branding and Official package name (N-1a216b, 2026-10-25)
- GmsCore support and Spoof features: Akash-Sriram offers them too; rushiranpise already ships both (one bundle per name), so they are excluded for Akash.

## Risks
- No licence is declared for Akash-Sriram/morphe-google-photos. If the author objects, drop the extra.
- DCIM & backup control overlaps rushiranpise's Enable DCIM folders backup control if both are chosen; the smoke build shows whether both apply.

## Decision
Owner, 25 Oct 2026 (packet W16j): take Akash-Sriram except Custom Morphe branding and Official package name; AMOLED dark theme stays ("what if someone wants it").
