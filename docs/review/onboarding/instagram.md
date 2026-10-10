# Instagram (instagram)

Package: com.instagram.android
Source APK: APKPure, the newest version the provider supports (source "apkpure" in src/targets.json)
Provider: crimera/piko (primary, channel prerelease) with brosssh/morphe-patches (extra bundle, channel prerelease); recorded here from packet W13 on.
Provider: SysAdminDoc/HushGram (fallback only; licence: GPL-3.0, checked against the GitHub licence API by the W13 controller before anything is pushed; bundle: the one .mpp asset of the newest release including pre-releases; channel: prerelease). Same author as SysAdminDoc/HushFacebook, the Facebook provider.

## Patches
HushGram builds only when a piko build fails (packet W13 provider fallback); piko stays primary. Names as the community index lists them (src/community/bundles.json, 5 Oct 2026 snapshot, 48 HushGram patches), plus three named in HushGram's own CHANGELOG for 0.0.8 (79 patches, Instagram 450.0.0.50.77 only, read 10 Oct 2026). A name a later HushGram renames is dropped by the build and reported by the Selection watch. Each maps a patch the owner already uses with piko or brosssh:

- HushGram settings: the settings screen the other HushGram patches need (piko equivalent: Add settings)
- Hide ads: ads; the reason this app is built (piko: Disable ads)
- Disable analytics: tracking (piko: Disable analytics)
- Remove the advertising ID: tracking: the app cannot read the phone advertising ID
- Don't send reel watch history: tracking: stops reporting which reels were watched
- Hide Meta AI: interface: removes Meta AI entry points
- Hide suggested posts: suggested content (the app note: suggested content removed)
- Hide suggested stories: suggested content (piko: Filter stories)
- Hide suggested people on profiles: suggested content (piko: Disable discover people)
- Copy comment: piko equivalent: Copy comment
- Save comment photo: piko equivalent: Save media comment
- Story ring size: piko equivalent: Customise story ring size
- Show a story's exact time: piko equivalent: Customise story timestamp
- Stop Reels scrolling: piko equivalent: Disable Reels scrolling
- Stop Story auto-advance: piko equivalent: Disable story flipping
- Stop swipe to create: piko equivalent: Disable swipe to create
- Tap to play: piko equivalent: Disable video autoplay
- Turn off double tap to like: piko equivalent: Disable double tap like
- Hide the Explore grid: piko equivalent: Disable explore
- Hide highlights: piko equivalent: Disable highlights
- Hide the Repost button: piko equivalent: Hide reshare button
- Download any reel: piko equivalent: Download media
- Download any story: piko equivalent: Download media
- Download any video: piko equivalent: Download media
- Show if a profile follows you: piko equivalent: Friendship status indicator
- Open links in external browser: piko equivalent: Open links externally
- Remove build expired popup: keeps an older build usable (brosssh and piko had it)
- Remove the empty space at the bottom: piko equivalent: Remove empty bottom space
- Sanitize sharing links: piko equivalent: Sanitize share links
- Restore trust on re-signed builds: makes a re-signed build work (brosssh equivalent: Bypass signature check); changes nothing Instagram servers see
- Open developer options: piko equivalent: Unlock developer options (owner includes it in piko)
- View stories anonymously: piko equivalent: View stories anonymously; story views are not reported to the poster, which Instagram can notice (account risk below)
- Hide that you're typing: piko equivalent: Disable typing status; the other person does not see typing, which Instagram can notice (account risk below)
- Read messages without the seen receipt: piko equivalent: Mark chat as read manually; the sender does not see the read receipt, which Instagram can notice (account risk below)
- See who a story mentions: piko equivalent: View story mentions
- View DM photos and videos anonymously: piko equivalent: View DMs anonymously; the opened receipt for view-once media is held back, which Instagram can notice (account risk below)

Not included (exclude list):
- Change version code: owner, 10 Oct 2026; also matches BANNED.
- Spoof location: owner, 10 Oct 2026.
- Start on x86 devices: the phone is ARM64; nothing to gain (same call as Facebook).

Removed from the piko list in W13: Remove build expired popup and Validate links. piko 3.10.0-dev.14 (10 Oct 2026) applies both always and no longer lists them; Nightly watch 10 Oct reported them MISSING. brosssh still applies Remove build expired popup.

## Risks
- View stories anonymously and View DM photos and videos anonymously hold back reports Instagram normally receives. Instagram can notice that, and an account could be limited. The owner uses the same behaviour with piko today without problems.
- HushGram is at version 0.0.x and is a fallback only. If a fallback build ships, its release notes say so, and the names lost compared with piko show as removed patches.
- Re-signed Instagram: account restrictions are possible. Phone-test a fallback build before relying on it.

## Decision
Owner, 10 Oct 2026 in chat: keep piko + brosssh as primary (piko-only features in use; HushGram is v0.0.x). Add SysAdminDoc/HushGram as the fallback candidate, excluding Change version code and Spoof location. Revisit HushGram as primary after HushGram 0.1 and the HushFacebook phone test. The owner pre-approved packet W13, merge included.
