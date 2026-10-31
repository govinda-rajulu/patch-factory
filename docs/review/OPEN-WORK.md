# Open work

## Current checkpoint: 31 October 2026 evening (packet W16z)

### Done in W16z (31 October 2026)

- Recorded: the owner's install-over phone test of the split-signed Telegram (works; other patches unconfirmed), L115 and L116 in the ledger, the owner's answers of 31 Oct ([HANDOVER-2026-10-31-W16z.md](HANDOVER-2026-10-31-W16z.md)).
- Pin probe fix (wrong call 122), failure-issue reasons (#280), portal freshness row, patch fold, CCleaner Coming soon, Needs you link, UI pass, issue forms, labels and feature requests through Repo setup, three removals, retention prose, CI wording, closed records to history/, #154 triage ([w16z/README.md](w16z/README.md)).

### Open after W16z

- **Owner:** a heavy Telegram user runs the check guide in [onboarding/telegram.md](onboarding/telegram.md).
- Read the post-merge pin check run; schedule it weekly only on OK lines. Read the Sunday Council probe (nemotron swap, PR-only) and monthly digest, and the Monday retention preview; retention apply only with the owner token, from 3 Nov.
- Reddit: held at 2026.41.0 while Morphe's bundle targets 2026.40.0; Check new patch stays red until Morphe catches up (the guard is right). If the next failure issue still says "No failing step", probe the jobs API timing.
- W17 phase 0: run the scored agent trials ([w16z/AGENT-TRIALS.md](w16z/AGENT-TRIALS.md)); fallback attempt summaries (tests first); attempt in `build-evidence-<t>` and `provider-scan-<t>-<run>` (update the controller's scan download with it); signature-file pattern (`META-INF/.SF`, lowercase `meta-inf/`); historical credential scan disposition; W16w 64/65 wording.
- Fallback recovery (owner: keep) stays a design until its own packet ([w15g-close/earlier/TELEGRAM-FALLBACKS-2026-10-30.md](w15g-close/earlier/TELEGRAM-FALLBACKS-2026-10-30.md)).
- Wrong calls 122 to 124 are in [w16z/FINDINGS.md](w16z/FINDINGS.md).

## Checkpoint: 31 October 2026 afternoon (W15g merged as #283; records packet W15g-close)

Every still-open item carried forward from the older checkpoints is listed once below. Closed,
superseded and decided notes remain verbatim in [the archive](history/OPEN-WORK-ARCHIVE-2026-10.md).

### Done in W16y-a (30 October 2026)

- Owner actions completed: `TDL_BACKUP` was deleted, secret scanning and push protection were enabled, and the merged CCleaner branch was deleted. The old Cloud Shell username stays in history because rewriting it would break 43 release tags.
- Wrong call 110 was fixed: the second store now receives `${RVER:-$version}` even when the first download fails.
- The unused `apply_choices.py`, `chooser.py` and `community_diff.py` utilities and the dead chooser branch in `selection_writer.py` were removed; the removal and restore record is [REMOVED-2026-10.md](history/REMOVED-2026-10.md).
- The closed `CANDIDATES-2026-10-08.md` scout moved from onboarding to [history](history/CANDIDATES-2026-10-08.md), with inbound links repaired.

### Done in W15g (31 October 2026)

- Signing split built: Patch without key or write token (unsigned APK, `--unsigned` probed first), Sign with the release key and first-party code only (`src/build/sign_apk.py`), Publish with the write token and no key ([HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md)). Closed in W16z: the owner installed the split-signed Telegram over the current one and it works (31 Oct).

### W15g result and carry-forward (31 Oct 2026, afternoon)

- Merged as #283 (`95be30da`); 17 of 17 smokes signed in the Sign job; Telegram published by the split jobs. Details: [HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md) (Result) and [w15g-close/README.md](w15g-close/README.md).
- Done (W16z): the owner installed the published Telegram over the current one, no uninstall; it opens signed in.
- Pin check run 41158386985 (31 Oct) printed `PIN_STORE_MISSING` (version_code_not_listed) for Facebook, Facebook De-Vanced and Instagram, while the same day's smokes downloaded those exact pins from APKMirror: the probe's page reading is wrong, not the pins. Fix the probe before any weekly schedule.
- LOW, for W16z: artifact names `build-evidence-<t>` and `provider-scan-<t>-<run>` carry no attempt (pre-existing; GitHub reruns are per attempt); the signature-file pattern differs from apksig on `META-INF/.SF` (empty base name) and lowercase `meta-inf/`; the release tag date comes from build end, not the job stamp (cosmetic; run and attempt are bound). Round 4 detail: [w15g-close/scenarios/SUMMARY.md](w15g-close/scenarios/SUMMARY.md).
- Test lesson (wrong call 120): fake tools copy the real tool's output policy from its source; fixtures carry what store APKs carry (source stamp, directory entries).
- Signature schemes: the split signs minimum SDK 23 apps with v1+v2+v3 (Telegram, MX Player, plus Hotstar and ES File); same certificate, so install-over is unaffected. The owner phone test on Telegram confirms it.
- Done (W16z): L115 and L116 approved by the owner (31 Oct) and appended to docs/council/LESSONS.md.
- **Owner ask (31 Oct), not yet scheduled:** give some W16z housekeeping and triage work to the Council and other free agents as scored trial tasks (ask, audit, triage) to see how they perform; record scores in the session note.
- Owner Cloud Shell after this records packet merges: the old `~/pf-w15g-combo-071f39d4.py`, `~/pf-sp.py` and the W15g launcher texts can go (both scripts are now in the repo); keep `~/work/run-logs`.
- Wrong call 121 (close-out): the first close-out swept only the 31 Oct work; the owner's "check again" found the 28 to 30 Oct notes, the rehearsal tools, the scenario tests, the issue collector and two owner asks missing. All are in this packet now; a close-out sweeps every day of the chat.
- From the close-out sweep of 28 to 30 Oct notes ([w15g-close/LEFTOVERS-AUDIT.md](w15g-close/LEFTOVERS-AUDIT.md)):
  - Triage the Council desk (#154) report of a `safeLink` path-validation problem in the portal: confirm or close it in writing (a report, not proof).
  - Storage: the 30 Oct artifact snapshot (capped at 2,000 artifacts) showed at least 36.9 GB, 92.5 percent of it `test-apk-*`. **Owner decision:** keep test APK artifacts 7 days, or cut to 2 or 3 days once phone tests always use Releases ([earlier/STORAGE-PLAN-2026-10-30.md](w15g-close/earlier/STORAGE-PLAN-2026-10-30.md)).
  - **Owner decision:** the generic fallback-recovery proposal (a stale-fallback marker after 7 days; a newer primary may replace a fallback shelf only with a downgrade/uninstall warning; never an older fallback over a newer primary) ([earlier/TELEGRAM-FALLBACKS-2026-10-30.md](w15g-close/earlier/TELEGRAM-FALLBACKS-2026-10-30.md)).
  - Fallback attempts: bounded attempt summaries with tests first, later a cached ELIGIBLE / INELIGIBLE / UNKNOWN check where UNKNOWN never skips a fallback; candidate order and caps unchanged ([earlier/AUTOMATION-MAP-2026-10-30.md](w15g-close/earlier/AUTOMATION-MAP-2026-10-30.md)).
  - Council model catalogue watcher: the detailed safe design (free-pricing proof, bounded requests, PR-only) is in the same AUTOMATION-MAP note; build only if still wanted.
  - `.gitignore`: decide whether to ignore `.pytest_cache/`.
  - The 30 Oct historical credential and personal-data scan produced candidate hits only, no verdict: re-run it sanitized and record a disposition (never publish raw hits).
  - W16w handover says 64 broken relative links, its review counted 65 changed destinations: clarify the wording.

### Next: W16z (owner, 31 Oct 2026)

- Portal: one freshness row (patch bundle age plus last built; the 180-day limit only near or over it); one `N patches` fold instead of count plus toggle; CCleaner card with its icon and `Coming soon` (drop the release-history line: no CCleaner release was published); one `Open Needs you` link with the reply words on the Watch tab; no repeated links.
- Issues and PRs: two issue forms (owner action, verified bug) and a small label set; note on #262 (closed after a green rerun; the root cause was fixed in W16v); track the follow-ups of #75 (PotHelper companion review), #78 (live source-preparation timing proof), #81 (documentation migration destination; likely the cross-repo mirror item) and the W16y-c pin-check read; #280 (Reddit refusal counted as a failure).
- Housekeeping: delete `src/options/arandomhooman.json`, `src/options/bufferk.json` and the duplicate `docs/review/providers/hushtelegram-org.telegram.messenger.names` (restore points in the survey); retention prose to the code (3 releases, 3 Pages records, 7 days); closed session and handover records into `history/`; CI schedule wording; pin check weekly after an OK read; Council nemotron replacement after the Sunday probe.
- File feature requests: W17 owner console (Pages builds issue-form links; the owner submits on GitHub; tests run for anyone, only the owner's submission makes a ready PR; merges stay with the owner; note field saved as a dated decision record, optional lesson flag) and Android Auto apps.

### Done in W16y-c (31 October 2026)

- W16y-b merged as #281 (`27adc7b4`, tree `c761f1c6`), RESULT OK. Telegram rahul9999xda built 14 of 14 on 13.1.1; the owner installed the smoke build and **signed in without the API error** (31 Oct). This packet publishes Telegram from rahul9999xda after the merge. The owner has not yet checked every patch on the phone.
- Provider scan: bare names count as hosts only with a real public top-level domain (wrong call 118); the Amazon Music HOLD of 30 Oct was 22 code names, not hosts.
- Pin check probe reads APKMirror the way the build does (store helper, lazily started), follows the build's own release-page and uploads-page lookup, and stops at the variant row with the pinned version code; it never asks for a download page or a file. Candidate `overrides.version_code` pins are checked too. Still manual and report-only until a live run shows OK lines.
- Packet controller: a `git push` that fails with a transient server or network error is retried twice (30 s, 90 s); a rejection is never retried (the 30 Oct HTTP 500 stop).
- The controller keeps scan evidence with the smoke logs; the owner probe reads the newest Pin store check, Retention preview and Batch Patch runs, so no separate collect command is needed.
- Wrong calls 118 and 119 recorded. Wrong call 120 (W15g first smoke: signer drops directory and source-stamp entries) in HANDOVER-2026-10-31-W15g.md.

### Done in W16y-b (30 October 2026)

- Provider safety scan (`src/etc/provider_scan.py`, allowlist `src/etc/provider_scan_allowlist.json`): a nonpublishing Manual Patch with `scan` on compares the original and patched APK (permissions added, new hosts, new code red flags, new native libraries), runs ClamAV on the bundle and the patched APK, and looks up their sha256 on VirusTotal (repo secret `VT_API_KEY`, used only in that step; hashes only, no upload). It prints one `PROVIDER_SCAN ... verdict=PASS|HOLD|BLOCK` line and keeps `provider-scan.json` for 30 days. Publishing builds never run it. ClamAV and VirusTotal are credited in CREDITS.md.
- Controllers: `SMOKE_SCAN` entries dispatch that scan smoke and record its line (always advisory).
- Monthly watched-provider digest in Needs you (shown in the issue body on UTC days 1 to 7 of each month, collapsed); HushTelegram, HushGram and HushFacebook added as watch sources (`src/etc/extra-providers.json`). Nothing is adopted automatically.
- Pin check probe (`pin-check.yml`, manual dispatch only, report-only): reads the store listing for targets with an exact build pin (Facebook and Instagram today), prints `PIN_STORE_OK`, `PIN_STORE_MISSING` or `PIN_STORE_UNKNOWN`, keeps evidence 30 days and never fails. Not scheduled yet (wrong call 115): the build reaches APKMirror through its browser helper, and plain reads were only tested against stubs. The controller dispatches it once after the merge; the weekly schedule follows with that evidence.
- 180-day patch-age warning on every target (preflight enforces 180), shown on the status page and portal app cards; never blocks a build.
- Weekly Council model report: the Sunday morning probe prints one `MODEL_OK` or `MODEL_MISSING` line per listed seat model; swaps stay PR-only.
- Telegram survey: [TELEGRAM-SURVEY-2026-10-30.md](TELEGRAM-SURVEY-2026-10-30.md). Owner, 30 Oct evening: non-Hush. rahul9999xda v1.17.0 is primary on 13.1.1 with 14 names (integrity bypass and a no-op left out); rushiranpise stays the fallback; HushTelegram on watch, its files kept ([onboarding/telegram.md](onboarding/telegram.md)).
- Amazon Music: De-Vanced v1.6.2 fixed its declared version; the W16y-a smoke built 26.36.1 with 5 of 5 chosen patches. The fail-closed note below is closed.
- Workflow YAML contract and the Add app patch-age default (wrong calls 113 and 114, both caught before the commit). Review fixes: the scan never says PASS when ClamAV or VirusTotal did not answer, and flags a native library replaced under the same name; the Council model lines sit below the table.

### Next (after W16y-b)

- **Owner:** check the Telegram rahul9999xda patches on the phone (sign-in passed 31 Oct); report any patch that does nothing.
- Read the post-merge pin check probe; schedule it weekly only when its lines are OK or a real MISSING.
- Scan and pin-probe limits from the second review (LOW, recorded): the scan reads only the merged APK and loads each dex fully (fine on 16 GB runners); the pin probe's page parsing is heuristic and does not check Facebook's fallback `overrides.version_code`. Revisit with the first live evidence.
- New-provider ready PR: discovery, then the scan smoke, then a green test build, then a ready pull request the owner merges. W16y-b ships the scan step only; the orchestration is not built.
- Read the first runs: Council probe (Sunday 1 Nov morning), monthly digest (Needs you, 1 Nov), the post-merge pin check probe, retention preview (Monday 2 Nov). Then schedule the pin check weekly (reading pages the way the build does if plain reads are refused). Retention apply only with the owner's token, from 3 Nov.

### Carried open list (from W16x, 29 October 2026)

- **Owner:** Ten decision questions with recommendations and downsides (pin health check, Amazon Music paid patches, Android 10 Signer pin, idle fallback smokes, near-version rule, patch age, watched providers, release cleanup, Council models, switch-audit gate): [DECISION-REVIEW-2026-10-29.md](DECISION-REVIEW-2026-10-29.md).
- **Owner:** Phone setup: import Android 10 without the Signer pin and keep it on for Android 11/12 as recorded in [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md).
- Closed in W16y-b: Amazon Music builds 26.36.1 again (De-Vanced v1.6.2 fixed its declared version; [onboarding/amazonmusic.md](onboarding/amazonmusic.md)).
- **Owner:** Instagram fallbacks are idle: HushGram v0.0.17 and oxbow v453 support only Instagram 453.0.0.55.79 (build 385914283), piko stays on the 452.1 pin. Giving the fallbacks their own 453 pin would let a fallback release lock piko out (publish_guard refuses an older version than the shelf). Options: wait for piko 453 (recommended), or allow a 453 fallback ([onboarding/instagram.md](onboarding/instagram.md)).
- MX Player fallback MightyMichs v1.12.0: "Unlock MX Player Pro" fails its fingerprint (Lxo;.j1()Z) on 1.93.4, the only version it supports. Record only; ftl stays primary; recheck on the next MightyMichs release ([onboarding/mxplayer.md](onboarding/mxplayer.md)).
- Status page red can be a nonpublishing smoke (Instagram oxbow run 40783288101, 28 Oct), not the release; the page reports the newest build job ([status.py](../../src/etc/status.py)).
- **Owner (optional):** File the upstream Obtainium issue using the text and steps in [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md); test same-version patch-only notification and installed-setting migration.
- Move the Instagram pin when piko supports build 385914182 or newer; keep the piko/brosssh held names for a provider update ([W15G-MAP.md](W15G-MAP.md); [instagram onboarding](onboarding/instagram.md)).
- Restore hoo-dles to prerelease when morphe-desktop stable reads its new bundles ([W17-BRIEF.md](W17-BRIEF.md)).
- Closed in W16y-b: Telegram rahul9999xda became the primary (watch row N-55429f removed).
- W15g signing split: built in packet W15g; open until the post-merge Telegram publish and the owner's install-over phone test pass ([HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md); [SIGNING-SPLIT.md](SIGNING-SPLIT.md)).
- Prove the W16w MCP scout settings with one post-merge dispatch (no `run-gemini-cli`, YOLO off, default approval, two read tools, lite model apart from the Council seat, QUOTA fail-fast) ([MCP-PLAN.md](MCP-PLAN.md)).
- Make the next scheduled Council audit finish under 50 minutes with one line per part and seat; read the Council desk after the run ([KT-2026-10-28.md](KT-2026-10-28.md)).
- Needs you: every 28 Oct choice is in DECISIONS.json (W16w decision sheet D1 to D18 in [KT-2026-10-28.md](KT-2026-10-28.md)); after the merge the issue should list only new items.
- Implement and verify W17a/W17b Add app, including owner answers, provider-named smokes, disabled-target semantics and logo choice ([W17A-MAP.md](W17A-MAP.md); [W17-BRIEF.md](W17-BRIEF.md)).
- Plan and run W18's bounded combo planner with its 16-combo budget and manual phone receipt ([W17-BRIEF.md](W17-BRIEF.md)).
- Council nvidia seat: replace the missing nemotron model with one the live catalogue serves (a seat keeps two models).
- **Owner:** Decide whether to add or drop the optional CLOUDFLARE seat keys ([MCP-PLAN.md](MCP-PLAN.md)).
- Probe APKMirror's curl path on every APKMirror app before curl returns there; retain the transfer/host evidence ([AUDIT-2026-10-26.md](AUDIT-2026-10-26.md)).
- **Owner:** Review the optional patcher and extra-bundle pins only with owner approval, and warn on unpinned extra bundles ([AUDIT-2026-10-26.md](AUDIT-2026-10-26.md)).
- Keep the six-folder, 48-name stale-exclude warning visible; these owner vetoes are retained because removing them could let a re-offered name pass auto-adopt ([morphe provider baseline](providers/morphe-com.google.android.apps.youtube.music.names); [ADOPT.json](../../src/patches/ADOPT.json)).
- Re-enable CCleaner only after a newer provider release is explored, enabled and smoke-tested; keep Disable Telemetry out unless requested ([KT-2026-10-28.md](KT-2026-10-28.md)).
- Qualify Key Mapper's APKMirror 4.5.0 variant or keep APKPure as the only qualified source ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Dispatch/read the next green Nightly, Community and MCP watch runs before closing their failure issues; investigate unreadable provider output from the report ([W16-WATCHES.md](W16-WATCHES.md)).
- Reconcile thin/late schedules and any runs that miss their grace period before relying on daily watches ([docs/SCHEDULES.md](../../docs/SCHEDULES.md)).
- **Owner:** Decide whether to restore one Council solo slot and whether daily watches should share a run; the latter needs a status.py change ([W16-WATCHES.md](W16-WATCHES.md)).
- **Owner:** Complete phone tests for Truecaller with MicroG RE, Telegram, Reddit 2026.41, Instagram piko and Facebook 584 ([KT-2026-10-28.md](KT-2026-10-28.md)).
- Mirror the generic controller/sandbox notes and shared review method into openskip and brain through separate pull requests ([controllers/README.md](controllers/README.md); [REVIEW-METHOD.md](REVIEW-METHOD.md)).
- Preserve the safety decisions: Amazon Music uses only a throwaway account; review Photos Akash-Sriram licensing; keep Rushiranpise's AMOLED copy excluded ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Six resource-reduction selections excluded (APK Junk Cleanup, Remove Duplicate, Remove Languages) in `esfile-ftl` and `mxplayer-ftl` stay excluded; APPVERSION-only delivery, YouTube's `Remember live stream playback position`, the original semantic poller, and the warning that Reddit recovery is not established remain open ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- **Owner:** Re-import the Obtainium JSON if needed, decide Cloudflare/CodeRabbit/pf-vault actions and handle external-only cleanup ([OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md)).
- Retire or regenerate [UNREVIEWED.tsv](UNREVIEWED.tsv), and complete the speed target (one-app Check new patch under five minutes) ([AUDIT-2026-10-26.md](AUDIT-2026-10-26.md)).
- Review Council v4's desk, safe-output split, triage and digest templates ([KT-2026-10-28.md](KT-2026-10-28.md)).
- Keep the shared openskip/brain handbook fixes (AGENT-PERSONAS, FREE-LLM-APIS and PACKET-LESSONS) in their own pull requests ([REVIEW-METHOD.md](REVIEW-METHOD.md)).
- Resolve the unknown-status records: agent runner pilot, portal SRI, PR53, F05/F06, ES File logo and CLUTTER sections 1/3/4 ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Finish full fingerprints and durable baselines, including exact dynamic inputs and omitted-target observation ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Finish qualification trust with independent provenance and attestation of the original APK, plus reproducibility evidence ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Complete watcher provider/extra/default coverage, deltas and actionable options including universal patches ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Finish same-version Obtainium delivery behavior, migration and notification tests without catalog autosync ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Audit required-CI/bypass, add-target schema and disabled semantics, GitLab-primary capability and effective/default approvals ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Complete supply-chain/recovery work: original-APK trust, alternative-source pilot, restore-tested backups, signing restore and phone validation ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Refresh cleanup with APK-byte backup, review agent guidance/skills and inspect PR53 separately ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Review provenance and permitted use for remaining official app artwork ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Periodically review upstream attribution, Morphe NOTICE handling and each provider's pinned licence/source record ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Add or decide reproducible-build and PR integration-test coverage with explicit acceptance limits ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Keep evidence links current and label work shipped, partial, blocked or deferred ([REPORT-STYLE.md](REPORT-STYLE.md)).
