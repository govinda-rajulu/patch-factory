# Facebook (facebook)

Package: com.facebook.katana
Source APK: https://www.apkmirror.com/apk/facebook-2/facebook/facebook-582-0-0-50-54-release/ (arm64-v8a, 320-640dpi, Android 11+, version code 475417104, read 10 Oct 2026; the build pins that code and refuses any other). Until W13: 581.0.0.45.58, version code 475215365.
Provider: SysAdminDoc/HushFacebook (licence: GPL-3.0, bundle: the one .mpp asset of the newest stable release, v0.8.0 on 8 Oct 2026; channel: stable). GitHub spells the repository HushFacebook; the community index says Hushfacebook.
Provider: RookieEnough/De-Vanced (fallback only, packet W13; licence: GPL-3.0, the same repository the Amazon Music record cites; bundle: the one .mpp asset of the newest release including pre-releases; channel: prerelease). Built only when a Hushfacebook build fails, on Facebook 580.0.0.51.74 (version code 475019344, 240-640dpi): its own pins, so the 581 pins above stay Hushfacebook's. Patches: src/patches/facebook-derevanced (Disable all ads, Disable analytics and telemetry, Messenger install compatibility; Change package name excluded).

## Patches
W13 (10 Oct 2026): Hushfacebook 0.9.0 supports only Facebook 582.0.0.50.54 (its CHANGELOG: "Hushfacebook now targets Facebook 582.0.0.50.54 only"), so the pins move to 582; the 581 build stays published until the 582 build replaces it.
Names exactly as the patcher listed them in Explore run 37976702866 (issue #173): 85 patches, 82 included.

- Hide affiliate product links: owner, 10 Oct 2026: every Hushfacebook patch except three
- Disable Audience Network: owner, 10 Oct 2026: every Hushfacebook patch except three
- Block Instant Games ads: owner, 10 Oct 2026: every Hushfacebook patch except three
- Block background ad prefetch: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide sponsored Marketplace listings: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide sponsored posts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide sponsored profile posts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide sponsored reels: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide sponsored search results: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide sponsored stories: owner, 10 Oct 2026: every Hushfacebook patch except three
- Block ad telemetry: owner, 10 Oct 2026: every Hushfacebook patch except three
- Clean up Facebook's chat list: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide the Get Messenger card: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide read receipts: the sender does not see that a message was read; Facebook can notice missing receipts and could limit the account. Owner decision 10 Oct 2026: on, for the phone test (the owner uses the same with piko Instagram without problems)
- Hide typing indicator: the other person does not see typing; Facebook can notice and could limit the account. Owner decision 10 Oct 2026: on, for the phone test (same behaviour in piko Instagram without problems)
- Open Messenger from the top bar: owner, 10 Oct 2026: every Hushfacebook patch except three
- Send chat photos and videos at original quality: owner, 10 Oct 2026: every Hushfacebook patch except three
- Default comment order: owner, 10 Oct 2026: every Hushfacebook patch except three
- Comment sheet options: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide Meta AI comment summaries: owner, 10 Oct 2026: every Hushfacebook patch except three
- Tag suggestions only after @: owner, 10 Oct 2026: every Hushfacebook patch except three
- Download any photo: owner, 10 Oct 2026: every Hushfacebook patch except three
- Download any reel: owner, 10 Oct 2026: every Hushfacebook patch except three
- Download any story: owner, 10 Oct 2026: every Hushfacebook patch except three
- Download any video: owner, 10 Oct 2026: every Hushfacebook patch except three
- Use the phone's emoji: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide AI-detected posts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Turn off auto-translation: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide the Feeds header: owner, 10 Oct 2026: every Hushfacebook patch except three
- Following feed on Home: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide Meta AI questions under posts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Keep post dates: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide post prompts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide Reels in the feed: owner, 10 Oct 2026: every Hushfacebook patch except three
- Block background-return feed refresh: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide seen posts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide Stories tray: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide suggested and promoted posts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide posts by words: owner, 10 Oct 2026: every Hushfacebook patch except three
- Use the system font: owner, 10 Oct 2026: every Hushfacebook patch except three
- Accent color: owner, 10 Oct 2026: every Hushfacebook patch except three
- AMOLED black theme: owner, 10 Oct 2026: every Hushfacebook patch except three
- Force dark mode: owner, 10 Oct 2026: every Hushfacebook patch except three
- Material You theme: owner, 10 Oct 2026: every Hushfacebook patch except three
- Turn off HDR brightness: owner, 10 Oct 2026: every Hushfacebook patch except three
- Picture-in-picture: owner, 10 Oct 2026: every Hushfacebook patch except three
- Keep the progress bar: owner, 10 Oct 2026: every Hushfacebook patch except three
- Default playback quality: owner, 10 Oct 2026: every Hushfacebook patch except three
- Keep the reel speed: owner, 10 Oct 2026: every Hushfacebook patch except three
- Resume long videos: owner, 10 Oct 2026: every Hushfacebook patch except three
- Tap to play: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide Menu promotions: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hushfacebook in the Menu: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hold back analytics uploads: owner, 10 Oct 2026: every Hushfacebook patch except three
- Open links in external browser: owner, 10 Oct 2026: every Hushfacebook patch except three
- Turn off haptics: owner, 10 Oct 2026: every Hushfacebook patch except three
- Restore screens on re-signed builds: owner, 10 Oct 2026: every Hushfacebook patch except three
- Allow screenshots: owner, 10 Oct 2026: every Hushfacebook patch except three
- Block screenshot detection: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hushfacebook settings: owner, 10 Oct 2026: every Hushfacebook patch except three
- Sanitize sharing links: owner, 10 Oct 2026: every Hushfacebook patch except three
- Turn off screen transitions: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide Meta upsells: owner, 10 Oct 2026: every Hushfacebook patch except three
- Tab bar at the bottom: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide tabs: owner, 10 Oct 2026: every Hushfacebook patch except three
- Marketplace only: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide the Reels tab: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide the Reels tab dot: owner, 10 Oct 2026: every Hushfacebook patch except three
- Show View profile on Marketplace sellers: owner, 10 Oct 2026: every Hushfacebook patch except three
- Open on a chosen tab: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide tab badges: owner, 10 Oct 2026: every Hushfacebook patch except three
- Block promotional notifications: owner, 10 Oct 2026: every Hushfacebook patch except three
- Clean up Reels: owner, 10 Oct 2026: every Hushfacebook patch except three
- Turn off double tap to like: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hold a reel for 2x: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide reel interest prompts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Don't send reel watch history: owner, 10 Oct 2026: every Hushfacebook patch except three
- Hide Meta AI in search: owner, 10 Oct 2026: every Hushfacebook patch except three
- Stop Story auto-advance: owner, 10 Oct 2026: every Hushfacebook patch except three
- View stories anonymously: the poster does not see the view; Facebook can notice and could limit the account. Owner decision 10 Oct 2026: on, for the phone test (same behaviour in piko Instagram without problems)
- Hide suggested stories: owner, 10 Oct 2026: every Hushfacebook patch except three
- Stop update prompts: owner, 10 Oct 2026: every Hushfacebook patch except three
- Share sheet items: new in Hushfacebook (86 patches, 10 Oct 2026); it changes the app's own share sheet on the phone, nothing Facebook receives. Owner left the call to the assistant on 10 Oct 2026; on, so Sunday's phone test covers the full set. If the name differs in the provider's list, the build drops it by name (W13) and the Selection watch reports it.

Not included (exclude list):
- Install beside Meta's apps: gives the app another package name, so Obtainium and in-place updates of com.facebook.katana stop; the intent of the BANNED package-name rule.
- Disable Play Store updates: once installed, a build without it cannot install over it (the provider says so).
- Start on x86 devices: the phone is ARM64; nothing to gain.

## Risks
- Hide read receipts, Hide typing indicator and View stories anonymously hold back signals Facebook normally receives, so Facebook can notice them and an account could be warned or limited. Owner decision: include them and test on the phone (Sunday 11 Oct 2026); drop them if the account shows warnings.
- Hushfacebook supports one exact Facebook build at a time and Facebook ships weekly. A newer Facebook is not built until the provider supports it; the version-code pin stops a wrong download.
- The provider pages disagree on 580 and 577 (README: no longer supported; v0.8.0 notes: still work). This record relies only on 581.0.0.45.58 build 475215365.
- Re-signed Facebook: account restrictions are possible. Test with the owner's phone before relying on it.

## Decision
Owner, 9 to 10 Oct 2026 in chat: move Facebook to Hushfacebook 581 with every patch, the three server-visible ones included for testing (packet W11). De-Vanced (580) stays in src/patches/facebook-derevanced as the fallback, unreferenced until per-provider version pins exist (W12).

Owner, 10 Oct 2026 (packet W13): De-Vanced on 580 becomes the fallback with per-provider pins; the three account-risk lines above describe the risk instead of naming a rule (lesson L047). The owner pre-approved packet W13, merge included.
