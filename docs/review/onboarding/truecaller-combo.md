# Truecaller (truecaller-combo)

Package: com.truecaller
Source APK: the target's current source mapping (unchanged); the version follows the provider's compatible list.
Provider: heval99/Heval-Morphe-Patches (licence: the upstream repository LICENSE file; bundle: the one `.mpp` asset of the newest prerelease; channel: prerelease). Names below come from the live list-patches run in Explore issue #234 (24 Oct 2026, 24 patches) and the community index (compatible 26.40.5, 26.41.5).

Owner decision, 24 Oct 2026 (packet W16g): use the provider with the newest app version and the most patches. heval99 targets 26.41.5 with 24 patches; the old combo (bufferk 7 + paresh 10 + binarymend 2) targets 26.10.6. heval99 becomes primary, built alone; bufferk alone (7 patches, 26.10.6) is the fallback. The paresh and binarymend extras leave: heval99 covers what they did, and their patches fit 26.10.6 only. Enable Premium and GmsCore support stay in, so the owner can compare.

Owner approved: Enable Premium
Owner approved: GmsCore support

## Patches

Truecaller is an exclusive target, so the names are listed in `src/patches/truecaller-heval99/include-patches`:

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

Left out: `Spoof signature` (default on; BANNED rule `spoof signature`, listed in exclude-patches), and the default-off ones that remove a core feature or change sign-in: `Hide Blocking tab`, `Hide Messages tab`, `Hide business media`, `Restore classic call log`, `Use SMS for verification codes`.

## Risks

- Truecaller signs in with a phone number and its servers can see account state. Enable Premium may be ignored or noticed server-side; the owner accepts this (tested before).
- GmsCore support moves Google services to MicroG and may change the installed package, so this build can install beside the store app. Install MicroG RE first.
- Signature spoofing stays off by rule; if sign-in fails on the phone, that is the first suspect.
- The bufferk fallback has no GmsCore patch; its release notes will still say MicroG (one target-level flag).
