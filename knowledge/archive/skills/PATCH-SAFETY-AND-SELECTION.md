<!-- archived from assistant skill 'Patch Safety and Selection', last updated 2026-09-24 10:21 (Asia/Calcutta), exported 2026-09-29 -->
<!-- summary: Load before patch selection changes; preserves approvals, per-bundle semantics, resolved ES/MX exclusions, YouTube decision and account-risk limits. -->

# PATCH-SAFETY-AND-SELECTION

Reconciled 10 September 2026. Load **Patch Factory Builds** for current state. Separate configured, applied, explicitly approved and device-tested states; none implies the others.

## Current rules

Read live BANNED/CONFIRM/EXCEPTIONS/QUARANTINE, exact provider bundle output with -x -u, both include/exclude files and actual Applied names. BANNED and CONFIRM are lowercase SUBSTRING policies, not exact-name sets. Exceptions are explicit per directory/name; do not invent an exception from a general preference. CONFIRM requires owner judgment, not an agent's recommendation.

The actual selection writer reconciles both files, preserves question-mark decisions, validates banned/quarantined names and stale directories, checks cross-bundle requested-name collisions, and stages before replacing. The expected unchanged review round trip is zero modifications. It does not establish a complete effective/default approval system or decide CONFIRM choices.

Per-bundle -e and -d bind to the nearest preceding -p; same-bundle -d wins. Do not call exclusions a global deduplication mechanism, or claim they are always dead under exclusive. Inspect the exact active argv. One requested name under two selected bundles is refused. An empty extra include is not universally inert: provider defaults and exclusive scope determine behavior. Adding a second bundle can collide despite different patch names.

## Owner decisions and unresolved selections

PR47 excludes exactly **Remember live stream playback position**. Its YouTube-only smoke retained the other 62 applied names. This does not remove all live-stream features. Preserve GmsCore support, PoToken provider and Spoof video streams approvals.

DECISIONS-youtube-morphe.tsv still says IN for the old spelling Remember livestream playback position. Its edit was refused and not bypassed. Do not reapply that stale row, claim reconciliation, or confuse an unmerged local approval candidate with shipped code. The broader effective/default approval gate is OPEN.

**Six CONFIRM selections are already configured, with approval unresolved:** APK Junk Cleanup, Remove Duplicate Graphics and Remove Languages in each of esfile-ftl and mxplayer-ftl. Do not describe them as inactive. Do not silently disable or approve them. Record the gap and obtain the owner's specific decision before changing enforcement/selections.

Remove Debug Info remains quarantined in both FTL directories after IllegalAccessException against FfmMappedFile. Mitigated by exclusion does not mean upstream fixed. Reddit Morphe and parked extra providers still need explicit reviewed selections and collision tests.

## Diagnostic lessons

- Applying N counts selected patches. Applied names plus exit/SEVERE checks establish execution. A lower selected/applied count is a diagnostic, not proof of one specific collision mechanism.
- Skipping disabled: X (default) describes provider defaults; without (default), a selection flag disabled it. Do not equate skipped count with exclude-file length.
- A supported app version is not a guarantee every patch works. Silent non-selection, explicit disablement and actual patch exceptions need different evidence.
- Test fresh store input, not an already-patched release: a historical Instagram re-patch created meaningless fingerprint failures.
- Do not enable a repository-wide COE variable casually. If authorized, isolate diagnostics, preserve/restore the prior setting and require publish=false and final failure gates; inspect current behavior rather than trusting old COE claims.
- Generate state and advice in separate columns. A writer once erased untouched undecided rows and emptied exclusions because advice markers doubled as state.

## Account and variant risk

The historical Hotstar account restriction followed patch changes; which change caused it was NOT proven. Owner later reported using the web version. Current nonpublishing CI does not prove renewed on-device use or account safety. Do not remove dependencies or add identity/entitlement patches without understanding purpose and owner intent. Client-only is not a blanket safety certificate; names alone do not prove what a server observes.

TV and phone variants can share package IDs. Read descriptions, compatibility and actual artifacts. SonyLIV/ZEE5 are removed/out of scope; do not collapse inconsistent historical technical explanations into a new fact. Changing package/signing/data behavior is an owner decision. The owner deferred new phone testing until engineering is finished and time allows.

## September 24 owner-decision reconciliation

Supersedes the older unresolved-CONFIRM wording above for these six names. On 19 September the owner said he did not know what the patches did and delegated judgment. The reviewed decision is to **exclude** APK Junk Cleanup, Remove Duplicate Graphics and Remove Languages in both esfile-ftl and mxplayer-ftl, because the resource reduction trades languages, deduplicated graphics and license/assorted assets against the owner's reliability-first goal.

PR70 shipped that exact exclusion configuration and the resource-decision record. Preserve it as an explicit exclusion decision, not as approval to apply the patches, not as proof old APKs were broken, and not as device/runtime evidence. Do not treat this scoped decision as blanket authority for future patches or cleanup.
