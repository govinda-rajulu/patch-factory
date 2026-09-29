<!-- archived from assistant skill 'Build Chain and Gates', last updated 2026-09-24 10:22 (Asia/Calcutta), exported 2026-09-29 -->
<!-- summary: Load for build, resolver, identity or fingerprint work; preserves fail-closed gates and the PR61/PR64 groundwork without claiming full F05/F06 closure. -->

# BUILD-CHAIN-AND-GATES

Reconciled 10 September 2026 against `4bec910fef80c46c5affff2799ed5beec6245cf9`. Load **Patch Factory Builds** for checkpoint/evidence and recheck live source before editing.

## Current execution contract

`src/build/build.sh TARGET` invokes shared preflight, refuses reused release output, captures the pre-build signing certificate, validates the latest patcher JAR, resolves a candidate to exact bundle bytes, stages numbered extras, prepares per-bundle selections, downloads an APK, checks package/SDK and captures input evidence. The active patch route is **patch_target.py**, a subprocess argv array without shell eval, not the old split_arch route. It refuses ambiguous JAR/bundle inventories and compares its ledger with `selections.sh`. Never print its argv: it contains signing passwords.

Patcher nonzero exit, zero applied names, missing/wrong patcher package, SEVERE failure and missing explicitly requested names refuse release. Distinct requested names are checked, not only counts; duplicate requested names across bundles fail before patching. Empty YouTube includes still leave effective/default approval enforcement OPEN. The count condition is not a claim that all output dependencies have been owner-approved.

The real module is **src/build/artifact_identity.py**, not apk_identity.py. It captures inputs, reads actual manifest/version/SDK, checks native content and cryptographically verifies the final APK signer against the captured CI certificate. verify_output.py and the workflow's finished-identity check cover final output; release_contract.py binds exactly one checked APK/report/path/hash to the release consumer. These are different gates, not one filename-exists test.

## Versions and downloads

Honor target pin and max_app_version ceiling. Current `resolve.sh` downloads an exact GitHub bundle, lists versions locally with -x -u, refuses failed listing rather than falling back, chooses supported versions within the ceiling and uses patch count/publication date as tie-breakers. A successful but unparsable version listing can use a configured ceiling with applicability explicitly unverified until patching. No ceiling and no parseable version means no candidate. Provider age WARNS; no date fuse. Do not assume every provider always exposes exactly one version.

Build uses the resolved path/hash rather than downloading the winner again. Exact input APK metadata corrects release version: Prime Video's store value 3.0.452 differed from actual 3.0.452.257. near_version/store navigation is not a safety guarantee. Unknown package/SDK must not be silently accepted; final input/output identity evidence matters.

## Lessons retained

- A manifest fallback that assigns the expected package to the observed package is tautological. Replacing it with a sentinel without testing real readers can reject valid downloads; test both real-format positives and negative fixtures.
- Applying N is selected work, not completed work. Use actual Applied names and exit/failure evidence. Duplicate Facebook names once inflated counts while adding no coverage.
- Facebook contains DEX and ZIP bytes named .so. Classify content, require appropriate bounded validation and exact input/output equality. DEX is executable bytecode; preserved bytes are not runtime-safety proof.
- SDK37's observed V3.0 signer labels differed from the legacy parser. Support measured formats, never weaken verification to get green.
- A release consumer can reject correct upstream output. Read the handoff consumer before designing a producer gate.
- A no-op edit proves nothing about correctness; print actual field values. Do not use literal zero as an empty version placeholder.
- Test the changed stage with a case that reaches it. Full logs beat a truncated diagnostic filter.

## Boundaries

Read actual target ceilings; Facebook is 30 versus 29 for the other current targets. arm64 naming does not establish installability on every phone. Current CI signer match does not prove original publisher authenticity or historical installed-app continuity. Shared preflight does not prove malicious-runner isolation. Dormant vendored helpers are not all refactored. No full local Android build is implied by Python fixtures; actual CI and phone evidence are separate.

## September 24 fingerprint boundary

PR57 typed Plan, PR59 connected shadow receipts, PR61 dependency reuse/qualification groundwork and PR64 prepared subset comparison are stages, not full F05/F06. They do not establish exact source-APK/runtime/transitive/effective-default closure, a durable qualified baseline independent of expiring run metadata, or authority to skip real builds. PR70's exclusions are selection/resource policy, not fingerprint completion. Use the queue's full producer-to-consumer acceptance contract before any next engineering packet.
