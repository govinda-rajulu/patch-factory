# APK signing/alignment facts (official sources)

Scope: AOSP `platform/tools/apksig` and `platform/build/tools/zipalign`, Android Developers documentation, and the official GitHub Actions runner-image README. Source links below are official; AOSP source links are rendered HTML (the same files are available with `?format=TEXT`, base64-encoded).

## 1. `apksigner sign` flags and defaults

### Current `ApkSignerTool.java`

[ApkSignerTool.java (AOSP main)](https://android.googlesource.com/platform/tools/apksig/+/refs/heads/main/src/apksigner/java/com/android/apksigner/ApkSignerTool.java) initializes:

```java
boolean v1SigningEnabled = true;
boolean v2SigningEnabled = true;
boolean v3SigningEnabled = true;
boolean v4SigningEnabled = true;
boolean alignmentPreserved = false;
int libPageAlignment = LIBRARY_PAGE_ALIGNMENT_BYTES;
int minSdkVersion = 1;
```

The parser accepts all four flags and parses each as an optional boolean (a bare flag means `true`):

```java
} else if ("v1-signing-enabled".equals(optionName)) {
    v1SigningEnabled = optionsParser.getOptionalBooleanValue(true);
} else if ("v2-signing-enabled".equals(optionName)) {
    v2SigningEnabled = optionsParser.getOptionalBooleanValue(true);
} else if ("v3-signing-enabled".equals(optionName)) {
    v3SigningEnabled = optionsParser.getOptionalBooleanValue(true);
} else if ("v4-signing-enabled".equals(optionName)) {
    v4SigningEnabled = optionsParser.getOptionalBooleanValue(true);
    v4SigningFlagFound = true;
}
```

It also parses:

```java
--alignment-preserved       // optional boolean, default false
--lib-page-alignment        // required integer, default LIBRARY_PAGE_ALIGNMENT_BYTES
--min-sdk-version           // required integer; default 1 when omitted
--ks-type                   // required string when supplied
--ks-pass                   // required password spec when supplied
--key-pass                  // required password spec when supplied
```

Relevant exact source quote for the alignment and signer wiring:

```java
.setV1SigningEnabled(v1SigningEnabled)
.setV2SigningEnabled(v2SigningEnabled)
.setV3SigningEnabled(v3SigningEnabled)
.setV4SigningEnabled(v4SigningEnabled)
...
.setAlignmentPreserved(alignmentPreserved)
.setLibraryPageAlignmentBytes(libPageAlignment);
```

The [current `help_sign.txt`](https://android.googlesource.com/platform/tools/apksig/+/refs/heads/main/src/apksigner/java/com/android/apksigner/help_sign.txt) describes the scheme defaults as “enabled based on min and max SDK version” for v1, v2 and v3, and likewise for v4. Thus the Java booleans start true, while the signer applies scheme/API applicability. `--min-sdk-version` overrides manifest-derived min SDK; if omitted, the help says the value from `AndroidManifest.xml` is used. `--ks-type` help says: “By default, the default type is used.” `--ks-pass` and `--key-pass` both document `env:<name>` as “password provided in the named environment variable”; therefore `--ks-pass env:P --key-pass env:P` is valid.

### Important v4 consequence

The current tool explicitly creates the v4 sidecar when v4 is enabled:

```java
if (v4SigningEnabled) {
    final File outputV4SignatureFile =
        new File(outputApk.getCanonicalPath() + ".idsig");
    Files.deleteIfExists(outputV4SignatureFile.toPath());
    apkSignerBuilder.setV4SignatureOutputFile(outputV4SignatureFile);
}
```

The [Android Developers `apksigner` documentation](https://developer.android.com/tools/apksigner) confirms that v4 “produces a signature in a separate file (`apk-name.apk.idsig`)”. Therefore **do not rely on the default** if no `.idsig` is wanted: pass `--v4-signing-enabled false`.

For the stated compatibility targets, use explicit flags rather than relying on defaults:

```text
# minSdk >= 24: v2 only, no v1/v3/v4 and no .idsig
--min-sdk-version N --v1-signing-enabled false --v2-signing-enabled true \
--v3-signing-enabled false --v4-signing-enabled false

# minSdk < 24: retain the requested v1+v2+v3 apksig default, but suppress v4 sidecar
--min-sdk-version N --v4-signing-enabled false
```

(`N` is the actual minimum SDK.)

## 2. Signing and existing alignment

The [current `ApkSigner.java` (AOSP main)](https://android.googlesource.com/platform/tools/apksig/+/refs/heads/main/src/main/java/com/android/apksig/ApkSigner.java) documents that the signer “preserves as much of the input APK as possible”, including “compressed form and alignment of data.” However, current defaults intentionally change alignment policy unless preservation is requested. The CLI help states verbatim:

> `--alignment-preserved` Whether the existing alignment within the APK should be preserved; the default for this setting is false. When this value is false, the value provided to `--lib-page-alignment` will be used to page align native library files and all other files will be aligned to 4 bytes in the APK.
>
> `--lib-page-alignment` The number of bytes to be used to page align native library files in the APK; the default value is 16384.

`ApkSigner.java` defines `ANDROID_FILE_ALIGNMENT_BYTES = 4096`; the CLI default is `LIBRARY_PAGE_ALIGNMENT_BYTES` (16,384). In current build-tools, default signing therefore rewrites alignment padding/extra fields and targets **16 KiB for uncompressed `.so` entries** and **4-byte alignment for other uncompressed entries**. It does **not** reduce an already-16-KiB-aligned `.so` to 4 KiB. To retain the input’s existing 16-KiB alignment (and its existing alignment metadata/padding), pass:

```text
--alignment-preserved true
```

A bare `--alignment-preserved` is equivalent because it is an optional boolean.

The AOSP change that introduced this policy is [“Set defaults to align native libraries to 16k”](https://android.googlesource.com/platform/tools/apksig/+/f1682abcc0752e3231fc65f727f94b4f821e2d05), whose commit message says the new behavior is “not [to] preserve existing alignment”, to align native libraries on a “16k boundary” and all other uncompressed files to 4 bytes. The AOSP history shows the change merged during Android 14 development; the official 35.0.0 prebuilt is available [here](https://android.googlesource.com/platform/prebuilts/fullsdk-linux/build-tools/+/5d7b781b0367b83e6249396cbd4f9fab0a5313f0/35.0.0). **The exact first published build-tools cut is not stated in the source/help pages themselves; the policy is present in build-tools 35.0.0 and later (including 36.x).**

## 3. Payload copying and v1 `META-INF`

The `ApkSigner.java` class-level documentation says the signer preserves entry order and “their contents, including compressed form and alignment of data.” Its signing loop says it outputs the input entries’ “Local File Header + data”; gaps are output “verbatim”. Consequently, for ordinary entries that remain in the output, apksigner does not decompress/recompress their payloads: compressed bytes, uncompressed bytes, CRC, and compressed/uncompressed sizes remain the input values. It may rewrite local-header extra data to implement the selected alignment and necessarily adds/replaces signature structures.

The [current `help_sign.txt`](https://android.googlesource.com/platform/tools/apksig/+/refs/heads/main/src/apksigner/java/com/android/apksigner/help_sign.txt) starts with this explicit behavior: “This signs the provided APK, stripping out any pre-existing signatures.”

For v1, [V1SchemeSigner.java](https://android.googlesource.com/platform/tools/apksig/+/refs/heads/main/src/main/java/com/android/apksig/internal/apk/v1/V1SchemeSigner.java) generates the standard JAR-signing entries:

- `META-INF/MANIFEST.MF`
- `META-INF/<v1-signer-name>.SF`
- `META-INF/<v1-signer-name>.<key-algorithm>` — normally `.RSA`, `.EC`, or `.DSA` (the source derives this from the public-key algorithm).

The same source explicitly lists the META-INF signature names ignored when making the new manifest: `MANIFEST.MF`, `*.SF`, `*.RSA`, `*.DSA`, `*.EC`, and `SIG-*`. With the normal/default non-append signing invocation, old v1 signature files—including another signer’s `.SF`/`.RSA`—are not carried forward; they are replaced/removed as part of stripping pre-existing signatures. Other non-signature entries under `META-INF/` are ordinary entries and are preserved. `--append-signature` is a separate opt-in preservation mode and is not part of the command in the question.

## 4. `zipalign` verification syntax and `-P`

The [Android Developers `zipalign` page](https://developer.android.com/tools/zipalign) gives the exact check command:

```text
zipalign -c -P 16 -v 4 existing.apk
```

This checks all uncompressed entries at 4-byte alignment and uncompressed `.so` files at 16-KiB page alignment. The page also says:

- `-c`: “Checks alignment only (does not modify file).”
- `-P <pagesize_kb>`: aligns uncompressed `.so` files to the selected page size; valid values are 4, 16, and 64.
- `-p`: 4-KiB page-aligns uncompressed `.so` files; it is deprecated and `-P 16` is recommended.

The [AOSP `ZipAlignMain.cpp`](https://android.googlesource.com/platform/build/+/refs/heads/main/tools/zipalign/ZipAlignMain.cpp) gives the same usage line:

```text
Usage: zipalign [-f] [-p] [-P <pagesize_kb>] [-v] [-z] infile.zip outfile.zip
 zipalign -c [-p] [-P <pagesize_kb>] [-v] infile.zip
```

and validates `-P` values 4, 16, and 64, converting KiB to bytes. Its verifier computes the required alignment per entry; [AOSP `ZipAlign.cpp`](https://android.googlesource.com/platform/build/+/refs/heads/main/tools/zipalign/ZipAlign.cpp) returns the selected page size for `.so` and the ordinary alignment for other uncompressed entries. `-P` is present in the 35.0.0 prebuilt [zipalign artifact](https://android.googlesource.com/platform/prebuilts/fullsdk-linux/build-tools/+/5d7b781b0367b83e6249396cbd4f9fab0a5313f0/35.0.0/zipalign), and is present in current 36.x. **The exact first build-tools release introducing `-P` is not stated in the currently cited release-note page; 35.0.0 is the earliest official prebuilt verified here.** Older tools supporting only `-p` can check 4-KiB `.so` pages, not the required 16-KiB condition.

## 5. GitHub Actions `ubuntu-24.04` image

Official [Ubuntu2404-Readme.md](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md) currently lists:

```text
Android SDK Build-tools: 37.0.0 36.0.0 36.1.0 35.0.0 35.0.1 34.0.0
ANDROID_HOME:    /usr/local/lib/android/sdk
ANDROID_SDK_ROOT: /usr/local/lib/android/sdk
```

For the January 2025 Ubuntu 24.04 image, the pinned official [README](https://github.com/actions/runner-images/blob/ubuntu24/20250120.5/images/ubuntu/Ubuntu2404-Readme.md) listed build-tools `35.0.0 35.0.1 34.0.0` and the same two SDK paths. Image contents change over time; pin an image/version if reproducibility matters.

The official image installer [install-android-sdk.sh](https://github.com/actions/runner-images/blob/main/images/ubuntu/scripts/build/install-android-sdk.sh) sets both variables to `/usr/local/lib/android/sdk` (and labels `ANDROID_HOME` deprecated), but does not add every versioned `build-tools/<version>` directory to `PATH`. The Ubuntu README does not promise that `apksigner` or `zipalign` are shell-PATH commands. **UNVERIFIED from the image documentation: do not assume either is on PATH.** Invoke them by absolute SDK path, for example:

```text
$ANDROID_HOME/build-tools/35.0.1/apksigner
$ANDROID_HOME/build-tools/35.0.1/zipalign
```

or prepend the selected build-tools directory to `PATH` in the workflow.
