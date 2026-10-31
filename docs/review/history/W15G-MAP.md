# W15g: signing split implementation map (patch-factory)

> **Superseded, 31 Oct 2026:** W15g implemented the split; this map is the pre-build plan and its line anchors and some instructions (for example the all-v1/v2/v3 signing recipe and keeping `capture_signer`) are out of date. Current design and what was built: [HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md) and [SIGNING-SPLIT.md](SIGNING-SPLIT.md).

**Checkout:** main `97abdc7c` (W16u merge #267, 27 Oct 2026), read-only. This is an implementation map, not a patch. Line numbers below are current checkout anchors; they will move when the split is implemented.

## Decision and upstream gate

The patch job must be **strictly unsigned** and must stop rather than fall back to signing. The official Morphe Desktop implementation calls the flag `--unsigned`, describes it as “Disable signing of the final apk,” and branches so that `!mount && !unsigned` calls `ApkUtils.signApk`, while the unsigned path copies the patched temporary APK to the output. Evidence: [official upstream `PatchCommand.kt` at the W15h implementation commit](https://raw.githubusercontent.com/MorpheApp/morphe-desktop/4505091624b854706b39656bae642e5dc1132dcd/src/main/kotlin/app/morphe/cli/command/PatchCommand.kt), [upstream PR #20](https://github.com/MorpheApp/morphe-desktop/pull/20), and [merge commit `4505091`](https://github.com/MorpheApp/morphe-desktop/commit/4505091624b854706b39656bae642e5dc1132dcd). The PR's test invocation also uses `--unsigned`.

**Required hard stop:** pin/qualify the downloaded Morphe jar as usual, then inspect its `patch --help` (or equivalent first-party capability probe) for the literal `--unsigned`. If absent, fail before invoking patch. Do not retry without the flag and do not reintroduce a key into the patch job.

The sign job should use Android's official `apksigner` syntax: `sign --ks src/ks.keystore --ks-key-alias "$KEYSTORE_ALIAS" --ks-pass env:KEYSTORE_PASS --key-pass env:KEYSTORE_PASS --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true --out <signed.apk> <unsigned.apk>`, then `verify --verbose --print-certs <signed.apk>`. Android's reference documents `--ks`, `--ks-key-alias`, `--ks-pass env:NAME`, `--key-pass env:NAME`, `--out`, the v1/v2/v3 switches, and `verify --print-certs`: [official apksigner reference](https://developer.android.com/tools/apksigner). Use `--out`; signing in place would destroy the input needed for the handoff proof. Do not create a v4 `.idsig` unless explicitly wanted.

## Current HIGH finding and target topology

* `.github/workflows/manual-patch.yml:3-4` grants `contents: write` globally; `:61-67` declares all three keystore secrets; `:153-160` decodes the keystore; `:180-201` runs the third-party patcher and then identity verification while pass/alias are in the step env; `:241-248` publishes in the same job. The patcher argv is assembled at `src/build/patch_target.py:44-50` and legacy helpers still use `eval java` with passwords at `src/build/utils.sh:898-924` and `:1004-1013`.
* `.github/workflows/batch-patch.yml:38-53` calls the reusable workflow with `contents: write` and forwards all signing secrets. `.github/workflows/ci.yml:211-230` does the same for the daily matrix (`contents: write`, all three secrets). The callers may continue to map secrets for the reusable workflow, but only the called **sign** job may reference them; patch and publish jobs must have no keystore secret env.
* There are 17 enabled targets in `src/targets.json`: youtube, ytmusic, adguard, photos, truecaller-combo, primevideo, esfile, facebook, instagram, reddit, hotstar, edge, mxplayer, telegram, keymapper, amazonmusic, linkedin. (Count checked from the live file; the exact enabled set is a rollout input, not a new source of authority.)
* `docs/review/SIGNING-SPLIT.md:9-15` is the three-job design; `:17-23` records the shadow receipt complication and rollout gate; `:25-31` records W15h and `--unsigned`. `docs/review/PLAN-2026-10-26.md:154` is the owner-plan row. Keep those design statements true after implementation.

## Workflow graph and permissions

### `.github/workflows/manual-patch.yml`

Replace the one job at `:68-253` with three jobs, preserving the existing preflight, resolver/source packet, store, provider-attempt, shadow and release-contract gates in the appropriate job:

1. **`patch` / `Patch <target>` (`contents: read`, `actions: read`; no signing secrets).**
   * Keep checkout, build-time stamp, ref/keep-going guards, target preflight, dependency/source downloads and verification, preparing, connection checks, patcher download/cache, and `build_attempts.py` in this job (`:86-195`). Remove `Decode keystore` (`:153-160`) entirely.
   * The patch step env (`:183-193`) must contain target/provider/resolution/store flags only; remove `KEYSTORE_PASS` and `KEYSTORE_ALIAS`. Set a non-secret `PF_UNSIGNED=true` (or equivalent) that reaches `build.sh`/`patch_target.py`. The current job-wide `GITHUB_TOKEN` at `:76-77` must not be forwarded to the patcher child (the existing `patch_target.py` allowlist already excludes it); after the split, the patch job's permission is read-only.
   * Remove the old `Verify finished APK identity` from this job (`:196-201`) or replace it with a no-secret **unsigned** identity check. It must verify structure, manifest/package/version/architecture, applied-patch evidence, zip alignment and unsigned output hash, but must not call `cert_from_keystore`, `capture-signer`, or require a signer certificate.
   * Keep `Save build evidence`, release handoff and shadow observation as patch-side validation, but emit an unsigned report and a sealed receipt draft. Upload one **run-scoped** patch artifact after all patch-side checks. Recommended exact name: `patch-output-${{ inputs.target }}-${{ github.run_id }}-${{ github.run_attempt }}`. Contents should include the unsigned APK, `.build-inputs.json`, `.requested`, `.signer-pin.json`/expected public pin, unsigned identity report, release metadata files, and sealed shadow draft. Do not upload `src/ks.keystore`, passwords, raw logs, or provider output.
   * Rename current nonpublishing artifact names at `:203-208`, `:225-229`, `:233-240` to include `${{ github.run_id }}-${{ github.run_attempt }}`. In particular, current `build-evidence-${{ inputs.target }}` is not run-scoped and must become e.g. `build-evidence-${{ inputs.target }}-${{ github.run_id }}-${{ github.run_attempt }}`. Keep `test-apk-...` run-scoped, but make it the signed artifact on a successful split run, not the patch job's unsigned file.

2. **`sign` / `Sign <target>` (`contents: read`, `actions: read`; only `KEYSTORE_B64`, `KEYSTORE_PASS`, `KEYSTORE_ALIAS`).**
   * `needs: patch`, and run only when patch succeeded. Checkout the repository with persisted credentials disabled, download the exact `patch-output-...` artifact by exact run ID/attempt and fail on digest mismatch. Do not call `preparing`, `build.sh`, `build_attempts.py`, `patch_target.py`, `utils.sh`, provider code, network resolution, or shadow observation here.
   * Decode `KEYSTORE_B64` only in this job, with the existing truncation check from `:153-160`. The secret-bearing env is limited to the decode/sign/capture steps. Do not place it in a job-wide env. `capture-signer` runs here before signing and must compare the exported DER certificate hash with `src/build/ci-signer.json`; a mismatch stops before `apksigner`.
   * Verify the artifact handoff before signing: read the patch report's `unsigned_output` path, bytes and SHA-256; compute SHA-256 over the downloaded unsigned APK; require exact equality and run-scoped target/commit/attempt equality. Also compare ZIP entries excluding `META-INF/*.(RSA|DSA|EC|SF)`/`META-INF/MANIFEST.MF` as an additional post-sign proof (the cryptographic signature files are the only expected additions/changes). Check the unsigned file is zipaligned before signing. Preserve the unsigned copy; write a separate signed output.
   * Run `apksigner sign` with the flags above and `verify --verbose --print-certs`. Require exactly one signer and certificate equal to `src/build/ci-signer.json`. Upload a run-scoped signed artifact, recommended exact name `signed-output-${{ inputs.target }}-${{ github.run_id }}-${{ github.run_attempt }}`, containing the signed APK, unsigned/signed records, signer capture, and final identity/release evidence. Never upload keystore material.

3. **`publish` / `Publish <target>` (`contents: write`, no secrets).**
   * `needs: sign`; condition must preserve `check-gh == 0`, `inputs.publish`, and main-ref guard. Checkout with `persist-credentials: false`; download the exact signed artifact by run ID/attempt with `digest-mismatch: error`. No `KEYSTORE_*`, no `secrets: inherit`, and no keystore decode. The only token is the normal `github.token` used by the release action/receipt upload.
   * Run `release_contract.py "$TARGET" --github-output` only after signed artifact download and signed evidence verification. Then invoke `.github/actions/release`; release action remains keyless with respect to the signing key. For nonpublishing runs, still execute patch + sign and retain the signed `test-apk-<target>-<run_id>-<run_attempt>` artifact; skip only publication.

At workflow top-level, remove `permissions: contents: write` (`:3-4`) and set least privilege per job. Keep the `workflow_call` secret declarations (`:61-67`) only as inputs to the reusable workflow; a declaration is not an injection, but every job reference must be audited. Keep dispatch defaults/ref guards. Ensure job names are stable and update shadow/publication readers from the old single `Patch <target>` job to the new patch/sign/publish job names.

### `.github/workflows/batch-patch.yml`

* `fan` remains read-only (`:17-37`). Change the matrix call job `build` (`:38-53`) from `contents: write` to `contents: read`/`actions: read`; the called workflow owns separate patch/sign/publish permissions. Continue forwarding the three secret inputs only to the reusable workflow so its sign job can use them; do not use `secrets: inherit`.
* Keep `publish` flowing to the reusable workflow (`:47-49`). Artifact names must include run ID/attempt; the reusable workflow must not accidentally download another batch run's artifact.

### `.github/workflows/ci.yml`

* Change daily matrix caller `build` permissions at `:218-220` from `contents: write` to read/action-read. Keep `:221-230` as a reusable call and map the three secrets for the sign job only. `plan`, `resolve`, and `dependency_report` remain secretless/read-only.
* Update tests and comments that currently treat the called job as a single build/publish job. Daily build remains non-ambiguous: patch and sign run for each matrix target; publish runs only when `publish` is true through the existing input path.

## Build and shell code

### `src/build/build.sh`

* `:28` currently runs `python3 src/build/artifact_identity.py capture-signer` before any patching. Remove it from the patch job; capture-signer belongs in the sign job after the keystore is decoded. This is the critical ordering change that prevents the patcher from ever seeing the key.
* `:30-38` sources `utils.sh` and initializes `KEYSTORE_PASS`/`KEYSTORE_ALIAS`. Remove the signing variables and any export/inheritance in the patch path. Keep only non-secret runtime switches. `utils.sh` must remain sourceable without a keystore.
* `:74-80` retains jar provenance; immediately after a verified jar is selected, add the unsigned capability gate (literal `--unsigned` in `patch --help`) and fail closed if absent. This must occur before any patch attempt and must never choose a signed fallback.
* `:102-107` and `:296-308` continue selecting/staging exact inputs and capturing input evidence, but `.build-inputs.json` must bind the expected public certificate from `src/build/ci-signer.json` rather than a live keystore. At `:308`, capture the selected input records before patching as today.
* `:310-340` remains the patch gate; it now invokes a command containing `--unsigned`. The output is explicitly an unsigned APK and is handed to sign, not release. Preserve applied-patch/package/failure checks.

### `src/build/build_attempts.py`

* `:132-137` is the only attempt subprocess boundary and `:172-223` carries the per-attempt environment. Keep provider fallback and store lifecycle here, but ensure the environment passed to `build.sh` contains `PF_UNSIGNED=true` and no `KEYSTORE_*`; the reusable workflow must not put signing secrets in the environment that reaches this wrapper. The wrapper must never be moved into the sign job.

### `src/build/patch_target.py`

* `:10-51` must build two mutually exclusive argv shapes. In unsigned mode (`PF_UNSIGNED=true`) append `--unsigned` and **omit** `--keystore`, `--keystore-password`, `--keystore-entry-alias`, and `--keystore-entry-password`; do not read `env['KEYSTORE_PASS']`/`env['KEYSTORE_ALIAS']`. In any other mode, fail with a clear error rather than silently signing; the production entry point should require unsigned mode. Keep output/input paths and `--force`.
* `:54-80` continues invoking a subprocess with a non-secret allowlist; retain the allowlist and never pass a signing secret to the child. Update comments that currently say signing inputs remain argv-compatible (`:70-74`); after this change no signing input is argv-compatible in patch mode. Keep stderr/log redaction.
* `execution_inputs.py`/its tests currently call `patch_target.command` with dummy credential values (`src/build/execution_inputs.py:22-29`). Change the fixture to set unsigned mode and assert `--unsigned`, no keystore options, no secret/dummy material. This is not a production secret path.

### `src/build/execution_inputs.py`

* `:22-29` intentionally builds a public/dummy command for execution evidence and currently filters keystore argv. Update its forbidden list and expected record to require `--unsigned` and no keystore/password options. `:60` must continue excluding raw environment/signing values from persisted evidence. This file must never be changed to pass real signing values merely to make the command shape work.

### `src/build/utils.sh`

Remove credential-bearing legacy `eval` invocations even though current `build.sh` reaches `patch_target.py`:

* `:898-912` (`patch`): replace the `eval java ... --keystore*="${KEYSTORE_*}"` command with an argv-safe unsigned invocation, or make this legacy entry point delegate to the same unsigned `patch_target.py` path. It must include `--unsigned`, and must not expand either password.
* `:915-932` (`patch_multi`): same treatment; preserve per-bundle arguments/order but remove all four keystore/password options and add `--unsigned`.
* `:1004-1017` (`split_arch`): same treatment; remove `eval`, all `KEYSTORE_*` expansions and signing options; add `--unsigned`. If this helper is retained only for an old path, make it refuse rather than silently sign.
* Add a shell-level assertion/test that no production patch helper contains `KEYSTORE_PASS`/`KEYSTORE_ALIAS` or `--keystore-password`; the only production `KEYSTORE_*` reads should be first-party sign/capture code in the sign job. `utils.sh` still owns downloading/store helpers; that behavior is unchanged.

## Identity, handoff, contract, and publication

### `src/build/artifact_identity.py`

Current anchors: `capture-signer` is `:96-118`; `capture_inputs` is `:137-213`; final signed verification is `:387-424`; CLI dispatch is `:427-450`.

* Keep `cert_from_keystore` and `capture_signer`, but make them sign-job-only. `capture_signer` continues exporting a public DER certificate with `keytool`, compares its SHA-256 to `src/build/ci-signer.json`, and writes only public fingerprint evidence. It must not be imported/run by patch or publish jobs.
* Change `capture_inputs` so its `expected_certificate_sha256` comes from the committed `ci-signer.json` public pin (not `.signer-before-build.json` produced by a secret-bearing pre-build step). Add an unsigned output record (`path`, `bytes`, `sha256`, run/attempt binding) and preserve the exact patch inputs needed by the shadow draft.
* Split current `verify_final` (`:387-424`) into a no-secret `verify_unsigned` and a sign-job `verify_signed` (or equivalent). `verify_unsigned` checks structure, metadata, architecture, input records, applied patches, zip alignment and the unsigned output record; it must not call `cert_from_keystore`, `apk_signer`, or require a signature. `verify_signed` consumes the unsigned handoff, checks the pre-sign SHA-256, invokes `apksigner verify --verbose --print-certs`, checks the certificate equals `ci-signer.json` and the captured keystore certificate, checks signed output record, and emits a report containing both unsigned and signed records.
* Add a dedicated entry point for the sign job (`verify-signed`/`sign`) and keep CLI errors redacted. `apk_signer`'s existing `verify --print-certs --verbose` at `:334-355` is usable for the post-sign check but must be called only after the sign job has the signed APK and never with signing credentials.
* Keep the certificate comparison at the final artifact boundary; do not rely only on keystore export. This catches a wrong key, an apksigner invocation using another alias, or a mutated signed artifact.

### `src/build/release_contract.py`

Current release checks are `:33-99`, especially signature/expected-cert at `:46-49`, exactly one release APK and record at `:55-66`, and `--github-output`/publish guard at `:113-127`.

* Require the **signed** report schema and both `unsigned_output` and `signed_output` records. Require signed output hash/path to equal the downloaded artifact and require the unsigned handoff SHA-256 to equal the signer job's recorded pre-sign hash. Keep package, version, architecture, applied patch, tag, build suffix and publish guard checks.
* Retain `:46-49` as a signed-cert check against the committed expected certificate, but read the cert from the sign evidence/report, not from a keystore in publish. A publish checkout must not call `cert_from_keystore`.
* Add explicit `signing_split: true`, `unsigned_sha256`, `signed_sha256`, `signer_certificate_sha256`, and run/attempt/source-commit fields to release evidence. Reject old unsigned-only or legacy reports rather than publishing them.
* `verify()` remains a pure local handoff check; `--github-output` at `:113-127` remains the only place that evaluates publication guards and writes metadata. It must run in the publish job after the signed artifact download.

### `.github/actions/release/action.yml`

* The existing metadata step (`:10-16`) is correctly first-party/keyless; run it only in `publish` after downloading the signed artifact. The release action at `:18-33` continues to use `${{ github.token }}`/the action's normal token and the signed APK path; it must not receive any `KEYSTORE_*` env or secret.
* Keep receipt ordering (`:35-49`): release first, then confirmed-publication receipt. Change receipt inputs so the publish job consumes the patch job's sealed shadow draft and sign job's unsigned→signed handoff, rather than trying to re-read patcher JAR/bundle/input files that are absent from publish.
* Update comments/step names used by shadow job evidence. Publication proof should enumerate the separate `Sign <target>` and `Publish <target>` successful steps, not demand the old single job's `Verify finished APK identity` step.

### `src/build/shadow_inputs.py` (required by the design record)

The design explicitly calls out the receipt boundary (`docs/review/SIGNING-SPLIT.md:17-23`). Current `observe` is `:520-542` and `publish_receipt` is `:544-607`.

* Keep patch-side `observe` and add a sealed receipt draft after it. The draft binds target, source commit, workflow run/attempt, captured consumed-input records, declaration/effective hashes, **unsigned APK SHA-256**, and the identity report. It must be produced/uploaded by patch before the job ends.
* At publish, `publish_receipt` must validate the signed handoff and read the signed release asset; it may use the carried sealed draft and artifact evidence, but must not require local patcher JARs, bundles, input APK, or request ledger. Preserve release/tag/asset/read-back checks, no overwrite, and the `effective_sha256` comparison. Include both unsigned and signed APK hashes in the public receipt, and keep limits stating this is same-run evidence, not independent attestation.
* Update the job lookup/step proof around `:360-407` to require complete coverage of the new sign/publish steps. Never let a missing patch or sign step appear as a successful publication.

## Artifact names and contents (all run-scoped)

Use exact names containing both `${{ github.run_id }}` and `${{ github.run_attempt }}` (not only target):

* `resolved-inputs-${target}-${run_id}-${run_attempt}` (existing CI handoff; retain).
* `source-inputs-${target}-${run_id}-${run_attempt}` (existing CI handoff; retain).
* `patch-output-${target}-${run_id}-${run_attempt}`: unsigned APK + patch-side `.build-inputs.json`, unsigned identity report, release metadata, and sealed shadow draft.
* `signed-output-${target}-${run_id}-${run_attempt}`: signed APK + sign evidence, unsigned/signed hash handoff and final identity report.
* `build-evidence-${target}-${run_id}-${run_attempt}`: if retained separately, run-scoped only; avoid duplicate conflicting reports.
* `shadow-inputs-${target}-${run_id}-${run_attempt}`: existing name already run-scoped; carry patch draft and final receipt evidence without secrets.
* `test-apk-${target}-${run_id}-${run_attempt}`: nonpublishing signed APK + final evidence; existing name already run-scoped.
* `shadow-plan-${run_id}-${run_attempt}`, `source-observation-${target}-${run_id}-${run_attempt}`, `resolved-observation-${target}-${run_id}-${run_attempt}`, `dependency-report-${run_id}-${run_attempt}`, `source-report-${run_id}-${run_attempt}`: existing CI artifacts already have run IDs; keep target/run/attempt uniqueness where matrix fan-out can collide.

On every download use exact run-scoped names (or a run-scoped pattern plus digest mismatch failure), never a broad unscoped `pattern` that can mix attempts. Artifact action versions remain the repository's pinned SHAs.

## Tests that pin current behavior and must change

These are the directly relevant tests/fixtures found in `tests/`; unrelated app/provider tests do not need signing changes.

* `tests/audit_contracts.py:20-21,62-81,132-160,213-240`: current expected secret holders are `Patch apk` and `Verify finished APK identity`; change to sign-only decode/capture/apksigner holders, assert patch has no secret and publish has no secret, and update import-closure expectations.
* `tests/daily_plan_contracts.py:231-240`: current assertion only checks the caller forwards `KEYSTORE_B64`; change it to assert forwarding reaches the reusable sign path while patch/resolve remain secretless.
* `tests/input_recipe_contracts.py:263,317-400`: recipe/release fixtures include `KEYSTORE_PASS` and release verification; keep the non-recording guarantee but update report fixture to the split unsigned/signed schema and run-scoped handoff.
* `tests/publish_ref_contracts.py:9-22`: current ordering checks `Decode keystore` before/after the single reusable job; replace with main-ref guard before dispatch and assertions that publish is a separate keyless job after sign.
* `tests/resolved_contracts.py:363-379,381-435`: change pre-secret ordering from “verify … before Decode keystore” to patch job has no decode at all; change test launcher cases that intercept `capture-signer` and `.signer-before-build.json` to the sign job/committed pin boundary.
* `tests/shadow_contracts.py:389-410` and publication fixtures around `:31-48,299-347`: update expected job steps from the single patch job's `Verify finished APK identity`/release handoff to patch→sign→publish, and test sealed patch receipt draft plus unsigned/signed hash carry.
* `tests/signer_pin_contracts.py:57-75`: current assertion requires `capture-signer` before `patch_target.py`; reverse it: patch must run without capture-signer, sign must capture and compare against `ci-signer.json` before apksigner.
* `tests/test_identity.py:36-86,134-155,181-214,355-379`: fixtures currently provide keystore material to one build and expect final signer in the same verify path; split tests into no-secret unsigned verification and sign-job certificate/keystore verification. Keep keytool `-storepass:env` and “password absent from argv” assertions for capture.
* `tests/test_identity.py:386-395,864-910,1060-1114`: update workflow ordering, report fixtures and release-contract fixtures for unsigned/signed records and run/attempt binding; retain wrong-signer refusal and keyless release-note env assertions (`:964-972`, `:1091-1093`).
* `tests/test_repair.py:1077-1103,1114-1145`: resource/argv tests must expect `--unsigned`, no keystore/password argv. In particular `test_safe_argv_literal_shell_metacharacters` currently asserts `--keystore-password=dummy password;$test` at `:1143-1144`; replace with an assertion that the value and all keystore options are absent while the patch name remains literal.
* `tests/test_source_inputs.py:141-163,343-359`: actual patch subprocess and public execution evidence must assert unsigned mode and no signing secret; preserve input-byte boundary checks.
* `tests/w16o_shell_contracts.py:20-26,99-102`: retain child env allowlist tests and add `--unsigned`/no-credential assertions; add tests covering all three `utils.sh` legacy call sites (`:904`, `:924`, `:1008-1013`) so future edits cannot restore `eval` password forwarding.
* `tests/lost_patches_contracts.py:70`: retain `--force` assertion but add unsigned-mode assertion if it covers patch argv construction.
* `tests/shadow_contracts.py`/`tests/status_contracts.py` fixtures that name the old `Verify finished APK identity`, `Verify release handoff (no publishing)`, and `Releasing APK files` steps must follow the new named jobs/steps; do not weaken the requirement that publication evidence has complete successful job coverage.

Also add new focused tests (in an existing identity/workflow contract module or a new `tests/signing_split_contracts.py`) for: absent `--unsigned` capability is a hard stop; patch job has no `KEYSTORE_*` in env/secrets; exact run-scoped artifact names; downloaded unsigned SHA mismatch fails before sign; ZIP-entry identity proof; wrong `ci-signer.json` certificate fails; apksigner flags are exact; publish has no signing secret; and unsigned/signed hashes are present in release/receipt evidence.

## Rollout proof (must be recorded before merge)

1. **Full nonpublishing batch:** dispatch `batch-patch.yml` with all 17 enabled IDs and `publish=false` on the candidate main/rehearsal. It must complete patch→sign for every target, with no keystore secret in patch logs/job env, `--unsigned` observed in each patch invocation, zipaligned unsigned handoff, exact pre-sign SHA match, signed `apksigner verify` pass, and signer equal to `src/build/ci-signer.json`. Retain run-scoped patch/signed/evidence artifacts and confirm no release was created.
2. **One publishing build of a small app:** from main, run one small/fast target with `publish=true`; verify patch and sign jobs succeeded, publish downloaded the signed run-scoped artifact, release asset SHA equals signed evidence, release metadata passed `release_contract`, and publication receipt read-back succeeded. Confirm publish job had only `github.token`, no `KEYSTORE_*`.
3. **Owner phone test:** install the published APK as an in-place update over the currently installed app (not uninstall/reinstall), exercise launch and the relevant update path, and record package identity, update success, signer/certificate continuity expectation and any data/login behavior. This is the only requested device proof; CI evidence is not a substitute.

## Risk rating

| Risk | Rating | Control / residual |
|---|---:|---|
| Patcher version lacks `--unsigned`, or flag behavior changes | **HIGH** | Capability probe and hard STOP before patch; pin/record patcher provenance; never fallback to signed mode. |
| Secret exposure via legacy `utils.sh` `eval` or future helper | **HIGH** | Remove all credential-bearing argv/eval paths; static tests and audit require no `KEYSTORE_*` in patch code; child env allowlist remains. |
| Wrong/mutated artifact signed due to cross-run download or tampering | **HIGH** | Run/attempt/commit/target binding, exact run-scoped artifact name, artifact digest mismatch failure, pre-sign SHA handoff and entry-level proof. |
| Wrong CI keystore/certificate or wrong apksigner alias | **HIGH** | `capture-signer` compares DER cert to `src/build/ci-signer.json` before signing; post-sign `apksigner verify --print-certs` compares again; release contract repeats pin. |
| Signing changes bytes beyond signature material / breaks alignment | **HIGH** | `--out` preserves unsigned input; zipalign check before sign; member-level identity proof; `apksigner verify`; phone in-place update. |
| Publish receives unsigned/stale/mismatched report | **HIGH** | Publish downloads only signed run-scoped artifact; release contract requires split schema, signed hash and cert; old reports refused. |
| Shadow receipt loses consumed patch inputs after jobs separate | **HIGH** | Sealed patch-side draft carries hashes/material identity; publish finishes with signed hash and release read-back without re-reading absent patch files. |
| Permissions accidentally permit patch/publish signing secret or write token | **MEDIUM-HIGH** | Per-job permissions (`read` patch/sign, `write` publish), no job-wide secret env, tests inspect workflow wiring. |
| Artifact retention/size or matrix naming collision | **MEDIUM** | Run-scoped names, explicit paths, retention policy, full 17-app batch before merge. |
| Re-signing changes device update compatibility | **HIGH** | Certificate pinned to current CI signer and owner in-place update test; if current installed APK uses another signer, stop and follow key-rotation/recovery process rather than publish. |

## Limitations / unverified points

* The checkout does not contain the downloaded Morphe jar, so the exact runtime output of its current `patch --help` and whether its unsigned output is zipaligned cannot be verified here. The upstream source/PR establishes the flag spelling and intended branch behavior; the capability probe plus full batch is still required against the jar actually selected by CI.
* The proposed helper/function names and artifact filenames are implementation choices; they are intentionally explicit so tests can pin them. No code was edited in the checkout.
