# patch-factory

Private build pipeline. Patches YouTube with [Morphe](https://github.com/MorpheApp/morphe-patches) in GitHub Actions and publishes a signed APK to Releases.

Target device: Micromax IN Note 1, Android 10, arm64-v8a.

Build manually:

    gh workflow run manual-patch.yml -f org=Morphe

Runs automatically every Monday.

**See [RECOVERY.md](RECOVERY.md) for the signing key, file layout, and everything else that matters.**
