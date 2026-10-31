# Telegram + provider fallback handoff (WH)

**Status: READY WITH OWNER CALLS.** This is a read-only research/design handoff against live `main` and live HushTelegram evidence. No repository or workspace content was changed. The requested publication path is outside this worker's permitted write area; this copy is at (assistant sandbox) for the parent to place at `TELEGRAM-FALLBACKS.md`.

## Summary

| Area | Finding | Recommendation |
|---|---|---|
| Telegram target | `org.telegram.messenger` is exclusive; HushTelegram is currently first, rushiranpise second/fallback ([targets](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L549-L585)). | Follow the owner's stated preference: rushiranpise/non-Hush primary; HushTelegram fallback in the same target, not a mixed bundle. |
| Hush live release | `v0.0.21` (published 2026-10-27) has 67 patches and supports Play Telegram 13.1.1/version code 72371 and telegram.org package 13.1.0/version code 72299 ([release](https://github.com/SysAdminDoc/HushTelegram/releases/tag/v0.0.21), [tagged patch list](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/patches-list.json)). | Candidate is viable only after the source APK/package/version is matched. The repo watch row says ours is still 13.1.0 and watches Rahul until 13.1.1 ([DECISIONS](https://github.com/govinda-rajulu/patch-factory/blob/main/src/patches/DECISIONS.json#L907-L933)). |
| Hush keys/privacy | Own Telegram API credentials are needed only if login hits `API_ID_PUBLISHED_FLOOD`; Maps credentials, custom branding and Firebase certificate repair are separate options. | Keep all credential-dependent/re-signing-risk options out. Never commit `apiId`, `apiHash`, Maps keys or AI keys. |
| Provider fallback | `build_attempts.py` retries primaries then fallbacks, with candidate overrides and a clean reset, but `publish_guard` rejects any app version below the newest shelf version. | Adopt controlled stale-fallback exception (Option B below) now; design a separate app only if a clone/package identity is introduced. |
| Store fallback | `store_chain.sh` already tries APKMirror/APKPure and refuses unsafe version gaps. | Keep it; it solves store failure, not provider-version publication lockout. |

## 1. Telegram evidence

### Current repository state

* Target is enabled, package `org.telegram.messenger`, source APKMirror, exclusive, no target pin ([`src/targets.json:549-585`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L549-L585)).
* Current candidate order is `hushtelegram` (SysAdminDoc/HushTelegram, prerelease, no `fallback` field) then `rushiranpise` (rushiranpise/morphe-patches, prerelease, `fallback: true`) ([same target](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L559-L578)). This is opposite the owner's 28-Oct rule that non-Hush providers are primary and Hush* providers are fallback/separate ([KT-2026-10-28.md:13](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/KT-2026-10-28.md#L11-L14)).
* Hush local selection has 62 names and excludes five names: registered Maps key, registered Telegram API credentials, Firebase repair, Hush branding and black/white launch logo ([include](https://github.com/govinda-rajulu/patch-factory/blob/main/src/patches/telegram-hushtelegram/include-patches), [exclude](https://github.com/govinda-rajulu/patch-factory/blob/main/src/patches/telegram-hushtelegram/exclude-patches)). `src/options/hushtelegram.json` is an empty array ([file](https://github.com/govinda-rajulu/patch-factory/blob/main/src/options/hushtelegram.json)).
* rushiranpise's local fallback has 13 selected names (including Remove ads, Download speed boost and Unlock Premium) and excludes integrity/re-signing, certificate, identity spoofing and MicroG names ([include](https://github.com/govinda-rajulu/patch-factory/blob/main/src/patches/telegram-rushiranpise/include-patches), [exclude](https://github.com/govinda-rajulu/patch-factory/blob/main/src/patches/telegram-rushiranpise/exclude-patches)). Existing onboarding records that Telegram Premium is client-side and may be ignored/noticed, and that re-signed Telegram can refuse signature-dependent features ([onboarding:96-99](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/onboarding/telegram.md#L96-L99)).
* `rahul9999xda/morphe-patches` is explicitly watched because it lists Telegram 13.1.1 while ours is 13.1.0 ([DECISIONS.json:927-932](https://github.com/govinda-rajulu/patch-factory/blob/main/src/patches/DECISIONS.json#L927-L932)); do not silently promote it or infer compatibility from the community index.

### Live HushTelegram release and tag checks

The live GitHub release API's newest entry is **v0.0.21**, published 2026-10-27. Its release body says 67 patches, Google Play `org.telegram.messenger` Telegram 13.1.1/code 72371, and telegram.org `org.telegram.messenger.web` Telegram 13.1.0/code 72299. It requires Morphe Manager 2.2.0+. The `.mpp` asset is `patches-0.0.21.mpp`, SHA-256 `9004f99d772db018e72f4af9e8223993ef145564bea0a35eae06be0190cf6f94`; the API also exposes a SHA256SUMS asset. Sources: [release API](https://api.github.com/repos/SysAdminDoc/HushTelegram/releases?per_page=5), [v0.0.21 release](https://github.com/SysAdminDoc/HushTelegram/releases/tag/v0.0.21), [release bundle metadata](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/patches-bundle.json).

The tagged `patches-list.json` has blob SHA `3e488a73b925ebed4180d5940c03cd6907dabd97`, 67 patch records, both package compatibility maps, and ARM64 codes 72371/72299 ([tagged API object](https://api.github.com/repos/SysAdminDoc/HushTelegram/contents/patches-list.json?ref=v0.0.21), [raw tag file](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/patches-list.json)). Pin the tag plus asset digest in review evidence; do not consume mutable `main` metadata for a release. Important limitation: the live release API reports `immutable: false` for v0.0.21, so it should not be called an immutable GitHub release. The tag/blob and MPP digest are useful evidence pins, not a cryptographic signature.

**Version/package gate:** the configured target package is `org.telegram.messenger`, but v0.0.21 declares that package only for Telegram 13.1.1/code 72371. Its 13.1.0/code 72299 support is for the different `org.telegram.messenger.web` telegram.org package. The checked-in watch row says ours is 13.1.0. Therefore do not assume Hush v0.0.21 can patch the current target: first prove the APKMirror artifact package and version. If ours remains `org.telegram.messenger` 13.1.0, Hush must be held until a release declares that exact pair or the source target is deliberately changed.

The live repository is active: the commit API has commits on 2026-10-30, including a Play-signed walk-receipt requirement and 13.1.0 ad/analytics recheck ([recent commits](https://api.github.com/repos/SysAdminDoc/HushTelegram/commits?per_page=10)). The repository metadata reports GPL-3.0 and 52 stars/12 open issues ([repo](https://github.com/SysAdminDoc/HushTelegram)); the license file is GPLv3 ([LICENSE](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/LICENSE)). Activity is therefore high, but releases/tags are unsigned in the API response and should be digest-pinned/reviewed before adoption.

### Hush patches and network/key risks

* The v0.0.21 README says four patches start unselected: **Use registered Telegram API credentials**, **Use registered Maps API key**, **HushTelegram icon and name**, and **Black and white launch logo** ([tagged README](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/README.md#L31-L45)). Login may fail with `API_ID_PUBLISHED_FLOOD`; the documented one-time fix is to create a personal app at [my.telegram.org/apps](https://my.telegram.org/apps), then fill `apiId`/`apiHash` in Morphe Manager. The keys must remain private and never enter this repository, build logs, release metadata, or a patch-options JSON.
* The excluded Maps-key patch is not needed for the owner use case. Keep it excluded. Keep Firebase repair excluded: the live patch description says it gives Firebase Telegram's original certificate ([tagged README patch table](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/v0.0.21/README.md#L85-L93)); this is a privacy/trust tradeoff and is explicitly excluded locally.
* Hush's own code documents that its optional release check is **off until the person enables it**, at most daily, one HTTPS GET to `api.github.com`, with no username/cookie and no download/install ([ReleaseCheck.java](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/main/extensions/telegram/src/main/java/app/hushtelegram/extension/telegram/settings/ReleaseCheck.java#L47-L70), [ReleaseTransport.java](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/main/extensions/telegram/src/main/java/app/hushtelegram/extension/telegram/settings/ReleaseTransport.java#L20-L32)). This is an opt-in Hush update check, not silent telemetry. The extension source states the only other extension requests are Google translation and user-configured AI translation.
* If the owner enables **Translate with an outside service**, message text is sent to Google's keyless translate endpoint ([GoogleTranslate.java](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/main/extensions/telegram/src/main/java/app/hushtelegram/extension/telegram/misc/GoogleTranslate.java#L20-L31), [endpoint/fetch](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/main/extensions/telegram/src/main/java/app/hushtelegram/extension/telegram/misc/GoogleTranslate.java#L80-L130)); a configured AI service receives text and the owner's API key at the address the owner typed ([AiTranslate.java](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/main/extensions/telegram/src/main/java/app/hushtelegram/extension/telegram/misc/AiTranslate.java#L15-L29), [request](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/main/extensions/telegram/src/main/java/app/hushtelegram/extension/telegram/misc/AiTranslate.java#L170-L200)). Treat these as explicit privacy choices; do not claim Hush is entirely network-free.
* The `Disable analytics` patch is selected locally and its implementation suppresses Telegram's read-metrics, selected Premium-screen telemetry and dual-camera report while leaving messages/calls/notifications working ([Analytics.java](https://raw.githubusercontent.com/SysAdminDoc/HushTelegram/main/extensions/telegram/src/main/java/app/hushtelegram/extension/telegram/misc/Analytics.java#L15-L72)). This supports the owner's “nothing affected” rule, but it does not prevent Telegram traffic needed for chats or the optional translation/update functions.
* Account risk remains: Premium unlock is client-side and Telegram may ignore or notice it; Telegram may refuse signature-sensitive functions on a re-signed APK. Hush's README explicitly says it does not give away paid Premium features, so its 67-patch current release does not replace rushiranpise's Unlock Premium. The current onboarding record already accepts the rushiranpise Premium risk; owner should explicitly decide whether that acceptance carries to a Hush fallback ([onboarding risks](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/onboarding/telegram.md#L96-L99)). No evidence here establishes that either provider causes account bans; do not promise zero-ban risk.

### Other Telegram providers in `src/community/bundles.json`

Exact target-app matches in the checked-in community index are:

* `ch3thanhs/stylus` — Force system font (Telegram), plus other apps (8 total).
* `mich111discord/MightyMichs-Patches` — Unlock Telegram Premium, plus other apps (50 total).
* `newuser7171/telegram-morphe-patches-` — 20 Telegram-oriented names; already removed from the target after it failed to build.
* `Paresh-Maheshwari/paresh-patches` — Telegram-oriented names among a multi-app bundle (61 total).
* `rahul9999xda/morphe-patches` — 20 names; the 13.1.1 watch candidate.
* `rushiranpise/morphe-patches` — Telegram among a large multi-app bundle (277 total); this is the configured non-Hush fallback today.
* `sudeepcapri/morphe_patch` — Telegram.org among a multi-app bundle (18 total).
* `SysAdminDoc/HushTelegram` — 67 patches; configured Hush provider.
* `WZSE/aapam-patches` — Telegram.org among a multi-app bundle (19 total).

The community index is discovery evidence, not a compatibility/release admission. Every provider to add must pass the live release, patch fingerprint, license, and build tests; this is especially important for the watched 13.1.1 row.

### Recommended Telegram target change

Use one exclusive target, with a non-Hush primary and Hush fallback. Do **not** add Hush as an extra bundle: the owner rule says Hush is fallback/separate, and mixing it into the primary would collide with provider-selected patch names and blur provenance.

Recommended shape (after confirming the primary's live supported version and the source APK package):

```json
{
  "id": "telegram",
  "package": "org.telegram.messenger",
  "exclusive": true,
  "candidates": [
    {
      "name": "rushiranpise",
      "host": "github",
      "channel": "prerelease",
      "patch_dir": "telegram-rushiranpise",
      "options": "rushiranpise-telegram",
      "owner": "rushiranpise",
      "repo": "morphe-patches"
    },
    {
      "name": "hushtelegram",
      "host": "github",
      "channel": "prerelease",
      "patch_dir": "telegram-hushtelegram",
      "options": "hushtelegram",
      "owner": "SysAdminDoc",
      "repo": "HushTelegram",
      "fallback": true,
      "overrides": {"extra_bundles": []}
    }
  ]
}
```

The `overrides.extra_bundles: []` is defensive and follows the existing HushGram/Oxbow fallback pattern ([Instagram target](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L328-L363)); it prevents unrelated extras from being mixed into Hush's build. A separate target is not recommended today because Hush does not provide a clone/package-name patch and the target is exclusive; a second target with the same installed package would conflict in the Obtainium catalog.

### Exact onboarding/owner record required

1. In `docs/review/onboarding/telegram.md`, change the provider paragraph to: rushiranpise primary; HushTelegram fallback; Hush v0.0.21 release-tag evidence; supported Play/web package/version matrix; Morphe Manager >=2.2.0; MPP SHA-256 above; tagged patch-list blob SHA above; 67 upstream/62 locally selected; local excludes unchanged.
2. Add a “Hush fallback login” note: if `API_ID_PUBLISHED_FLOOD`, owner creates a personal app at `my.telegram.org/apps`, enters `apiId`/`apiHash` in Morphe Manager only, and never commits or pastes either value into logs/issues/metadata. Keep a second signed-in Telegram device because stock-to-patched installation may require uninstall and deletes secret chats; cloud chats return after sign-in (README).
3. State that Hush's own release check remains off; external translation is opt-in and sends message text; Firebase repair and Maps/API-key/branding/logo options remain excluded. Record that no account-ban guarantee exists and Premium unlock is not present in Hush.
4. Keep `DECISIONS.json` Rahul watch row until a real build of the 13.1.1 source passes. Add a decision row for the Hush fallback only after a smoke verifies package, source version/code, login, cloud chats, notifications, downloads, analytics switch, and no unintended network endpoint.
5. Preserve the exact release/tag/digest evidence and record the live API's `immutable:false` limitation; this is a review pin, not a signature claim.

**Recommended owner answers:** “Yes, rushiranpise remains primary; HushTelegram is fallback only.” “Yes, allow personal API credentials interactively when Telegram returns API_ID_PUBLISHED_FLOOD; never store them.” “No, do not enable Maps key, Firebase certificate repair, custom branding/logo, or external translation by default.” “No, do not promise no ban; retain the current client-side Premium risk acceptance only for rushiranpise.” “No, do not add a duplicate separate target unless a clone package and separate Obtainium identity are deliberately implemented.”

## 2. Fallbacks that do not create a one-way version door

### What the current code guarantees

* `build_attempts.plan()` tries the configured primary candidates, then fallback candidates; a target pin or `fallback:false` disables retries. Later candidates are pinned and applied with overrides ([`build_attempts.py:74-101`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/build/build_attempts.py#L74-L101)). Default is one initial attempt plus at most two fallback attempts ([`build_attempts.py:197-237`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/build/build_attempts.py#L197-L237)). A failed attempt is reset before the next; a successful later attempt writes `release/.fallback` and emits `fallback=true`.
* `preflight.effective()` overlays only the whitelisted candidate keys, pins the candidate, and leaves the rest of the target unchanged ([`preflight.py:9-23`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/preflight.py#L9-L23)). Existing examples prove the useful pattern: Facebook De-Vanced pins version 580/code 475019344/dpi; Instagram HushGram/Oxbow and MX MightyMichs clear extra bundles; ES rushiranpise fallback clears extras ([`targets.json:292-305`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L292-L305), [`targets.json:339-363`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L339-L363), [`targets.json:517-528`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L517-L528), [`targets.json:240-251`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/targets.json#L240-L251)).
* `store_chain.sh` alternates APKMirror/APKPure, applies exact/near-version checks, and refuses an APK from a different version line rather than silently downgrading ([`store_chain.sh:24-28`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/build/store_chain.sh#L24-L28), [`store_chain.sh:63-88`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/build/store_chain.sh#L63-L88)). This is already the right store-failure behavior.
* `release_notes.publish_guard()` scans non-draft/non-prerelease releases with the same tag prefix and refuses any current app version below the newest published version; its comment records the incident where a Facebook 580 fallback repeatedly displaced Hushfacebook 582. The guard applies to both primary and fallback builds ([`release_notes.py:174-193`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/build/release_notes.py#L174-L193)); `release_contract.py` runs it before emitting publication output ([`release_contract.py:113-127`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/build/release_contract.py#L113-L127)).
* Obtainium's generated import uses one repository, one prefix regex per target, `includePrereleases:false`, `fallbackToOlderReleases:true`, and version extraction from `prefix-vVERSION-bBUILD` ([`obtainium.py:36-63`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/obtainium.py#L36-L63)). It also has a no-pin Android 9/10 companion; Android still enforces same-signer updates ([`obtainium.py:79-83`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/obtainium.py#L79-L83)). Obtainium's older-release setting does not make Android accept a lower installed versionCode: the user must uninstall/downgrade manually, which can affect app data.

### Options

| Option | Phone impact | Obtainium behavior | Complexity/risk | Assessment |
|---|---|---|---|---|
| **A. Separate fallback tag prefix + separate Obtainium app/package** | Best: primary app never sees fallback shelf; a genuinely newer fallback can install only if it has a separate package/signing identity. | Requires a second regex/app identity; same package in two catalog rows is ambiguous. A tag prefix alone is not enough. | High: Hush has no clone/package-name patch; needs clone implementation, package/data migration, signer and portal/import work. | Safest end state, not a safe tag-only change. |
| **B. Stale fallback exception in `publish_guard`** | Keeps one package. A lower primary over a newer fallback still requires uninstall/downgrade; publish notes must warn clearly. | Existing feed can carry the release; Obtainium will not force a downgrade, so owner must follow the warning. | Medium: metadata decoding, age policy and tests. Risk is explicit but bounded; never allows an older fallback over a newer primary. | **Recommend now** as the least invasive way to reopen primary publication after a fallback shelf entry. |
| **C. Per-candidate pins + fallback-ineligible preflight skip** | No phone change; prevents an unusable candidate from being selected/published. | No release means no Obtainium update; does not help when only an older fallback can build. | Low/medium, but it converts “fallback” into “skip” and can still stall. | Useful admission guard, insufficient as the main answer. |
| **D. Existing store fallback chain** | No package/version change; second store may provide the same requested APK. | Transparent to Obtainium after a successful build. | Already implemented; no provider publication behavior change. | Keep, but it cannot solve the provider/version shelf door. |

### Recommended fallback policy: Option B, with strict safety rails

Implement **B** as an emergency/recovery path, not as permission to overwrite a newer primary casually:

1. Keep the existing refusal for an older **fallback** candidate when the newest shelf row is a primary release.
2. When the current candidate is **primary** and the newest same-prefix shelf row is marked fallback in its structured release metadata, allow the primary's lower version only after `N` days (recommend `N=7`) since that fallback was published. This is the explicit “fallback went stale; reopen the primary lane” condition.
3. Add a structured boolean such as `fallback_release: true` to the release summary (retain the existing human-readable `fallback` note for compatibility), and validate it in `release_notes.checked()`. Have `publish_guard()` decode the shelf row's marker instead of guessing from tag text.
4. Add a `downgrade_warning` release-note section whenever a primary is accepted below a fallback: “This version is lower than the fallback shelf entry. Android will not update an installed newer versionCode; uninstall the fallback first. Back up Telegram/secret chats and keep the signing key.” Do not imply Obtainium can perform an Android downgrade automatically.
5. Keep the normal `release_contract.py` guard ordering: inventory read first, version guard second, previous-release notes after. An unreadable release inventory must still block a fallback and never publish blind.
6. Add `PF_FALLBACK_STALE_DAYS` only as a bounded integer configuration (default 7, test override allowed); do not permit zero/negative or an arbitrary workflow input. Log the shelf tag, shelf version, age, candidate kind and warning.
7. Keep the current `build_attempts` clean reset and `.fallback` provenance. The winning candidate and source version must remain in release evidence; never turn a failed primary into a primary-looking release.

Illustrative implementation shape (not a patch):

```python
# release_notes.py
FALLBACK_STALE_DAYS = 7

def _shelf_summary(row, target):
    try:
        return decode(row.get('body'), row['tag_name'], target)
    except (ValueError, TypeError, KeyError):
        return None

def publish_guard(current, rows, fallback, now=None, stale_days=FALLBACK_STALE_DAYS):
    # existing inventory/unreadable and same-prefix newest-version scan...
    if current_is_older:
        shelf = _shelf_summary(best_row, current['target'])
        shelf_is_fallback = bool(shelf and shelf.get('fallback_release') is True)
        age_ok = published_at_age(best_row, now) >= stale_days
        recovery = (not fallback and shelf_is_fallback and age_ok)
        if not recovery:
            return existing_refusal
        # return None, but expose downgrade_warning to release rendering/metadata
    return None
```

Do not use only a tag prefix or the human prose `.fallback` file as the marker: tags can be edited and `.fallback` is not in the GitHub release body unless the release contract carries it. Do not allow a fallback release below the newest primary; that is the exact Android/shelf failure this guard was introduced to stop.

### Exact code/test list

**Code changes:**

* `src/build/release_notes.py`: validate `fallback_release` and optional `downgrade_warning`; decode shelf summaries; parse `published_at`; implement 7-day stale fallback recovery; render warning; preserve current inventory-unreadable behavior.
* `src/build/release_contract.py`: carry `fallback_release`/warning into `snapshot()` and release notes; ensure guard runs before publication output as today.
* `src/build/build_attempts.py`: keep behavior, but write an unambiguous fallback provenance value (candidate name, source app version, failure reason) into the metadata consumed by release contract. Add no automatic downgrade behavior.
* `src/etc/obtainium.py`: no behavior change for Option B; update generated app description/portal text to say an older recovery release requires uninstall/downgrade. If later choosing A, this file needs a separate package/import identity and prefix regex, not merely a second tag prefix.
* `docs/review/onboarding/*.md`: record fallback candidate version, whether it is lower than shelf, the uninstall/downgrade warning and data-loss precautions.

**Tests (must be added before merge):**

1. `tests/publish_guard_contracts.py`: older fallback below newer primary still refuses; primary below newer fallback with age 0/6 days refuses; same case at 7 days allows and emits downgrade warning; malformed/missing shelf marker refuses; draft/prerelease/other target rows do not count; unreadable inventory still blocks fallback.
2. `tests/release_contracts.py` (or the existing release-contract suite): summary round-trips `fallback_release`; marker cannot be forged by a human `.fallback` file; warning is present in rendered notes and does not leak keys.
3. `tests/build_attempts_contracts.py`: primary failure → fallback still resets checkout, applies overrides, writes provenance; fallback success does not claim `fallback_release` absent release metadata; a primary recovery build can be represented without changing the winner semantics.
4. `tests/preflight_contracts.py`: override whitelist remains closed; candidate version code still requires pinned max version; fallback candidate with `extra_bundles: []` produces the expected effective target; no per-candidate override can bypass package/signer checks.
5. `tests/store_mapping_contracts.py` and `tests/fallback_adapter_contracts.py`: APKMirror failure → APKPure same-version success; wrong-version result remains refused; near-version guard remains refused outside the same release line.
6. `tests/obtainium_contracts.py` (or generator check): one prefix/regex remains valid; `fallbackToOlderReleases` does not claim it can downgrade Android; generated JSON remains byte-stable.
7. End-to-end rehearsal: primary build fails, fallback builds, release is marked fallback; after seven test days, primary recovery is allowed with a warning; then run `python3 src/etc/preflight.py`, full test suite, release identity/signature checks, and a non-publishing phone install rehearsal. No live keys.

## Owner questions (with recommended answers)

| Question | Recommended answer |
|---|---|
| Should HushTelegram remain the Telegram primary? | **No.** Make rushiranpise/non-Hush primary and HushTelegram fallback, matching the 28-Oct Hush rule. |
| Should Hush be mixed as an extra bundle? | **No.** Keep it a candidate with `overrides.extra_bundles: []`; the target is exclusive. |
| Should Hush be a separate target now? | **No.** Same package and no clone patch would make the Obtainium identity ambiguous. Revisit only with a separately tested package/signing/data migration. |
| Can the owner enter Telegram API credentials? | **Yes, interactively only**, if login returns `API_ID_PUBLISHED_FLOOD`; create at my.telegram.org/apps. Never commit/log/share them. |
| Enable Maps credentials, Firebase repair, Hush branding/logo? | **No** by default; preserve current excludes. Firebase repair exposes original certificate to Firebase and branding/logo are unnecessary. |
| Does Hush phone home? | **Not by default for its optional release check**; it is opt-in and constrained to api.github.com. External translation is a separate explicit network path. Do not promise “no network” because Telegram, Google translation and owner-configured AI remain networked. |
| Does Hush guarantee no account ban? | **No.** No evidence establishes a ban; client-side Premium and re-signing can be ignored/noticed or break signature-sensitive features. |
| Which fallback-door option should ship? | **Option B now**, with a 7-day stale shelf marker, strict fallback-vs-primary direction, explicit downgrade warning and tests. Option A is the later safest design only after a separate clone/package identity exists. |
| Can Obtainium install an earlier release? | **It can select an older shelf entry, but Android still refuses a lower installed versionCode.** The recovery warning must require uninstall/downgrade and explain Telegram data/secret-chat consequences. |

## Evidence / limitations

* Local file/line links above refer to live `main` URLs and were checked against (assistant sandbox); line numbers can drift after future commits. The parent should preserve the commit/revision in the published record.
* Live Hush v0.0.21 was checked through GitHub API release metadata, release-tag README/patch list, release bundle metadata, license, repository metadata and recent commits. GitHub reports the release object as not immutable; no signed provenance claim is made.
* The live Hush source review covered the release-check transport, analytics, Google translation and AI translation files linked above. It did not perform a dynamic packet capture of a patched APK, so “no other phone-home behavior” is not proven beyond the reviewed source/documentation. Telegram's own normal traffic is outside this provider review.
* Community-bundle enumeration is a checked-in-index population, not proof that every provider is currently buildable or that its patches support ours. Live release/fingerprint checks remain required before adding any provider.
