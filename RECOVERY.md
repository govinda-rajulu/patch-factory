# Recovery and operations

This is operating guidance, not permission to dispatch, publish, delete, restore
secrets or install anything. Verify the current repository state and approve the
specific action first. Historical incident notes are not executable recovery
instructions.

## Preserve recovery before changing distribution

Keep independent, access-controlled copies of the repository and required
release assets. A Git clone or bundle does **not** include release APKs, Actions
artifacts, repository settings or secrets. A knowledge export is not a repository
or signing-key backup. Keep old copies until the new copy has been restored and
checked in an isolated location.

Record the exact refs, release/tag/asset IDs, sizes and hashes in a manifest.
Verify downloaded bytes, not filenames. Check storage capacity before copying
large APK collections. Do not place signing material, private environment data,
chat exports or personal backup locations in public repository files.

The frozen `truecaller-v26.10.6` release and `src/patches/_attic/` are retained.
A frozen APK is a historical recovery option, not proof that Android will accept
a downgrade or preserve sessions. No backup location or restore success is
asserted by this document.

## Signing recovery

GitHub Actions uses `KEYSTORE_B64`, `KEYSTORE_PASS` and `KEYSTORE_ALIAS`.
GitHub secrets are not a retrievable backup. Keep the original keystore and the
information needed to unlock it in independently recoverable private storage;
do not paste keys, passwords or base64 material into issues, chat or public logs.

The configured CI certificate SHA-256 is
`08480f6649a2be33ff3cccacce07454761d5fb9abe65f1e2caeeb782e382d050`.
This identifies the expected CI signer, not an original publisher or the signer
of an app already installed on a phone.

A restore drill is separate work: in a trusted isolated environment, recover
the saved material, open the keystore successfully and compare its certificate
fingerprint without replacing production secrets. Record only non-secret
evidence. A minimum file size, successful base64 decode, or green workflow does
not prove that a restored key/password/alias is correct.

Do not rotate the key to fix a build failure. If signing continuity cannot be
established, stop before publication or installation and preserve existing
working artifacts. Lost signing access does not justify automatic uninstall.

## Installation and rollback

Check package, versionName/versionCode, Android API requirement, native
architecture, file size, SHA-256 and signer compatibility. Prefer an in-place
update when Android permits it. Matching package and certificate are necessary
in common update paths, but not a guarantee of installability or data retention.

If Android refuses an update, capture the actual installer error and compare
the artifact and installed identity before trying another file. Do not clear
data, uninstall, disable Play Protect, or bypass signature checks as routine
troubleshooting. Downgrade restrictions, split packages, storage and OS
requirements can matter independently of the signing key.

Authentication/session recovery and data export are app-specific. No fixed
Truecaller verification quota or promise of cost-free reinstall is made here.
MicroG is optional upstream software with its own variant, signer and data
considerations. Phone validation and signing-restore validation remain separate
from repository CI and publication.

## A controlled fresh-release campaign

1. Confirm the reviewed main commit, exact CI result and target list. Finish
   source/selection decisions first. Do not quietly omit blocked targets or
   override a pin to make the run green.
2. Inventory active runs and existing releases. Do not duplicate a running
   target. Preserve rollback assets and obtain a restorable copy before cleanup.
3. Dispatch the approved workflow once with explicit targets and publication
   intent. Manual and Batch default to publishing; `publish=false` is still a
   real signed build, not a harmless read.
4. Bind the new run to workflow, commit, inputs and attempt. A failed dispatch
   must not lead to watching an older run. An uncertain acknowledgement is a
   stop-and-inspect condition, not an automatic second dispatch.
5. Inspect every target job, including source download under `Patch apk`,
   finished identity, release handoff and publication. Batch does not fail-fast:
   a failed target does not erase successful publications.
6. Verify new release/tag/source identity and APK bytes against recorded hashes
   and reports. Retain logs/reports needed for diagnosis. Qualification requires
   the whole source run to succeed under the current policy.
7. Only then prepare a fresh exact cleanup preview, with release/asset totals,
   protected records and backup references. Obtain explicit deletion approval.
   A failed replacement keeps its previous working release.

Do not rerun an old workflow to test a new fix: reruns keep the original commit.
Do not rebuild successful targets merely because a sibling failed. Existing
daily schedules can run independently; approval for a manual campaign neither
disables them nor authorizes changing their schedule.

## Cleanup boundaries

`src/etc/release_retention.py` makes a read-only, fingerprinted inventory preview.
It has no apply mode. It keeps the newest two dated releases per configured
prefix and protects frozen/manual/unknown/draft/prerelease/ambiguous entries.
Known evidence JSON assets can be recognized as part of a release's metadata
shape, but the planner does not fetch or validate their contents.

The preview fingerprint binds the observed release records and asset metadata,
not APK byte backups, future GitHub state or independent provenance. Re-read
the inventory before any write. A changed fingerprint or uncertain identity
requires another review.

Release deletion removes its downloadable assets; tag deletion is a separate
operation. Actions run/artifact deletion can remove diagnosis and qualification
evidence. Branches, local folders and the attic are different scopes again.
Never interpret "clean releases" as permission to delete all of these.

## Known gaps and entrypoints

Use [OPEN-WORK](docs/review/OPEN-WORK.md) for dated blockers and remaining work,
[README](README.md) for generated target inventory, and the
[visitor guide](docs/guide.md) for download/import behavior.
Same-version Obtainium delivery, full semantic fingerprints, independent
provenance and phone/recovery drills are not solved by a fresh release campaign.
