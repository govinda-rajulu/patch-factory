# Preserve resources in ES File Explorer and MX Player

## Decision and scope

On 19 September 2026 the owner delegated review of three optional FTL resource
patches with a reliability-first goal. The selected outcome is to exclude
`APK Junk Cleanup`, `Remove Duplicate Graphics` and `Remove Languages` in both
`esfile-ftl` and `mxplayer-ftl`. These six selections previously had unresolved
CONFIRM approval; this is an explicit exclusion decision, not approval to apply
them or a claim that previous APKs were broken.

Remove each name from its include list and add it once to its same-bundle exclude
list. Retain every other include/exclude entry and order, the Paresh MX license
selection, existing options, providers, source/version/SDK limits, policy files
and Remove Debug Info quarantine. No phone data, installed apps, old APKs or
releases are changed by this source configuration edit.

## Why

- **Remove Languages:** the reviewed implementation deletes language-qualified
  resource directories across resource packages, retaining selected exact
  variants. Its reviewed defaults are `en`, `en-rIN` and `ru`; an unqualified
  language does not automatically preserve every regional variant. There is no
  reviewed per-device language requirement here. Keeping shipped translations
  avoids unnecessary loss of language coverage.
- **Remove Duplicate Graphics:** the reviewed implementation prioritizes xhdpi
  by default and deletes same-named files in other drawable/mipmap directories.
  It compares filenames, not image byte identity, and can remove files under
  different resource qualifiers. Its option prose and implementation do not
  fully agree about fallback/icon behavior. Retaining original resources avoids
  assuming all those variants are interchangeable.
- **APK Junk Cleanup:** more than cache cleanup. Reviewed rules remove license/
  notice files, baseline profiles, assorted metadata and asset files/directories,
  including app-specific entries. Runtime irrelevance is not established for
  each file in these exact two source APKs. Native-ABI stripping is off by default
  in the patch; the existing build's own ARM64 selection remains unchanged.

The tradeoff is potentially larger APKs. No size saving or runtime improvement
has been measured against the exact upcoming inputs, so resource stripping is
not worth adding to a reliability-focused release campaign.

## Evidence and limits

Upstream `dev` source was read on 19 September 2026:

- [Language cleanup](https://github.com/BlazeFTL/FTL-Patches/blob/dev/patches/src/main/kotlin/app/ftl/patches/ApkCleanup/LangCleanPatch.kt),
  Git blob `257ed774a535f33fac5463c4c8219e61f23dbd11`.
- [Drawable cleanup](https://github.com/BlazeFTL/FTL-Patches/blob/dev/patches/src/main/kotlin/app/ftl/patches/ApkCleanup/DrawableCleanPatch.kt),
  Git blob `7078fcc14dfb229a932dfd9183aa92dd4b5cb44e`.
- [APK junk cleanup](https://github.com/BlazeFTL/FTL-Patches/blob/dev/patches/src/main/kotlin/app/ftl/patches/ApkCleanup/ApkJunkClean.kt),
  Git blob `350194024e05eebca4f0be341b7a569c4cb24f19`.

These are reviewed source descriptions, not proof that a previously consumed
published bundle was built from those exact blobs. The existing local patch
inventory also describes the three as optional resource-reduction patches.
No upstream code is vendored. Actual future bundle resolution and requested/
applied checks still apply; local argv fixtures are not APK or phone tests.

Fresh release publication needs its own exact target/commit approval. Reddit's
exact-version source remains unresolved and is not silently replaced with a
latest-version download. Release cleanup remains a separate approved operation.
