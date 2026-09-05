# patch-factory

Patches Android APKs in GitHub Actions and publishes signed, per-build releases.
Downloads: **https://govinda-rajulu.github.io/patch-factory/**

Target devices: arm64-v8a, Android 10 (SDK 29) and newer. One arm64 build
installs on every device we care about, so there is one APK per app, not one
per phone.

## Build

    gh workflow run "1. Manual Patch" -f target=youtube

A weekly cron polls targets flagged `"poll": true` and rebuilds only when a
provider ships a newer bundle. See RECOVERY.md.

Targets live in `src/targets.json`. Run this to see what is enabled:

    jq -r '.[] | [.id, (.enabled|tostring), (.source // "apkmirror")] | @tsv' src/targets.json

## Release tags and filenames

Tags are `PREFIX-vAPPVERSION-bYYYYMMDD` and assets are
`APKNAME-vAPPVERSION-arm64-v8a.apk`. Every build gets a new tag instead of
replacing the asset on an existing one, because replacing an asset in place
moves neither the tag nor `published_at`, so anything tracking releases by tag
never sees a patch-only rebuild.

Costs of that choice, and the Obtainium settings that follow from it, are in
RECOVERY.md. Read them before relying on it.

## How a build works

`src/build/build.sh TARGET` does all of it:

1. reads the target from `src/targets.json`, refuses if `enabled` is false
2. downloads morphe-desktop, then `resolve.sh` elects the winning provider
   and settles the app version
3. renames the winner's bundle `09-NAME.mpp`, then fetches every
   `extra_bundles` entry as `01-NAME.mpp`, `02-...` via `fetch_bundle.sh`,
   and asserts the expected bundle count
4. keeps the lowest-numbered bundle in the cwd for `split_arch`'s glob and
   passes the rest as explicit `-p` flags, because `patch` is not variadic
5. `selections.sh` builds the patch selection flags, grouped per bundle
6. downloads the APK from the store named by `source`: `apkmirror` (default,
   needs a hand-found `list_url`) or `apkpure` (needs only the package name)
7. verifies the download: size floor, real zip, has an `AndroidManifest.xml`,
   and the package name matches what the target asked for
8. `check_sdk.sh` against `min_sdk_ceiling` (report-only)
9. `split_arch`, then asserts the applied patch count equals the include list
   when `exclusive` is on, and refuses to release if it does not
10. writes `.version`, `.tagprefix`, `.tagsuffix`, `.patchver`, `.provider`
11. renames the APK to carry the app version, and fails loudly if none exists

`morphe.sh` wraps `build.sh youtube` and ignores any argument you give it.

## Patch selection binds to the preceding -p

This is the single fact most likely to cost you a bad build. In
morphe-desktop, `-e` and `-d` are scoped to the bundle named by the nearest
preceding `-p`, not to the whole command. So a multi-bundle target needs a
`patch_dir` **per bundle**, including on each `extra_bundles` entry.
`selections.sh` emits the flags in that order; do not hand-build them.

With `"exclusive": true` the include list is the whole spec: anything not
listed is disabled, and the build refuses to release unless the applied count
matches. Without it, provider defaults still apply and the include list only
supplements them.

Providers differ on defaults. Some ship every patch `default: true`, others
`default: false`, so an empty include list on the second kind produces a
signed APK with zero patches applied that looks like a success. That is what
`exclusive` plus the count gate exists to prevent.

## Adding a target

1. add an entry to `src/targets.json` with a `tag_prefix`, and set
   `"enabled": false` until it has a real patch list
2. create `src/patches/DIR/{include,exclude}-patches` for every candidate,
   and for any `extra_bundles` entry that needs its own selection
3. create `src/options/NAME.json` containing a **JSON array**, `[]` if empty
4. add the app to `src/build/helper/apps.json`: an `apkmirror.list_url`, or an
   `apkpure.download_url` of the form
   `https://apkpure.com/x/PACKAGE/download`
5. add the id to the dropdown in `.github/workflows/manual-patch.yml`,
   or `workflow run` will be rejected with HTTP 422
6. push, wait for **3. Validate** to go green, then dispatch

Workflow **5. Add target** does steps 1 to 5 for you and lands the target
disabled on purpose. Workflow **4. Explore patches** lists a provider's patch
names and defaults as a GitHub issue, which is how you pick the include list
without a terminal.

**`tag_prefix` must never contain a provider name.** Obtainium matches on the
tag; a provider change would silently orphan the app. `youtube-morphe` is a
grandfathered exception.

## Sources, and when a version pin fails

`source` picks the store. APKPure resolves by package name alone, so
`apkpure.com/x/PACKAGE` works with no per-app lookup. APKMirror needs a
category slug found by hand.

A store may not carry the exact version a provider targets. That is the most
common single-app failure, and the symptom is `Could not find download link`.
Setting `"any_version": true` on a target takes the store's newest build
instead of the pinned one. The applied-count gate still guards the result, so
a version too new for the patches fails loudly rather than shipping.

## Multi-provider targets

A target may load bundles from several patch repos at once, on github or
gitlab. One candidate wins and decides the app version; anything in
`extra_bundles` is loaded alongside it. Bundle filenames set load order, and
on a name collision the bundle loaded **first** wins silently, so the numbered
prefixes are the knob.

`truecaller-combo` is the reference example: bufferk (github) as winner with
its own patch dir, paresh (gitlab) as an extra with its own patch dir, 17
patches loaded and 11 applied.

A gitlab source needs `project_id`, because its release assets live at opaque
upload URLs that must be read from the API.

See [RECOVERY.md](RECOVERY.md) for the signing key, the install ladder, the
cancel window, and everything that has burned us.

<!-- state-5sep2026 -->
## State, 5 September 2026

- **16 targets, 14 opted in to the weekly build.** Disabled: sonyliv.
- The weekly run (`2. Check new patch`) polls **every** target with `poll: true` and builds
  the ones whose provider shipped something newer. A `plan` job emits the matrix from
  `src/targets.json`, so adding a target to the weekly build is one field, not a workflow edit.
  Before this it was a hardcoded list of three.
- Every candidate and extra bundle is on `channel: prerelease`, deliberately: providers ship
  dev builds constantly and the newest release wins whether or not it is marked stable.
- Include lists are reconciled against what each provider currently offers. When a build says
  `applied N but include list says M`, a provider renamed or dropped a patch: run
  `list-patches` for that bundle and compare, do not weaken the gate.
- `src/etc/bancheck.sh` runs in `3. Validate` and blocks any banned patch reaching an include
  list. `BANNED` and `CONFIRM` hold **lowercase substrings**, not exact patch names.
- Build failures open one issue **per target** with the failing job, step and error lines in the
  body. Older issues titled per workflow accumulated unrelated targets for weeks.
- `gh run rerun` replays a run at its **original commit**, so it never tests a new fix.
  Dispatch `manual-patch.yml -f target=<id>` instead.
