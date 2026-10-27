# Obtainium "Downloaded certificate hash: None" (27 Oct 2026)

Owner report, 27 Oct 2026 18:03 IST: every patched app (AdGuard shown) is blocked with "Signing certificate mismatch", expected `08:48:0F:...:D0:50`, downloaded "None". Obtainium reset, JSON re-imported, apps uninstalled: same result.

## Cause (read from official source)

- Obtainium v1.7.3 (`fcd1807c`) `lib/utils/signing_cert_utils.dart` reads a downloaded APK's signer with `getPackageArchiveInfo(path, flags: {PMFlag.getSigningCertificates})` through the android_package_manager plugin (`b5bc0365`). An empty result prints "None" and, with a configured pin, blocks the install. The pin was added in 1.6.16 (`0fa9c8ba`); no later change.
- Android 9 and 10 (`PackageManager.getPackageArchiveInfo`, implemented through `PackageParser.collectCertificates`) collect certificates only `if ((flags & GET_SIGNATURES) != 0)`: [Android 9 PackageParser](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-9.0.0_r42/core/java/android/content/pm/PackageParser.java), [Android 10 PackageParser](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-10.0.0_r41/core/java/android/content/pm/PackageParser.java), [Android 11 PackageManager](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android11-release/core/java/android/content/pm/PackageManager.java). With only GET_SIGNING_CERTIFICATES nothing is read. Android 11 changed the condition to `GET_SIGNATURES || GET_SIGNING_CERTIFICATES`, so Android 11+ reads the signer.
- Our APKs: morphe-patcher signs v2-only when minSdk >= 24 (AdGuard min_sdk 28). CI verifies the signer `08480f66...d050` with apksigner on every build. v2-only is not the cause, and adding a v1 signature would not change Android 9/10's result.
- The import's hash format (64 lower-case hex) is valid: Obtainium normalizes it.

Confidence: high for the Android 9/10 vs 11+ split. To confirm on the phone: Settings > About phone > Android version.

## What we ship (W16v)

The pin stays on by default. The portal has a **Signer pin** checkbox (untick only on Android 9 or 10) and a static `docs/obtainium-nopin.json`; the guide says when to use it. Android still enforces same-signer updates after the first install.

## Owner action (after W16v merges)

Owner devices, 27 Oct: the main phone runs **Android 10** and carries most apps; an Android 11 and an Android 12 device carry MX Player Pro, YouTube and Facebook.

- Android 10 phone: open the portal, untick **Signer pin**, export and import (or import `docs/obtainium-nopin.json`). Import replaces each app's settings, so the old pin goes. No reset, no uninstall.
- Android 11 and 12 devices: keep the pin (default). Obtainium reads the signer there.
- Fits the targets: Facebook accepts a store APK needing up to Android 11 (`min_sdk_ceiling` 30), every other enabled app at most Android 10 (29), so those all install on the Android 10 phone.
- On the Android 10 phone each update still needs Android's own Install tap (silent updates need Android 12 or Shizuku/root). Android itself still refuses an update signed by anyone but the installed app's signer.

Read from Obtainium source (W16v review): with no `allowedSigningCertHashes` and no hash read, the install goes ahead with no warning and no "Install anyway" step; there is no global switch to skip the check.

## Upstream fix (owner to file at github.com/ImranR98/Obtainium/issues)

Title: Signing certificate check always reads "None" on Android 9 and 10

> `apkSigningCertHashes()` calls `getPackageArchiveInfo` with only `PMFlag.getSigningCertificates`. On Android 9 and 10, `PackageManager.getPackageArchiveInfo` collects certificates only when `GET_SIGNATURES` is set (android-9.0.0 / android-10.0.0 `PackageManager.java`; Android 11 added `|| GET_SIGNING_CERTIFICATES`). The downloaded hash set is then empty, so every app with `allowedSigningCertHashes` is blocked with "Downloaded certificate hash: None". Fix: request `{PMFlag.getSigningCertificates, PMFlag.getSignatures}` (or fall back to `getSignatures` on API < 30).
