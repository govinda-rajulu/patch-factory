# patch-factory

Patches Android APKs in GitHub Actions and publishes signed, per-version releases.
Downloads: **https://govinda-rajulu.github.io/patch-factory/**

Target device: Android 10 (SDK 29), arm64-v8a, not rooted.

## Build

    gh workflow run "1. Manual Patch" -f target=youtube

Targets live in `src/targets.json`. Enabled: `youtube`, `photos`, `truecaller`,
`truecaller-combo`. Disabled: `adguard`.

## How a build works

`src/build/build.sh TARGET` does all of it:

1. reads the target from `src/targets.json`, refuses if `enabled` is false
2. downloads morphe-desktop, then `resolve.sh` elects the winning provider
   and settles the app version
3. renames the winner's bundle `09-NAME.mpp`, then fetches every
   `extra_bundles` entry as `01-NAME.mpp`, `02-...` via `fetch_bundle.sh`,
   and asserts the expected bundle count
4. `get_patches_key` with the winner's `patch_dir`
5. keeps the lowest-numbered bundle in the cwd for `split_arch`'s glob and
   passes the rest as explicit `-p` flags, because `patch` is not variadic
6. `get_apk` from APKMirror
7. `check_sdk.sh` against `min_sdk_ceiling` (report-only)
8. `split_arch` to `./release/APKNAME-arm64-v8a.apk`
9. writes `.version`, `.tagprefix` and `.provider`; tag becomes `PREFIX-vVERSION`
10. fails loudly if no APK was produced

`morphe.sh` wraps `build.sh youtube` and ignores any argument you give it.

## Adding a target

1. add an entry to `src/targets.json` with a `tag_prefix`
2. create `src/patches/DIR/{include,exclude}-patches`
3. create `src/options/NAME.json` containing a **JSON array**, `[]` if empty
4. add the id to the dropdown in `.github/workflows/manual-patch.yml`,
   or `workflow run` will be rejected with HTTP 422
5. push, wait for **3. Validate** to go green, then dispatch

**`tag_prefix` must never contain a provider name.** Obtainium matches on the
tag; a provider change would silently orphan the app. `youtube-morphe` is a
grandfathered exception.

## Multi-provider targets

A target may load bundles from several patch repos at once, on github or gitlab.
One candidate wins and decides the app version and patch selection; anything in
`extra_bundles` is loaded alongside it. Duplicate patches are switched off by
name in `exclude-patches`, which matches across every loaded bundle.

`truecaller-combo` is the reference example: bufferk (github) as winner, paresh
(gitlab) as an extra, 17 patches loaded, 11 applied, 6 duplicates disabled.

A gitlab source needs `project_id`, because its release assets live at opaque
upload URLs that must be read from the API.

See [RECOVERY.md](RECOVERY.md) for the signing key, the cancel window, and
everything that has burned us.
