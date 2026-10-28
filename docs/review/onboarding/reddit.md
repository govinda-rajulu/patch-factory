# Reddit (reddit)

Package: com.reddit.frontpage
Source APK: APKPure, per `src/build/helper/apps.json` (the current source mapping is unchanged)

Provider: MorpheApp/morphe-patches (licence: the upstream repository LICENSE; bundle: the one `.mpp` asset of the newest stable release, v1.48.0, sha256 82bc696c94c26dbf75242b59980251315145457575b663200b981ca351e1c0f7, channel: latest). This is the official MorpheApp provider. Names below come from the owner's live list-patches run with morphe-desktop v1.19.0 on 23 Oct 2026, saved as `docs/review/PATCHES-reddit-morphe.txt`: 31 Reddit patches, compatible versions 2026.42.0, 2026.41.0, 2026.40.0, 2026.24.0, 2026.10.0.
Provider: jkennethcarino/adobo (fallback only; licence: the LICENSE file at https://github.com/jkennethcarino/adobo; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). Adobo remains the fallback for its supported Reddit 2026.41.0 build; the 2026.42.0 retirement in `src/etc/retired-builds.json` covers only builds published before 23 Oct 12:00Z (the deleted Adobo one), so a new Morphe 2026.42.0 build is not touched.

Provider: Alastor-Kaneki/Morphe-Patches (extra on the Morphe build since W16j; Adobo builds without it; licence: GPL-3.0-or-later, the LICENSE file (blob fa3ca584, read through the GitHub API on 25 Oct 2026) at https://github.com/Alastor-Kaneki/Morphe-Patches; bundle: the one `.mpp` asset of the newest release including pre-releases; channel: prerelease).

## Patches
- Download Reddit gallery originals: Alastor-Kaneki, owner took it in the Needs you review file (N-03fcf2, 2026-10-25); saves original-quality gallery images
- Reddit native post-menu originals (2026.41.0): Alastor-Kaneki, owner took it in the Needs you review file (N-03fcf2, 2026-10-25); saves original-quality gallery images; held since W16l (see Held patch W16l below)
- Hide related posts: owner took it in the Needs you review file, 2026-10-25 (N-2b1bc7)
- Hide search answers preview: owner took it in the Needs you review file, 2026-10-25 (N-8c47a1)
- Hide awards: owner took it in the Needs you review file, 2026-10-25 (N-b6b49b)
- Hide community highlights: owner took it in the Needs you review file, 2026-10-25 (N-66e165)
- Hide community menu badge: owner took it in the Needs you review file, 2026-10-25 (N-f57b96)
- Hide crosspost: owner took it in the Needs you review file, 2026-10-25 (N-8d4ee0)
- Hide post view counts: owner took it in the Needs you review file, 2026-10-25 (N-25c152)
- Hide prominent search bar: owner took it in the Needs you review file, 2026-10-25 (N-c89895)
- Hide share count: owner took it in the Needs you review file, 2026-10-25 (N-64e5f7)
- Hide upvote scores: owner took it in the Needs you review file, 2026-10-25 (N-057e70)
- Hide user community badges: owner took it in the Needs you review file, 2026-10-25 (N-5b9164)
- Hide user flairs: owner took it in the Needs you review file, 2026-10-25 (N-75061a)
- Hide Reddit search: owner took it in the Needs you review file, 2026-10-25 (N-612eb8)

Rule: the same as YouTube and YouTube Music on Morphe: the provider's default-on Reddit patches, minus the banned and branding ones. Reddit is an exclusive target, so the 27 names (26 before W16l) are listed in `src/patches/reddit-morphe/include-patches`:

- Hide ads
- Custom font
- Force system font
- Hide Ask button
- Hide communities shelf
- Copy text
- Keep feed position
- Show flairs in home feed
- Full width feed media
- Feed media max height
- Hide media viewer components
- Media viewer black background
- Media viewer fade
- Hide navigation buttons
- Customize post layout
- Disable screenshot popup
- Hide sidebar components
- Remove subreddit dialog
- Hide Trending shelves
- Remember collapsed comments
- Download location
- Start as guest
- Open links directly
- Open links externally
- Sanitize sharing links
- Redgifs audio

Left out: `Disable modern home` (default on, but Morphe says it works only up to Reddit 2026.24.0 and every build of 41 printed "does not work with Reddit 2026.25.0+"; W16c), `Spoof signature` (default on; BANNED rule `spoof signature`), `App icon` (default on; branding, left out as Custom branding is on YouTube), and the default-off ones (`Custom branding name for Reddit`, `Hide Reddit search` (taken since W16j, DECISIONS.json), and the five universal patches Clone app, Change installer source, Override certificate pinning, Spoof signature, Disable Play Store updates).

Adobo choices with a Morphe match: ad and telemetry removal -> Hide ads; screenshot banner -> Disable screenshot popup; guest mode -> Start as guest; external links -> Open links directly; share links -> Sanitize sharing links. Adobo-only choices (Firebase and WebView telemetry switches, feed refresh and swipe switches, comment indent colours, transparent navigation bar) stay available on the Adobo fallback.

## Risks

- Reddit 2026.42.0 needs Android 12 (SDK 32). The shelf ceiling is Android 10 (SDK 29), so the build steps down to 2026.41.0 (smoke run 40002216628 on 23 Oct: 27 of 27 patches applied on 41). Adobo is the configured provider fallback.
- A re-signed Reddit APK can change account or server-visible behaviour. The signature-spoof patch is excluded. The live list-patches output, patch compatibility, and applied names must be checked before publishing.
- Signature spoofing stays off by rule even though Morphe turns it on by default for Reddit; if sign-in or feeds fail on the phone, that is the first suspect (owner phone test).

## Decision

History, not current: owner brief, 23 Oct 2026. Superseded version part: since W16b Reddit is capped at 2026.41.0 (max_app_version in src/targets.json) because 42 needs Android 12, so do not build 42. The brief said: make official MorpheApp/morphe-patches primary for Reddit, keep Morphe 2026.42.0 (no owner downgrade to 41), and retain Adobo as fallback. The Morphe 42 path is experimental; verify it with morphe-desktop v1.19.0 and use the provider's 41 support only if 42 fails. The selection mapping is repository evidence only and remains subject to the live v1.48.0 list-patches check.

## Held patch (W16l, 25 Oct 2026)

`Reddit native post-menu originals (2026.41.0)` (Alastor-Kaneki extra bundle) fails on Reddit 2026.41.0:
"Failed to match the fingerprint: dev.alastorkaneki.morphe.patches.reddit.Reddit202641OverflowEventFingerprint"
(publish batch run 40212870923), so the Morphe build fell back to Adobo. The name moves to
`src/patches/reddit-alastor/exclude-patches`; Download Reddit gallery originals and the Morphe names build again.
The owner's take (N-03fcf2) stands: put it back when an Alastor build applies it on the Reddit we build.
- Owner, 28 Oct 2026 (W16w D6): adobo (fallback) Hide upvote scores, Hide post view counts, Hide share count, Hide related posts, Hide search answers preview and Hide crosspost dropped (always on); its cosmetic hides stay.
