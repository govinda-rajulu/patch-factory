<!-- archived from assistant skill 'Releases Obtainium and Devices', last updated 2026-09-24 10:22 (Asia/Calcutta), exported 2026-09-29 -->
<!-- summary: Load for releases, Obtainium or devices; covers neutral imports, optional MicroG, PR68 retention evidence, same-version gaps and signing/device limits. -->

# RELEASES-OBTAINIUM-AND-DEVICES

Reconciled 19 September 2026. Read **Patch Factory Builds** for the current code checkpoint. Keep configured, approved, merged, published, imported and device-tested states separate.

## Obtainium catalog and optional MicroG

PR55 replaced both personalized JSONs with `docs/obtainium.json`: one neutral 14-app catalog with All apps / Select only page flows. `src/etc/obtainium.py --check` is deterministic and network-independent; release availability is separate and no per-release catalog commit is needed. Derive membership from current config/generator. Photos and YouTube intentionally use patched package IDs; verify exact mapping and actual output rather than assuming the source ID.

The owner reported the earlier bulk Obtainium import working. That is not proof of all devices, update paths or configuration migration. Existing patched-app filters still extract APPVERSION, require numeric build suffixes, use capture group 1 as a string and allow older-release fallback. Unique release tags do not complete patch-only/same-version delivery. Actual client semantics and installed-setting migration remain open.

On 19 September the owner approved the exact six-path MicroG/page candidate, tree `8c3b99df410dfb644dd9159327328e337a14dbe9`, on main `3a855e5bb93ca6cc2580c7e9db4006b68f7b96f0`: one PR, exact-head CI-gated merge, main CI and Pages verification. The handoff has been delivered, not yet confirmed executed. Recheck its RESULT and live deployment before claiming the companion is available.

The candidate generates separate `docs/obtainium-microg.json` and a `Morphe MicroG RE only` option. It leaves the existing 14-app export byte-identical. MicroG is an optional upstream companion, not a fifteenth patched target, not silently included in All apps, and not vendored or re-signed. Its standard-APK filter is strict, stable-only, with no older-release fallback. Do not generalize the patched-app fallback settings to this companion.

Fresh [MicroG release 6.1.4](https://github.com/MorpheApp/MicroG-RE/releases/tag/6.1.4) metadata exposed one `microg-6.1.4.apk`, 13,393,291 bytes, host SHA256 `907b0f1d64d4bdf2fc15df596129cdf9f140f5360f557d24ff2e987c9f586f15`. Immutable source at `d8df10ab687a1c1ca05221634cfa46bad262023a` derives `app.revanced.android.gms`; minSDK24, target29, DefaultRelease. Source flavors/ABI filters do not prove four published variants. The earlier four-variant claim was unsupported. Source-derived identity and host metadata are not binary/signature inspection or compatibility with the owner's installed MicroG.

[Official Obtainium deep links](https://wiki.obtainium.imranr.dev/deep_links/) distinguish app/apps config confirmation, add-source links and `obtainium://refresh` update checks. Refresh is not catalog subscription or automatic configuration sync. Warn that importing a matching tracked entry may replace its settings; preserve existing update/install preferences, signer checks and app data. No forced migration, uninstall or protection bypass is authorized.

## Release identity and retention, implemented

PR46 tags are PREFIX-vAPPVERSION-bBUILDID, with UTC date8, zero-padded runID20 and attempt6. Different attempts get distinct tags; missing/invalid real metadata refuses. Legacy date tags remain readable. This packet did not change APK filename or package/versionName/versionCode formats.

`release_contract.py` binds exactly one checked APK/report/path/hash and current run identity to publication. The release action disables allowUpdates/replacesArtifacts, enables artifactErrorsFailBuild and binds a new tag to github.sha. This is not owner-proof immutability. Inspect partial publication; a rerun creates a new attempt identity, not a repair of the previous tag. Never use the repository's globally latest release as an app-specific answer.

PR45 retention is read-only preview, with no apply/delete mode. Protect the newest two dated releases per configured prefix, frozen `truecaller-v26.10.6`, manual/nonstandard/unknown/ambiguous entries, drafts/prereleases and keep markers. Fresh inventory, restore evidence and approval precede deletion. The initial 29 protected/zero candidates is historical; release-body prose alone is not authenticated provenance.

## Shadow publication evidence is not full F05/F06

PR59 connects daily declarations, consumed-input comparison and non-secret publication receipts. Reader qualification checks exact completed-successful run/attempt, target identity/handoff/publication evidence and asset/source identities. Failed, partial, cancelled, pending, nonpublishing or unrelated runs cannot qualify; missing metadata is UNKNOWN, and newer legacy release prevents older-baseline fallback. No real build-selection authority was transferred to shadow decisions.

[Scheduled run 35369326453](https://github.com/govinda-rajulu/patch-factory/actions/runs/35369326453) succeeded on exact main3a855e5b with Plan and YouTube/AdGuard/Prime Video/Facebook. YouTube receipt asset `pf-publication-v1-youtube.json` exists, 1057 bytes, host SHA256 `7b4ee78ac06a1df5fa6de79baaccbc65dbac769c20d794711bc583e8a97d7d50`. Its body download failed in this review. Asset metadata and green composite steps do not independently qualify downloaded receipt/APK bytes or every advisory substep. Full dynamic pre-resolution/reuse, omitted-target observation, runtime/transitive coverage and a durable baseline independent of expiring live-run metadata remain open.

## Signing, recovery and devices

CI signer SHA256 `08480f6649a2be33ff3cccacce07454761d5fb9abe65f1e2caeeb782e382d050` is checked against the pre-build certificate by final identity gates. This is not original-publisher authenticity or installed-app continuity.

On 10 September the owner reported second copies of BOTH signing backup files in a personal cloud drive. Signing restore is untested, not proved encrypted/offline recovery. Never request keys, passwords or tokens in chat; repository secrets are not retrievable backups. Any future restore drill must verify the certificate privately and be explicitly nonpublishing. Current `RECOVERY.md` contains obsolete/risky advice, including a nominal restore drill that publishes; do not execute it as trusted guidance.

Separate Git recovery bundles were restore-tested and owner download confirmed during PR55 closeout. That backup predates PR56 onward; refreshing independent recovery remains open. Cloud storage was not inspected. A knowledge ZIP is not a lossless transcript, Git backup or signing backup.

Phone tests remain owner-deferred without blocking unrelated engineering. Original MX APK46,494,122 bytes, SHA256 `9688efdfcd9327ebe0bd45c2466d6f9cb52a7c3eca76d08910724c0032226426`, passed owner-run apksigner v1/v2/v3. Later wrapper failure leaves that wrapper incomplete, not the signature test failed; no prerequisite verifier rerun.

Prefer updating in place, but same package/key alone does not guarantee update, rollback or preserved sessions: check versionCode, SDK/ABI, certificates, download hash and actual installer error. Do not reflexively uninstall or disable protections. Frozen Truecaller remains protected, not a proven downgrade. Historical OTP limits and app inventories are dated observations, not current guarantees.

## Evidence boundaries

Earlier repair smokes used publish=false. Batch34870190849 supplied 14 APK/report pairs checked by the owner collector, not independent Android/publisher testing. Daily ci.yml at12:30UTC/18:00IST remains independently enabled and may publish. PR54 removed the page credential/API-write surface and added safe text/target-aware rendering; current hardening does not finish trusted watcher deltas, official icons/fonts or same-version updates.

## Live companion update, 19 September 2026 at 19:15 IST

The earlier approved/local-only labels are now historical. [PR60](https://github.com/govinda-rajulu/patch-factory/pull/60) merged to `04e7d29e9125e164727d202908838ad19dcad56f`, exact approved tree `8c3b99df410dfb644dd9159327328e337a14dbe9`. Main CI35446648748 and Pages35446648272 independently show success on that commit. [Live page](https://govinda-rajulu.github.io/patch-factory/) and [companion JSON](https://govinda-rajulu.github.io/patch-factory/obtainium-microg.json) were separately read: optional Morphe MicroG RE, app.revanced.android.gms, strict standard APK/stable filters, no older fallback. Owner controller verified four exact public byte hashes including unchanged7985-byte14-app catalog and605-byteMicroG JSON.

The147570-byte handoff is executed/retired, not a command to rerun. No APK dispatch, deletion or device installation. Optional import still needs Obtainium confirmation; matching tracked settings may change and existing installation preferences apply. Installed MicroG signer/variant/data migration and Android behavior remain unverified. Same-version patched-app delivery and full durable fingerprints remain open.

## September 24 release/device reconciliation

PR60 is merged and live, so older delivered-but-unverified MicroG/page wording is historical. PR68 later shipped retention-preview support and safety-document corrections. Its 19 September inventory recorded 63 releases, 68 assets, 37 protected and 26 candidate releases/assets at that time; this was not a backup, and no release/tag/APK/local folder/phone deletion occurred.

PR70 shipped the explicit six ES/MX resource exclusions and dispatched one approved 13-target publishing batch with Reddit held. Dispatch acknowledgement is not publication: the writer stopped at the identity reader, qualified baselines were not verified, and batch `35571131023` attempt 1 must not be redispatched. Phone tests, installed MicroG compatibility, signing restore and same-version patched-app delivery remain unverified.
