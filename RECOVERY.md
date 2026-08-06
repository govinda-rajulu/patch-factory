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
