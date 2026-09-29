<!-- archived from assistant skill 'Providers and APK Sources', last updated 2026-09-24 10:21 (Asia/Calcutta), exported 2026-09-29 -->
<!-- summary: Load for provider, sources or bundle transport; preserves channel rules, exact-byte evidence, gated alternative pilot and PR68 shipped safety-doc boundaries. -->

# PROVIDERS-AND-APK-SOURCES

Reconciled 10 September 2026 against main 4bec910fef80c46c5affff2799ed5beec6245cf9. Load **Patch Factory Builds**; derive current inventory from src/targets.json, not a hand-maintained provider/count table.

## Selection and transport

Primary candidates and extra bundles serve different roles. Only candidates enter version election; an extra is not automatically a fallback. Current extras are Paresh GitLab + binarymend on truecaller-combo, brosssh on Instagram and Paresh GitLab on MX Player. Facebook's redundant meridianfresco extra was removed; Reddit uses adobo, not the old rushiranpise extra. Do not resurrect removed choices from an old table.

`resolve.sh` honors pin/ceiling and uses github_bundle.py to download the exact candidate bytes, then lists versions locally with -x -u. Build reuses the selected path/hash. Channels belong to each provider: Edge/Hotstar use latest at this checkpoint, most others prerelease. Current stable fallback and exact transport replaced older mismatched resolver/build downloads; monitoring readers are not all migrated. Inspect actual metadata rather than assuming upstream always publishes one channel/version.

The latest-stable patcher is intentionally not version-pinned. github_patcher.py checks exactly one all.jar against fresh GitHub expected size/digest plus ZIP/manifest/Main-Class, verifies cached bytes and downloads atomically with bounded attempts. A corrupt Key Mapper JAR exposed the old existence-only check; the failed bytes were unavailable, so its corruption mechanism was not proven.

extra_bundle.py/fetch_bundle.sh handle exact GitHub/GitLab extra assets, HTTPS/source scope, pagination where implemented, bounded download/expansion, CRC/path/duplicate/symlink checks and atomic retries. GitLab project 82031658 Paresh v1.20.0 supplied an opaque upload asset URL, not something to construct. Inspected metadata supplied no expected size/digest: local SHA is recorded but upstream verification is false. GitHub digest is a host transport anchor, not independent publisher authenticity. Do not assert arbitrary GitLab primary candidates are supported because extras work.

## Policy and metadata

Provider age is advisory, no bufferk expiry/date fuse. Read exact current patch output using -x -u so experimental/default-off entries are visible. Options are JSON arrays; required options/resources must exist. adobo's hosts blocker needed a filePathOption and hosts.txt, not an empty options array. Check actual declared options rather than reusing an old URL description.

Preserve owner approvals for GmsCore support, PoToken provider and Spoof video streams. Provider declared compatibility is not a successful patch/build/runtime guarantee. A patch name can be present yet fail, collide or be disabled. BANNED/CONFIRM substrings and approved exceptions remain separate from availability.

## APK sources and retained pilot

Current build chooses APKPure explicitly, otherwise APKMirror. Use verified app-scoped slugs/metadata from config and the actual download; Android TV and phone variants can share package IDs. A single 403 is not a permanent-block diagnosis. Owner browser evidence can resolve data unavailable to a public fetcher; never equate unavailable with nonexistent.

Alternative APK sourcing is retained OPEN work: pilot exact version/package/ABI/SDK and original-signer evidence before replacing a working source. Dormant Play helper requests current metadata using an SDK35 profile and lacks the requested-version contract; it is not a ready fallback. apkeep historically listed versions but one download produced no file, so require actual bytes, size/shape/identity checks. Do not blindly switch to newest Play/APKPure, replace containers or promise timing savings from an unmeasured curl_cffi suggestion.

## Discovery lessons

Scope wired-provider identity by target/package AND canonical host/repository. A generic morphe substring once hid new providers; a global wired set falsely marked Paresh wired to Hotstar. PR41 fixed code scope; issue #17 correction remains unposted. Preserve explicit cross-host aliases, not fuzzy authors.

Community JSON is a dated snapshot: inspect its actual bundles/store/compatibilities representation rather than assuming arrays or copying old counts. Existing discovery/generators/Dependabot should not be duplicated. Historical RookieEnough reference code can inform an adapter, not prove current capabilities. Never infer no phone provider forever from an old TV-only observation; SonyLIV/ZEE5 remain removed by owner decision.

## September 24 operational-doc boundary

PR68 shipped a bounded README/RECOVERY/SECURITY/OPEN-WORK and retention refresh on 19 September as main `60c59eade6d1aea936586a316e927bfa47aa5a70`. The old claim that all repo operational documents remain unapplied is stale: the refused 14-file proposal remains unshipped, but this exact eight-path PR68 scope did ship. RECOVERY now avoids routine Play Protect disable, uninstall-freely, one-backup and same-key/data guarantees; it remains documentation, not a restore-tested backup or phone proof. No deletion, dispatch, signing/source/selection/import or issue change shipped in that scope.
