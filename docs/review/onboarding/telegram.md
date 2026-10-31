# Telegram (telegram)

Package: org.telegram.messenger
Source APK: APKMirror, per the target's `source` (unchanged).

**Current (W16y-b, 30 Oct 2026):** rahul9999xda/morphe-patches is primary with 14 names in `src/patches/telegram-rahul9999xda/include-patches`, Telegram 13.1.1 (the shelf version). Owner, 30 Oct 2026: non-Hush for Telegram, the latest version with the most patches. HushTelegram builds could not sign in (`API_ID_PUBLISHED_FLOOD`); its fix is the owner's own API ID baked in at patch time, which a public build cannot carry, so the owner patches Hush on his phone if he wants it. rushiranpise stays the fallback (12.10.1; it cannot publish below the 13.1.1 shelf until it updates). HushTelegram's selection files stay, unreferenced, for a later return; it is on watch (DECISIONS.json N-ed3a5f).
Owner phone test, 31 Oct 2026: the W16y-b smoke build (run 41125099253, 14 of 14 patches) installed and signed in with no `API_ID_PUBLISHED_FLOOD`. Why HushTelegram builds are refused while this one is not is unknown (both patch Telegram's stock API ID). W16y-c publishes it.
Provider: rahul9999xda/morphe-patches (primary since W16y-b; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 30 Oct 2026) at https://github.com/rahul9999xda/morphe-patches; bundle: the one `.mpp` asset of the newest stable release (v1.17.0, 28 Oct 2026, sha256 06a9365e52ba987ff4660f74223b86837f414dc01e82fc3212da4b6ac8ac87d2); channel: latest). Left out: Bypass integrity check (CONFIRM rule, not owner-approved), Disable channel switching (the provider calls it a no-op), Fix Firebase after re-signing and Provide Original app certificate (re-signing helpers; the second is banned). Read from https://raw.githubusercontent.com/rahul9999xda/morphe-patches/v1.17.0/patches-list.json; survey: docs/review/TELEGRAM-SURVEY-2026-10-30.md.

**Current (W16j, 25 Oct 2026):** SysAdminDoc/HushTelegram is primary with 62 names in `src/patches/telegram-hushtelegram/include-patches` (owner: the most patches wins); rushiranpise/morphe-patches (12.10.1, 13 names, Unlock Premium among them) is the backup. newuser7171 is removed: it never built (24 and 25 Oct smokes: its fingerprints miss the APKMirror 12.10.4 build).
Provider: SysAdminDoc/HushTelegram (primary since W16j; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/SysAdminDoc/HushTelegram; bundle: the one `.mpp` asset of the newest release including pre-releases; channel: prerelease). Same author as HushFacebook and HushGram. Left out: Use registered Maps API key (BANNED), Use registered Telegram API credentials (needs your own API id), Repair Firebase push registration (hands Firebase the original certificate), HushTelegram icon and name (branding), Black and white launch logo (expert only, rebuilds resources).
Provider: rushiranpise/morphe-patches (primary in W16h, fallback since W16j; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/rushiranpise/morphe-patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease).

Superseded in W16j (newuser7171 was removed; HushTelegram is primary, rushiranpise the fallback). Owner decision, 24 Oct 2026 (packet W16g): newest version and most patches wins. newuser7171 targets 12.10.4 with every rushiranpise Telegram patch plus `Bypass translation restrictions`; rushiranpise (12.10.1) stays as the fallback. Owner keeps Remove ads, Bypass translation restrictions, Download speed boost, Hide typing indicator and Unlock Premium.

Owner approved: Unlock Premium


## Patches
- Anti-delete messages: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Anti-disappearing media: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Anti-screenshot notification: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Bypass channel restrictions: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Bypass content restrictions: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Disable auto-update: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Disable telemetry and analytics: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Download speed boost: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Hide Stories read status: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Hide typing indicator: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Remove ads: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Unlock Premium: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Use normal paste for Rich HTML clipboard content: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
- Voice to music: rahul9999xda, owner chose the non-Hush primary (30 Oct 2026, W16y-b)
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

## W16z (31 Oct 2026): split-signed release on the phone, and a check guide

- Owner phone test, 31 Oct: `telegram-v13.1.1-b2026103100000000041180839861000001` (the first release
  signed by the W15g Sign job) **installed over the current Telegram without uninstalling and works**:
  signed in, Premium icons show, the AI feature works. The other patches are **not confirmed**: the
  owner is a light Telegram user. Open item: a heavy Telegram user runs the guide below.
- Check guide for the 14 rahul9999xda patches (what a user should see; "no visible effect" means skip):

| Patch | How to check |
| --- | --- |
| Anti-delete messages | Ask a contact to delete a message they sent you; it stays, marked deleted. |
| Anti-disappearing media | Receive a view-once photo; it can be opened again. |
| Anti-screenshot notification | Screenshot a secret chat; the other side gets no screenshot notice. |
| Bypass channel restrictions | Open a channel with saving or forwarding disabled; save or forward works. |
| Bypass content restrictions | Content marked restricted on this device opens. |
| Disable auto-update | No visible effect; Telegram never offers its own update. |
| Disable telemetry and analytics | No visible effect; skip. |
| Download speed boost | Large file downloads are faster than stock (hard to judge; skip unless obvious). |
| Hide Stories read status | View a contact's story; it does not list you as a viewer. |
| Hide typing indicator | Type in a chat; the other side sees no "typing...". |
| Remove ads | Sponsored messages in large channels do not show. |
| Unlock Premium | Premium-only icons and features show (owner: confirmed for icons). |
| Use normal paste for Rich HTML clipboard content | Copy formatted text from a browser and paste; it pastes as plain text. |
| Voice to music | Voice notes play through the media player (background, seek). |

The "how to check" column is inferred from the patch names (W16z), not read from the provider's
descriptions: confirm a row against the rahul9999xda list-patches text before calling it a defect.

