# Open work

## Current checkpoint: 30 October 2026 (packet W16y-a)

Every still-open item carried forward from the older checkpoints is listed once below. Closed,
superseded and decided notes remain verbatim in [the archive](history/OPEN-WORK-ARCHIVE-2026-10.md).

### Done in W16y-a (30 October 2026)

- Owner actions completed: `TDL_BACKUP` was deleted, secret scanning and push protection were enabled, and the merged CCleaner branch was deleted. The old Cloud Shell username stays in history because rewriting it would break 43 release tags.
- Wrong call 110 was fixed: the second store now receives `${RVER:-$version}` even when the first download fails.
- The unused `apply_choices.py`, `chooser.py` and `community_diff.py` utilities and the dead chooser branch in `selection_writer.py` were removed; the removal and restore record is [REMOVED-2026-10.md](history/REMOVED-2026-10.md).
- The closed `CANDIDATES-2026-10-08.md` scout moved from onboarding to [history](history/CANDIDATES-2026-10-08.md), with inbound links repaired.

### W16y-b (next packet)

- 180-day patch-age warning (all targets; warning only, never blocks a build) on the portal app cards and the status page. Not implemented in W16y-a.

- Add the provider gate and monthly watched-provider digest.
- Add the weekly pin check only for apps whose patches rely on the pin.
- Add the weekly Council model report; model swaps remain PR-only.
- Survey Telegram first; keep Hush API keys interactive-only and never stored.

### Done in W16x (29 October 2026)

- W16q and W16s cleanup previews were never applied; both are **superseded/expired**. Reason: a cleanup preview token goes stale after a Pages deploy. No deletion is authorized by this note.
- The controller cleanup path already prints an explicit `OK` result when cleanup is preview-only; owner-facing controller launcher text has no `a && b || c` compound fallback. Internal rehearsal/suite short-circuit commands are unchanged because they are not owner launchers.
- Workflow comments and handbook references were corrected; the generated Truecaller row in `README.md` shows `heval99 (fallback: bufferk + paresh + binarymend)`. `readmegen.py --check` covers the generated row.
- W16w ran and merged (#275, `2db6cde8`, 28 Oct). LinkedIn v1.2.0 with Material You published; the owner's phone test passed (Michii Patches shows in the Me panel). The 25 Oct and 28 Oct 18:29Z LinkedIn releases were deleted by the planned cleanup.
- Store near-version picks are refused outside the same release line (`STORE_DOWNGRADE_REFUSED ... reason=near_version_gap`); Prime Video (3.0.470.1047 to 3.0.470) and Hotstar (26.06.22.3 to 26.06.08.2) still build and print `STORE_NEAR_VERSION`. Amazon Music asked for 2.36.1 and got APKMirror's 2.8.1 (a 2013 file); only the signer pin stopped it. It now stops at the store step.
- PR #277 (7 switchable names: 3 Hushfacebook, 3 HushGram, oxbow Hide Meta AI) folded in; #277 closed by the packet.
- ES File fallback rushiranpise (Unlock VIP Lifetime only, built alone) back (D15).
- Onboarding checker: a malformed `overrides.extra_bundles` gives a named problem instead of a crash (test added).
- Truecaller "shadow receipt not verified" (#186): absent from the W16w T1 logs; closed.
- Cloud Shell cleanup (owner, 29 Oct): [record](history/CLOUDSHELL-CLEANUP-2026-10-29.md).

- **Owner:** Ten decision questions with recommendations and downsides (pin health check, Amazon Music paid patches, Android 10 Signer pin, idle fallback smokes, near-version rule, patch age, watched providers, release cleanup, Council models, switch-audit gate): [DECISION-REVIEW-2026-10-29.md](DECISION-REVIEW-2026-10-29.md).
- **Owner:** Phone setup: import Android 10 without the Signer pin and keep it on for Android 11/12 as recorded in [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md).
- Amazon Music fails closed until De-Vanced fixes its declared version (2.36.1, likely meant 26.36.1). Re-read the provider's live patches-list before any change; do not set max_app_version by hand ([onboarding/amazonmusic.md](onboarding/amazonmusic.md)).
- **Owner:** Instagram fallbacks are idle: HushGram v0.0.17 and oxbow v453 support only Instagram 453.0.0.55.79 (build 385914283), piko stays on the 452.1 pin. Giving the fallbacks their own 453 pin would let a fallback release lock piko out (publish_guard refuses an older version than the shelf). Options: wait for piko 453 (recommended), or allow a 453 fallback ([onboarding/instagram.md](onboarding/instagram.md)).
- MX Player fallback MightyMichs v1.12.0: "Unlock MX Player Pro" fails its fingerprint (Lxo;.j1()Z) on 1.93.4, the only version it supports. Record only; ftl stays primary; recheck on the next MightyMichs release ([onboarding/mxplayer.md](onboarding/mxplayer.md)).
- Status page red can be a nonpublishing smoke (Instagram oxbow run 40783288101, 28 Oct), not the release; the page reports the newest build job ([status.py](../../src/etc/status.py)).
- **Owner (optional):** File the upstream Obtainium issue using the text and steps in [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md); test same-version patch-only notification and installed-setting migration.
- Move the Instagram pin when piko supports build 385914182 or newer; keep the piko/brosssh held names for a provider update ([W15G-MAP.md](W15G-MAP.md); [instagram onboarding](onboarding/instagram.md)).
- Restore hoo-dles to prerelease when morphe-desktop stable reads its new bundles ([W17-BRIEF.md](W17-BRIEF.md)).
- Telegram rahul9999xda is on watch until we build 13.1.1 (DECISIONS.json watch, N-55429f).
- Build the W15g signing split in its own packet: keyless `--unsigned` patch job, isolated apksigner job, sha256 handoff, nonpublishing batch, publishing build and owner phone test ([W15G-MAP.md](W15G-MAP.md); [SIGNING-SPLIT.md](SIGNING-SPLIT.md)).
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
