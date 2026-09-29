<!-- archived from assistant skill 'Workflows Hygiene and Environment', last updated 2026-09-24 10:22 (Asia/Calcutta), exported 2026-09-29 -->
<!-- summary: Load for workflows or hygiene; separates shipped Plan/notifier/docs/runtime repairs, schedule evidence, PR53 gaps, governance and cleanup limits. -->

# WORKFLOWS-HYGIENE-AND-ENVIRONMENT

Reconciled 19 September 2026 against main `3a855e5bb93ca6cc2580c7e9db4006b68f7b96f0`. Read **Patch Factory Builds** and **Solo Repo Engineering**. Use personal Cloud Shell and fresh isolated checkouts; never assume a Codespace or issue-script executor.

## Inventory, schedules and shipped corrections

The reviewed workflow inventory has add-target.yml, agent-watch.yml, batch-patch.yml, ci.yml, community-watch.yml, explore.yml, keepalive.yml, manual-patch.yml, notify-failure.yml, validate.yml and watch.yml. Re-derive it from live source before future edits. PR52 changed Batch Patch's display prefix to9; the old duplicate6 complaint is fixed. Display numbers are not filenames.

ci.yml polls opted-in enabled targets daily12:30UTC/18:00IST and can publish independently. Agent watch runs Monday07:00UTC, community watch Monday03:00UTC, Provider watch nightly02:00UTC, keepalive monthly day1 at02:00UTC. Re-read exact current schedules before changing them. Late or absent results at one query time do not establish a disabled schedule or a cause for delay.

PR51 made Batch planning strict and delivered test APK/evidence when publish=false. Keep max-parallel=6 unless measurement justifies changing it. Batch34870190849 produced14 target APK/report pairs, checked by the owner's collector. Nonpublishing evidence is not a Releases-page publication or phone test. Prefer coherent approved batches, not dispatch storms; match run/ref/head/target and verify the changed stage actually ran. Reruns retain the original commit.

PR52 shipped full Nightly report/enforcement. PR57 shipped typed exact daily Plan coverage and malformed-resource refusal. Missing/duplicate/disabled/malformed target evidence must not become a healthy zero matrix. PR59 added advisory Plan declarations, consumed-input comparison and publication receipts without replacing legacy build selection. F05/F06 dynamic pre-resolution/reuse and durable baseline trust remain partial.

PR58 replaced truncated failure reporting with metadata-only complete job pagination, exact run/attempt identity and deduplication across issue states. Batch is included; the first-three-failures truncation is removed. It does not expose raw logs, check out untrusted code or expand permissions. Future matching reports were owner-approved. Local REST-mocked entrypoint tests passed; no deliberately failed live notification test was dispatched. These shipped notifier fixes do not prove full monitoring coverage.

## Latest observed scheduled evidence

[Run35369326453](https://github.com/govinda-rajulu/patch-factory/actions/runs/35369326453) completed successfully on exact3a855e5b. All five jobs were inspected: Plan plus YouTube, AdGuard, Prime Video and Facebook; meaningful shadow, identity, handoff and release stages passed. Start was18September16:34:59UTC/22:04:59IST. Cause of delay is unknown. The query returned no19September run at that moment, not proof the schedule is disabled.

YouTube release metadata includes a1057-byte shadow receipt. Its body download failed; no fresh receipt/APK bytes or phone test was completed. Composite success cannot prove every continue-on-error substep. Weekend MX recovery on unchanged main4bec910f predates PR48 and cannot validate its failed mandatory-session experiment or diagnose the earlier403.

## Remaining coverage and governance

Provider watch/namecheck/headroom/Explore/review still need a common expected-versus-checked coverage/error contract, including GitLab, extras, defaults and malformed/missing results. Unreadable or zero coverage is not healthy. Structured deltas and meaningful action options on the existing page remain requested; issue text/run links are only partial delivery.

The approved19September page candidate reads each relevant workflow independently, preserves partial Watch evidence and stops validation runs crowding the Builds window. It is locally tested and handed off, not yet confirmed merged/deployed. It does not fix producer coverage, authorize workflow dispatches or turn the page into a writer.

Add-target/schema/disabled-dropdown semantics remain open. PR53 major-action compatibility is separate: recheck its current exact head and full logs for all five action migrations before repair. The previously observed v4-to-v7 upload-artifact contract failures do not authorize weakening tests. September18 effective main rules showed deletion/non-fast-forward protections but no required CI; protected=true is insufficient. Authenticated enforcement/bypass inspection and any settings changes are separate work, not authorized here.

Validate includes shared preflight, three regression suites, shell syntax/shellcheck and generator/policy checks. YAML parsing is not actionlint, and either is not runtime caller/callee permission evidence. Green after skipping all meaningful work is not a pass. Validated moving JAR/cache transport is already implemented on the build path; other readers may differ. Measure cache/timing improvements instead of promising historic savings or replacing containers without evidence.

## Read CI and failures correctly

Read exact run/jobs and full failing logs, checking timestamps/head/completeness. `gh run watch` is status, not failure logs; use the exact failed run when reading logs. Do not assume job-log endpoints follow redirects or return ZIPs. Paths may contain spaces; inspect actual files. Run-list output does not provide all jobs. Batch reads and bound polling; never watch an unrelated green run after dispatch refusal.

Short time-to-failure is a clue, not a diagnosis. Preserve raw evidence when grep/head/tail would hide earlier403s. Personal and repository token quotas differ; inspect actual bucket/response. Never print credentials or signing argv. A provider failure in one client/network/session context does not prove global outage or permanent blocking.

## Hygiene and completed cleanup

Retain `src/patches/_attic` and deliberately dormant helpers. Unreferenced is not deletion permission. `report.sh` fast/full is useful only when coverage/error semantics are checked; stored hooks/settings are not necessarily active in a fresh checkout.

Historical cleanup after PR47 removed exactly six approved refs with checked tips/ancestry, restore points, atomic push and leases. Later PR55 closeout removed exactly five approved branches for PR47/48/51/52/54 after restore-tested Git backup; owner confirmed download. These are separate dated batches, not current branch inventories or standing permission. No releases/tags/APKs/local directories were deleted. Recovery snapshot predates PR56 onward and needs refresh. Any new cleanup requires fresh preview, restore evidence and approval.

Keep existing work/dirt untouched; stage exact paths. Check effective Git config when commits fail: Everything up-to-date after a failed commit is not success. Do not disable signing globally, sweep scratch tools into staging or wipe user work. Earlier Codespace exhaustion is history, not today's route. Verify actual checks after token-created PRs. Obtain apksigner from actual Android SDK tools, not a package parser substitute; current quotas/prices/tool capabilities require current evidence.

## September 24 workflow reconciliation

PR60's page/MicroG scope is complete and retired. PR68 shipped the bounded operational-document/retention work, and PR62/PR63 later repaired six major actions, grouped policy and release-note presentation. Do not use those later repairs to declare PR53 closed: its final disposition was not evidenced in the supplied records. Recheck exact PR identity/current head/full logs only if PR53 remains relevant; no workflow dispatch, settings write or issue mutation is authorized by this note.

PR70's one acknowledged 13-target publishing dispatch stopped before publication verification. Do not redispatch `35571131023` attempt 1 or infer qualified baselines. Historical false `merge_attempted=false`/deletion flags were reporting defects; correct reports prospectively without rewriting old RESULTs.
