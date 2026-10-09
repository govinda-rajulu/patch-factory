# Provider and patch review, 9 October 2026 (packet W10)

Owner ask (9 Oct): one Truecaller; for every app, the best provider overall (more providers,
more good patches), with the build and patch lists updated to match; check the newly added
providers and patches. This record holds the evidence and the decisions. Configured in W10:
only the decided items below. Nothing here is built or phone-tested.

## Evidence

| Source | What it is |
| --- | --- |
| Provider watch run 37970846200 | Dispatched on main `a2c2ab27`; 22 of 22 provider rows read. Patch names only, listed with `-x -u`. |
| Community index `src/community/bundles.json` | The repository's own copy of the Morphe community index, 210 bundles, committed 5 Oct (`7b6504e`). The official MorpheApp bundle is not in it. |
| W9 RESULT `providers.tsv` | The five newest releases of all 14 provider repositories, read 9 Oct. |

Counts below are package-specific patches. Universal patches (no package in their
declaration) are left out of the index counts and, until W10, out of the watch.

## Finding: the watch hid universal patches (#102)

With `-u` the patcher omits universal patches. 15 names in our include lists looked
"gone" (Reddit 7, MX Player 4, ES File 3, Photos 1) while those apps built on 6 and 7 Oct;
the index shows every one of them with no package key, so they are universal. W10 drops `-u`
from the watch. All 22 baselines are re-seeded from the first run without it (W11), so the
next comparison is complete.

## Decided: one Truecaller

`truecaller-combo` (tag `tc-combo`) stays: it already uses every Truecaller provider in the
index (bufferk 7, paresh 10, binarymend 2 patches, all 19 included). The old standalone
`truecaller-v26.10.6` release (same app version) is retired: `cleanup.py` now removes a
release whose app prefix no target builds, and its protection is gone from `RECOVERY.md`
and `docs/council/OWNER.md`.

## Every app

| App | Provider(s) now | Offered / used | Other providers in the index | Call |
| --- | --- | --- | --- | --- |
| youtube | MorpheApp/morphe-patches | 96 / 77 | none | Keep. Provider defaults apply (not exclusive): the 15 new names below arrive by themselves unless excluded. |
| ytmusic | MorpheApp/morphe-patches | 48 / 39 | none | Keep. Only provider; defaults apply. Baseline seeded in W11. |
| adguard | rushiranpise/morphe-patches, hoo-dles/morphe-patches | 2 / 2 | none | Keep. |
| photos | rushiranpise/morphe-patches | 7 / 5 | Akash-Sriram/morphe-google-photos 14 (7.95.0.989626323); RookieEnough/De-Vanced 4 (7.80.0.929302933, 7.92.0.977185651) | Keep for now. Akash-Sriram adds 10 names, but they include "Change to official package name" and "Disable Play Store updates". Owner call. |
| truecaller-combo | bufferk/morphe-patches, Paresh-Maheshwari/paresh-patches, binarymend/morphe-patches | 19 / 19 | none | Keep (decided). Uses all three providers. |
| primevideo | hoo-dles/morphe-patches | 3 / 3 | none | Keep. |
| esfile | BlazeFTL/FTL-Patches | 1 / 1 | rushiranpise/morphe-patches 1 (4.4.3.7) | Keep. |
| facebook | RookieEnough/De-Vanced | 15 / 3 | andrewliang25/morphe-patches 18 (577.0.0.50.72); SapitoSucio/FroggoMorphePatches 11 (573.0.0.37.74) | Owner call: andrewliang25 has 18 Facebook patches (ads, sponsored, downloads) for 577; we build 580 with De-Vanced and use 3 of its 15. |
| instagram | crimera/piko, brosssh/morphe-patches | 82 / 50 | FoxxoOwO/foxxo-patches 11 (any); dawidd612/dudeks-morphe-patches 1 (439.0.0.37.89); giaaaacomo/nifty-patches-selection 1 (426.0.0.37.68) | Keep piko + brosssh. FoxxoOwO adds signature-check bypass and a debug bridge: no. |
| reddit | jkennethcarino/adobo | 24 / 12 | Santodan/santodan-patches 3 (2026.37.0); Mubelotix/my-morphe-patches 1 (2025.03.1) | Keep. Santodan: 3 experimental names for an older version. |
| hotstar | durgesh0505/chiggi_morphe_patches | 14 / 6 | Paresh-Maheshwari/paresh-patches 7 (26.04.27.10) | Keep. paresh adds only "Bypass signature check": no. |
| edge | quantavil/edge-morphe-patches | 5 / 4 | none | Keep. |
| mxplayer | BlazeFTL/FTL-Patches, Paresh-Maheshwari/paresh-patches | 5 / 3 | mich111discord/MightyMichs-Patches 1 (2.2.4) | Keep. |
| telegram | rushiranpise/morphe-patches | 14 / 13 | newuser7171/telegram-morphe-patches- 15 (12.10.4); ch3thanhs/stylus 1 (12.10.6); mich111discord/MightyMichs-Patches 1 (12.10.1) | Keep. newuser7171 adds one name (translation) on 12.10.4: not worth a switch. |
| keymapper | kiraio-moe/Lain-Patches | 1 / 1 | none | Keep. |
| amazonmusic | RookieEnough/De-Vanced | 5 / 4 | none | Keep. Baseline seeded in W11. |
| linkedin | heyymichii/michii-patches | 11 / 11 | none | Keep. Not in the 5 Oct index yet; baseline seeded in W11. |

"Offered" is what the watch listed (without universal patches); "used" is included, or applied
by default for YouTube and YouTube Music.

## New and removed names since the baselines


| App / provider | Name | Now |
| --- | --- | --- |
| youtube / morphe | AI channel filter | applied by default |
| youtube / morphe | Channel search | applied by default |
| youtube / morphe | Channel whitelist | applied by default |
| youtube / morphe | Copy text | applied by default |
| youtube / morphe | DeArrow | applied by default |
| youtube / morphe | Disable auto feed refresh | applied by default |
| youtube / morphe | Disable continue watching prompt | applied by default |
| youtube / morphe | Force fullscreen landscape | applied by default |
| youtube / morphe | Hide status bar | applied by default |
| youtube / morphe | Picture-in-picture button | applied by default |
| youtube / morphe | Playback buffer | applied by default |
| youtube / morphe | Player icon style | applied by default |
| youtube / morphe | Remember live stream playback position | excluded |
| youtube / morphe | Restore original titles | applied by default |
| youtube / morphe | Shorts icon style | applied by default |
| youtube / morphe | Skip silence | applied by default |
| youtube / morphe | Alternative thumbnails | removed upstream |
| youtube / morphe | Remember livestream playback position | removed upstream |
| photos / rushiranpise | Custom branding | not used (exclusive target) |
| facebook / derevanced | AMOLED dark theme | not used (exclusive target) |
| facebook / derevanced | Clean Home feed | not used (exclusive target) |
| facebook / derevanced | De-Vanced Settings | not used (exclusive target) |
| facebook / derevanced | Disable all ads | already included |
| facebook / derevanced | Disable analytics and telemetry | already included |
| facebook / derevanced | Disable auto refresh | not used (exclusive target) |
| facebook / derevanced | Download Media | not used (exclusive target) |
| facebook / derevanced | Facebook signature compatibility | not used (exclusive target) |
| facebook / derevanced | Material You theme | not used (exclusive target) |
| facebook / derevanced | Media quality controls | not used (exclusive target) |
| facebook / derevanced | Messenger install compatibility | already included |
| facebook / derevanced | Open Marketplace on launch | not used (exclusive target) |
| facebook / derevanced | Optimize Facebook | not used (exclusive target) |
| facebook / derevanced | Picture-in-picture | not used (exclusive target) |
| facebook / derevanced | Reels 2x speed | not used (exclusive target) |
| facebook / derevanced | Hide 'Sponsored Stories' | removed upstream |
| facebook / derevanced | Hide story ads | removed upstream |
| instagram / piko | Custom font | not used (exclusive target) |
| instagram / piko | Customize navigation bar | not used (exclusive target) |
| instagram / piko | Focus Lock | not used (exclusive target) |
| instagram / piko | Hide Reels follow button | not used (exclusive target) |
| instagram / piko | Hide save buttons | not used (exclusive target) |
| instagram / piko | Hide share button | not used (exclusive target) |
| instagram / piko | Inbox lock | not used (exclusive target) |
| instagram / piko | Save Instants | not used (exclusive target) |
| instagram / piko | Hide navigation buttons | removed upstream |
| reddit / adobo | Hide crosspost | not used (exclusive target) |

YouTube's renamed `Remember live stream playback position` is already excluded under its new
name; `Alternative thumbnails` became `DeArrow` (kept, `YTMUSIC-2026-10-06.md`).

## Open for the owner (W11)

1. Facebook: switch to andrewliang25 (577, 18 patches) or stay on De-Vanced (580) and pick from
 its 12 unused names. A provider change needs its onboarding record and the onboarding review.
2. YouTube: keep the 15 new default names, or name any to exclude.
3. Optional names for exclusive apps (Instagram 8 new, Facebook 12 unused, Photos 1, Reddit 1):
 none are added without the owner naming them.

## Correction, 10 October 2026 (packet W11)

The "Other providers" column above missed every bundle that names its app once in
`targetApps` instead of on each patch. That hid two candidates: `SysAdminDoc/HushFacebook`
(Facebook; 60 patches in the 5 Oct index, 85 in Explore run 37976702866, issue #173) and
`SysAdminDoc/HushGram` (Instagram; 78 in Explore, issue #171). HushTelegram targets
`org.telegram.messenger.web`, not our package. No other row changes.

Owner calls since (10 Oct):
- Facebook moves to HushFacebook 581.0.0.45.58 with 82 of its 85 patches, the three
 server-visible ones included for testing. Record: `onboarding/facebook.md`.
- Instagram stays on piko + brosssh. HushGram lists `Change version code` (BANNED) and
 `Spoof location`, and overlaps piko.
- YouTube keeps its new default names.
- Build rule for every app (design for W12): the version where most of the chosen patches
 apply wins; the newest breaks a tie; a failed build steps down, then falls back to the next
 provider. A patch lost on the way is named in the log.
