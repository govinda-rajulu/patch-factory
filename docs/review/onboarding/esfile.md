# ES File Explorer (esfile)

Package: com.estrongs.android.pop
Source APK: APKMirror, per the target's `source` (unchanged).
Provider: BlazeFTL/FTL-Patches (ftl, primary; channel prerelease; licence: the LICENSE file at https://github.com/BlazeFTL/FTL-Patches, as in docs/review/onboarding/mxplayer.md).
Provider: rushiranpise/morphe-patches (extra; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/rushiranpise/morphe-patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). The community index lists its ES File patch for 4.4.3.7, the version ftl builds.
Provider: rushiranpise/morphe-patches as `rushiranpise-fallback` (fallback only, built alone after ftl fails, `overrides.extra_bundles: []`; licence: GPL-3.0, the LICENSE file at https://github.com/rushiranpise/morphe-patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). The immutable v1.23.1 patch index lists Unlock VIP Lifetime for ES File Explorer 4.4.3.7. Owner, 28 Oct 2026: add it as the ES File fallback (W16w decision D15).

## Patches

- Fallback `rushiranpise-fallback` (`src/patches/esfile-rushiranpise-fallback/include-patches`): Unlock VIP Lifetime only, the same name as the extra below, built alone (`overrides.extra_bundles: []`), offered for 4.4.3.7 (owner, 28 Oct 2026, D15).

The extra (`rushiranpise`):
Exclusive target; the name is in `src/patches/esfile-rushiranpise/include-patches`:

- Unlock VIP Lifetime: index description "Unlocks VIP lifetime features in ES File Explorer Phone and TV", default on. ES File works without an account and is in the owner's paid_ok_targets (owner, 20 Oct 2026); asked for again on 25 Oct 2026 ("why was that not included"). It had been open since 20 Oct as "ES File plus rushiranpise Unlock VIP Lifetime" (OPEN-WORK); W16h configures it.

ftl keeps its four names (ES File Explorer Ui Cleanup, Remove Ads, Remove Analytics, Remove Analytics New); no name is in both bundles.

## Risks

- The card said "VIP unlocked" before any VIP patch was built; W16h fixes the note.
- VIP is a client-side unlock on an offline app; nothing server-side is spoofed.

## Decision

Owner, 25 Oct 2026: include it.
