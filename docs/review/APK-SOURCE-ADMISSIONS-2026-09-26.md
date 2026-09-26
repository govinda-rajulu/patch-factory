# APK-source admissions, 26 September 2026

## Status: 4 EXACT-VERSION ADMISSIONS, ACTIVE ONLY AFTER MERGE

Each admission is one exact version and one exact original container. It is used only after the
existing primary downloader has already failed for that same version. It does not change patch
selection, version election, ceilings, signing, publication or any other target.

Baseline: main `037bf8f96685b4ad7796e4ccee4fe0b8f79ea776`, tree `88c35071dc6472a56f8a9da26547c8362952f7f1`.

## Admitted

| Target | Version (code) | Alternate | Container bytes / SHA-256 | Original signer SHA-256 | Kind, ABIs, min SDK |
|---|---|---|---|---|---|
| reddit | 2026.38.0 (2638001) | apkmirror | 68282446 / `3ab0a58a4ce8425d3e9bd40574f3952d1c1eda6f3394a4cd07ee1c2dde79995c` | `970b91143813b4c9d5f3634f672c9fcaa5621b4efaaedafd6c235cbbb869736f` | bundle, arm64-v8a, 29 |
| telegram | 12.10.1 (70382) | apkpure | 125179933 / `f88359ba39e1b3c44d6f86f3e2a435109c456715a8996d8388fccbbbbc7362f8` | `49c1522548ebacd46ce322b6fd47f6092bb745d0f88082145caf35e14dcc38e1` | apk, arm64-v8a+armeabi-v7a+x86+x86_64, 23 |
| facebook | 490.0.0.63.82 (457215604) | apkpure | 63922261 / `6f0b901f03af5c511d92338b1179a8411542e06cf4e6b9e151b90be4f3e29371` | `e3f9e1e0cf99d0e56a055ba65e241b3399f7cea524326b0cdd6ec1327ed0fdc1` | apk, arm64-v8a, 28 |
| truecaller-combo | 26.10.6 (2610006) | apkpure | 110330489 / `b453dc1d4517f6c7bb8a049b7f155cc52ec452d8d8558076058bbd0e22f3f6e5` | `7712b5f255f2c85b8b164519116ac4381bb9a3582dcdd2b73ac06ee7464913ae` | bundle, arm64-v8a, 26 |

## Evidence per admission

### reddit

- Publisher anchor: PR85 reviewed evidence reddit-2026.38.0-originals.json (27 originals, SDK29, ARM64) (signer present).
- Independent reference: Reddit publisher signer as recorded in the PR85 originals review.
- Qualification record: [reddit-2026.38.0-apkmirror.json](source-qualifications/reddit-2026.38.0-apkmirror.json).
- Owner Cloud Shell consumer check on this exact change: primary mapping removed (simulated failure), fallback re-downloaded the admitted original byte-identical, verified 27 split file(s), receipt valid, patcher input 83346417 bytes sha256 e64b6020b222d5f58c1b06d7b5099c8bb126ba9814b0e5c8d08ec335d01767c8.

### telegram

- Publisher anchor: https://telegram.org/.well-known/assetlinks.json (signer present).
- Independent reference: privacyguides/verified-apps#498 (Google Play + AppVerifier).
- Qualification record: [telegram-12.10.1-apkpure.json](source-qualifications/telegram-12.10.1-apkpure.json).
- Owner Cloud Shell consumer check on this exact change: primary mapping removed (simulated failure), fallback re-downloaded the admitted original byte-identical, verified 1 split file(s), receipt valid, patcher input 125179933 bytes sha256 f88359ba39e1b3c44d6f86f3e2a435109c456715a8996d8388fccbbbbc7362f8.

### facebook

- Publisher anchor: https://www.facebook.com/.well-known/assetlinks.json (signer present).
- Independent reference: privacyguides/verified-apps#752 (Google Play).
- Qualification record: [facebook-490.0.0.63.82-apkpure.json](source-qualifications/facebook-490.0.0.63.82-apkpure.json).
- Owner Cloud Shell consumer check on this exact change: primary mapping removed (simulated failure), fallback re-downloaded the admitted original byte-identical, verified 1 split file(s), receipt valid, patcher input 63922261 bytes sha256 6f0b901f03af5c511d92338b1179a8411542e06cf4e6b9e151b90be4f3e29371.

### truecaller-combo

- Publisher anchor: https://www.truecaller.com/.well-known/assetlinks.json (signer present).
- Independent reference: APKMirror Truecaller certificate listing (CN=truecaller).
- Qualification record: [truecaller-combo-26.10.6-apkpure.json](source-qualifications/truecaller-combo-26.10.6-apkpure.json).
- Owner Cloud Shell consumer check on this exact change: primary mapping removed (simulated failure), fallback re-downloaded the admitted original byte-identical, verified 5 split file(s), receipt valid, patcher input 109997838 bytes sha256 80d9639d9f41ddde1e9edb752cdf2def0dd20c0ea8378b95551a42501c0b1b25.

## Not admitted

- photos: 7.92.0.977185651 APKPure original verified 26 Sep 2026 but signer rotates (v3.1 5aad2bee for SDK33+, v3.0 3d7a1223 for SDK24-32); rotation-aware admission not implemented.
- youtube, adguard, primevideo, esfile, instagram, hotstar, edge, mxplayer, keymapper: unchanged, no qualified alternate.

## Code changes that made these admissible

- `artifact_identity.parse_signers` also recognises the SDK37 `V2 Signer:` label, which apksigner prints
  when v2 is the highest verified scheme (Facebook). Exactly one identity is still required; V3.1
  rotation lines remain unrecognised and refuse (Photos).
- `original_apk.parse` allows a missing minimum SDK only on `config.X` or `FEATURE.config.X` splits
  and returns None, never a guessed value. The consumer still requires the base SDK to equal the
  reviewed variant and applies the ceiling/equality gate to every split that declares an SDK.
- The loopback browser wait in `utils.sh` is 60 s instead of 15 s. On 26 Sep 2026 every exact APKPure
  page failed at 15 s (12 of 12 attempts) and loaded in 16 to 19 s with 60 s (8 of 8).

## Limits

- Exact versions only. When the provider moves past an admitted version, that admission stops applying.
- Patch/output pilots were run for Reddit only (PR85). The finished-APK identity, signature, SDK and
  native gates still run before any publication, for every target.
- build.sh patches arm64-v8a only; a universal original (Telegram) still yields an arm64 output.
- Primary failure was simulated in disposable clones by removing the primary mapping; no real outage
  was observed for these checks. Not a device, install or runtime-safety test.
- Owner run: pf-packet-b-v1 sha256 b9b987f2563589bc4caf30b3f733479f792eb9d95be9d60abb963e182079bbc2, 2026-09-26 13:52 UTC.
