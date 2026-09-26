# APK-source fallback candidate, 26 September 2026

## Status: PREPARED CANDIDATE, NOT ACTIVATION-READY

Owner scope: prepare and test fallbacks across all 14 enabled apps; no merge or publishing.
Baseline: main `b5ab2b3fcc171c14c90bd75956f3366d3f8aec52`, tree
`c084702d95941ea6adf2962dd7dbc6653ef14661`, rechecked through the public GitHub API.
Local parent is the already-reviewed premerge commit `1c08642795744d50a1732e8040045437d338a621`
with that exact same tree. Delivery must gate on the real merged main/tree, not the local parent.

**14 targets covered, ZERO qualified source admissions. This candidate by itself does not recover current download failures.**
No source/patch selection, signing setting, target ceiling, credential, release, issue, PR or remote branch
was changed. No real APK downloaded, no actual Android crypto verification performed, and no device tested.

## Implemented in the candidate

Both legacy Build and prepared-source downloads invoke the same fallback gate only after their existing
primary downloader returns nonzero. Successful primaries and their established version-selection rules
remain unchanged. An integrity/SDK failure after a nominally successful primary does not trigger a bypass.

Admission is deliberately exact-version and exact-container, not an unlimited store switch. It requires
reviewed original container bytes/hash, original publisher signer anchor, package, version name/code,
variant compatibility, a specific app-scoped mapping and a committed qualification record. Existing
GitHub patch-provider candidates/extras are unrelated and are unchanged.

The alternate runs in a fresh retained directory with a restricted environment and no signing/API tokens.
It disables latest/nearest-version selection, preserves originals before APKEditor, checks bounded ZIPs,
every split's identity/SDK/certificate, ARM64 availability, and post-merge package/version/SDK. All checks
precede exposing an alternate to patching. Partial primary output is preserved, not silently deleted.

A secret-free receipt is bound into direct input capture/final evidence and the sealed prepared-source
lock. Qualification files are included in the input recipe fingerprint. Old source-observation records
remain reportable; prepared packets from old code are not migrated into new code. Prepared input packets
are already bound to an exact commit/run/dependency recipe and must be regenerated together.

The candidate adds three contract modules discovered by the existing Validate pattern; no workflow,
permission, manual dispatch, publication or merge is added.

## All-target source coverage

Metadata below describes discovery, NOT acceptance of downloaded artifacts. All rows are blocked until
the original artifact and publisher/variant evidence is reviewed. Existing configured URLs do not prove
that a store currently serves the correct app or requested version.

| Target | Package | Primary | Alternate metadata | Specific boundary |
| --- | --- | --- | --- | --- |
| youtube | `com.google.android.youtube` | apkmirror | [apkpure](https://apkpure.com/youtube-app/com.google.android.youtube) | No artifact bytes/signer comparison; listing identity alone cannot establish a safe fallback. |
| adguard | `com.adguard.android` | apkmirror | No verified apkpure listing | Official AdGuard APK is a separate potential source, NOT APKMirror or the Play Content Blocker. No reviewed official-source adapter or APKPure mapping. |
| photos | `com.google.android.apps.photos` | apkmirror | [apkpure](https://apkpure.com/google-photos/com.google.android.apps.photos) | No artifact bytes/signer comparison; APKPure listing is metadata only. |
| truecaller-combo | `com.truecaller` | apkmirror | [apkpure](https://apkpure.com/truecaller-caller-id-block-for-android-2024/com.truecaller) | Bundle split set, version, and signer still need artifact-level checks. |
| primevideo | `com.amazon.avod.thirdpartyclient` | apkmirror | [apkpure](https://apkpure.com/x/com.amazon.avod.thirdpartyclient/download) | Configured APKPure endpoint is not independently verified here; no artifact bytes/signers. |
| esfile | `com.estrongs.android.pop` | apkmirror | [apkpure](https://apkpure.com/x/com.estrongs.android.pop/download) | Current official-store availability unclear; APKPure endpoint unverified; no artifact bytes/signers. |
| facebook | `com.facebook.katana` | apkmirror | [apkpure](https://apkpure.com/x/com.facebook.katana/download) | No artifact bytes/signer comparison; target max version 490.0.0.63.82 must be enforced separately. |
| instagram | `com.instagram.android` | apkpure | [apkmirror](https://www.apkmirror.com/apk/instagram/instagram-instagram/) | APKMirror listing identity is verified, but no selected-version artifact/signature comparison. |
| reddit | `com.reddit.frontpage` | apkpure | [apkmirror](https://www.apkmirror.com/apk/redditinc/reddit/) | No artifact bytes/signer comparison; APKMirror split variants need selection validation. |
| hotstar | `in.startv.hotstar` | apkmirror | [apkpure](https://apkpure.com/x/in.startv.hotstar/download) | APKPure endpoint not independently verified; no artifact bytes/signers. |
| edge | `com.microsoft.emmx` | apkpure | [apkmirror](https://www.apkmirror.com/apk/microsoft-corporation/microsoft-edge/) | Observed APKMirror signature labels are listing metadata, not a local artifact signer verification; no bytes available. |
| mxplayer | `com.mxtech.videoplayer.pro` | apkmirror | [apkpure](https://apkpure.com/x/com.mxtech.videoplayer.pro/download) | No legitimate APKPure Pro mapping established; paid-license/provenance and artifact signer checks remain unresolved. |
| telegram | `org.telegram.messenger` | apkmirror | [apkpure](https://apkpure.com/x/org.telegram.messenger/download) | APKPure endpoint not independently verified; no artifact bytes/signers. |
| keymapper | `io.github.sds100.keymapper` | apkpure | [apkmirror](https://www.apkmirror.com/apk/keymapperorg/key-mapper-github-version/) | Located APKMirror listing is the FOSS/GitHub variant. Package match alone does not make it interchangeable with the configured distribution. |

## Why no admissions were fabricated

The previous report counted six apps with nonempty metadata in both store mappings. That is a config
coverage count, not six working fallbacks. Public research found seven package-matching listing candidates
among the eight missing mappings, but Key Mapper is a different named distribution and AdGuard has no
verified APKPure mapping. MX Player Pro's configured APKPure URL is unverified; the free MX package is
not an acceptable substitute. Official AdGuard distribution is independent of APKMirror and is a future
adapter candidate, not a currently implemented fallback.

The current repository's CI signing certificate is for patched OUTPUTS, not original upstream APKs.
A certificate printed on a listing page is not a cryptographic check of a downloaded APK. A merged APK
usually cannot prove the original split signatures; therefore the new gate runs before merging.

## Qualification required before the first activation

1. Select the exact patch-compatible version already resolved by the current build, under its existing
   ceiling. Retain package, distribution variant, complete split set and ARM64/SDK evidence. No newest-
   version substitution; Facebook stays <=490.0.0.63.82, MX stays <=1.93.4.
2. Obtain the original alternate container, without merging/repacking. Inspect every split with the real
   Android tools. Retain original container hash/size and each split's verified signer and identity.
3. Independently establish the publisher certificate/variant anchor from an accepted original or an
   authoritative publisher record. Merely observing the same signer on two untrusted sites is insufficient.
   Never substitute a patched release or the CI key. Do not upload keys/tokens or private account data.
4. Record the evidence and one exact-version admission in a separately reviewed change. The booleans in
   a qualification record summarize human review; they do not manufacture authenticity. New versions or
   changed container bytes need new qualification. No wildcard/default admission.
5. Run a nonpublishing real-run pilot before broader activation. Keep this separate from merge approval,
   patch selection, store-account access and phone installation.

Strict split metadata checking may refuse a legitimate split with absent versionName/SDK metadata.
That is an explicit compatibility limit, not authority to infer missing values. Signing rotations or a
legitimate repack with a new digest also refuse until reviewed. Official AdGuard and other-source adapters,
automatic latest-version trust enrollment, and general fingerprint closure are NOT delivered here.

## Verification scope

Synthetic fixtures test positive and negative policy/identity gates, raw-store download sequencing,
full CLI subprocess boundaries, original signature failure before merging, partial preservation,
prepared-source receipt transport, final-report binding and tampering refusal. Network, publisher keys,
Android readers/verifier and APKEditor are fixture processes in the full CLI tests. They are not a real
source-availability, Android signature or device certification.

Separate reviewer passes found a snippet-status regression, a missing receipt consumer and a stale
file-glob assertion; all were corrected before the final gate run. The earlier claim that normal APK
functions necessarily returned the short-circuit status was too broad: later shell conditionals affect
that status. Actual full adapter tests now check primary success as well as the extracted snippets.

See the delivery GATE-RESULTS.json for exact commands, outcomes, counts and unavailable tools. Suite
counts overlap because existing unittest imports expose some of the same tests; never add them together
as a unique-test count. Shellcheck/real Android tools are unavailable in the assistant sandbox. The
sandbox has no internet access; public web metadata was read separately.

## Nothing to run against the repository yet

This is an unapplied review packet. No installer, commit, push, PR, merge, workflow dispatch, patched APK,
publication, issue comment or closure is authorized by downloading it. Current working copies and all
retired September-26 controllers remain untouched. The next substantive step is original-APK qualification,
not another blind download-source switch.
