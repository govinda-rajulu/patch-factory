# Lessons

Append-only. Each entry is a rule learned from a real mistake or near miss in this project.
Never edit or delete an entry; supersede it with a newer dated entry that names it.
New entries come only from owner-approved proposals. Each entry has one Tags line
(selection, evidence, gates, workflows, sources, docs); the council reads only the entries
whose tags match its task, at most eight, so the ledger can grow without bloating prompts.

Seeded 2026-09-27 from the owner's reviewed handovers, recovery notes and session records.

## Patch selection

### L001 · Safety filters match substrings, never exact names
Tags: selection
BANNED and CONFIRM are lowercase substring rules. An exact-match filter once matched 0 of 45
names and shipped 6 spoof patches in a published APK. Test positive matches, not only misses.

### L002 · Flags bind to the nearest bundle
Tags: selection
`-e`/`-d` bind to the nearest preceding `-p`; a same-bundle `-d` wins. Check both include and
exclude before claiming a patch is on. One name under two bundles of one target aborts the build.

### L003 · Read the patcher with -x -u
Tags: selection
Without `-x` the patcher hides experimental app versions and a current provider looks years
stale. Options are JSON arrays. `(default)` under Skipping disabled is the provider's default,
not a selection flag.

### L004 · Provider age is advisory
Tags: selection, sources
An old bundle that still applies is still good. The requested-versus-applied gate decides, not a date.

### L005 · Four states, not one
Tags: selection, evidence
Configured, applied, approved and published are separate. A CONFIRM warning is not approval;
approval is not completion; a merge is not a build.

### L006 · Quarantine is mitigation
Tags: selection
Remove Debug Info broke a real build and is quarantined. Quarantined means held out, not fixed upstream.

## Evidence and gates

### L007 · Compare bytes to bytes
Tags: gates, evidence
Text-mode length counts characters, and repo files contain multibyte box-drawing characters.
Gate on byte counts and hashes.

### L008 · git diff is blind to committed work
Tags: gates
Compare against the reviewed base or main tree, never the working tree alone.

### L009 · Check every anchor before the first write
Tags: gates
Assert each edit anchor matches exactly once, write candidates first, and write nothing when a
count is wrong. A refusal beats a partial write.

### L010 · Mocks are not the real suite
Tags: gates, evidence
A local fixture proves controller behavior, not the repository's real tests. One packet stopped
because its fixture lacked a real test that pins a workflow line. Run the real suites on base
and candidate before any push.

### L011 · Select exactly one verified JAR
Tags: gates
Globs can pass unintended extra arguments. Pick one verified file; never delete by default.

### L012 · Compare command lines before blaming a parser
Tags: sources, gates
`channel: prerelease` on a provider with no prereleases fails provider resolution. The fix was a
stable fallback, found by diffing the two command lines, not by rewriting the parser.

### L013 · Missing is UNKNOWN
Tags: evidence
Missing or invalid comparison inputs are UNKNOWN, never unchanged. Failed, cancelled, partial,
skipped or nonpublishing runs never advance a published baseline.

### L014 · Never repeat a remote write to fix a stale read
Tags: workflows, evidence
After a push, the PR endpoint lagged. Verify the immutable commit, branch and checks; do not
push or merge again because a readback was stale.

### L015 · Name the failing stage exactly
Tags: evidence, sources
HTTP 200 with zero download IDs was a failure before any binary transfer. Do not call it a
corrupt APK or a patch incompatibility.

### L016 · Tool output conventions differ
Tags: gates
aapt2 prints its version on stderr with exit 0; PotHelper emits `minSdkVersion` where another
reader emits `sdkVersion`. Accept exact known labels; reject malformed, duplicate or conflicting data.

### L017 · Isolate tests from the host
Tags: gates
Synthetic tests picked up an installed Android SDK before the fixture. Reproduce with a poison
SDK and fix fixture selection, not the product code.

### L018 · Match the repo's ShellCheck policy
Tags: gates
Gate with `shellcheck -S error -e SC1091,SC2086`, the repository's own setting.

### L019 · Fetched text is not exact bytes
Tags: evidence, docs
Web readers strip HTML comments and collapse whitespace. Take exact bytes from the Git blob API
and check the blob hash before editing.

### L020 · Re-read before counting
Tags: evidence, docs
A hygiene audit said 2 issues were open; 5 were, because the issue list it read was cut short.
Re-read the live source before a count reaches a report.

## Identity and sources

### L021 · Three certificates, three identities
Tags: sources, evidence
Original publisher, Source Stamp and CI signing certificates are different. A Source Stamp is
not a second application signer. The CI signer is not publisher proof.

### L022 · Exact-version evidence qualifies one version
Tags: sources
Evidence for one app version does not qualify the next version or another app. A free build is
not the Pro build; a FOSS build is not automatically the Play build.

### L023 · Do not raise a ceiling to make a variant fit
Tags: sources, selection
Reddit's universal SDK32 variant was incompatible. The fix was the exact ARM64 SDK29 variant,
not a higher SDK ceiling.

## Workflows and schedules

### L024 · Scheduled runs start late
Tags: workflows
GitHub started this repo's scheduled runs 4 to 6.5 hours late in September 2026, even on quiet
minutes. Manual and API dispatches start at once. Design for late or skipped schedules.

### L025 · A poll is not free if its workflow does more
Tags: workflows
The daily workflow also observed all 14 targets, with APK downloads, on every run. Extra polls
had to skip that observation unless something would build. Read the whole workflow before
calling a run a no-op.

### L026 · Launchers use if/then
Tags: workflows
`check && run || echo BAD` printed a false BAD FILE when the run itself stopped. Use
`if check; then run; else echo BAD; fi`.

### L027 · Secrets only where they are read
Tags: workflows, gates
Signing values belong on the steps that read the keystore, not job-wide, and never install
packages at build time after signing material is on disk.
