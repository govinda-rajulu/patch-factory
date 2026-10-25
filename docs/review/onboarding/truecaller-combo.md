# Truecaller (truecaller-combo)

Package: com.truecaller
Source APK: the target's current source mapping (unchanged); the version follows the provider's compatible list.

**Current (W16j, 25 Oct 2026):** heval99/Heval-Morphe-Patches is primary on 26.41.5 and builds alone (its candidate overrides drop the extras; src/build/build_attempts.py applies a lone primary's overrides since W16j). The backup is the combo: bufferk/morphe-patches with the paresh-patches and binarymend/morphe-patches extras (19 names, 26.10.6). Owner, 25 Oct 2026: "Make heval99 Truecaller's main provider, with the 19-patch set as the backup."
Provider: heval99/Heval-Morphe-Patches (primary since W16j, fallback in W16h; licence: GPL-3.0, the LICENSE file at https://github.com/heval99/Heval-Morphe-Patches; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). Names below come from the live list-patches run in Explore issue #234 (24 Oct 2026, 24 patches) and the community index (compatible 26.40.5, 26.41.5).

Owner decision, 24 Oct 2026 (packet W16g): use the provider with the newest app version and the most patches. heval99 targets 26.41.5 with 24 patches; the old combo (bufferk 7 + paresh 10 + binarymend 2) targets 26.10.6. heval99 becomes primary, built alone; bufferk alone (7 patches, 26.10.6) is the fallback. The paresh and binarymend extras leave: heval99 covers what they did, and their patches fit 26.10.6 only. Enable Premium and GmsCore support stay in, so the owner can compare.

Owner approved: Enable Premium
Owner approved: GmsCore support

## heval99 names (primary in W16g, fallback since W16h)
- Hide Blocking tab: owner took it in the Needs you review file, 2026-10-25 (N-c4f7b1)
- Hide business media: owner took it in the Needs you review file, 2026-10-25 (N-2a7712)
- Hide call log filters: owner took it in the Needs you review file, 2026-10-25 (N-7de88d)

Truecaller is an exclusive target; the heval99 fallback's names are in `src/patches/truecaller-heval99/include-patches`:

- Disable ads: default on; ad removal.
- Hide promotions: default on; promotion removal.
- Hide Wear OS settings: default on; clutter.
- Disable auto-launch: default on; stops the app starting itself.
- Disable contact upload: default on; privacy, stops the contact book upload.
- GmsCore support: default on; owner keeps it (24 Oct 2026) to compare. Needs MicroG RE on the phone.
- Disable nags: default on; prompt removal.
- Disable telemetry: default on; tracking removal.
- Disable update prompts: default on; prompt removal.
- Enable Premium: default on; owner approved (tested a premium patch for this app before).
- Hide Assistant tab: default off; the old combo hid it (paresh), kept for parity.
- Hide Premium tab: default off; the old combo hid it (paresh), kept for parity.
- Hide family button: default off; the old combo hid Family Protection (paresh), kept for parity.
- Hide Scam feed: default off; the old combo hid the Scams tab (paresh), kept for parity.
- Show caller number in call log: default off; shows information, removes nothing.
- Fix T9 contact search: default off; a bug fix.
- Remove screenshot restriction: default off; lets the owner take screenshots.
- Hide after-call screen for contacts: default off; the after-call popup only for saved contacts.

Left out: `Spoof signature` (default on; BANNED rule `spoof signature`, listed in heval99's exclude-patches; the combo's exclude list is empty). W16i also lists `Restore classic call log` and `Use SMS for verification codes` there: left out on purpose in W16g, they were only absent, so the Selection rule offered them again in PR #243, and the default-off ones that remove a core feature or change sign-in: `Hide Blocking tab`, `Hide Messages tab`, `Hide business media`, `Restore classic call log`, `Use SMS for verification codes`.

## Risks

- Truecaller signs in with a phone number and its servers can see account state. Enable Premium may be ignored or noticed server-side; the owner accepts this (tested before).
- GmsCore support moves Google services to MicroG and may change the installed package, so this build can install beside the store app. Install MicroG RE first.
- Signature spoofing stays off by rule; if sign-in fails on the phone, that is the first suspect.
- The combo has no GmsCore patch and the target-level MicroG note is off (W16h). If the heval99 fallback wins, its GmsCore support needs MicroG RE.

## W16h (25 Oct 2026): back to the combo

The W16g smoke (run 40108958168) stopped at "needs SDK 32, device is 29". That was the APK
variant, not the version: APKMirror has three 26.41.5 variants (Android 12L+ universal, Android 8.0+
and Android 10+ arm64, 480-640dpi) and the picker took the first row. The picker now skips rows above
the cap (L088). The owner found the Android 10+ upload (25 Oct 2026).
The combo (bufferk primary with paresh and binarymend extras, 26.10.6, 19 patches) is primary again;
paresh and binarymend come back with their W16f include lists. heval99 stays as a fallback on its own versions
(no extras); its smoke on 26.41.5 with the Android 10+ variant decides whether it becomes primary. If it ever
wins, MicroG RE is needed for GmsCore support (the target-level MicroG note is off for the combo).

Provider: Paresh-Maheshwari/paresh-patches on GitLab, gitlab:82031658 (extra; licence: GPL-3.0-or-later per the GitLab API, read by the owner sweep on 25 Oct 2026; bundle: the newest prerelease `.mpp`; channel: prerelease). Restored.
Provider: binarymend/morphe-patches (extra; licence: GPL-3.0, the LICENSE file (blob f288702d, read through the GitHub API on 25 Oct 2026) at https://github.com/binarymend/morphe-patches; bundle: the newest prerelease `.mpp`; channel: prerelease). Restored.

Restored names (as built on main until W16g; each is back in its W16f list):
- Truecaller Premium: paresh extra, restored from the combo built since 9 Oct 2026.
- Hide Premium tab: paresh extra, restored from the combo built since 9 Oct 2026.
- Hide Premium from settings: paresh extra, restored from the combo built since 9 Oct 2026.
- Neutralize third-party SDKs: paresh extra, restored from the combo built since 9 Oct 2026.
- GMS sign-in bypass: paresh extra, restored from the combo built since 9 Oct 2026.
- Disable telemetry: paresh extra, restored from the combo built since 9 Oct 2026.
- Disable update check: paresh extra, restored from the combo built since 9 Oct 2026.
- Hide Assistant tab: paresh extra, restored from the combo built since 9 Oct 2026.
- Hide Family Protection button: paresh extra, restored from the combo built since 9 Oct 2026.
- Hide Scams tab: paresh extra, restored from the combo built since 9 Oct 2026.
- Remove Ads: binarymend extra, restored from the combo built since 9 Oct 2026.
- Disable Telemetry: binarymend extra, restored from the combo built since 9 Oct 2026.
