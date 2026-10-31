# Morphe v1.20.0 source audit

Scope: official Morphe GitHub/raw sources. Release `v1.20.0` is commit [`1ef541a`](https://github.com/MorpheApp/morphe-desktop/commit/1ef541a) and its changelog says it updates Patcher to [`4f580f0`](https://github.com/MorpheApp/morphe-desktop/commit/4f580f0cf7eeaf9943c13d685765916a16199c1e). The matching current Patcher release is [`v2.1.0`](https://github.com/MorpheApp/morphe-patcher/releases/tag/v2.1.0), commit `f3997dc`.

## 1. `--unsigned`, help text, keystore interaction

The CLI source was moved by v1.20.0 to `desktop/command`; the user-specified old path `src/main/kotlin/app/morphe/cli/command/PatchCommand.kt` is **UNVERIFIED/not present at the v1.20.0 source fetched**. The actual file is [`PatchCommand.kt` at v1.20.0 / 1ef541a](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/1ef541a/src/main/kotlin/app/morphe/desktop/command/PatchCommand.kt?raw=1).

Exact option declaration:

```kotlin
@CommandLine.Option(
    names = ["--unsigned"],
    description = ["Disable signing of the final apk."],
)
private var unsigned: Boolean = false
```

Therefore picocli's `patch --help` entry is the long option `--unsigned` with description **`Disable signing of the final apk.`** (spacing/wrapping around it is terminal-width dependent).

The same declaration and exact description are present in the historical [`4505091` PatchCommand](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/4505091/src/main/kotlin/app/morphe/cli/command/PatchCommand.kt?raw=1), which also shows the old save branch:

```kotlin
if (!mount && !unsigned) {
    ApkUtils.signApk(...)
} else {
    patchedApkFile.copyTo(outputFilePath, overwrite = true)
}
```

At v1.20.0, patching is routed through [`PatchEngine.kt`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/1ef541a/src/main/kotlin/app/morphe/engine/PatchEngine.kt?raw=1). Its visible source has `unsigned` in `Config`, checks custom-keystore existence only under `if (!config.unsigned ...)`, and rebuilds by copying input to `rebuilt.apk` then calling `patcherResult.applyTo(rebuiltApk)`. The unsigned final-output branch is in the latter part of this large raw file; exact tail text was not independently extractable through the page reader, so the v1.20.0 tail quote is **UNVERIFIED**. The historical branch plus the v1.20 engine structure support the conclusion: unsigned copies the already-rebuilt APK to the requested output; it does not call the signer. Alignment is performed earlier by `applyTo`, not by the unsigned copy.

`PatchCommand` still constructs `cliKeystoreDetails` from `--keystore*`, then calls [`KeystoreService.resolveSigningDetails`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/1ef541a/src/main/kotlin/app/morphe/engine/util/KeystoreService.kt?raw=1). With explicit details, that function immediately returns them; it does not create a file. `PatchEngine`'s early custom-keystore existence check is explicitly guarded by `!config.unsigned`. Thus `--unsigned` ignores keystore contents for signing and does **not** create/try to create a keystore. (It still parses/holds the options.)

The `unsigned` declaration is unchanged in the fetched v1.19.0 command source: [`v1.19.0 PatchCommand.kt`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/v1.19.0/src/main/kotlin/app/morphe/desktop/command/PatchCommand.kt?raw=1) has the same option/name/description. The old 4505091 spelling/description is also exact-match above.

## 2. Alignment before signing / unsigned output

Patcher v2.1.0's [`ApkUtils.kt`](https://raw.githubusercontent.com/MorpheApp/morphe-patcher/v2.1.0/src/main/kotlin/app/morphe/patcher/apk/ApkUtils.kt?raw=1) defines:

```kotlin
private const val LIBRARY_ALIGNMENT = 1024 * 16
private const val DEFAULT_ALIGNMENT = 4
...
private val zFileOptions =
    ZFileOptions().setAlignmentRule(
        AlignmentRules.compose(
            AlignmentRules.constantForSuffix(LIBRARY_EXTENSION, LIBRARY_ALIGNMENT),
            AlignmentRules.constant(DEFAULT_ALIGNMENT),
        ),
    )
```

Its `PatcherResult.applyTo` sequence ends with:

```kotlin
logger.info("Aligning APK")
targetApkZFile.realign()
```

and its doc comment explicitly says the order includes `5. Realign the APK.` Therefore the patched/rebuilt APK is aligned **before** the signing branch and also before the unsigned copy. All entries get 4-byte alignment; `.so` entries get 16 KiB alignment (which is also a 4 KiB boundary, and stronger than ordinary `zipalign -p 4`). The current code does not only align inside signing. The 16-KiB native-library rule was introduced/documented in Patcher changelog commit [`f8d1a84`](https://github.com/MorpheApp/morphe-patcher/commit/f8d1a84), released in 1.15.1; v2.1.0 retains the code.

The same file also provides `ApkModule.writeAlignedApk` using `ZipAligner` with `setDefaultAlignment(4)` and `.so` alignment `16*1024`; however, the normal CLI path uses `PatcherResult.applyTo`/`ZFile.realign()` above.

## 3. Signing schemes and keystore details

Official current Patcher [`ApkSigner.kt`](https://raw.githubusercontent.com/MorpheApp/morphe-patcher/v2.1.0/src/main/kotlin/app/morphe/patcher/apk/ApkSigner.kt?raw=1) says:

* The keystore instance is hard-coded to **`KeyStore.getInstance("BKS", BouncyCastleProvider.PROVIDER_NAME)`**. The class installs Bouncy Castle if missing.
* It creates a 4096-bit RSA key and a self-signed `SHA256withRSA` certificate (`CN=$commonName`).
* For APKs whose effective minimum SDK is below 24, `signApk` calls `com.android.apksig.ApkSigner.Builder(...)` without disabling schemes. The source comment says: “From API level 24 no v1 signature is needed.” With apksig defaults, this is the compatibility path using v1 plus v2 and v3; it does not request v4. The exact Morphe source does not call any v4 API.
* For effective min SDK >=24, the source calls `DefaultApkSignerEngine.Builder(..., minSdkVersion)` and explicitly uses `.setV1SigningEnabled(false).setV3SigningEnabled(false)`, leaving v2 enabled. It then writes the signing block in place. This is v2-only; no v1/v3/v4.
* No `setV4SigningEnabled`/v4 signing call exists in this source. **v4 is not produced.**
* For v1 signing, apksig generates/replaces standard `META-INF/MANIFEST.MF` and signer `.SF`/`.RSA`/etc. files. Morphe itself does not add custom META-INF files. It does not call `setCreatedBy` in either signing path. The engine/apksig default is its own default (commonly `1.0 (Android)` in the apksig implementation), not a Morphe-specific string; exact version-dependent default is **UNVERIFIED from Morphe source**.

The Morphe wrapper's accepted input formats are broader than the Patcher signer: [`KeystoreImporter.kt`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/1ef541a/src/main/kotlin/app/morphe/engine/util/KeystoreImporter.kt?raw=1) detects BKS/Java keystore, PKCS12, and JKS; it passes already-BKS through and converts non-BKS input to BKS. Thus the Patcher signer expects BKS/BC internally, while the v1.20 desktop pipeline accepts PKCS12/JKS by conversion.

Defaults are visible in [`PatchEngine.kt`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/1ef541a/src/main/kotlin/app/morphe/engine/PatchEngine.kt?raw=1):

```kotlin
const val DEFAULT_KEYSTORE_ALIAS = "[REDACTED]"
const val DEFAULT_KEYSTORE_PASSWORD = "[REDACTED]"
const val DEFAULT_SIGNER_NAME = "Morphe"
const val LEGACY_KEYSTORE_ALIAS = "[REDACTED]"
const val LEGACY_KEYSTORE_PASSWORD = "[REDACTED]"
```

`PatchCommand` uses the declared default alias/password values; `--keystore-password` is nullable. If no keystore exists on a signed run, `ApkUtils.newPrivateKeyCertificatePair` creates the default BKS keystore. This is not reached when `--unsigned` is true.

## 4. `--striplibs` and `--force`

Both remain in v1.20.0 [`PatchCommand.kt`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/1ef541a/src/main/kotlin/app/morphe/desktop/command/PatchCommand.kt?raw=1):

```kotlin
names = ["-f", "--force"],
description = ["Don't check for compatibility with the supplied APK's version."],
```

and:

```kotlin
names = ["--striplibs"],
description = ["Architectures to keep, comma-separated (e.g. arm64-v8a,x86). Strips all other native architectures."],
split = ",",
```

`--striplibs arm64-v8a` remains valid; its values are converted to `CpuArchitecture` and passed as `architecturesToKeep` into `PatchEngine`/Patcher.

## 5. v1.19.0 → v1.20.0 pipeline-impacting changes

The official v1.20.0 changelog [`CHANGELOG.md`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/v1.20.0/CHANGELOG.md?raw=1) lists only:

```md
* Update to latest Patcher (... several dev updates, final 4f580f0)
* Verify patch bundle signatures and pin the signing key (67dcf06)
```

No PatchCommand CLI-option change is listed. The fetched v1.19.0 and v1.20.0 `PatchCommand.kt` declarations are materially identical for the pipeline shown: `--patches`, `--striplibs`, `--keystore`, all keystore passwords/alias, `--force`, `-o/--out` and `--unsigned` remain. v1.20.0 does add/retain newer options already present by v1.19.0 (`--validate`, `--bytecode-mode`, `--verify-with-sdk`, options-file controls, `--disable-purge`), none of which affect the supplied command.

The release-note change that can affect this pipeline is patch-bundle signature verification/pinned key: a previously accepted unsigned/untrusted `.mpp` may now be rejected. The Patcher update also includes the 16-KiB `.so` alignment behavior (already present in the inspected v2.1.0 source). Existing pipeline arguments remain syntactically compatible.

Historical context: v1.19.0 itself introduced the unified CLI/GUI engine, first-run default keystore creation, and `--validate` (see its official [`CHANGELOG.md`](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/v1.19.0/CHANGELOG.md?raw=1)); these are not v1.20.0 option changes.

## Limitations / verification notes

* The release's changelog points to desktop commit `4f580f0` as the final dependency-update commit; the Patcher source was read at official tag `v2.1.0`, while the raw URL for short commit `4f580f0` under the Patcher repository did not resolve. The exact pinned Patcher tree can therefore be treated as **UNVERIFIED**, though v2.1.0 is the release contemporaneous with v1.20.0 and contains the requested signing/alignment code.
* The old `app/morphe/cli/command/PatchCommand.kt` path is historical (works at 4505091); v1.20.0's file is under `app/morphe/desktop/command`.
* Exact v1.20.0 PatchEngine tail (the final `unsigned` copy statement) was not extractable due the raw reader truncating the large file. The conclusion is supported by the historical exact branch and the visible v1.20 engine structure; mark the exact tail quote UNVERIFIED.
