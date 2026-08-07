# patch-factory - recovery

Patches Android APKs in GitHub Actions, publishes signed releases, consumed by
Obtainium. Target device: Android 10, arm64-v8a, not rooted.

## Signing key - READ FIRST
- Alias: `factory`. Same key forever. Losing it means uninstall and clean
  reinstall of every app, permanently.
- The key file is NOT in this repo and must never be. `.gitignore` blocks `*.keystore`.
- Offline copies: TODO_WRITE_WHERE_YOU_PUT_IT
- Secrets: `KEYSTORE_B64`, `KEYSTORE_PASS`, `KEYSTORE_ALIAS`.

## Build it

    gh workflow run "1. Manual Patch" -f target=youtube      # or photos, truecaller
    gh run watch

Two minutes per target. Weekly cron polls Morphe for youtube only.

## Layout
- `src/targets.json` - the source of truth. Every target, its candidates,
  `tag_prefix`, `min_sdk_ceiling`, `enabled`.
- `src/build/build.sh` - the build, generic over target id.
- `src/build/morphe.sh` - wrapper for `build.sh youtube`.
- `src/build/resolve.sh` - elects a provider, prints WINNER / VERSION / PATCHES / MPP.
- `src/build/check_sdk.sh` - minSdk gate, four readers, report-only.
- `src/build/utils.sh` - upstream engine. `split_arch` at ~line 830. Do not edit.
- `src/patches/
/{include,exclude}-patches` - patch selection, one exact name per line.
- `src/options/.json` - **must be a JSON array**, not an object.
- `docs/` - the GitHub Pages download site. Nothing else goes in here.
- `reference/` - notes, patch dumps, FAQ.

## Never exclude
GmsCore support (MicroG breaks), Spoof video streams (playback breaks).

## Hard-won lessons
- Never let an AI write files via the GitHub Contents API. It silently ate every
  backslash escape in utils.sh, right byte count, broken file. Edit in a
  terminal, diff against upstream.
- Never paste base64 through a phone clipboard. It truncates. Pipe it:
  `gh secret set NAME < file`
- EOFException on the keystore means the secret is truncated, not a wrong password.
- After any file write, read it back and check byte size.
- **An options file of `{}` fails the whole patch step.** morphe-desktop wants an
  array. `[]` is the correct empty value. Two files shipped as `{}` and killed
  both new targets on their first run. CI now guards this.
- **`tag_prefix` must not contain the provider name.** A provider change would
  break Obtainium matching, and the prune step deletes by prefix, so the old
  releases become unprunable. `youtube-morphe` is grandfathered.
- check_sdk exiting 0 used to mean "could not read", which looked identical to a
  pass. Silence is not success. It now says UNVERIFIED out loud.

## Known gap
`resolve.sh` judges the newest **prerelease** bundle, but `dl_gh` downloads
whatever assets the release carries, which for rushiranpise and bufferk was the
**stable** .mpp. The patch count and compatible-version list you resolved are
therefore not guaranteed to match the bundle that actually patches. Not yet fixed.

## On-device
MicroG RE installed and signed in BEFORE the patched YouTube, battery
Unrestricted. Play Store shows an uninstallable YouTube update forever; ignore it.
