# Google Photos APK-source admission (key rotation), 26 September 2026

## Status: ONE EXACT-VERSION ADMISSION WITH A PINNED SIGNER ROTATION, ACTIVE ONLY AFTER MERGE

Used only after the primary APKMirror download has already failed for 7.92.0.977185651.
No patch selection, version election, ceiling, signing or publication change.

Baseline: main `9a0b7283071927f86177628eb2466e777f350397`, tree `0d56c5c8baf67472fbf3591136afeac899f34a0b`.

## Admitted artifact

| Field | Value |
|---|---|
| Version (code) | 7.92.0.977185651 (52372370) |
| Alternate | apkpure, `https://apkpure.com/google-photos/com.google.android.apps.photos/download` |
| Container | 230966267 bytes, SHA-256 `20047c44376edaac9380d01632eabd6db1087ecaca0252aad80cc5b8b3b42624` |
| Kind, ABIs, min SDK | universal APK, arm64-v8a+armeabi-v7a+x86+x86_64, 24 |

## Signer pin: both keys, each tied to its Android range

| Scheme | Android API range | Certificate SHA-256 | Anchor |
|---|---|---|---|
| V3.0 (lineage start) | 24 to 32 | `3d7a1223019aa39d9ea0e3436ab7c0896bfb4fb679f4de5fe7c23f326c8f994a` | photos.google.com assetlinks.json; APKMirror Google Photos signature |
| V3.1 (rotated) | 33 and later | `5aad2bee6db95d17e05a08d7d1e64c10a1511879154483916b6ae6c7fd9cb0c6` | privacyguides/AppVerifier Google Play reference lists 3D7A... and 5AAD... together |

The consumer accepts this original only when `apksigner verify` succeeds, v3 and v3.1 both verify,
there is exactly one signer, and the ranged V3.0 and V3.1 identities are exactly this pair with
exactly these ranges. A single key, the new key alone, different ranges, a third range, V3.2, an
unlabelled or legacy identity, or a second source stamp all refuse. The source stamp is never
used as the app identity.

## Why this does not loosen anything else

- `parse_signers` is unchanged and still refuses V3.1. It is the reader for finished APKs, which
 must carry the one CI certificate.
- Single-key admissions (reddit, telegram, facebook, truecaller-combo) keep the exact old reader;
 the rotation reader runs only when an admission carries `signer_rotation`.
- If Google rotates again or changes ranges, verification refuses and the primary path is
 unaffected. A new version always needs a new reviewed admission anyway.

## Evidence

- Qualification record: [photos-7.92.0.977185651-apkpure.json](source-qualifications/photos-7.92.0.977185651-apkpure.json).
- Observed verifier output: `tests/fixtures/apksigner-37-photos-v31-rotation.txt` (SDK 37.0.0).
- Owner Cloud Shell consumer check on this exact change: primary mapping removed (simulated failure), fallback re-downloaded the admitted original byte-identical, verified 1 file(s) against the pin, receipt valid, patcher input 230966267 bytes sha256 20047c44376edaac9380d01632eabd6db1087ecaca0252aad80cc5b8b3b42624.
- Regression on the same change: reddit HANDOFF_VERIFIED, telegram HANDOFF_VERIFIED, facebook HANDOFF_VERIFIED, truecaller-combo HANDOFF_VERIFIED; wrong-second-key control refused the same real bytes.

## Limits

- Exact version only. When the provider moves past 7.92.0.977185651 this admission stops applying.
- build.sh patches arm64-v8a only; the universal original still yields an arm64 output.
- Primary failure was simulated in disposable clones by removing the primary mapping.
- Not a device, install or runtime-safety test. Finished-APK gates still run before publication.
- Owner run: pf-packet-d-v1 sha256 374b370fa39f479c8d2fac5fdb9472d35b61a49fe05b225b4f271fa80538b9be, 2026-09-26 15:05 UTC.
