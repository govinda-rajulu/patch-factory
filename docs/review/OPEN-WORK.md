# Open work

## Current checkpoint: 30 October 2026 (packets W16y-a and W16y-b)

Every still-open item carried forward from the older checkpoints is listed once below. Closed,
superseded and decided notes remain verbatim in [the archive](history/OPEN-WORK-ARCHIVE-2026-10.md).

### Done in W16y-a (30 October 2026)

- Owner actions completed: `TDL_BACKUP` was deleted, secret scanning and push protection were enabled, and the merged CCleaner branch was deleted. The old Cloud Shell username stays in history because rewriting it would break 43 release tags.
- Wrong call 110 was fixed: the second store now receives `${RVER:-$version}` even when the first download fails.
- The unused `apply_choices.py`, `chooser.py` and `community_diff.py` utilities and the dead chooser branch in `selection_writer.py` were removed; the removal and restore record is [REMOVED-2026-10.md](history/REMOVED-2026-10.md).
- The closed `CANDIDATES-2026-10-08.md` scout moved from onboarding to [history](history/CANDIDATES-2026-10-08.md), with inbound links repaired.

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

- **Owner:** phone test of the Telegram rahul9999xda smoke build (sign-in first). If sign-in fails with `API_ID_PUBLISHED_FLOOD`, the options are the owner patching HushTelegram on the phone with his own API ID, or approving `Bypass integrity check` (CONFIRM rule) in a later packet.
- Scan and pin-probe limits from the second review (LOW, recorded): the scan reads only the merged APK and loads each dex fully (fine on 16 GB runners); the pin probe's page parsing is heuristic and does not check Facebook's fallback `overrides.version_code`. Revisit with the first live evidence.
- New-provider ready PR: discovery, then the scan smoke, then a green test build, then a ready pull request the owner merges. W16y-b ships the scan step only; the orchestration is not built.
- Read the first runs: Council probe (Sunday 1 Nov morning), monthly digest (Needs you, 1 Nov), the post-merge pin check probe, retention preview (Monday 2 Nov). Then schedule the pin check weekly (reading pages the way the build does if plain reads are refused). Retention apply only with the owner's token, from 3 Nov.

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
- Closed in W16y-b: Amazon Music builds 26.36.1 again (De-Vanced v1.6.2 fixed its declared version; [onboarding/amazonmusic.md](onboarding/amazonmusic.md)).
- **Owner:** Instagram fallbacks are idle: HushGram v0.0.17 and oxbow v453 support only Instagram 453.0.0.55.79 (build 385914283), piko stays on the 452.1 pin. Giving the fallbacks their own 453 pin would let a fallback release lock piko out (publish_guard refuses an older version than the shelf). Options: wait for piko 453 (recommended), or allow a 453 fallback ([onboarding/instagram.md](onboarding/instagram.md)).
- MX Player fallback MightyMichs v1.12.0: "Unlock MX Player Pro" fails its fingerprint (Lxo;.j1()Z) on 1.93.4, the only version it supports. Record only; ftl stays primary; recheck on the next MightyMichs release ([onboarding/mxplayer.md](onboarding/mxplayer.md)).
- Status page red can be a nonpublishing smoke (Instagram oxbow run 40783288101, 28 Oct), not the release; the page reports the newest build job ([status.py](../../src/etc/status.py)).
- **Owner (optional):** File the upstream Obtainium issue using the text and steps in [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md); test same-version patch-only notification and installed-setting migration.
- Move the Instagram pin when piko supports build 385914182 or newer; keep the piko/brosssh held names for a provider update ([W15G-MAP.md](W15G-MAP.md); [instagram onboarding](onboarding/instagram.md)).
- Restore hoo-dles to prerelease when morphe-desktop stable reads its new bundles ([W17-BRIEF.md](W17-BRIEF.md)).
- Closed in W16y-b: Telegram rahul9999xda became the primary (watch row N-55429f removed).
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
