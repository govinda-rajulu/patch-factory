# Patch Factory

Builds Android APKs with configured third-party patch bundles in GitHub Actions,
checks the finished output, and publishes a separate signed release per build.

**[Downloads and status](https://govinda-rajulu.github.io/patch-factory/)**
| [Install and Obtainium guide](docs/guide.md)
| [Recovery and operations](RECOVERY.md)
| [Security boundaries](SECURITY.md)
| [Open work](docs/review/OPEN-WORK.md)

The generated table below is the configured patched-app inventory. Morphe MicroG
RE is an optional upstream companion, not another patched target. The site
offers stable or stable-plus-dev tracking for its standard universal APK.
Neither importing a catalog nor refreshing the site changes installed apps.

## Builds and releases

The supported entrypoints are `.github/workflows/manual-patch.yml` for one target,
`batch-patch.yml` for an explicit comma-separated target set, and `ci.yml` for
the scheduled poll. The manual and batch workflows default to **publishing**.
An approved nonpublishing smoke must explicitly select `publish=false`; it still
downloads, patches and signs an APK and is not a signing-key restore drill.

Use the current main commit after its exact validation succeeds. Rerunning an
old Actions run tests its original commit, not a newer fix. Record the dispatched
workflow, input set, commit, run ID and attempt; do not identify a run by "latest".
Batch jobs do not fail-fast, so a red workflow can contain published successes.
Inspect every requested target and its release rather than repeating the entire
batch. Existing per-target concurrency queues work instead of cancelling it.

The daily schedule is generated below. Its legacy provider-date poll still
controls build selection. Prepared dependency comparisons are shadow evidence,
not permission to skip an APK build. Missing or invalid comparison inputs are
UNKNOWN, not unchanged.

## How a build works

1. Validate the enabled target and configuration before downloads and keystore
   decoding in the workflow.
2. Verify a supplied same-run dependency packet when available; otherwise use
   the existing validated resolver. The patcher intentionally tracks latest
   stable. Elect one candidate and load ordered extra bundles separately.
3. Reuse the exact selected bundle bytes, validate tools and options, and build
   per-bundle argument arrays. `-e` and `-d` bind to the nearest preceding `-p`;
   a same-bundle exclusion wins. Duplicate requested names across bundles fail.
4. Fetch the configured APK source and check package, container and minimum
   Android API. Enforce the target's current version ceiling and source contract.
   A missing link is not permission to substitute the store's latest version.
5. Apply the configured selections and compare requested versus applied names.
   Verify finished APK identity, native payloads and the configured CI signer.
6. Validate the exact release handoff before publication. Save build evidence
   and shadow comparisons separately; advisory shadow output is not a build gate.
7. Publish a new tag/asset identity only when the workflow's publication
   conditions pass. A separate follow-up qualifies eligible publication receipts
   only after the **whole source workflow succeeds**.

This is not an Android installation test, an original-publisher authenticity
proof, or a complete reproducibility/semantic-fingerprint system.

## Release identity and Obtainium

New tags use `PREFIX-vAPPVERSION-bBUILDID`. BUILDID contains the UTC date
(8 digits), run ID (20 zero-padded digits), and attempt (6 zero-padded digits).
APK names remain `APKNAME-vAPPVERSION-arm64-v8a.apk`. An APK without native
libraries can retain that filename; read its identity report.

Publication refuses an existing identity rather than overwriting it. Older
date-only releases remain historical entries. Release notes show available
version/patch/source differences; absent comparable metadata stays unknown.
Equal applied names do not mean equal provider code, options or defaults.

The generated Obtainium imports currently extract **APPVERSION only**, not
BUILDID. A patch-only rebuild therefore does not guarantee an update notification.
Catalog import is not subscription or automatic settings migration. Confirm
tracking changes in Obtainium; do not uninstall or bypass Android protections.
See the [guide](docs/guide.md) for optional MicroG and selected-app imports.

## Selection and source decisions

`src/targets.json` is the source for targets, candidates, ordered extras, channels,
ceilings and SDK limits. Only candidates enter provider election; an extra bundle
is not a fallback candidate. GitLab extra support does not imply GitLab primary
candidate support. Provider age is advisory, never a date-based kill switch.

`BANNED` and `CONFIRM` use lowercase substring rules. Configured, approved,
applied and published are separate states. CONFIRM warnings do not mean approval
has been granted. Preserve explicit owner decisions and inspect both include and
exclude lists; do not use historical review sheets to silently change them.

Store responses can redirect, omit a version, or change layout. HTTP 200 and a
version string somewhere in HTML do not establish an exact-version download.
Changing `any_version`, a ceiling, source, provider or patch set is a separate
review decision; an applied-count check alone does not establish compatibility.

## Repository maintenance

Use isolated checkouts, explicit path staging, a reviewed PR and exact-head
validation. No direct-main or force push. Run preflight, the Python suites,
portal contracts, generator checks and shell checks before requesting merge.
Generated content is edited through its generator or source data, not by hand.

The Add target workflow and related tools need a separate cross-consumer schema
review before their disabled-target behavior can be treated as a complete
onboarding contract. Do not enable a target merely because scaffolding exists.

**Rebuild first, cleanup last.** Preserve working releases until replacements
and recovery copies are verified. `src/etc/release_retention.py` is GET-only and
preview-only: it protects the newest two dated releases per prefix plus frozen,
manual, unknown and ambiguous records. Recognizing evidence assets is not
verification of their contents or deletion authority. Review exact release and
asset identities before any separately approved cleanup; tags, run artifacts,
branches and local folders are distinct scopes.

<!-- STATE:GENERATED - edit src/targets.json, not this block -->

## Current state

Generated from `src/targets.json` by `src/etc/readmegen.py`. **3. Validate** fails a push
that leaves this block stale, so it cannot drift.

- **14 apps**, all enabled, 14 polled by the scheduled build (`30 12 * * *` UTC).
- Patch-age warning: 60, 120 days. Age is advisory; requested/applied checks and build verification decide.
- 2 build tool(s) pinned by sha256 in `src/build/TOOLING.sha256`; a byte mismatch aborts the build.
- 2 patch(es) quarantined in `src/patches/QUARANTINE`, held out of every include list by CI.

| App | id | tag prefix | store | patch providers | polled |
|---|---|---|---|---|---|
| AdGuard | `adguard` | `adguard` | apkmirror | rushiranpise + hoo-dles | yes |
| ES File Explorer | `esfile` | `es-file` | apkmirror | ftl | yes |
| Facebook | `facebook` | `facebook` | apkmirror | derevanced | yes |
| Google Photos | `photos` | `gg-photos` | apkmirror | rushiranpise | yes |
| Instagram | `instagram` | `instagram` | apkpure | piko + brosssh | yes |
| JioHotstar | `hotstar` | `hotstar` | apkmirror | chiggi | yes |
| Key Mapper | `keymapper` | `key-mapper` | apkpure | lain | yes |
| Microsoft Edge | `edge` | `edge` | apkpure | quantavil | yes |
| MX Player Pro | `mxplayer` | `mx-player` | apkmirror | ftl + paresh | yes |
| Prime Video | `primevideo` | `prime-video` | apkmirror | hoo-dles | yes |
| Reddit | `reddit` | `reddit` | apkpure | adobo | yes |
| Telegram | `telegram` | `telegram` | apkmirror | rushiranpise | yes |
| Truecaller | `truecaller-combo` | `tc-combo` | apkmirror | bufferk + paresh + binarymend | yes |
| YouTube | `youtube` | `youtube-morphe` | apkmirror | morphe | yes |

### Build gates and separate validation checks

1. `bancheck.sh` blocks a BANNED patch reaching an include list; CONFIRM warns; EXCEPTIONS is dated.
2. `quarantine.sh` keeps a patch that broke a real build out of every include list.
3. `selections.sh` aborts if one patch name is requested under two bundles of one target.
4. `build.sh` compares requested against applied **by name** and refuses to release on a gap.
5. The package name is verified twice: on the downloaded APK, and against what the patcher filtered.
6. `check_sdk.sh` rejects an excessive or unreadable `min_sdk_ceiling` measurement.
7. `tooling.sh` verifies pup and APKEditor; morphe-desktop intentionally tracks latest.
8. `readmegen.py --check` and `pagegen.py --check` fail a push that leaves docs stale.
9. `shellcheck` at severity=error over every script in `src/build` and `src/etc`.

<!-- /STATE:GENERATED -->
