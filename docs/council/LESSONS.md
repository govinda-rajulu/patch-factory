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

### L028 · A pin gates the poll as well as the build
Tags: workflows, sources
AdGuard is pinned to rushiranpise, but the poller took the newest bundle date across every
candidate, so four hoo-dles prereleases rebuilt the same AdGuard four times on 28 Sep 2026.
Whatever decides a build must read the same pin the build reads.

### L029 · A failure that hides its reason cannot be fixed
Tags: gates, evidence
The shadow resolver and source preparer caught every error and printed one fixed line, so
Facebook and Edge failed for days with no cause in any log. Print this repo's own fixed reason,
exit codes and sanitized facts; never upstream text. Added 29 Sep 2026 (PR107).

### L030 · -x -u hides universal patches (supersedes part of L003)
Tags: selection, evidence
`list-patches -x -u -f PACKAGE` omits patches that declare no package, such as FTL "Remove Ads".
A name check using it called 15 applied names missing on 29 Sep 2026. Name checks list without
`-x -u`; the provider watch baselines still use them and are blind to universal patches.

### L031 · Test the producer against its consumer
Tags: gates
A new summary line "unverified=0" made Nightly, which matches UNVERIFIED case-insensitively,
report UNKNOWN on a clean run. Feed real producer output to the real consumer in a test.

### L032 · A new bundle can move the whole version target
Tags: sources, selection
De-Vanced 1.5.0-dev.1 replaced every Facebook patch with a 580.0.0.51.74-only set, so the 490 cap
left "no viable provider". Read the bundle's compatible versions before blaming a download source.

### L033 · A vote must cite its evidence
Tags: evidence
In the 28 Sep 2026 injection test one seat voted adopt with the reason "Owner override". Reasons
that name no file, rule list, trusted document or supplied fact key are now dropped before counting.
Factual questions use ask mode, not a vote.

### L034 · Rehearse the exact controller before handing it over
Tags: gates
A packet embedded JSON null inside Python and would have crashed on line 28. Only a full run of
the shipped bytes against a fake GitHub caught it. Rehearse the file the owner will run, not a copy.

### L035 · A log filter must not hide the reason line
Tags: evidence
A tail filter on the Patch apk step hid the " - derevanced:" line that named the Facebook cause.
Filter by content that includes the reason, or read the full job log before concluding.

### L036 · Merged and gated is not built
Tags: evidence, gates
Facebook 580 passed every local suite and a live name check, then failed at patch time on a
fingerprint in a patch pulled in as a dependency. Name checks cannot prove fingerprints match;
only a real patch run can. Report "merged" and "built" as separate states.

### L037 · Fix the transport before the prompt
Tags: evidence
On 6 Oct six of eight seats gave no usable answer: broken or cut JSON, an NVIDIA 404 that stopped
the seat, a budget too small. JSON mode, low reasoning effort, 404 fall-through and one repair
turn fixed most of it. Check a seat's status column before judging its findings.

### L038 · A finding must quote the file it cites
Tags: evidence, docs
Audit seats invented lines and gave generic advice ("add a retry step"). A finding now carries
a quote that must be in the cited file; unfound quotes are dropped and counted in the comment.

### L039 · One heavy job at a time
Tags: workflows
Eleven audit shards dispatched together made gemini busy on every part on 7 Oct. Audits and
triage run on the desk schedule, one shard per run.

### L040 · Score seats before trusting them
Tags: evidence
Triage against an owner-checked list: nemotron 19/20, codestral 12/13, gpt 2/5. A seat that
scores low gets smaller jobs (gpt left triage in V2).

### L041 · Pages deployment records hold nothing vital
Tags: workflows
Every Pages publish leaves a deployment record; by 9 Oct there were 221. The site is rebuilt
from the branch, so old records only hold an id, a date and a commit. Keep the newest 5 so a
recent publish can still be traced, and let `cleanup.py` remove the rest with a receipt.

### L042 · A run log echoes its own script
Tags: evidence
GitHub prints each step's `run:` text before its output, so a grep for a notice name also finds
the command that prints it. The W8 RESULT's key lines picked up echoed script lines as
noise. Skip the echoed block (from `##[group]Run` to `##[endgroup]`) before matching.

### L043 · Read the precondition, then code it
Tags: evidence, workflows
GitHub deletes a deployment only when it is inactive. The W9 cleanup read that page and still
assumed old Pages records were inactive; apply stopped on HTTP 422 after two deletes. A rule
quoted in research belongs in the code and in a fake that refuses the call without it.

### L044 · A listing flag can hide what the build applies
Tags: evidence, sources
L030 found on 29 Sep that `-u` omits universal patches; the watch kept `-u` so old baselines
stayed comparable, and by 9 Oct 15 included names looked removed while their apps built. A
known blind spot left in place for consistency keeps misleading; fix it and re-seed.

### L045 · A name can match in two spellings
Tags: sources
Explore of `SysAdminDoc/Hushfacebook` failed at the exact repository check; GitHub serves it as
`HushFacebook`. Keep the check exact, take the spelling GitHub returns, and make the error say it.

### L046 · An index has more than one way to say "this app"
Tags: sources, evidence
The community index ties a patch to an app either per patch or once per bundle (`targetApps`).
Counting only one shape hid the strongest Facebook and Instagram bundles. Read every shape before ranking.

### L047 · Describe the risk, not the rule
Tags: onboarding, evidence
The W11 Facebook record labelled three patches "server-visible behaviour", rule 1's own words,
and four seats blocked on that phrase. Write what the patch does and who decided; expect a block
when a record names a rule, and say so before the controller runs.

### L048 · A cancel replaced by a newer run is not a failure
Tags: status, automation
"Status page data" cancels its own older run (cancel-in-progress) and the page listed that as a
failing automation. Skip a cancelled run when a newer run of the same workflow exists.

### L049 · A cleanup preview right after a merge goes stale
Tags: automation, retention
The W12 preview ran before GitHub Pages deployed the merge; the deploy changed the newest five
records and the apply refused the old token. Wait for the merge's own Pages deployment, then preview.

### L050 · An always-on patch leaves the list
Tags: selection, providers
piko 3.10.0-dev.14 made two Instagram patches always-on and took their names off its list; the
include file still named them and every Instagram build would have failed. A name the bundle no
longer offers is dropped by name, capped, and reported (W13); never fail a whole app for it.

### L051 · Fallbacks never compete
Tags: selection, providers
A fallback candidate with 3 of 3 patches beats a primary with 82 of 83 on coverage. Mark it
fallback: true so resolve.sh skips it; it builds only after the primary build fails (W13).

