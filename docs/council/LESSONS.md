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

### L052 · A wrapper changes the signals
Tags: build, ci
W13's first Instagram smoke failed both attempts at "zip has no AndroidManifest.xml" on a good
133 MB APK. An Actions step runs with SIGPIPE ignored; Python's subprocess resets it, so
`unzip -l | grep -q` under pipefail died with 141 once grep stopped reading. Keep the step's
signals (`restore_signals=False`) and name the zip entry instead of piping into `grep -q`.

### L053 · Predict only what the tool enforces
Tags: selection, ci
W13 dropped 4 working brosssh Instagram patches (Hide ads among them) because the bundle lists
Instagram 439 only; the patcher runs with --force and W12 had applied them on 447. The smoke
gate also wanted a COVERAGE line an any-version provider never prints. A pre-check must be no
stricter than the step it predicts; read a success run's log before writing the gate.

### L054 · A store row can be wider than the filter
Tags: build, stores
Reddit 2026.41.0 came as one APKMirror row, "universal 120-640dpi", and APKPure had no link yet;
the arm64 filter found nothing and the build died with no fallback. A universal row serves an
arm64 target, and a version no store serves steps down like an SDK miss (W14).

### L055 · Data is not a message
Tags: watch, ci
Nightly watch went UNKNOWN because its "incomplete reader" regex matched the patch name
"Unlimited track skipping". A detector reads only the lines its producer writes as messages;
names and other data are excluded first (W14).

### L056 · A plan in a review doc is not work
Tags: docs, review
CLUTTER-2026-10-07 named every repeated notice and a home for each; nothing was done for four
days and the owner had to ask again. A review's proposals become OPEN-WORK items with a packet,
or are declined in writing, on the day the review lands (W14).

### L057 · A hand list must match the workflows
Tags: workflows, watch
Three scheduled workflows never opened a failure issue and one had no purpose line, because
notify-failure, status.yml and status.py PURPOSE are hand lists. tests/automation_contracts.py
compares each list with .github/workflows (W14).

### L058 · A title is not an identity
Tags: workflows, notify
notify-failure compared run.name with the workflow name, but run.name is the run-name
("Batch Patch: youtube"), so real failures were refused as out of scope from W13 on. Scope is the
workflow path plus the workflow record (getWorkflow: id, path, name); branch runs are skipped (W15).

### L059 · A fallback must not publish below the primary
Tags: build, release
De-Vanced Facebook 580 (3 patches) published four times, 11 to 16 Oct, over Hushfacebook 582
(82 patches): nothing compared versions before publishing. release_contract.py refuses any app
version below the newest published one; a fallback is never published without the inventory (W15).

### L060 · A dpi string is not a variant
Tags: build, store
Facebook 583 asked APKMirror for arm64 480-640dpi and got build 475614280 (480dpi), not the
pinned 475614366. The identity gate refused it; the downloader now picks the row that carries the
pinned version code (W15).

### L061 · Never suppress a signal; "impossible" is not a finding
Tags: review, workflows, agents
Owner rule, 17 Oct 2026. A Dependabot pull request, failing run, warning, issue or agent finding is
applied, fixed, or kept open with a written reason; never ignored or closed to make a page green
(#185 failed for six days because one test hardcoded a sha). An agent that cannot find a fix says
what it tried and keeps the item open; the fix can be one character (W15).

### L062 · A fake must copy the real tool's refusals
Tags: gates, evidence
The W15b log script passed its rehearsal and read 0 of 13 logs on the owner's box: real gh refuses
job logs that hold terminal escape codes unless told to pass them, and the fake gh never refused.
A rehearsal fake copies the real tool's refusals; a control run of the old script against the
corrected fake must reproduce the owner's failure before the fix counts (W15b, wrong call 31).

### L063 · An evidence step names its reason
Tags: evidence, workflows
Four silent steps hid four different causes behind generic lines: the publication receipt (19 Oct
Facebook: merged APK past the 256 MiB bound; 11 Oct LinkedIn: plan version differs from the
stepped-down build), the APKMirror transfer (wget -q), the APKMirror merge (exit not checked) and
the shadow receipt reason. A step that may fail prints its own reason text; foreign text never (W15b).

### L064 · Measure a rule on real data before it ships
Tags: selection, gates
The first auto-adopt rule passed its unit tests and would have adopted 100 of 129 older names,
including four names two bundles of one app both offer (a build abort, AGENTS rule 4) and
always-on hides like "Hide all stories". Running it over the committed baselines and index
descriptions found both; a rule is run on the real inventory, and its counts read, before it ships (W15b).

### L065 · Local gates run with the environment Actions sets
Tags: tests, gates
The adopt test expected the branch adopt/<date>-local; Actions sets GITHUB_RUN_ID, so 3. Validate went red
on the W15b pull request while the local suite passed. Tests pin what they read from the environment, and
suite.sh exports the Actions variables so the local gate sees what the runner sees (W15b, 20 Oct).

### L066 · A fail-closed rule is checked on every path that feeds it
Tags: gates, signing
W15b made an unreadable pinned certificate stop the build. The prepared-source path only carries the merged
APK, whose bytes no longer match the original signature, so 2. Check new patch went red on Facebook. Before
a rule turns strict, list every caller and the input each one really has (W15c, 21 Oct).

### L067 · A bot step that can be refused keeps no daily side effect
Tags: automation
The adopt step pushed a branch, then GitHub refused the pull request; the next day it would push another.
A side effect waiting on a refusal is found again and reused, never repeated (W15c, 21 Oct).

### L068 · An agent's "missing" is checked against the file before it is planned
Tags: agents, review
The history agent listed "watch.yml has no job timeout"; it has had one since W2. Two more of its
eight "dropped" items were by design. Every claim names a file; read that file before a packet or
the owner hears it (W15d, 21 Oct).

### L069 · An unquoted ' #' in YAML is a comment, and bot-started runs wake nothing
Tags: workflows, automation
`run-name: Onboarding review #${{ inputs.pr }}` named every run "Onboarding review": YAML read the
rest as a comment, so 11. Rule merge never found the review of #207. Quote any value holding `#`
(tests/yaml_comment_contracts.py). Runs the workflow token starts fire no workflow_run either; a
waiter needs a schedule, its own patience or an explicit dispatch (W15e, 22 Oct).

### L070 · Pull request checks on a bot pull request wait for approval; never gate on them
Tags: workflows, automation
Validate, Council and Onboarding review on adopt PR #207 sat "Action required". Rule merge reads
the dispatched runs and the bot's own comments instead. A gate that needs a human click is not
automation (W15e, 22 Oct).

### L071 · A controller tolerates bot drift on main, never human drift
Tags: automation, review
Bot commits (Selection, Community, Provider watch) land on main every few hours, so a controller
that stops on any move sent the owner back for a new bundle (e46ff50e, 21 Oct). Since W15e the
clone proves each commit after the base is a plain bot commit touching no packet file, and the
merge must equal the packet tree plus those files; any other move still stops (W15e, 22 Oct).

### L072 · A Rule merge is bot drift too; every main gate shares one drift rule
Tags: automation, review
Rule merge merged #207 at 06:00Z, four minutes after W15e merged, and T1 stopped with MAIN_MOVED:
its bot check wanted the bot as committer, but GitHub (web-flow) commits the merges it makes. The
controller check written that morning (L071) had the same gap. Both now accept a two-parent
merge authored by the bot and committed by GitHub; an owner merge still stops (W15f, 22 Oct).

### L073 · A recall filter must reach every tag it stores
Tags: agents, review, evidence
Seats read lessons by tag, but tags_for knew five tags; eleven lessons tagged build, ci,
automation, review or signing were never shown to any seat. Found by the outside-repo review
(memory systems "recall"). A contract test now fails on any stored tag no path asks for (W15f, 22 Oct).

### L074 · A watch whose report only lands in an artifact is not a watch
Tags: watch, evidence
The owner asked on 8 Oct for every outside tool to be watched for updates and features. Tooling
watch checked two pins and wrote its report to a 30-day artifact unless a pin moved, so nobody saw
Obtainium 1.7, morphe-desktop 1.19.0 or FlareSolverr 3.5.2. Since W15h it reads all 13 upstreams in
src/etc/upstreams.json into one standing issue, edited in place, with a comment only on change (22 Oct).

### L075 · An empty answer from a list API is not proof that the list is empty
Tags: sources, evidence
On 22 Oct the releases API answered empty for this repository (the evening check said "every
release is gone"; the W15f cleanup later deleted 20 that were there) and for three providers with
100+ releases (AdGuard, ES File and Instagram builds failed "no matching release"). Minutes later the
same calls returned full pages. The bundle fetch and the poll now ask three times and name the
answer as transient; a person reading "0" checks a second way before acting on it (W15h).

### L076 · A tool that keeps its data beside its own file writes into whatever folder holds it
Tags: build, evidence
morphe-desktop 1.19.0 (22 Oct) keeps "morphe-data" next to its JAR. The shadow resolver ran the JAR
from the dependency packet it was sealing, so every packet gained an unlisted folder and all 17
Check new patch shadow jobs refused their own lock (23 Oct). The owner's Cloud Shell probe printed
"Morphe data root: .../payload/morphe-data (JAR-adjacent)". Tools now run from a byte-identical copy
in their own folder, and the refusal names the unexpected files (W15i).

### L077 · "Worked" that counts a fallback build hides the primary's failure
Tags: ci, evidence
T1 said "17 of 17 apps worked" on 23 Oct while Facebook had built on De-Vanced 580 (Hushfacebook
0.17.0 had moved to Facebook 584) and Instagram on HushGram (a piko fingerprint failed). A fallback
keeps the shelf stocked; it is still a finding, and T1 now reports it as one (W15i).

### L078 · Check the official bundle before choosing or keeping a community provider
Tags: providers, evidence
Reddit ran on Adobo alone for weeks with a note saying "adobo covers reddit alone", while the
official MorpheApp/morphe-patches listed Reddit all along (v1.48.0: 31 patches, 2026.42.0 down to
2026.10.0). On 23 Oct the Adobo 42 build was deleted for Adobo's sake and the shelf had no Reddit.
Before a provider is chosen, kept or retired, the official bundle's live list-patches comes first (W16).

### L079 · Never delete a shelf build until its replacement is published and verified
Tags: release, retention
The W15i cleanup deleted Reddit 2026.42.0 so 2026.41.0 would publish; Check new patch never built
41 (nothing upstream changed), so the shelf had no Reddit release. A retirement waits for the
replacement's publish receipt, and retirements name the provider they apply to (W16).

### L080 · Check new patch builds only changed apps; a switch needs an explicit build
Tags: ci, release
The poll builds an app only when its provider published something new. A provider switch, a
retirement or a selection change does not count, so it needs its own Batch Patch dispatch for that
app, said in the packet's owner steps (W16).

### L081 · A command's --help exit code is not a health check
Tags: build, evidence
morphe-desktop 1.19.0 prints its usage and exits 2 on `list-patches --help` because --patches is
required. A probe that stopped on that exit code cost the owner a round trip (23 Oct). Record help
text; gate on the real command's exit code and output (W16).

### L082 · A version a provider lists is not a version the shelf can install
Tags: build, release
Morphe v1.48.0 lists Reddit 2026.42.0, and the owner was told W16 brings Morphe 42. The 42 APK needs
Android 12 (SDK 32); the shelf ceiling is Android 10 (SDK 29), so the build stepped down to 41
(23 Oct). Check the app's minimum SDK against min_sdk_ceiling before promising a version (W16).

### L083 · A guard copied into several readers needs the fix in every copy
Tags: evidence, tests
The version chooser refused Morphe's Reddit listing for a repeated name; W16 fixed src/build/coverage.py
only. The provider watch has its own copy (DUPLICATE_PATCH_NAME), so after the merge Provider and
Nightly watch went red on the same listing (23 Oct). Before fixing a refusal, grep every reader of
the same input for the same check (W16b).

### L084 · Read the build's own warnings before calling a selection done
Tags: build, evidence
Reddit on Morphe shipped "Disable modern home" through four builds of 2026.41.0 while every log said
"does not work with Reddit 2026.25.0+" and Morphe's own description says it works up to 2026.24.0.
A patch the patcher says does nothing on the built version is left out, and the release notes stop
listing it (W16c, 24 Oct).

### L085 · A faked command line proves the code, not the command
Tags: tests, evidence
Needs you asked `gh issue list --json` for `user`; gh has no such field, so the first real run
failed (24 Oct). Its tests replaced gh with a fake that answered anything. A test that fakes a
CLI also checks the arguments against that CLI's documented set (W16d).

### L086 · A found provider is an owner decision, not a note
Tags: evidence, release
heval99 for Truecaller sat in the community index, a watch issue and an OPEN-WORK line from 19 Oct;
the owner never saw it (24 Oct). Anything the watches find that the owner could take goes to Needs
you as its own item with take, drop and hold, and take starts the next step (W16e).

### L087 · The sandbox has no docker or network; Actions has both
Tags: gates, ci, build
W16g's store helpers started on a test's first Cloudflare fetch. The sandbox has no docker, so the
suite passed; on the Validate runner the helpers really started, a fixture download worked, and a
refusal test went red (24 Oct, PR #239). Side effects that need docker, network or secrets run only
behind a flag the real job sets (PF_STORE_LAZY=1 on the Manual Patch build step). Validate's test
steps also write their step summary to a scratch file: fixture tables (UNKNOWN,
MISSING_OR_INVALID_OBSERVATION) are test data, not results, and were filling the run page.

### L088 · Minimum Android belongs to the variant, not the version; keep the working combo
Tags: sources, build, evidence
W16g made heval99 primary for Truecaller. The smoke downloaded 26.41.5's first APKMirror row
(Android 12L+) and stopped at the Android 10 cap; the assistant then said "heval99 only supports
Android 12 versions". The same release has an Android 10+ arm64 row; the owner found it. Every build
fell back to bufferk alone (7 patches instead of 19). The picker now skips rows above the cap. Read a
store's variant list before claiming a version cannot install, and keep the working combo primary
until the new provider's smoke is green.

### L089 · A build that stops at the first failing patch hides the rest
Tags: build, evidence
newuser7171 failed on Bypass channel restrictions (24 Oct), was trimmed, then failed on Bypass
content restrictions (25 Oct): two runs, two packets, one cause (obfuscated fingerprints that miss
12.10.4). A smoke of a new provider runs with keep_going (Manual Patch, never with publish) so one
run names every failing patch (PATCH_FAILED lines). The guard that refused a release on a failed
patch grepped the old `SEVERE: FAILED` wording; the patcher now prints `ERROR: FAILED`. Check a
guard against today's log, not the log it was written for.

### L090 · Decide once per app and name, not once per provider
Tags: selection, review
The owner answered 104 items in one sitting, many the same name from a second provider or a newer
version. src/patches/DECISIONS.json keeps each call by app and normalised name; Selection watch and
Needs you read it, so the same question is never asked twice. BANNED and one-bundle-per-name still
win over a remembered take.

### L091 · A known tree rebuilds a base without a bundle
Tags: ci, evidence
Main moved by two bot commits after the last bundle. Replaying them with blob shas checked against
the API, `git mktree --missing` for the one blob not held, and the commit object rebuilt byte-exact
(the gpgsig header ends with a " " continuation line) gave main's exact sha. The packet commit can
then sit on the real parent; a rehearsal still needs a full twin world.

### L092 · A fallback needs its own plan
Tags: build, release
Qualify compared every publication with the configured declaration; a fallback build pins another
candidate and its overrides, so it always read DRIFT. The plan now carries one key per candidate.

### L093 · Judge a version's rows together
Tags: build
The picker took the first row of the wanted type and checked Android afterwards, so a version
with a fitting arm64 build and a non-fitting universal one failed on the wrong row. Score every
row on chip, minimum Android and screen at once, and say "none fits" apart from "no rows".

### L094 · One file is not a choice
Tags: build
APKPure serves one file per version; for Key Mapper 4.5.0 it needed Android 12L. The same version
had an Android 10 arm64 build on APKMirror. Before stepping down a version, try the same version
from the other store.

### L095 · The third smoke of an app is cancelled
Tags: ci
Manual Patch keeps one running and one pending run per app; a third dispatch replaces the pending
one, which ends cancelled (Instagram oxbow, W16j). A controller dispatches at most two per app.

### L096 · Followers multiply
Tags: ci
A workflow_run follower without a branch filter starts for every branch smoke, and two followers
per run double it: 180 of 299 runs on 25 Oct were followers. Filter to main and call the second
follower from the first.

### L097 · A failure without a reason is two failures
Tags: ci, evidence
Community collect and Nightly report failed with only "exit 1" and "UNKNOWN" in the log, so the
cause could not be read from the owner's log zip. Every stop prints its stage and its own code.

### L098 · A fallback build is not a green smoke
Tags: build, ci
The W16k Instagram smoke ended success, but piko had failed on Hide feed posts and HushGram built
it; the publish batch did the same, and Reddit fell back to Adobo the same way. A smoke that names
a provider (app/provider) passes only when that provider wins; read PROVIDER_FALLBACK as a failure
of the primary, find its PATCH_FAILED name and hold that name, not the provider.

### L099 · Only report what a follower was built for
Tags: ci
Notify, called inside Status page data, threw "Unexpected triggering event" for a run started by an
event it never reports, which turned Status red. The job's own if: now lists the events it reports.

### L100 · Read the provider's issues before the second smoke
Tags: sources, build
CCleaner's first smoke failed on Disable Telemetry, so it was removed; the second failed on Unlock
Premium. The provider's own tracker already had the same fingerprint failure from a phone, opened
that afternoon (MightyMichs issue #18): the bundle did not fit the app version, the APK was fine.
Read the provider's open issues for the package before removing names one by one.

### L101 · Search the records before reusing a label; list before saying "cleaned"
Tags: docs, evidence
W16l named the owner's Add app idea "W17" while the 25 Oct records already used W17 for the combo
planner, and the first W16m handover said the assistant sandbox was cleaned while /tmp still held
three days of files. Both were found only on a third read. Before giving out a packet label, search
every record for it; before writing that something was removed, list the place and quote the count.

### L102 · Run a test the way the suite runs it and read the count
Tags: tests, gates
A docs contract file run as `python3 tests/x.py` has no main block: it ran zero tests, exited 0 and
was reported as passing (W16m third check). The suite runs `python3 -m unittest discover -s tests -p
x.py`. Run single tests that way and quote the "Ran N tests" line; exit 0 alone proves nothing.

### L103 · The author's own checks are not a review
Tags: review, evidence
The W16m handover needed eight check rounds. In rounds 1 to 4 the author re-read his own records and
each round found more; from round 5 independent agents with one lens each (open items, chat facts,
code facts, stale docs, a fresh-chat simulation) found what he could not see. Check a handover the
way docs/review/REVIEW-METHOD.md says: full populations split into shards, written evidence, a second
pass on the fixes, done only when fresh reviewers find no HIGH or MED item.

### L104 · Name checks list with -x and without -u
Tags: selection, evidence
`-u` hides universal patches; leaving out -x hides patches tied to experimental app versions. The
Nightly name check listed with neither flag from 29 Sep 2026, so it was blind to version-tied patches;
when the Alastor Reddit extra arrived on 25 Oct 2026 (both its patches are version-tied), every Nightly
ran UNKNOWN (#249). Name checks pass -x and omit -u, the same view the Selection and Provider
watches use. Supersedes the last sentence of L030.

### L105 · morphe-desktop needs a writable data root
Tags: tooling, sources
Since 1.19 `morphe-desktop` keeps a data root next to its JAR, or in `~/morphe` when the JAR folder is
not writable, and copies every bundle into tmp/shadow there before it lists or patches. In a read-only
container it failed with FileNotFoundException before reading a patch (owner probe P0, 26 Oct 2026).
Java takes the home folder from the passwd entry, not from $HOME: pass -Duser.home or give the JAR a
writable folder. The W15g keyless patch job must keep a writable JAR folder.

### L106 · A probe's isolation is part of the test
Tags: evidence, gates
The P0 probe ran list-patches in a locked-down container to keep provider code away from the owner's
shell; the lock-down itself broke the tool, so both runs listed nothing and the proof was
inconclusive (wrong call 78). Rehearsal fakes cannot catch this: run the isolation recipe once
against the real tool, and print the tool's own error next to any count.

### L107 · Check the premise before stating the impact
Tags: evidence
A review said the owner's Needs you answers were already lost; the owner had never answered by
comment, so nothing was lost yet and the bug was latent (wrong call 77). Read the population (here
the issue's comment authors) before writing what a bug already did.

### L108 · Name the model and its fallback
Tags: workflows, agents, evidence
The MCP scout passed no model, so Gemini CLI 0.65 picked its default and got HTTP 503 "high demand"
on all ten retries (run 40298683531, 26 Oct 2026); a headless run cannot accept the CLI's offer to
switch models. Every workflow that calls a hosted model names a stable model, caps its turns and
names one lighter fallback, and its last step prints which model answered or MODEL_UNAVAILABLE.
Read the stderr before guessing a cause (wrong call 79).

### L109 · An outside feed's duplicate is merged and named, and the raw input is kept first
Tags: evidence, sources
The community index listed one repository twice and the watch refused the whole index
(DUPLICATE_PROVIDER, run 40294788256); the raw index was written only after the compare, so which
repository was doubled is unknown. Merge duplicates on our own identity (here the repository a
target wires), say each merge in the report, and write every raw input before parsing it.

### L110 · Check a tool option against the installed tool, and prove network changes live
Tags: build, evidence, tests
In W16o a lane agent bounded store downloads with `wget --max-file-size`, an option GNU wget does not
have; every store download would have failed. The curl rewrite then added a preflight request without
the store's headers and an allowlist of guessed CDN hosts. A test now checks every option against the
installed tool's own help, and a change to how builds reach the network ships only after smokes of
every app on the packet branch, before the merge.

