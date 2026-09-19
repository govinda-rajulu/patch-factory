# Using Patch Factory

## Start with the download

The [app shelf](https://govinda-rajulu.github.io/patch-factory/) shows the newest eligible published APK for each app, its publication time, and release notes inline. “Recent upload” means recently published bytes, not necessarily a newer app version. The release archive is history, not one global “latest app.”

Patched apps are built here. Morphe MicroG RE is an optional upstream companion from MorpheApp, not patched or re-signed here. Its channel offers stable only or stable plus dev prereleases, using the standard universal APK. No other variant is silently substituted.

## What changed?

New releases share a structured summary between GitHub release notes and the shelf. Comparisons cover the app version, reported provider/bundle, applied patch names, package, minimum Android API, signing certificate, source commit and APK hash when both releases provide them. Equal patch names do not establish equal patch code, options or defaults.

Older releases remain unchanged. Their original notes are displayed; missing comparable history is labeled unknown. Comparison data is publisher-reported metadata, not an independently signed attestation or authority to skip builds. GitHub-source release notes are available to clients such as Obtainium, but client display and Android behavior are not tested by this website.

## Obtainium

Expand **Track with Obtainium**, choose All apps or Select only, prepare the configuration and confirm inside Obtainium. All apps includes the fourteen patched apps; MicroG is opt-in. Select only offers patched apps and MicroG together. **Done / collapse** hides the panel without discarding choices. **Reset choices** clears the page's selection and prepared links only; it never removes tracked or installed apps.

Importing a matching tracked app may replace its tracking settings. Unselected apps are not removed. Refresh checks tracked apps; it is not subscription to this catalog or automatic configuration synchronization. Patched-app tracking currently extracts the app version, so delivery of patch-only rebuilds with the same app version remains limited.

## Install and update

Check the APK's package, minimum Android API, architecture, size and SHA-256. Patched downloads use ARM64 naming; an APK may contain no native libraries. The configured CI signing certificate is checked, not the original publisher or your installed app's certificate. CI success is not a phone test.

Prefer an in-place update when Android permits it. A matching key/package does not guarantee data preservation or rollback. Do not uninstall, clear app data or disable device protections just to force an update. MicroG data and signer compatibility need the same care.

## Reading status

MicroG's download card has its own channel selector, synchronized with the Obtainium toolbar. The selected channel is visible even when both channels currently select the same release. Changing it updates page downloads and invalidates previously prepared imports; it does not update installed or tracked apps. To change Obtainium tracking, include MicroG, prepare a new import and confirm it in Obtainium. Refreshing this page resets the channel to stable.

Build reports distinguish dependency-only checks from app-build jobs and summarize successful, failed and other/pending app builds. A red batch can contain a successful app publication. The step named `Patch apk` also performs source downloading, so its failure is not proof that applying a patch failed. Open the exact job for the actual error. Existing baseline qualification requires the whole source run to succeed, even when one app published successfully.

| Surface | What it means | What it does not prove |
| --- | --- | --- |
| Published app | An eligible APK exists in that app's release history | Phone compatibility or a newer app version |
| Builds | Workflow status and target-job results, with failed steps when exposed | Every successful job published a release |
| Watch | Provider, community and repository checks, plus saved reports | Complete coverage, trusted changes, or all-clear from green alone |
| Validate | Repository contracts and action compatibility smoke | A full Android build or installation |

Missing, rate-limited, failed or truncated reads remain unknown. Timestamps describe the underlying run/report. Watcher coverage remains partial; issue comments are reports, not trusted build-selection instructions.

## Maintaining dependencies

The manual-only Reddit source page diagnostic observes two fixed APKPure HTML pages (version 2026.38.0 and the current download page) using the existing pinned resolver. It has no signing secrets and performs no APK download, build, publication or fallback. Its small seven-day report contains counts and boolean response-shape markers, not raw HTML, cookies or signed URLs. A marker is a hint, not a diagnosis, and today's response does not reconstruct a failed historical response. Observation failure stays UNKNOWN; this workflow is not an app-recovery test.

Dependabot groups minor/patch action updates, while major action upgrades receive individual PRs. Structural tests check action identity, pin format, production/smoke agreement, permissions and order instead of hardcoding yesterday's version number. The mandatory runtime smoke still has to execute the proposed versions successfully. No automatic merge and no promise that every future action upgrade is compatible.
