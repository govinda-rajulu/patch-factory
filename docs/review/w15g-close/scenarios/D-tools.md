# W15g signing split — scenario report

Scope: static source inspection, captured verifier fixtures, parser execution, and local fake-tool contracts in this checkout. No Android SDK build-tools, patcher JAR, APK payloads, apksigner, zipalign, aapt2, network, or GitHub runner were available. Therefore tool-version claims below are marked **UNVERIFIABLE** unless directly exercised by a checked-in fixture or a fake tool.

Confidence: **high** for repository control-flow and parser observations; **medium** for remembered Android build-tools behavior; **low/unverifiable** for exact 34/35/36/36.1/37 binary output, flag acceptance, keystore auto-detection, ZIP rewrite behavior, and exit codes.

## Result summary

- Executable checks: `10` tests, all pass.
- Scenario rows: `24` (`7` PASS, `1` FINDING, `16` UNVERIFIABLE; T15 is PASS for scheme selection but still tool-run UNVERIFIABLE).
- Findings: 1 HIGH parser-compatibility finding; 1 HIGH runner/tool-version risk; 1 HIGH keystore-format risk; per-app live execution remains UNVERIFIABLE (not a claimed failure).

## Scenario table

| ID | Scenario | Expected | Actual | Status |
|---|---|---|---|---|
| T01 | Patch command is keyless and requires Morphe `--unsigned` | Missing capability stops with `UNSIGNED_UNSUPPORTED`; no signed fallback | `build.sh` probes first; `patch_target.py` appends `--unsigned` and rejects missing `PF_UNSIGNED` | PASS |
| T02 | Patch job receives signing material | Any `KEYSTORE*` variable/file stops | `build_attempts.py` and `patch_target.py` reject it; child env is allowlisted | PASS |
| T03 | Legacy `utils.sh` patch helpers | No old helper may sign or be called | `patch`, `patch_multi`, and `split_arch` are refusal stubs; `build.sh` calls `patch_target.py`, not those helpers | PASS |
| T04 | SDK 34 representative verifier text | Parse v1–v4 lines, signer count, warnings without accepting v4 | Synthetic text parses; exact SDK34 output/flag support not available | UNVERIFIABLE |
| T05 | SDK 35 representative verifier text | Same | Synthetic text parses; exact SDK35 output not available | UNVERIFIABLE |
| T06 | SDK 36 representative verifier text | Same | Synthetic text parses; exact SDK36 output not available | UNVERIFIABLE |
| T07 | SDK 36.1 representative verifier text | Same | Synthetic text parses; exact SDK36.1 output not available | UNVERIFIABLE |
| T08 | SDK 37 v2-only and v3.0 final output | One signer and scheme booleans parse | Checked Facebook and Key Mapper fixtures parse to their recorded fingerprints | PASS |
| T09 | SDK 37 v3.1 rotation/source-stamp output fed to final signer parser | Final APK parser must not silently choose among rotated identities | `parse_signers` refuses the Photos fixture; range-aware `parse_original_signers` accepts its two ranges | FINDING (HIGH) |
| T10 | v4 output | Any v4=true must fail the W15g scheme contract | Parser exposes v4=true; expected v2-only dict differs | PASS |
| T11 | `--alignment-preserved true` on apksigner 34 | Tool must accept the flag and preserve alignment | No binary available; likely introduced for 16-KiB alignment after 34, but not verified | UNVERIFIABLE |
| T12 | `--alignment-preserved true` on 35/36/36.1/37 | Tool accepts and keeps input alignment/extra fields | No binaries or APKs available; source passes the flag | UNVERIFIABLE |
| T13 | v1/v2/v3/v4 signing flags | All requested flags accepted and v4 remains false | No binaries available; argv shape is exact in `sign_apk.py` | UNVERIFIABLE |
| T14 | Stale input META-INF entries with v1 disabled/enabled | apksig should replace/remove stale v1 material consistently | No apksigner binary/APK; verifier comparison intentionally excludes signature-file names | UNVERIFIABLE |
| T15 | v3 at minSdk <24 | v1+v2+v3, no v3.1/v3.2/v4 unless explicit rotation | Scheme selection code is exact; no real signing run | PASS (selection); tool result UNVERIFIABLE |
| T16 | `zipalign -c 4` and `-c -P 16 4` | Exit 0 for the relevant alignment; signing must not lose 16-KiB library alignment | No zipalign binary. Source unconditionally invokes both checks; `-P 16` is documented in source as build-tools 35+ | UNVERIFIABLE (HIGH risk on 34) |
| T17 | aapt2 badging before/after signing | Package, version code/name, and minSdk remain equal; reader path may differ | Verification strips only `reader`; parser accepts normal badging shape | PASS |
| T18 | Keystore decode and `--ks` auto-detection | Decoded release keystore must be readable by both keytool and apksigner | `KEYSTORE_B64` is decoded to `src/ks.keystore`; no `--ks-type`; actual secret format unavailable | UNVERIFIABLE (HIGH) |
| T19 | youtube / ytmusic single-bundle path | Direct `patch_target.py` path; no fallback or removed helper | youtube is APK/default source; ytmusic is APK with arm64 download selection; both use Morphe options and `--striplibs arm64-v8a` | UNVERIFIABLE live build |
| T20 | facebook / instagram / reddit split-container paths | Store container is merged before patching; extras/fallback views are exact | All are `apk_type=bundle`; APKMirror source; Reddit uses APKPure; each has configured extras/fallback overrides | UNVERIFIABLE live build (HIGH) |
| T21 | hotstar / edge / keymapper / linkedin bundle paths | Correct store format is normalized to standalone APK before patching | Hotstar/LinkedIn use APKMirror; Edge/Key Mapper use APKPure; all are bundle targets | UNVERIFIABLE live build (HIGH) |
| T22 | photos / mxplayer / adguard provider paths | Extra bundle and provider selection must not call removed helpers | Photos has an extra bundle; MX Player has an extra and fallback override; AdGuard has two candidates and is pinned to rushiranpise | UNVERIFIABLE live build (HIGH) |
| T23 | Truecaller combo and ES File fallback/override paths | Primary override and fallback must produce the intended bundle set | Truecaller primary `heval99` removes extras, fallback `bufferk` retains combo extras; ES File fallback removes extras while primary has rushiranpise extra | UNVERIFIABLE live build (HIGH) |
| T24 | Prime Video / Amazon Music APKMirror bundle paths | Bundle merge then single unsigned patch output | Both are `apk_type=bundle`, APKMirror, single configured provider; no multi-arch patch helper is used | UNVERIFIABLE live build (HIGH) |

## Findings

### F-01 — HIGH: final signer parser refuses a valid v3.1 rotation-shaped verifier output

**Evidence:** `tests/fixtures/apksigner-37-photos-v31-rotation.txt` contains verified v3 and v3.1, two SDK-ranged signer certificates, and one Source Stamp certificate. `artifact_identity.parse_signers()` only recognizes an un-ranged `V3.0 Signer` or `V2 Signer`; it counts the ranged v3.0/v3.1 certificates as unrecognized and raises `ValueError: unrecognized certificate identity in verifier output`. The repository already has a separate `parse_original_signers()` that correctly handles this original-APK shape.

**Impact:** If this output shape were ever used for a final signed artifact, verification would stop a legitimate artifact rather than publish it. It does not currently imply a bad-signer acceptance: the parser fails closed, and W15g's CI signing key is not configured for rotation in this code.

**Smallest fix:** Keep the strict final-artifact rule, but make the final parser explicitly accept only the expected single non-rotated CI signer and report a precise “key rotation unsupported for final output” error; do not reuse the original rotation parser for final identity pinning. Add a real final-APK fixture if rotated final signing is intended.

### F-02 — HIGH risk, not reproduced: build-tools 34 and 16-KiB alignment

**Evidence:** `sign_apk.py` invokes `zipalign -c -P 16 4` unconditionally and comments that 16-KiB checking is for build-tools 35+. The tool selector chooses the numerically newest installed build-tools. No local binary exists, so exact `-P` acceptance and return codes are unverified. My Android-tool recollection is medium confidence that `-P`/16-KiB support starts with the 35 line; treat that as a hypothesis, not a measured fact.

**Impact:** If a runner selects only 34.0.0 and the APK's unsigned `.so` files are 16-KiB aligned, an unsupported `-P` command could produce a nonzero result and the checker can report lost alignment. If ubuntu-latest selects 37.0.0 as intended, this specific risk is not expected.

**Smallest fix:** Either enforce a minimum build-tools version that supports `-P 16`, or gate the 16-KiB check by parsed tool capability/version while retaining the 4-byte check. Capture one real exit-code matrix for 34/35/36/36.1/37 before calling this fixed.

### F-03 — HIGH risk, unverified: keystore type is implicit

**Evidence:** `.github/workflows/manual-patch.yml` decodes `KEYSTORE_B64` to `src/ks.keystore`; `sign_apk.py` passes only `--ks`, not `--ks-type`; `artifact_identity.cert_from_keystore()` likewise invokes keytool without a store type. The repository does not contain the secret keystore bytes. The preparation action has optional Bouncy Castle installation for BKS, but the manual sign job does not enable that option. Review notes say the earlier throwaway BKS plan was superseded, but do not establish the release key's actual format.

**Impact:** A JKS/PKCS12 file that the installed JDK/apksigner auto-detects will work; a BKS file without the provider will stop before signing. This cannot be called a live failure without the secret or runner.

**Smallest fix:** Record and pin the release keystore type as non-secret workflow configuration, pass `--ks-type` consistently to keytool/apksigner, and install/register the required provider only if the recorded type is BKS. Add a fake-JKS/fake-PKCS12/BKS compatibility check around the production command shape.

## Tool-reality notes (not measured here)

- Captured SDK37 fixtures show the six scheme lines (v1, v2, v3, v3.1, v3.2, v4), `Number of signers`, and, for Photos, Source Stamp lines. The parser ignores ordinary `WARNING:`/`INFO:` lines. Exact warning placement, stale `META-INF` warning text, and SDK34–36 output wording remain unverified.
- `parse_schemes()` requires v1/v2/v3 and records absent v3.1/v3.2/v4 as false. It therefore handles the captured v2-only and v3.0 outputs, but does not prove that every apksigner release prints every line.
- W15g's scheme selection does not enable v3.1 automatically for minSdk <24; it requests v3, not key rotation. A normal v3 signer is therefore expected to be `V3.0`, not the range-labelled rotation shape.
- `sign_apk.compare()` deliberately excludes names matching `META-INF/MANIFEST.MF`, `.SF`, `.RSA`, `.DSA`, `.EC`, or `SIG-*`; stale v1 signature entries cannot be treated as payload-byte changes. Whether apksigner removes/replaces them when v1 is disabled/enabled needs a real APK experiment.
- Metadata comparison removes only the `reader` path, so normal aapt2 formatting, warnings, and tool path changes do not alter the semantic identity. A changed package/version/minSdk still fails.

## Sources in this checkout

- [sign_apk.py](src/build/sign_apk.py) — signer flags, scheme parser, ZIP comparison, zipalign checks.
- [artifact_identity.py](src/build/artifact_identity.py) — signer parsers, aapt2 metadata, SDK tool selection.
- [build.sh](src/build/build.sh) — unsigned probe and patch entry point.
- [patch_target.py](src/build/patch_target.py) — unsigned Morphe argv and secret refusal.
- [build_attempts.py](src/build/build_attempts.py) — fallback/override attempt views.
- [utils.sh](src/build/utils.sh) — APK/APKM/XAPK normalization and W15g refusal stubs.
- [targets.json](src/targets.json) — per-app source, type, providers, extras, and overrides.
- [apksigner-37-keymapper.txt](tests/fixtures/apksigner-37-keymapper.txt), [apksigner-37-facebook-v2-only.txt](tests/fixtures/apksigner-37-facebook-v2-only.txt), [apksigner-37-photos-v31-rotation.txt](tests/fixtures/apksigner-37-photos-v31-rotation.txt) — captured verifier evidence.
- [scenario_tools_contracts.py](tests/scenario_tools_contracts.py) — executable local checks (`python3 -m unittest discover -s tests -p 'scenario_tools_contracts.py'`).
