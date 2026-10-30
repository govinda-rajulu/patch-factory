# Using Patch Factory

Checked 29 October 2026 (W16x). This guide is the one home for what the site, imports and updates mean. The page, README and release notes keep one short line each and link here. Safety boundaries: [SECURITY.md](../SECURITY.md); cleanup and recovery: [RECOVERY.md](../RECOVERY.md).

## Start with the download

The [app shelf](https://govinda-rajulu.github.io/patch-factory/) shows the newest eligible published APK for each app, its publication time, and a concise change summary; the full original release notes stay on the linked GitHub release page. “Recent upload” means recently published bytes, not necessarily a newer app version. The release archive is history, not one global “latest app.”

Patched apps are built here. Morphe MicroG RE is an optional upstream companion from MorpheApp, not patched or re-signed here. Its channel offers stable only or stable plus dev prereleases. Universal is the default; the import panel also offers Auto architecture, ARM64 and ARMv7. Exact architecture choices refuse a different CPU file; if upstream has no matching asset, the selection can be unavailable. No no-icon variant is silently substituted.

See [Optional companions and review queue](companions.md) for PotHelper, Helper for Morphe and the other Morphe Workspace suggestions. They are separate apps, not patch bundles or additional Patch Factory build targets. The guide records what is available, what needs review and what is deliberately not a default.

The generated inventory in [README.md](../README.md#current-state) is the current app list: 17
enabled targets, all polled by the scheduled build. `src/targets.json` is the source for each
app's store, primary providers, fallback providers and poll flag. Do not use an older copied list.

## What changed?

New releases share a structured summary between GitHub release notes and the shelf. Comparisons cover the app version, reported provider/bundle, applied patch names, package, minimum Android API, signing certificate, source commit and APK hash when both releases provide them. Equal patch names do not establish equal patch code, options or defaults.

Older releases remain unchanged. Their original notes are displayed; missing comparable history is labeled unknown. Comparison data is publisher-reported metadata, not an independently signed attestation or authority to skip builds. GitHub-source release notes are available to clients such as Obtainium, but client display and Android behavior are not tested by this website.

## Dropped patches and fallback providers

Since packet W13 (10 Oct 2026) a build no longer fails when its provider stops offering a chosen patch: it builds without it and says so. Release notes then start with "Built without N chosen patch(es) the provider no longer offers: ..."; the build log has one `PATCH_DROPPED` notice per name. More than three, or more than a quarter of the chosen patches, still fails the build. When a build fails, the next provider of that app builds instead, with its own app version (Facebook: De-Vanced on 580; Instagram: HushGram). Its release notes start with "Built with fallback provider ..."; the log has `PROVIDER_FALLBACK`, and every attempt prints `ATTEMPT` and `ATTEMPTS_OK` or `ATTEMPTS_FAILED`. Manual Patch's `provider` box builds one provider on purpose. The daily Selection watch removes such names from the lists and keeps one issue, "Selection watch", with new patches waiting for a decision and every provider's release notes. In apps without an include list (YouTube, YouTube Music) a new patch already ships by the provider's default; the issue lists it once with the line to drop it. Reminders in `src/etc/reminders.json` (for example "HushGram reached 0.1") show under "Needs you" once a provider reaches the named version.

## Obtainium

No Obtainium yet? The shelf's **Obtainium** card downloads it straight from its upstream releases: the standard flavor (`dev.imranr.obtainium`, the one the self-update entry tracks), Universal by default, ARM64 and ARMv7 under the card with SHA-256 checksums. Install it, then use **Track with Obtainium**.

Expand **Track with Obtainium**, choose All apps or Select only, prepare the configuration and confirm inside Obtainium. All apps includes every configured patched app; MicroG is opt-in. Select only offers patched apps and MicroG together. **Include Obtainium self-update** adds the standard GitHub Obtainium companion to either flow; in Select only, you must also select its row after preparing the list. This is for `dev.imranr.obtainium`, not the F-Droid package `dev.imranr.obtainium.fdroid`. It does not replace or migrate an F-Droid installation.

Choose **MicroG architecture** and **MicroG channel** before preparing the import. Universal (recommended) avoids assuming which device will open a shared configuration. Auto architecture uses Obtainium's filename-based filter; it is not device detection by this website. ARM64 and ARMv7 require the matching published file. **Done / collapse** hides the panel without discarding choices. **Reset choices** clears the page's selection and prepared links only; it never removes tracked or installed apps.

Importing a matching tracked app may replace its tracking settings. Unselected apps are not removed. Refresh checks tracked apps; it is not subscription to this catalog or automatic configuration synchronization. Patched-app tracking reads the app version and the build id (W15), so a patch-only rebuild of the same app version is a new release; re-import the Obtainium JSON once if your tracking is older than that.

**Does an Obtainium update need patching again?** An APK downloaded from this repository's patched-app releases is already patched; Obtainium tracks and installs it, it does not run the patcher. An original APK from a store is not a replacement for that patched build. Keep each tracked app pointed at its intended source and inspect package/signature compatibility before updating. Do not switch patched entries to a stock store to work around a missing update.

## Install and update

**Signing warning:** the import pins this repository's CI signing certificate (not the original publisher's). Obtainium (1.6.16 to at least 1.7.3) reads a downloaded APK's certificate with a call that returns nothing on **Android 9 and 10**, so there every install says **Signing certificate mismatch** with **Downloaded certificate hash: None** and is blocked. Android 11 and newer read it normally. On Android 9 or 10 only, untick **Signer pin** in the portal before importing (or use the **no-pin JSON**); keep the pin for any other mismatch, where the downloaded hash is a different value. Android itself still enforces its same-signer check and refuses an update signed by another key, so never uninstall or disable protections to get around that. Update one non-critical app in place first. Reinstall only after Android itself refuses an update, and after backing up that app.

Android 9/10 cannot read signers in Obtainium: v1.7.3 and main use only `GET_SIGNING_CERTIFICATES`, while those Android versions fill archive certificates only with `GET_SIGNATURES`. Keep the pin off there. Android itself refuses an update signed by another key, so only the first install needs care: download that first APK from the release page.

Check the APK's package, minimum Android API, architecture, size and SHA-256 against the release's **Download evidence**. Patched downloads use ARM64 naming; an APK may contain no native libraries. Prefer an in-place update when Android permits it. A matching key/package does not guarantee data preservation or rollback; MicroG data and signer compatibility need the same care. What CI does and does not check: [About these builds](#about-these-builds).

## About these builds

The one home for the checks, limits and safety lines every release used to repeat (W14, 11 Oct 2026). Release notes and the page link here.

- **CI checks** APK identity, the declared minimum Android API, native payloads, applied patch names and the configured signing certificate.
- **Not checked**: builds are not phone-tested by this pipeline. The CI signing certificate is not proof of original-publisher authenticity or installed-app compatibility.
- **Updates**: a new build is not necessarily a new app version. Since 17 Oct 2026 the import tracks the build id too, so Obtainium offers a same-version patch-only rebuild as an update. Imported before W15h? Import the JSON once more (it replaces the tracking settings of matching apps), then update one non-critical app in place first. Do not reinstall every app.
- **Never needed**: No automatic uninstall, import migration or device-protection bypass is required or recommended. Do not uninstall, clear app data or disable device protections just to force an update.

## Reading status

MicroG's download card has its own channel selector, synchronized with the Obtainium toolbar. The selected channel is visible even when both channels currently select the same release. Changing it updates page downloads and invalidates previously prepared imports; it does not update installed or tracked apps. To change Obtainium tracking, include MicroG, prepare a new import and confirm it in Obtainium. Refreshing this page resets the channel to stable.

Build reports distinguish dependency-only checks from app-build jobs and summarize successful, failed and other/pending app builds. A red batch can contain a successful app publication. The step named `Patch apk` also performs source downloading, so its failure is not proof that applying a patch failed. Open the exact job for the actual error. Existing baseline qualification requires the whole source run to succeed, even when one app published successfully (qualify-baselines.yml runs only on a successful run; W16j added one plan per candidate inside it).

| Surface | What it means | What it does not prove |
| --- | --- | --- |
| Published app | An eligible APK exists in that app's release history | Phone compatibility or a newer app version |
| Builds | Workflow status and target-job results, with failed steps when exposed | Every successful job published a release |
| Watch | Provider, community and repository checks, plus saved reports | Complete coverage, trusted changes, or all-clear from green alone |
| Validate | Repository contracts and action compatibility smoke | A full Android build or installation |

Missing, rate-limited, failed or truncated reads remain unknown. Timestamps describe the underlying run/report. Watcher coverage remains partial; issue comments are reports, not trusted build-selection instructions.

## Schedules

Every scheduled automation with its IST time, generated from the workflow files: [SCHEDULES.md](SCHEDULES.md).
There is no keepalive cron. `keepalive.yml` is a manual fallback only.

## Needs you

`needs-you.yml` runs daily at 10:29 IST after Tooling watch. It combines the five standing watch
reports, provider candidates from the checked-in community index, review items and enabled-app
items into one issue. Only an owner comment on that issue is accepted. Comment one complete command
per line: `take N-xxxxxx`, `drop N-xxxxxx` or `hold N-xxxxxx`.

For a provider candidate, `take` dispatches Explore; `drop` or `hold` records the decision. For a
review item, `take` adds `accepted`, `drop` closes the review issue and `hold` adds the `hold`
label. Other choices are recorded in the watch-state ledger. A hold hides an ordinary item for 14
days. An app item is retired after an owner answer; the next packet applies its keep-building or
stop-building decision.

## Maintaining dependencies

The Reddit source page diagnostic was removed on 8 October 2026 (packet W4): Reddit builds from APKPure again and the probe had no remaining use. Its history stays in git and `docs/review/`.

The old Google Play APK helper was removed in W16d because no build called it. The
`src/build/helper/ggplay_dl/` path and its preparation dependency hooks no longer exist. APK
sources come from each target's `source` and store fields; there is no Google Play fallback.

Status page data also runs `cache-prune`. It reads every Actions cache page, keeps the newest
cache for each conservative key prefix, and deletes only a non-newest cache that is older than
24 hours and has not been accessed for more than 7 days. Missing or malformed timestamps are
kept. This is automatic stale-cache cleanup, not release cleanup.

Dependabot groups minor/patch action updates, while major action upgrades receive individual PRs. Structural tests check action identity, pin format, production/smoke agreement, permissions and order instead of hardcoding yesterday's version number. The mandatory runtime smoke still has to execute the proposed versions successfully. No automatic merge and no promise that every future action upgrade is compatible.
