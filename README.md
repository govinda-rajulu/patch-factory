# patch-factory

Patches Android APKs in GitHub Actions and publishes signed, per-version releases.
Downloads: **https://govinda-rajulu.github.io/patch-factory/**

Target device: Android 10, arm64-v8a, not rooted.

## Build

    gh workflow run "1. Manual Patch" -f target=youtube

Targets live in `src/targets.json`. Currently enabled: `youtube`, `photos`, `truecaller`.

## How a build works

`src/build/build.sh ` does all of it:

1. reads the target from `src/targets.json`, refuses if `enabled` is false
2. downloads morphe-desktop, then `resolve.sh` elects the winning provider
3. `get_patches_key` with the winner's `patch_dir`
4. `get_apk` from APKMirror
5. `check_sdk.sh` against `min_sdk_ceiling` (report-only)
6. `split_arch` to `./release/-arm64-v8a.apk`
7. writes `.version` and `.tagprefix`, tag becomes `-v`
8. fails loudly if no APK was produced

`morphe.sh` is a wrapper for `build.sh youtube`.

## Adding a target

Add an entry to `src/targets.json` with a `tag_prefix`, create
`src/patches//{include,exclude}-patches`, ensure
`src/options/.json` exists and is a **JSON array**, then add the id
to the dropdown in `.github/workflows/manual-patch.yml`.

**`tag_prefix` must never contain a provider name.** Obtainium matches on the
tag; a provider change would silently orphan the app. `youtube-morphe` is a
grandfathered exception.

See [RECOVERY.md](RECOVERY.md) for the signing key and everything that has burned us.
