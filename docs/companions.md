# Optional companions and review queue

Reviewed 22 September 2026. This is a decision record, not an installer, app
bundle, security certification or approval to change a phone.

The community [Morphe Workspace collection and discussion](https://www.reddit.com/r/MorpheApp/comments/1wiowwa/morphe_workspace_a_collection_of_android_apps/)
is useful discovery material. It is a personal collection, not one official
framework. Its MIS/MES/MAS categories are not security ratings. Links below do
not enable anything in Patch Factory. The fourteen patched targets, patch
selections, APK sources, signing and existing imports remain unchanged.

## Shortest useful route

Use the [existing download and Obtainium flow](guide.md#obtainium) for published
patched apps. MicroG and standard Obtainium self-update are already optional
companions. You do not need Morphe Manager, Desktop or an APK download helper
merely to install a finished Patch Factory APK.

If YouTube playback works, adding another service is not a required upgrade.
If it does not, PotHelper is a candidate to investigate against the exact
YouTube build and upstream instructions. This guide does not toggle Spoof video
streams, PoToken provider or any other approved patch or runtime setting.

If you patch manually in Morphe Manager, Helper for Morphe is relevant to
obtaining the original input APK. It is not the patcher and is not a repair for
Patch Factory's CI downloader.

## Already available here

| Companion | Current support | Boundary |
| --- | --- | --- |
| [MicroG-RE](https://github.com/MorpheApp/MicroG-RE) | Optional upstream import; stable or stable plus dev; Universal default, Auto architecture, ARM64 or ARMv7 | Not a patched target. Exact ABI may have no published file. Installed signer/data compatibility is not established. |
| [Obtainium](https://github.com/ImranR98/Obtainium) | Optional standard GitHub self-update entry | Not the F-Droid package; no automatic migration, catalog subscription or promise of same-version patched-app delivery. |

These import changes shipped in [PR73](https://github.com/govinda-rajulu/patch-factory/pull/73).
Preparing or importing a configuration is not proof of installation or device
compatibility. A matching tracked entry may have its tracking settings replaced.

## PotHelper: useful candidate, external only

[Pinned upstream README](https://github.com/MorpheApp/PotHelper/blob/0d4d9b4b4b335b2732c28b8ccd3df9b4b4870410/README.md)
describes a Java PoToken minter whose helper app runs without internet
permissions. It also disclaims functionality, stability and safety guarantees.
That README claim is not a measured battery/data result, full source audit or
verification of every published APK.

The same README says native components are distributed only as compiled
binaries, with corresponding source unavailable, and warns against linking or
distributing those components with GPLv3 or other strong-copyleft code.
**No native-code vendoring, bundling or re-signing is proposed.**

Reviewed release metadata:
[v1.1.1](https://github.com/MorpheApp/PotHelper/releases/tag/v1.1.1),
`pot-helper-1.1.1.apk`, 184718 bytes, host-reported SHA-256
`8e808a4f33d42e5c7534cf578305ca9cb48a0196a97bb35914d7a27a5f099a02`.
The release reports `immutable: false`; a version label alone cannot pin future
bytes. The APK was not downloaded, signature-checked or phone-tested in this
documentation review. Host metadata is not independent authenticity.

**Next integration gate:** inspect exact APK bytes, package, version, minimum
SDK, native ABIs and signing certificate; design a separate opt-in upstream
Obtainium entry with unambiguous asset matching and no incompatible fallback.
Check the client consumer and existing-install implications before adding the
entry. Device testing remains a separate, explicitly unverified step.
There is no PotHelper one-click import in this PR.

## Helper for Morphe: manual workflow and source-audit candidate

[Pinned upstream README](https://github.com/rushiranpise/helper-for-morphe/blob/8b0c487efdfbda24bb8fe4acb4693c7089b5522e/README.md)
describes receiving a package/version Android intent from Morphe Manager,
finding an original APK and returning a readable URI. Its license is GPLv3.
This review reads the documented contract; it is not a full implementation or
release-binary audit.

For an intentional manual-patching experiment:

1. Start the request from Morphe Manager. The shared discussion reports that
   Settings > System > APK Download Helper must be enabled before the helper
   option appears. This UI path is community-reported, not verified on a device
   here; consult the installed Manager version if the labels differ.
2. Prefer the exact requested version policy, not Latest as a rescue fallback.
   Upstream documents Requested, Latest and Always ask; it says Requested checks
   version name and version code, with build mismatches requiring a decision.
   Stop on an unexpected package, build, file format, ABI or signer.
3. Leave VirusTotal disabled unless you deliberately consent to its data sharing.
   Upstream documents hash lookup first and possible file uploads, including
   inner APKs of split bundles. Even a hash query discloses information; no API
   key, upload or automatic scan is required by Patch Factory.
4. Review any exported troubleshooting log before sharing. Upstream says logs
   include URLs, redirects and app/device details. Remove sensitive request
   values, tokens and identifiers; do not paste a raw log into a public issue.

A clean antivirus result does not establish trusted provenance or guarantee
safety. Patch Factory does not adopt the thread's blanket safety, banking-app,
battery or antivirus-superiority claims.

Upstream also documents `tools/audit_helper_sources.py` and matching-file reuse.
**Retained engineering ideas:** inspect the complete script and dependencies at
an immutable revision, then design a bounded secret-free source audit; reuse
only verified bytes bound to the exact request. Do not copy or execute that
script, switch the CI APK source, or substitute latest merely from README
claims. The existing Reddit page probe observes HTML only; an available link
does not prove the requested APK's identity or recovery.

## Remaining suggestions: retained, not silently enabled

These links came from the shared collection. Except for the pinned reviews
above, no current release, license, package, signer or device behavior was
verified in this packet. Descriptions below are candidate use cases, not
certified capabilities. Re-open a row only for a concrete need; installing the
whole collection adds configuration rather than removing it.

| Candidate | Possible use | Decision / next gate |
| --- | --- | --- |
| [Morphe Manager](https://github.com/MorpheApp/morphe-manager) | On-device manual patching | Separate workflow; not needed for finished APKs. Review separately before an import preset. |
| [Morphe Desktop](https://github.com/MorpheApp/morphe-desktop) | Manual desktop patching | Existing build tooling is a different contract; no desktop installation or ADB action here. |
| [Aurora Store](https://gitlab.com/AuroraOSS/AuroraStore/-/releases) | Stock-store access | Optional discovery only; do not redirect patched tracking to stock APKs. |
| [YTDLnis](https://github.com/deniscerri/ytdlnis) | Media-download companion | Optional candidate; verify release, permissions and user need before an import. No patched-app dependency. |
| [ML Manager](https://github.com/javiersantos/MLManager) | APK extraction | Maintenance concern reported in the thread; not independently established here. Compare maintained alternatives first. |
| [APK-Extractor](https://github.com/Domilopment/apk-extractor) | APK extraction | Review split handling and export scope; an APK export is not app-data or signing-key backup. |
| [Kanade](https://github.com/alexcmgit/kanade) | APK extraction / management | Same export and provenance review; not a replacement for repository recovery. |
| [F-Droid](https://gitlab.com/fdroid/fdroidclient/-/releases) and [Basic](https://f-droid.org/en/packages/org.fdroid.basic/) | Separate app catalog | Optional; preserve package/signing-channel distinctions. |
| [Aurora Droid](https://gitlab.com/AuroraOSS/auroradroid/-/releases) | Alternate catalog client | Discovery only; maintenance and source review pending. |
| [Droid-ify](https://github.com/Droid-ify/client) | Alternate catalog client | Discovery only; no duplicate update manager added by default. |
| [IzzyOnDroid client](https://gitlab.com/sunilpaulmathew/izzyondroid/-/releases) | Alternate catalog client | Discovery only; client/repository identity requires separate verification. |
| [Neo Store](https://github.com/NeoApplications/Neo-Store) | Alternate catalog client | Discovery only; no new import or store integration. |
| [Accrescent](https://github.com/accrescent/accrescent) | Separate app catalog | Optional discovery; not part of the build pipeline. |
| [Komi Store](https://github.com/komi-store/komi-store) | GitHub app discovery | Optional; Obtainium already handles the configured update path. No account integration added. |
| [Shizuku fork](https://github.com/thedjchi/Shizuku) | Privileged Android service | Advanced-only candidate, not a default. Separate device/privilege/rollback review. |
| [InstallerX-Revived](https://github.com/wxxsfxyzm/InstallerX-Revived) | Alternate installer | Not a default; no protection bypass or default-installer changes. |
| [Universal Installer](https://github.com/pass-with-high-score/universal-installer) | App inventory / management | Review any nonprivileged inventory mode separately; do not assume every feature needs Shizuku. No VirusTotal upload enabled. |
| [Canta](https://github.com/samolego/Canta) | Removing unwanted apps | Advanced-only; app/data removal needs exact targets and recovery review. |
| [Hail](https://github.com/aistra0528/Hail) | Freezing / suspending apps | Advanced-only; freezing a dependency can break service behavior. No blanket disable list. |
| [Shappky](https://github.com/YasserNull/shappky) | Background process management | Not a default; no automatic RAM-clearing policy or performance claim. |
| [NoMoreBackground](https://github.com/adil192/no_more_background) | Background-permission management | Advanced-only; preserve required companion background behavior. |
| [ShizuWall](https://github.com/AhmetCanArslan/ShizuWall) | Per-app network control | Advanced-only; permissions, persistence and rollback need their own review. |

Discovery references retained:
[Morphe website](https://morphe.software/),
[Morphe GitHub](https://github.com/MorpheApp),
[community patches](https://morphe-patches.software/),
[Awesome Morphe](https://awesome-morphe.vercel.app/),
[Awesome Shizuku](https://github.com/timschneeb/awesome-shizuku),
[Shizuku Apps Directory](https://rushiranpise.github.io/shizuku-modules/?sort=stars).
Being listed is not endorsement or individual patch approval.

## Scope and next work

This packet adds guidance, discovery links and a durable decision queue only.
No new app preset, APK download, installation, background service, source switch,
patch selection, account integration, upload, merge, build or cleanup is
authorized by this document. Those operations need their own reviewed scope.

The next companion implementation candidate is external PotHelper tracking
after the artifact/client gates above. Helper's exact-request source audit is a
separate candidate, not a fallback already wired into CI. Keep the existing
[open engineering work](review/OPEN-WORK.md), including full input fingerprints,
same-version delivery, exact Reddit input validation and separately approved
cleanup, visible rather than treating this guide as completion of those items.
