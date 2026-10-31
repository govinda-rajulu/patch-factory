# Open work

## Current checkpoint: 31 October 2026 night (packet W17a)

### Done in W17a (31 October 2026)

- W17 phase 0, all twelve owner items: weekly pin check, run attempt in artifact names, apksig signature-file rule, history scan (0 real), bounded fallback attempt table, scored agent trials (49 of 56), 5S moves and link repairs, content fixes, portal contrast and weight (433,819 to 320,021 bytes), prose pass, `knowledge/style/` with three Validate checks, five dead helpers removed ([w17a/README.md](w17a/README.md)).

### Open after W17a

- **Owner:** run **5. Add target** for Remote for Android TV (`remoteatv`), merge its pull request when Validate and Onboarding review are green, then phone-test a Manual Patch build; a logo follows in the next packet.
- **Owner, on hold:** the car. Photo of the YT Music install error on the head unit, then a ZLink Android Auto test ([w17a/README.md](w17a/README.md), car section).
- Read the Sunday 1 Nov Council probe and monthly digest, the Monday 2 Nov retention preview and the first weekly pin check (Wednesday 4 Nov); retention apply only with the owner token, from 3 Nov.
- Council-seat trials (the assistant agents were scored in W17a; seats need a workflow run).
- W17 phase 1: owner console (#286). Android Auto (#287) waits for the car test.
- Carried from W16z: **owner**, a heavy Telegram user runs the check guide ([onboarding/telegram.md](onboarding/telegram.md)); Reddit stays held at 2026.41.0 and Check new patch red until Morphe's bundle passes 2026.40.0 (#280; the guard is right); fallback recovery stays a design (owner: keep).
- **Owner decision, with the car test:** Morphe's YT Music "Android Auto" patch is excluded by an assistant rule of 6 Oct, not by an owner call; keep it out or turn it on.
- The W15g carry-forward and W16x lists below stay open where they are not marked done.

## Checkpoint: 31 October 2026 evening (packet W16z)

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

### W15g result and carry-forward (31 Oct 2026, afternoon)

- Merged as #283 (`95be30da`); 17 of 17 smokes signed in the Sign job; Telegram published by the split jobs. Details: [HANDOVER-2026-10-31-W15g.md](history/HANDOVER-2026-10-31-W15g.md) (Result) and [w15g-close/README.md](w15g-close/README.md).
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
- Move the Instagram pin when piko supports build 385914182 or newer; keep the piko/brosssh held names for a provider update ([W15G-MAP.md](history/W15G-MAP.md); [instagram onboarding](onboarding/instagram.md)).
- Restore hoo-dles to prerelease when morphe-desktop stable reads its new bundles ([W17-BRIEF.md](W17-BRIEF.md)).
- Closed in W16y-b: Telegram rahul9999xda became the primary (watch row N-55429f removed).
- W15g signing split: closed. Telegram was published from the split and installed over the current copy on the phone (W16z, [HANDOVER-2026-10-31-W16z.md](HANDOVER-2026-10-31-W16z.md); design in [history/SIGNING-SPLIT.md](history/SIGNING-SPLIT.md)).
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
