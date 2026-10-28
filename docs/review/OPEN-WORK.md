# Open work

## Current checkpoint: 28 October 2026 (packet W16w)

Every still-open item carried forward from the older checkpoints is listed once below. Closed,
superseded and decided notes remain verbatim in [the archive](history/OPEN-WORK-ARCHIVE-2026-10.md).

- **Owner:** Run the W16w combo, then do the phone setup; import Android 10 without the Signer pin and keep it on for Android 11/12 as recorded in [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md).
- **Owner:** File the upstream Obtainium issue using the text and steps in [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md); test same-version patch-only notification and installed-setting migration.
- Move the Instagram pin when piko supports build 385914182 or newer; keep the piko/brosssh held names for a provider update ([W15G-MAP.md](W15G-MAP.md); [instagram onboarding](onboarding/instagram.md)).
- Restore hoo-dles to prerelease when morphe-desktop stable reads its new bundles ([W17-BRIEF.md](W17-BRIEF.md)).
- **Owner:** After W16w: uninstall LinkedIn, install the fresh stable-v1.1.1 build, open it once, check Me panel > Michii Patches and the icon long-press ([onboarding/linkedin.md](onboarding/linkedin.md)).
- Watch the first fallback builds of MX Player (MightyMichs) and ES File (rushiranpise-fallback): they carry other patches than ftl ([onboarding/mxplayer.md](onboarding/mxplayer.md), [onboarding/esfile.md](onboarding/esfile.md)).
- Telegram rahul9999xda is on watch until we build 13.1.1 (DECISIONS.json watch, N-55429f).
- Build the W15g signing split in its own packet: keyless `--unsigned` patch job, isolated apksigner job, sha256 handoff, nonpublishing batch, publishing build and owner phone test ([W15G-MAP.md](W15G-MAP.md); [SIGNING-SPLIT.md](SIGNING-SPLIT.md)).
- W16w runs the MCP scout without `run-gemini-cli` (YOLO off, default approval, two read tools, lite model apart from the Council seat, QUOTA fail-fast): prove it with one dispatch after the merge ([MCP-PLAN.md](MCP-PLAN.md)).
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
- **Owner:** Re-import the Obtainium JSON if needed, delete TDL_BACKUP, decide Cloudflare/CodeRabbit/pf-vault actions and handle external-only cleanup ([OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md)).
- Retire or regenerate [UNREVIEWED.tsv](UNREVIEWED.tsv), and complete the speed target (one-app Check new patch under five minutes) ([AUDIT-2026-10-26.md](AUDIT-2026-10-26.md)).
- Review Council v4's desk, safe-output split, triage and digest templates ([KT-2026-10-28.md](KT-2026-10-28.md)).
- Keep the shared openskip/brain handbook fixes (AGENT-PERSONAS, FREE-LLM-APIS and PACKET-LESSONS) in their own pull requests ([REVIEW-METHOD.md](REVIEW-METHOD.md)).
- Resolve the unknown-status records: agent runner pilot, portal SRI, PR53, F05/F06, ES File logo and CLUTTER sections 1/3/4 ([OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md)).
- Add an explicit result line to the controller cleanup path and remove remaining `a && b || c` style from the next controller-touching packet ([controllers/README.md](controllers/README.md)).
- Correct the remaining workflow comments, handbook references and generated Truecaller provider row ([AUDIT-2026-10-26.md](AUDIT-2026-10-26.md)).
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
