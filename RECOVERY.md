# patch-factory

Builds a patched YouTube APK in GitHub Actions and publishes it as a release.
Target device: Micromax IN Note 1, stock Android 10, arm64-v8a, not rooted.

## Signing key — READ FIRST
- Alias: `factory`. Same key forever. Losing it means uninstall + clean reinstall of every app, permanently.
- The key file is NOT in this repo and must never be. `.gitignore` blocks `*.keystore`.
- Offline copies: TODO_WRITE_WHERE_YOU_PUT_IT
- Password: stored separately, not in this repo.
- Secrets used by the build: `KEYSTORE_B64`, `KEYSTORE_PASS`, `KEYSTORE_ALIAS`, `TDL_BACKUP` (unused, required by upstream workflow).

## Build it
    gh workflow run manual-patch.yml -f org=

    gh workflow run manual-patch.yml -f org=Morphe
    gh run watch

Runs ~5 min. Weekly cron: Mondays 01:00 UTC / 06:30 IST.

## Layout
- src/build/morphe.sh - the build. Case 1 only: YouTube, arm64-v8a.
- src/build/utils.sh - shared engine. Signing flags on lines 729, 749, 836.
- src/patches/youtube-morphe/exclude-patches - patches to skip, one exact name per line.
- .github/workflows/manual-patch.yml - build workflow. Decode step ~line 57.
- .github/workflows/ci.yml - weekly poll.
- .github/workflows/keepalive.yml - monthly commit. Without it GitHub disables the cron after 60 idle days.

## Never exclude
GmsCore support (MicroG breaks), Spoof video streams (playback breaks).

## Hard-won lessons
- Never let an AI write files via the GitHub Contents API. It silently ate every backslash escape in utils.sh, right byte count, broken file. Edit in a terminal, diff against upstream.
- Never paste base64 through a phone clipboard. It truncates. Pipe it: gh secret set NAME < file
- EOFException on the keystore means the secret is truncated, not a wrong password.
- After any file write, read it back and check byte size.

## On-device
MicroG RE installed and signed in BEFORE the patched YouTube, battery Unrestricted. Play Store shows an uninstallable YouTube update forever; ignore it.
