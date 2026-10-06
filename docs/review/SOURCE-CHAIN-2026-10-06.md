# Source chain: second store with the same gates (6 October 2026)

Owner question, 6 Oct 2026: "If apkpure fails why didn't it try apkmirror?" Run 37448758026
(Reddit, after PR #148): APKPure had no download link for 2026.40.0 (it lists 2026.39), the
qualified fallback refused because its only Reddit admission is 2026.38.0, and the build stopped.
APKMirror lists 2026.40.0 with an arm64-v8a bundle (480-640dpi, code 2640011, Android 10+).

## Shipped in packet S1

- `src/build/store_chain.sh` `try_other_store`: when the configured store fails, the other store
  is tried for the same exact version, if `apps.json` maps the package there. Then the qualified
  fallback runs as before. Used by `build.sh` and the preparation adapter `source_download.sh`.
- Trust is unchanged, not widened: the second store's file passes the same gates as a primary
  download (package from the manifest, SDK ceiling, pinned `version_code` where set, finished
  identity, applied-vs-requested). A primary download has never had more than these gates.
- APKMirror mappings added for Reddit, Instagram and Edge; their targets gain `arch: arm64-v8a`
  (Reddit also `dpi: 480-640dpi`, the only ARM64-only row with Android 10+ for 2026.40.0; the
  universal rows need Android 12L+ and fail the SDK ceiling). Key Mapper stays APKPure-only: the
  APKMirror listing is the FOSS/GitHub build, a different distribution.
- Not mapped for APKPure today: YouTube, YouTube Music, AdGuard, Photos, Truecaller. Their chain
  ends at the qualified fallback, as before.

## Next (packet S2, design only)

1. **Publisher certificate pins per package.** Verify every original APK/split with apksigner
   before merging, against a pinned publisher certificate (rotation pairs allowed), on every
   store path including the primary. Evidence exists for 5 of 15 packages (Photos with a v3.0/v3.1
   pair, Truecaller, Facebook, Reddit, Telegram, from the 26 Sep admissions); the other 10 need a
   recorded first observation and owner approval. Reusable code: `artifact_identity.original_signer`
   and `parse_original_signers`, `source_fallback` original inspection.
2. **Version step-down.** If the newest patch-supported version is in no store, try the next
   lower supported version from the patcher's own `-x` list, at most two steps, each with the full
   gate set; never below the last published version.
3. Record the store used in the build evidence and release notes.
4. Tests that pin exact-container admissions stay for the qualified fallback; new negative tests:
   wrong signer, wrong package, wrong version, x86-only bundle, zip-slip, symlink.
