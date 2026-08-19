# patch-factory - recovery

Patches Android APKs in GitHub Actions, publishes signed releases, consumed by
Obtainium. Target device: Micromax IN Note 1, Android 10 (SDK 29), arm64-v8a,
not rooted, MicroG RE installed alongside real Play Services.

## Signing key - READ FIRST
- Alias: `factory`. Same key forever. Signer sha256 starts `08480f6649a2`.
- Losing it means uninstall and clean reinstall of every app, permanently.
  On Truecaller that also costs a phone verification, and the app allows only
  3-4 per 24 hours.
- The key file is NOT in this repo and must never be. `.gitignore` blocks `*.keystore`.
- Offline copies:
  - Emailed to self as an attachment. Search the mail account for `family.keystore`.
    VERIFIED 16 Aug 2026: the attachment is the real .keystore file, and a
    second file alongside it holds the password, the alias and the cert validity.
  - **GitHub secrets are NOT a backup.** `KEYSTORE_B64`, `KEYSTORE_PASS` and
    `KEYSTORE_ALIAS` are write-only: they can be overwritten, never read back.
  - ONE copy today, so one deleted mail thread loses every app permanently.
    A second offline copy (USB or encrypted folder) is still owed.
- The keystore PASSWORD may exist only inside the `KEYSTORE_PASS` secret, which
  cannot be read back. Without it the key file is useless. Write it down wherever
  the key file lives. Alias is `factory`.
- Secrets used by CI: `KEYSTORE_B64`, `KEYSTORE_PASS`, `KEYSTORE_ALIAS`.
- Installing and updating: see the Installing a build section below.

## Installing a build

Same package plus same signing key means Android accepts a patched APK as a
normal update: app data, logins and sessions survive. That is the default path
and it costs nothing.

**Update in place first, every time.** Do not uninstall as a reflex.

If the installer refuses (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`, or a generic
"App not installed"), work down this ladder and stop at the first one that works:

1. Confirm the APK is the arch you expect (`*-arm64-v8a.apk`) and finished
   downloading. A truncated file fails with the same useless message.
2. Confirm the new version is not LOWER than what is installed. Android refuses
   downgrades even with a matching key. Check Settings > Apps > the app > version.
3. If Play Protect blocks it, turn Play Protect scanning off for the install and
   back on after.
4. Only now consider uninstalling, and read the app-specific rules below first.

`INSTALL_FAILED_UPDATE_INCOMPATIBLE` with the right arch and a higher version
means the SIGNATURE differs. That is either a build signed with a different key
or an app installed from a different source (Play Store copy vs patched copy).
Uninstalling is then genuinely required, and the app-specific cost applies.

### Truecaller: the verification budget

Truecaller allows roughly **3-4 phone verifications per 24 hours**, then a
cooldown you cannot shorten. Uninstalling clears the session, so the next
install needs one.

- **Budget it: one verification per day, deliberately.** Never uninstall twice
  in one session while trying variations of a build.
- Before uninstalling, be sure the replacement APK is already on the device and
  verified (correct size, arch, and version). Uninstalling first and discovering
  the download failed is how a whole day gets burned.
- If a patched Truecaller build turns out bad, the revert is
  `truecaller-arm64-v8a.apk` from the `truecaller-v26.10.6` release, installed
  OVER the top. Same key, so no verification needed. Keep that release alive.
- `GMS sign-in bypass` (paresh) forces SMS OTP instead of the GMS retriever,
  which is what makes sign-in possible at all on a re-signed APK. Without it a
  fresh sign-in can fail outright and still consume an attempt.
- Two patched Truecaller builds cannot coexist: same package, so one replaces
  the other. A/B testing therefore costs verifications, which is exactly why
  `truecaller-combo` loads both providers in a single APK instead.

### Photos, YouTube, and anything else

No verification cost, so uninstalling is merely inconvenient.

- **Photos:** signed in through MicroG. Uninstalling loses that account link and
  it must be set up again, but nothing rate-limits you. A DIFFERENT patch set on
  the same package IS a real reason to uninstall first: Android rejects it as an
  update when the signature or manifest conflicts.
- **YouTube:** no login required for the patched build to work. Uninstall freely.
  Play Store will keep offering an uninstallable update forever; ignore it.
- Any app patched with a CHANGED package name is a separate app. Installing it
  does not touch the original, and Obtainium tracks them separately.

## Build it

    gh workflow run "1. Manual Patch" -f target=youtube
    # targets: youtube | photos | truecaller | truecaller-combo   (adguard disabled)

Two to three minutes per target.

Weekly cron (Fri 12:30 UTC) polls only targets with `"poll": true` in
targets.json, one matrix leg each, via `src/etc/poll.sh`. It compares the
newest bundle date across ALL of a target's candidates AND extra_bundles
against my newest release for that tag_prefix, and builds only if a source is
newer. An unreadable provider date or a missing prior release means it refuses
to build rather than guessing, because "empty lookup" used to mean "rebuild"
and that quietly rebuilt every week forever after an asset rename.

Polled today: youtube, photos. `truecaller` stays manual on purpose (frozen
revert path) and `truecaller-combo` joins once its device test is settled: a
cron rebuild replaces the asset under you mid-test.

`build.sh` prints `[+] release tag: PREFIX-vVERSION` BEFORE the release step
runs. That line is the cancel window: if it is wrong, `gh run cancel ` now.
Prune keeps only the two newest releases per prefix and deletes their tags, so a
wrong prefix on a completed run is unrecoverable.

## Layout
- `src/targets.json` - source of truth. Per target: candidates, `extra_bundles`,
  `tag_prefix`, `min_sdk_ceiling`, `enabled`.
- `src/build/build.sh` - the build, generic over target id.
- `src/build/fetch_bundle.sh` - fetches exactly one .mpp from a github or gitlab
  release. `fetch_bundle.sh HOST IDENT CHANNEL OUT`, prints PUB= TAG= SIZE=.
- `src/build/resolve.sh` - elects a provider, prints WINNER / VERSION / PATCHES / MPP.
- `src/build/morphe.sh` - wrapper for `build.sh youtube`. IGNORES any argument
  you pass it. Do not use it for other targets.
- `src/build/check_sdk.sh` - minSdk gate, four readers, report-only.
- `src/build/utils.sh` - upstream engine. `split_arch` at ~line 830. Do not edit.
- `src/patches/DIR/{include,exclude}-patches` - one exact patch name per line.
- `src/options/NAME.json` - **must be a JSON array**, not an object.
- `docs/` - the GitHub Pages download site. Nothing else goes in here.
- `reference/` - notes, patch dumps, FAQ.

## Multi-provider targets

A target elects ONE winner via `resolve.sh` (which decides the app version and
which patch_dir and options file to use), and may list `extra_bundles` that are
fetched afterwards and loaded alongside. `truecaller-combo` is the working
example: winner bufferk on github, extra paresh on gitlab, 17 patches loaded,
11 applied, 6 bufferk duplicates disabled by name in exclude-patches.

- **A gitlab candidate or extra needs `project_id`.** Release assets there live
  at opaque `/-/project//uploads//` URLs that cannot be constructed;
  they must come from the API every run.
- **`exclude-patches` matches by name across every loaded bundle.** That is what
  makes dedupe work. Confirm no patch name exists in both bundles first, or an
  exclude will silently take out the one you wanted to keep.
- **Bundle filenames set load order.** When two bundles ship a class with the
  same name the first loaded wins, so build.sh renames them `01-` (primary) and
  `09-` (winner), rather than trusting version digits to sort as intended.
- **`patch` takes ONE `-p` per bundle.** Its `-p=` is not variadic,
  unlike `--patches=...` on `list-patches` and `list-versions`.
  `-p *.mpp` silently consumes the second bundle as the `` argument and the
  real APK becomes an unmatched argument. Also: `--patches` has no short form on
  the list subcommands, where `-p` means `--with-packages`.
- Provider defaults differ per repo. Always confirm `Applying N patches` and the
  `Applied:` lines. `Skipping disabled: X` lines are expected and should number
  exactly as many as your exclude list.

## Never exclude
GmsCore support (MicroG breaks), Spoof video streams (playback breaks).
The re-signing trio (`Provide Original app certificate` and its two dependents)
cannot work in CI: it reads the cert from an installed app, and a runner has no
device.

## Hard-won lessons
- Never let an AI write repo files via the GitHub Contents API. It silently ate
  every backslash escape in utils.sh: right byte count, broken file.
- **Never run `cd $(git rev-parse --show-toplevel)` from outside the repo.** The
  subshell fails, `cd` gets an empty argument and puts you in `$HOME`, and
  everything after it runs in the wrong place. Use the absolute path.
- **`gh run watch` prints step status only, never log lines.** To see the cancel
  window either open the run in a browser or pull `gh run view  --log` after.
- **Never read `databaseId` right after a dispatch** without checking it changed;
  a rejected dispatch leaves you watching an older run that already succeeded.
- Never paste base64 through a phone clipboard. Pipe it: `gh secret set NAME < file`
- EOFException on the keystore means the secret is truncated, not a wrong password.
- After any file write, read it back and check byte size.
- **An options file of `{}` fails the whole patch step.** `[]` is the correct
  empty value. CI guards this.
- **`tag_prefix` must not contain the provider name.** A provider change would
  break Obtainium matching, and prune deletes by prefix. `youtube-morphe` is
  grandfathered; `tc-combo` names a patch-set experiment, not a provider.
- check_sdk exiting 0 used to mean "could not read", identical to a pass.
  Silence is not success. It now says UNVERIFIED out loud.
- A green run does not mean an artifact exists. Check the release, not the tick.

## Known gap
`resolve.sh` and `dl_gh` both take the newest release on the prerelease channel
and agree in practice. Only the unused MPP cache fallback path can serve a stale
bundle, and `fetch_bundle.sh` clears its target directory before writing.

## Ageing out
`max_patch_age_days` is 60. bufferk's bundle is dated 18 Jul 2026 and is the
candidate for BOTH `truecaller` and `truecaller-combo`, so around 17 Sep 2026
both will fail with "no viable provider" even though the patches still work.
Fix then by raising the gate for that target or swapping the winner.
`extra_bundles` are deliberately NOT age-checked.

## On-device
MicroG RE installed and signed in BEFORE the patched YouTube, battery
Unrestricted. Play Store shows an uninstallable YouTube update forever; ignore it.
Photos keeps the default package with the label overridden, because changing a
package makes it a new app and Obtainium loses it.

## Release tags are unique per build

Tags are `PREFIX-vAPPVERSION-bYYYYMMDD`. Every build makes a new tag instead of
replacing the asset on an existing one.

Why: replacing an asset in place moves neither the tag nor `published_at`, only
the asset's `updated_at`. Anything that tracks releases by tag, Obtainium
included, therefore never sees a patch-only rebuild. See
FiorenMas/Revanced-And-Revanced-Extended-Non-Root issue 36, closed not planned.

A build date rather than the patch bundle version, because a target can load
several bundles (see truecaller-combo) and a tag keyed on one of them would not
change when the other moves. The bundle version is in the release body.

Costs, know them before you rely on this:

- Prune keeps the two newest releases per prefix and deletes their tags. More
  tags means older ones disappear sooner. Rollback by tag is impossible by
  design; keep a frozen target instead (truecaller is ours, poll false).
- Two builds of the same target on the same day share a tag and replace in
  place, which is the old behaviour and is fine.
- Obtainium: one version regex now works for every app, `[\d.]+-b\d+`.
  Tag filters are still mandatory, one per app.
