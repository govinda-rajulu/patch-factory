<!-- archived from assistant skill 'Target SonyLIV', last updated 2026-09-24 10:23 (Asia/Calcutta), exported 2026-09-29 -->
<!-- summary: Load for SonyLIV or ZEE5 references; records completed retirement and selection/variant lessons without authorizing rebuilds, deletions or new targets. -->

# TARGET-SONYLIV

Reconciled 10 September 2026. SonyLIV and ZEE5 were already removed from configured targets as out of scope. **No pending deletion, rebuild or provider hunt is authorized by this skill.** Read **Patch Factory Builds** for current state.

## Retained lesson

An August SonyLIV failure persisted after an edit to exclude-patches because the selected failing name remained force-enabled through the then-current execution path. The useful lesson is to trace actual CLI selection construction and verify the final selected/applied set, not to promote that old mechanism into a permanent rule.

Current patch_target.py and `selections.sh` emit per-bundle -d and -e; same-bundle -d wins and preflight refuses overlaps. The old statement that exclude-patches is always dead on exclusive targets is not the current contract. Reconcile both files rather than blindly deleting or adding a name. Applied names/exit/failure evidence, not a no-op edit, proves behavior.

Older notes disagree about SonyLIV's store/compatibility/TV cause. Preserve the settled owner decision that the apps are unused/out of scope; do not claim both providers were necessarily TV-only. ZEE5's historical TV/phone mismatch shows why package identity alone may not establish intended form factor.

any_version can silently select a different store version and skip incompatible patches; SDK checks alone do not validate patch applicability. Identify the actual gate covering each hazard. Required requested names, failure status, final identity and owner approval are different concerns.

Historical paid-account rename/entitlement concerns are cautions, not proof a particular patch causes an account restriction. No unused target should be resurrected or safety policy changed without a fresh owner request and current evidence.
