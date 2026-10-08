# Adding, changing or removing an app

Two steps for every change (packet W2, 8 Oct 2026).

1. **Actions → 5. Add target → Run workflow.** Pick the action, type the app id, fill the
   fields that action needs (table below), run it. It writes every file, runs the repo checks
   and opens a pull request. Its run summary says what changed, or why it refused.
2. **Merge that pull request** once **3. Validate** and **Onboarding review** are green.
   An enabled app builds in the next scheduled run, or now through **1. Manual Patch**
   (type the same id).

| Action | Fields | What it does |
| --- | --- | --- |
| add | id, package, label, provider (`OWNER/REPO`), patches, source, store_url, needs_microg | New app. With patch names it is enabled and builds exactly those; without them it stays disabled. |
| patch | id, patches | Add or drop patch names (rule below). |
| disable | id | Stop building. Files and published releases stay. |
| enable | id | Build again. Refused while the include list is empty. |
| remove | id | Delete the app from `src/targets.json`; its patch folders move to `src/patches/_attic`. Releases stay on GitHub. |

**Patch rule.** Names are separated by `;`. Most apps build an exact list: `Hide ads` adds it,
`-Hide ads` drops it. YouTube builds the provider's defaults minus an exclude list: `-Name`
excludes a default, `Name` turns it back on.

**Safety rules the tool applies.** A name matching `src/patches/BANNED` is always refused. A
name matching `src/patches/CONFIRM` is refused unless you tick **approve_confirm**; the record
then says `Owner approved: <name>`. Every change writes `docs/review/onboarding/<id>.md`, and
the agent review reads it on the pull request.

**needs_microg.** Tick it when the provider's patch list includes `GmsCore support` (Google
apps: YouTube, YouTube Music, Google Photos). The page then includes MicroG RE in Obtainium
imports and the release notes tell people to install it first.

**Where the original APK comes from.** `apkmirror-bundle` or `apkmirror-apk` with the
APKMirror uploads list URL, or `apkpure` with the APKPure download URL.

**If the pull request does not open.** GitHub may not let Actions open pull requests
(Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests").
The run summary then gives the compare link: one click opens it.

**Local, same tool:** `python3 src/etc/app.py add|patch|disable|enable|remove ...`, then
`python3 src/etc/app.py check`. `python3 src/etc/app.py list` prints every app id.

**What still needs a person.** A logo (`docs/assets/logos/<id>.png` plus a line in
`docs/review/ICON-PROVENANCE.md`); without one the card shows a letter tile. Phone testing.
