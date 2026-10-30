# Telegram patch survey — 30 October 2026

**Package:** `org.telegram.messenger`  
**Decision status:** proposal only; this file does not change `src/targets.json`.  
**Credit:** Written with Anthropic Claude models.

## Executive result

The strongest safe proposal is **HushTelegram v0.0.21 on Telegram 13.1.1 as the primary**, with **rahul9999xda v1.17.0 on the same 13.1.1 as the first fallback**. Hush has 67 package patches (62 selected after the reviewed exclusions); Rahul has 16 package patches, including a 13.1.1 audit. The gap is 46 selected/source names before considering the optional Mormislaw automotive patch, so the owner's 30 October exception applies: Hush may be primary because the best non-Hush group is far below it. The fallback must not mix Hush and non-Hush patches in one build.

The current primary already built Telegram 13.1.1 with Hush v0.0.21 and 62 selected patches on 28 October. The material improvement is replacing the current **12.10.1** rushiranpise fallback with Rahul's **13.1.1** fallback. An older fallback cannot replace the 13.1.1 shelf: `publish_guard` refuses an older version.

Hush's registered Telegram API-credentials patch remains excluded. If Telegram presents `API_ID_PUBLISHED_FLOOD`, ask for the owner's API ID/hash interactively at build/use time only; never put either value in this document, `targets.json`, an override, a bundle, or a generated artifact.

## Sources and method

I read the newest three-release feeds requested by the owner, the newest release's patch list where published, repository licence metadata, the checked-in target/selection files, and APK listing evidence. Release API records are pinned by release ID below; patch lists use release tags rather than mutable default branches wherever available. A claim marked **UNVERIFIED** was not established by a live source.

* Current target and selections: [`src/targets.json`](../../src/targets.json), [`telegram-hushtelegram/include-patches`](../../src/patches/telegram-hushtelegram/include-patches), [`telegram-hushtelegram/exclude-patches`](../../src/patches/telegram-hushtelegram/exclude-patches), [`telegram-rushiranpise/include-patches`](../../src/patches/telegram-rushiranpise/include-patches), and [`telegram-rushiranpise/exclude-patches`](../../src/patches/telegram-rushiranpise/exclude-patches).
* Current shelf evidence: [Telegram 13.1.1 patch-factory release](https://github.com/govinda-rajulu/patch-factory/releases/tag/telegram-v13.1.1-b2026102800000000040640881249000001).
* APKMirror evidence: [13.1.1 APK](https://www.apkmirror.com/apk/telegram-fz-llc/telegram/telegram-13-1-1-release/telegram-13-1-1-android-apk-download/), [13.1.1 bundle](https://www.apkmirror.com/apk/telegram-fz-llc/telegram/telegram-13-1-1-release/telegram-13-1-1-2-android-apk-download/), [13.1.0](https://www.apkmirror.com/apk/telegram-fz-llc/telegram/telegram-13-1-0-release/telegram-13-1-0-android-apk-download/), [12.10.4](https://www.apkmirror.com/apk/telegram-fz-llc/telegram/telegram-12-10-4-release/), and [12.10.1](https://www.apkmirror.com/apk/telegram-fz-llc/telegram/telegram-12-10-1-release/). APKPure's live version page did not expose these 2026 candidate rows in the fetched result; treat APKPure availability as **UNVERIFIED** for all four candidates.

## Provider matrix

Counts below are for the exact package `org.telegram.messenger`, not a repository's all-app total. “Source count” includes every package-specific patch in the release list; “reviewed selection” is the useful set after the repository's local include/exclude rules where those rules exist.

| Provider | Latest tag/date | Versions supported for this package | Source count / reviewed selection | Overlap with others | Licence | Activity, keys, network and risk |
|---|---|---:|---:|---|---|---|
| [rushiranpise/morphe-patches](https://api.github.com/repos/rushiranpise/morphe-patches/releases/427026510) | `v1.23.1` — 2026-10-28 | 12.10.1 | 14 / 13 local | Exact: 13 with Rahul; exact: 14 with newuser. Semantic equivalents with Hush: remove ads, faster downloads, update blocking, normal paste, voice player. | GPL-3.0 ([tag licence](https://raw.githubusercontent.com/rushiranpise/morphe-patches/v1.23.1/LICENSE)) | Active, but v1.23.1's release notes concern other apps. Includes high-risk `Bypass integrity check` in the source list; local exclude rules keep re-signing/integrity items out. Telegram Premium is client-side and server features remain server-controlled. Older than the shelf (12.10.1). Patch list: [`v1.23.1/patches-list.json`](https://raw.githubusercontent.com/rushiranpise/morphe-patches/v1.23.1/patches-list.json). |
| [SysAdminDoc/HushTelegram](https://api.github.com/repos/SysAdminDoc/HushTelegram/releases/426008005) | `v0.0.21` — 2026-10-27 | 13.1.1 for Play `org.telegram.messenger`; 13.1.0 for `org.telegram.messenger.web` | 67 / 62 local | Exact name overlap with Rush/Rahul is small because Hush names the same jobs differently. Semantic overlap: delete retention, update blocking, download speed, ads, analytics, normal paste and voice-player behavior. Deliberately does **not** provide premium unlock or restriction bypass. | GPL-3.0 ([tag licence](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/LICENSE)) | Most active Hush repo: release v0.0.21 says Play 13.1.1/version code 72371; repository activity was updated/pushed 30 Oct. `Translate with an outside service` can send selected text to Google/AI; UnifiedPush is a network/service dependency. `Use registered Telegram API credentials` and Maps credentials are not selected. API ID/hash are interactive-only on `API_ID_PUBLISHED_FLOOD`; never stored. Patch list: [`v0.0.21/patches-list.json`](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/patches-list.json). |
| [rahul9999xda/morphe-patches](https://api.github.com/repos/rahul9999xda/morphe-patches/releases/426173610) | `v1.17.0` — 2026-10-28 | 13.1.1 | 16 / 15 proposed safe (drop integrity) | Exact: 13 with newuser and 13 with Rush. Rahul-only package names: `Disable telemetry and analytics`, `Hide Stories read status`, and `Use normal paste for Rich HTML clipboard content`; exact overlap with Hush: none. | GPL-3.0 ([tag licence](https://raw.githubusercontent.com/rahul9999xda/morphe-patches/v1.17.0/LICENSE)) | Active and specifically audited/fingerprinted Telegram 13.1.1 in its release notes. Source list contains re-sign/integrity material; do not select `Bypass integrity check`. Premium remains client-side. Patch list: [`v1.17.0/patches-list.json`](https://raw.githubusercontent.com/rahul9999xda/morphe-patches/v1.17.0/patches-list.json). |
| [newuser7171/telegram-morphe-patches-](https://api.github.com/repos/newuser7171/telegram-morphe-patches-/releases/396946364) | `v1.0.0` — 2026-09-25 | 12.10.4 | 15 / 13 old local selection | Exact: 14 with Rush (the old source list); exact: 13 with Rahul. Adds `Bypass translation restrictions`; otherwise largely the Rush set. | GPL-3.0 **UNVERIFIED from a live licence response**; repository licence should be re-read before admission. | Stale and previously removed: local review records that it never built against the APKMirror 12.10.4 fingerprints. Keep out of the proposed order. Source list includes integrity, signature, install-source, and Firebase re-signing items; all are risky or banned locally. Patch list: [`v1.0.0/patches-list.json`](https://raw.githubusercontent.com/newuser7171/telegram-morphe-patches-/v1.0.0/patches-list.json). |
| [mich111discord/MightyMichs-Patches](https://api.github.com/repos/mich111discord/MightyMichs-Patches/releases/423421759) | `v1.12.0` — 2026-10-25 | 12.10.1 | 1 | `Unlock Telegram Premium` is the same job as Rush/Rahul `Unlock Premium`, but a distinct name. No useful unique Telegram function. | GPL-3.0 ([repository licence record](https://github.com/mich111discord/MightyMichs-Patches/blob/v1.12.0/LICENSE)) | Active broad multi-app repo, but no Telegram-specific release-note change and only one Telegram patch. Client-side premium risk; no reason to add it to a build that already has premium. Patch list: [`v1.12.0/patches-list.json`](https://raw.githubusercontent.com/mich111discord/MightyMichs-Patches/v1.12.0/patches-list.json). |
| [mormislaw/zeekr-adapt-morphe-patches](https://api.github.com/repos/mormislaw/zeekr-adapt-morphe-patches/releases/426470289) | `v1.0.0` — 2026-10-28 | Version target is null/unspecified in the published generic adapter list — exact 13.1.1 compatibility **UNVERIFIED** | 1 (`DHU adapter`) | No patch-name overlap; optional automotive UI/adapter function. | GPLv3 ([README licence](https://raw.githubusercontent.com/mormislaw/zeekr-adapt-morphe-patches/v1.0.0/README.md)) | Newly active. README explicitly lists Telegram and says the preset is Display/UI only; the generic list does not pin an app version. Native Pine/libpine injection and orientation/DPI hooks add device-specific risk; not useful on a normal phone. Patch list: [`v1.0.0/patches-list.json`](https://raw.githubusercontent.com/mormislaw/zeekr-adapt-morphe-patches/v1.0.0/patches-list.json). |
| [ch3thanhs/stylus](https://api.github.com/repos/ch3thanhs/stylus/releases/421511141) | `v1.8.1` — 2026-10-23 | 13.1.0 | 1 | `Force system font (Telegram)` is the same job as Hush `Use system font`; not compatible with Rahul 13.1.1 because its published target is 13.1.0. | GPL-3.0 ([tag licence](https://raw.githubusercontent.com/ch3thanhs/stylus/v1.8.1/LICENSE)) | Active accessibility/font collection; latest release says GitHub support, while its previous v1.8.0 announced Telegram support. Resource-patch risk is low but version-specific. Patch list: [`v1.8.1/patches-list.json`](https://raw.githubusercontent.com/ch3thanhs/stylus/v1.8.1/patches-list.json). |

### Patch names read from the package lists

* **Hush v0.0.21, 67:** AMOLED black; Add Repeat to the message menu; Allow chat blur on slower phones; Ask before sending a sticker; Black and white launch logo; Change sticker size; Disable analytics; Disable call debug upload; Disable chat swipe actions; Disable double-tap reactions; Disable draft link previews; Disable pull to archive; Disable pull to next channel; Disable update checks; Exact numbers; Faster downloads; Folders by chat type; Gallery camera on tap; Hide Contacts tab; Hide Premium, gifts and Stars; Hide Send as button; Hide Stories; Hide Telegram Features and Invite Friends; Hide ads; Hide blocked users in groups; Hide channel bar buttons; Hide contacts on Telegram; Hide folder tab counters; Hide gallery camera tile; Hide greeting stickers; Hide keyboard on scroll; Hide messages by keyword; Hide phone number; Hide popular apps; Hide promotional banners; Hide recommendations; Hide sender names when forwarding; Hide sponsored proxy channel; Hide time on stickers; Hide translate bar; Holiday look all year; HushTelegram icon and name; HushTelegram settings; Ignore mentions in muted chats; Keep deleted messages; Keep videos muted on volume keys; Message times with seconds; Open links externally; Play voice messages one at a time; Quiet contacts nag; Repair Firebase push registration; Reveal spoilers; Save downloaded files; Show user and chat IDs; Silence people outside your contacts; Start the camera on the rear lens; Strip link tracking; Swipe back on profiles; Translate with an outside service; Turn off haptic feedback; Turn off reaction effects; UnifiedPush notifications; Use normal paste; Use registered Maps API key; Use registered Telegram API credentials; Use system font; Voice messages in the music player. The five local exclusions are the Maps key, Telegram API credentials, Firebase repair, Hush branding, and black-and-white logo, leaving 62.
* **Rush v1.23.1, 14:** Anti-delete messages; Anti-disappearing media; Anti-screenshot notification; Bypass channel restrictions; Bypass content restrictions; Bypass integrity check; Disable auto-update; Disable channel switching; Download speed boost; Hide typing indicator; Remove ads; Unlock Premium; Use normal paste; Voice to music. The local selection is 13 because the integrity/re-signing set is excluded.
* **Rahul v1.17.0, 16:** Anti-delete messages; Anti-disappearing media; Anti-screenshot notification; Bypass channel restrictions; Bypass content restrictions; Bypass integrity check; Disable auto-update; Disable channel switching; Disable telemetry and analytics; Download speed boost; Hide Stories read status; Hide typing indicator; Remove ads; Unlock Premium; Use normal paste for Rich HTML clipboard content; Voice to music. Proposed safe selection drops Bypass integrity check (15).
* **newuser v1.0.0, 15:** Anti-delete messages; Anti-disappearing media; Anti-screenshot notification; Bypass channel restrictions; Bypass content restrictions; Bypass integrity check; Bypass translation restrictions; Disable auto-update; Disable channel switching; Download speed boost; Hide typing indicator; Remove ads; Unlock Premium; Use normal paste; Voice to music.
* **MightyMich v1.12.0:** Unlock Telegram Premium.
* **Mormislaw v1.0.0:** DHU adapter for Telegram, with version target unspecified in the published generic list (**UNVERIFIED** as an exact 13.1.1 match).
* **Stylus v1.8.1:** Force system font (Telegram), supported at 13.1.0.

## Common-version candidates

| Candidate | Version / source | Count | Gain versus current shelf | Lost versus current shelf | Newer/older and risks |
|---|---|---:|---|---|---|
| **A — best non-Hush union** | 13.1.1; Rahul v1.17.0 + optional Mormislaw DHU adapter | 17 source names, 16 safe proposed (15 Rahul safe + 1 DHU) | Same app version as shelf; Rahul adds audited 13.1.1 coverage and three package-specific behaviours not in Rush; Mormislaw adds car/DHU UI only if needed. | Loses Hush's 62 selected UX/privacy/ads/settings features; no Hush settings screen, UnifiedPush, external translation, or Hush's broad hide/retention controls. | Same version, so it passes the shelf age/version comparison. Rahul's integrity patch stays off. Mormislaw's null version target, native Pine hooks, and car-specific behaviour are **UNVERIFIED/high risk**; omit it for a normal-phone build, giving 15 source / 14 safe. Do not combine with Hush in this build. |
| **B — Hush alone** | 13.1.1; Hush v0.0.21 | 67 source, 62 selected | Retains the largest useful set, including analytics/privacy, ad/upsell/story controls, settings, file handling, translation, UnifiedPush, and usability switches. | None versus the current selected shelf: this is the same 62-patch Hush selection unless the owner deliberately changes exclusions. The five excluded source names remain out by policy. | Same version and already built. Hush-specific translation/network dependencies and API-flood interaction remain; no key is stored. Never add Rahul/Rush/Mormislaw to this Hush build. |
| **C — current configured setup** | Hush primary 13.1.1; Rush fallback 12.10.1 | Primary 62 selected; fallback 14 source / 13 local | Hush primary already delivers the current shelf. Rush preserves the older premium/restriction/download/typing/voice fallback. | Fallback is 0.1.0 behind the shelf and lacks Rahul's 13.1.1 audit and telemetry/stories/rich-paste names. | The fallback is older; `publish_guard` refuses it over a 13.1.1 shelf. It is therefore an emergency cold-start fallback, not a viable replacement after the current shelf exists. |

At 12.10.1, Rush plus Mighty would produce 15 distinct source names if premium duplicates are counted by name, but Mighty adds no unique useful behaviour. At 12.10.4, newuser produces 15 names but has a documented build/fingerprint failure. At 13.1.0, Stylus contributes one font patch. These are all inferior to the 13.1.1 Rahul group, even before Hush's exception is applied.

## Proposed `targets.json` shape (not applied)

This is the smallest shape that keeps Hush isolated while allowing the best non-Hush fallback to use Mormislaw's optional generic DHU patch. The global extra is explicitly removed for the Hush candidate. For a normal phone, omit the extra bundle entirely; the Rahul fallback then has 15 source names (14 safe after dropping its integrity patch).

```json
{
  "id": "telegram",
  "enabled": true,
  "package": "org.telegram.messenger",
  "apk_name": "telegram",
  "apk_type": "bundle",
  "max_app_version": null,
  "max_patch_age_days": 180,
  "min_sdk_ceiling": 29,
  "pin": "hushtelegram",
  "exclusive": true,
  "candidates": [
    {
      "name": "hushtelegram",
      "host": "github",
      "channel": "prerelease",
      "patch_dir": "telegram-hushtelegram",
      "options": "hushtelegram",
      "owner": "SysAdminDoc",
      "repo": "HushTelegram",
      "overrides": { "extra_bundles": [] }
    },
    {
      "name": "rahul9999xda",
      "host": "github",
      "channel": "prerelease",
      "patch_dir": "telegram-rahul9999xda",
      "options": "rahul9999xda-telegram",
      "owner": "rahul9999xda",
      "repo": "morphe-patches",
      "fallback": true
    }
  ],
  "extra_bundles": [
    {
      "name": "mormislaw",
      "host": "github",
      "owner": "mormislaw",
      "repo": "zeekr-adapt-morphe-patches",
      "channel": "latest",
      "patch_dir": "telegram-mormislaw"
    }
  ],
  "tag_prefix": "telegram",
  "poll": true,
  "source": "apkmirror",
  "any_version": false,
  "label": "Telegram",
  "note": "Proposal: Hush v0.0.21 remains the isolated 13.1.1 primary (62 reviewed names); Rahul v1.17.0 is the same-version non-Hush fallback. Mormislaw is optional only for a DHU/car build and its exact Telegram version target is UNVERIFIED. Never store Hush API credentials; prompt only for API_ID_PUBLISHED_FLOOD."
}
```

If preserving the old cold-start fallback is required, add Rush after Rahul with `fallback: true`, but expect 12.10.1 to be rejected against a 13.1.1 shelf. Do not add newuser, MightyMich, or Stylus to this order. Do not add Mormislaw globally unless its version compatibility is verified; the safe normal-phone proposal is the same shape with `extra_bundles: []` omitted and no Mormislaw patch directory.

## Recommendation and open verification

1. Keep Hush as primary under the owner's explicit “far below” exception: 62 selected versus Rahul's 15 safe names.
2. Replace Rush as first fallback with Rahul, because Rahul is audited for exactly 13.1.1 and avoids the known older-shelf refusal.
3. Keep integrity/signature/Firebase/re-signing patches excluded. Keep Hush API credentials interactive-only and absent from all files.
4. Treat Mormislaw as optional car-only work, not a normal-phone patch, until its Telegram target version is pinned and built.
5. APKMirror lists all candidate Play versions: 13.1.1 (version code 72371), 13.1.0 (72291), 12.10.4 (70992), and 12.10.1 (70382). APKPure availability for those exact candidates is **UNVERIFIED** from the fetched pages. newuser's APKMirror 12.10.4 build is listed, but the provider's fingerprints failed in the local historical smoke record.
6. Re-read newuser's `LICENSE` through the live API before any future admission; its licence is the only matrix licence not confirmed in the live response captured for this survey.
