# Telegram (telegram)

Package: org.telegram.messenger
Source APK: APKMirror, per the target's `source` (unchanged).

**Current (W16j, 25 Oct 2026):** SysAdminDoc/HushTelegram is primary with 62 names in `src/patches/telegram-hushtelegram/include-patches` (owner: the most patches wins); rushiranpise/morphe-patches (12.10.1, 13 names, Unlock Premium among them) is the backup. newuser7171 is removed: it never built (24 and 25 Oct smokes: its fingerprints miss the APKMirror 12.10.4 build).
Provider: SysAdminDoc/HushTelegram (primary since W16j; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/SysAdminDoc/HushTelegram; bundle: the one `.mpp` asset of the newest release including pre-releases; channel: prerelease). Same author as HushFacebook and HushGram. Left out: Use registered Maps API key (BANNED), Use registered Telegram API credentials (needs your own API id), Repair Firebase push registration (hands Firebase the original certificate), HushTelegram icon and name (branding), Black and white launch logo (expert only, rebuilds resources).
Provider: rushiranpise/morphe-patches (primary in W16h, fallback since W16j; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/rushiranpise/morphe-patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease).

Superseded in W16j (newuser7171 was removed; HushTelegram is primary, rushiranpise the fallback). Owner decision, 24 Oct 2026 (packet W16g): newest version and most patches wins. newuser7171 targets 12.10.4 with every rushiranpise Telegram patch plus `Bypass translation restrictions`; rushiranpise (12.10.1) stays as the fallback. Owner keeps Remove ads, Bypass translation restrictions, Download speed boost, Hide typing indicator and Unlock Premium.

Owner approved: Unlock Premium


## Patches
- AMOLED black: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Add Repeat to the message menu: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Allow chat blur on slower phones: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Ask before sending a sticker: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Change sticker size: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable analytics: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable call debug upload: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable chat swipe actions: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable double-tap reactions: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable draft link previews: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable pull to archive: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable pull to next channel: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Disable update checks: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Exact numbers: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Faster downloads: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Folders by chat type: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Gallery camera on tap: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide Contacts tab: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide Premium, gifts and Stars: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide Send as button: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide Stories: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide Telegram Features and Invite Friends: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide ads: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide blocked users in groups: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide channel bar buttons: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide contacts on Telegram: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide folder tab counters: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide gallery camera tile: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide greeting stickers: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide keyboard on scroll: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide messages by keyword: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide phone number: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide popular apps: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide promotional banners: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide recommendations: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide sender names when forwarding: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide sponsored proxy channel: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide time on stickers: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Hide translate bar: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Holiday look all year: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- HushTelegram settings: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Ignore mentions in muted chats: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Keep deleted messages: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Keep videos muted on volume keys: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Message times with seconds: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Open links externally: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Play voice messages one at a time: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Quiet contacts nag: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Reveal spoilers: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Save downloaded files: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Show user and chat IDs: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Silence people outside your contacts: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Start the camera on the rear lens: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Strip link tracking: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Swipe back on profiles: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Translate with an outside service: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Turn off haptic feedback: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Turn off reaction effects: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- UnifiedPush notifications: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Use system font: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)
- Voice messages in the music player: HushTelegram, owner took the provider in the Needs you review file (N-9bd13d, 2026-10-25)

Exclusive target. History: the W16h newuser7171 fallback list follows (that provider and its folder were removed in W16j). Today's fallback is rushiranpise; its 13 names are in `src/patches/telegram-rushiranpise/include-patches`: Anti-delete messages, Anti-disappearing media, Anti-screenshot notification, Bypass channel restrictions, Bypass content restrictions, Disable auto-update, Disable channel switching, Download speed boost, Hide typing indicator, Remove ads, Unlock Premium, Use normal paste, Voice to music. The old newuser7171 list:

- Anti-delete messages: default on; same as the rushiranpise build.
- Anti-disappearing media: default on; same as the rushiranpise build.
- Anti-screenshot notification: default on; same as the rushiranpise build.
- Bypass content restrictions: default on; same as the rushiranpise build.
- Bypass translation restrictions: default on; new on this provider, owner asked for it.
- Disable auto-update: default on; stops the in-app updater replacing the patched app.
- Disable channel switching: default on; same as the rushiranpise build.
- Download speed boost: default on; owner keeps it.
- Hide typing indicator: default on; owner keeps it.
- Remove ads: default on; ad removal.
- Unlock Premium: default on; owner approved (tested a premium patch for this app before).
- Use normal paste: default on; same as the rushiranpise build.
- Voice to music: default on; same as the rushiranpise build.

Left out of the W16i newuser7171 fallback (its exclude-patches then; today's rushiranpise fallback includes Bypass channel restrictions and excludes the CONFIRM and BANNED names): `Bypass channel restrictions` (W16i: fails on 12.10.4, run 40108956377; excluded so the Selection rule cannot add it back, as PR #243 tried), `Bypass integrity check` (CONFIRM rule, held as before), `Fix Firebase after re-signing`, `Provide Original app certificate`, `Spoof app signature`, `Spoof install source` (all BANNED re-signing rules).

## Risks

- Telegram accounts are server-side; Premium unlock is client-side and may be ignored or noticed. The owner accepts this (tested before).
- Re-signed build: Telegram may refuse some features that check the signature; the re-signing patches stay off by rule.

## W16h (25 Oct 2026): rushiranpise primary again

The W16g smoke (run 40108956377) failed on 12.10.4: "Bypass channel restrictions" did not match
(`PhotoViewer` fingerprint). rushiranpise (12.10.1, 13 patches including Bypass channel restrictions
and Unlock Premium) is primary again. newuser7171 is the fallback without Bypass channel restrictions
(13 names: it adds Bypass translation restrictions).
