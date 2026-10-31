# W15g signing-split adversarial scenario report

Scope: attacker controls every byte in the Patch artifact (`handoff/` after download). I ran the new
scenario tests with local fake `apksigner`, `zipalign`, `aapt2`, and `keytool`; no real Android SDK,
network, or private key was used. Existing `tests/signing_split_contracts.py` was treated as baseline
coverage and not duplicated.

## Results

| ID | Attack | Expected refusal point | Actual | Result |
|---|---|---|---|---|
| A-01 | Replace the release APK after the Patch identity report | `sign_apk.handoff`: exact path/bytes/SHA-256 | Report/output mismatch is refused | PASS |
| A-02 | Reuse a different run ID or run attempt | `handoff` and later signing evidence binding | Run/attempt mismatch is refused | PASS |
| A-03 | Reuse an APK/report from another source commit | `handoff` source-commit check | Different `HEAD` is refused | PASS |
| A-04 | Supply two APKs, an APK symlink, or a pre-existing destination folder | `place`/`one_apk` fresh-checkout checks | Ambiguous/link/existing destination is refused | PASS |
| A-05 | Carry an unexpected file, `..`-style path, or symlinked metadata | `place` staged-file allowlist | Unexpected names and symlinks are refused | PASS |
| A-06 | Carry an APK filename containing a newline/control character | `place` staged-file allowlist | **Before fix:** accepted; later release validation rejected it. **After fix:** refused at `place` | FINDING (fixed) |
| A-07 | Use a hardlink to a file outside the hand-off | `place` file movement and fresh checkout | Hardlinks are not explicitly rejected, but `os.replace` moves the hand-off name only; no outside path is written and no secret exists yet | PASS (hardening opportunity) |
| A-08 | Upload a sparse/huge APK or JSON to exhaust Sign disk/CPU | `place` bounded file-size check | **Before fix:** no bound; Sign would accept/hash it. **After fix:** files over 512 MiB are refused before hashing/tools | FINDING (fixed) |
| A-09 | JSON odd types, duplicate/NaN-like values, or malformed identity fields | report parsing and strict field comparisons | Type/key errors are caught; no attacker text containing test secrets reaches errors | PASS |
| A-10 | Abuse `src/targets.json` with arbitrary candidate/view JSON | `place` recomputed `build_attempts.view_text` comparison | Only checkout bytes or the committed candidate’s recomputed view is accepted | PASS |
| A-11 | Use target/view path traversal to write outside checkout | `place` root and carried-view checks | Traversal-like carried content is refused; no outside file appeared | PASS |
| A-12 | Put shell syntax, newlines, or `${{ secrets.KEYSTORE_PASS }}` in dotfiles/patch names | `release_contract` single-line/summary validation and multiline output delimiters | Control characters are refused; expression-looking text remains literal output data, not recursive Actions evaluation | PASS |
| A-13 | Make fake `apksigner` fail or throw credential-looking output | `sign` exception path and redacted subprocess errors | Keystore is deleted; raw tool output/argv/password/alias is not printed | PASS |
| A-14 | Leave `KEYSTORE_PASS`/`KEYSTORE_ALIAS` in Verify or leave `src/ks.keystore` | `verify` secret-environment/file checks | Verification refuses both conditions | PASS |
| A-15 | Sign with another certificate, multiple signers, v1/v3/v4 mismatch, or altered/reordered/non-signature ZIP bytes | `check_keystore_pin`, signer parser, schemes, `compare`, alignment and metadata checks | All tested variants refuse; fake v4 and second signer do not pass | PASS |
| A-16 | Add a v3.1/extra signer identity or unknown scheme line | strict signer/scheme parsing | Unrecognized or extra identity/scheme is refused | PASS |
| A-17 | Publish under another target’s prefix/package or wrong APK suffix/version | `release_contract` target/package/version/architecture/filename checks | Prefix, package, suffix, version and architecture must match committed target/report | PASS |
| A-18 | Fabricate a valid run/attempt suffix with a wrong date (wrong release tag) | Publish `--github-output` tag binding | **Before fix:** `verify_run` accepted any valid date, so same-run wrong-date tag reached output. **After fix:** date must equal Patch `PF_BUILT_AT` | FINDING (fixed) |
| A-19 | Use legacy date-only suffix to bypass run binding | Publish `--github-output` `verify_run` gate | Publish rejects legacy suffix; Sign’s non-publishing metadata check may read it, but it cannot reach the write-token action | PASS (legacy compatibility remains non-publishing only) |
| A-20 | Overwrite an existing release/tag or another app’s release | release action configuration plus contract | `allowUpdates: false`, `replacesArtifacts: false`, target prefix uniqueness/preflight; no overwrite path | PASS |
| A-21 | Make shadow evidence authorize a changed build or skip required checks | shadow evidence consumers | Shadow is explicitly diagnostic; Sign/Publish require real signed identity evidence and do not use shadow to skip | PASS |
| A-22 | Put secret-looking text into provider/patch metadata and inspect GITHUB_OUTPUT/body/name | `output_text`, `release_notes.checked`, fixed multiline delimiters | Values are bounded/literal; no key/pass value is derived or emitted | PASS |
| A-23 | Produce a different signer at verify time, or reintroduce the keystore between steps | `verify` no-secret/file checks plus pinned certificate | Refused | PASS |

### Finding severity and fixes

1. **A-06 — LOW (fixed): control-character hand-off names.** Before the fix, `STAGED` used `[^/]+`,
which included newlines and other control characters. This did not reach a publish because later
release-note filename validation rejected it, but it allowed attacker-controlled names into Sign
filesystem/log paths and weakened the boundary. Smallest fix: restrict every staged filename to
`[A-Za-z0-9._-]` in `src/build/sign_apk.py`.

2. **A-08 — HIGH (fixed): unbounded hand-off files.** Before the fix, `place` enumerated and moved
attacker-controlled files without a size limit; `handoff`/Sign then hashed and passed them to tools.
A sufficiently large artifact can consume the Sign runner’s disk/CPU and prevent publication. Smallest
fix: reject any staged component over 512 MiB before any move/hash/tool invocation. This is a resource
exhaustion finding, not a secret disclosure or wrong-APK finding.

3. **A-18 — BLOCKER (fixed): wrong-date release tag.** The Patch job controls `.tagsuffix`. The old
Publish gate checked only the run ID/attempt embedded in a 34-digit suffix; it did not bind the date
to the immutable Patch `PF_BUILT_AT`. A malicious artifact could therefore publish the verified APK
under a fabricated same-run date tag. Smallest fix: in `release_contract.py --github-output`, require
a valid `PF_BUILT_AT` and compare its UTC date with the parsed suffix date before writing
`GITHUB_OUTPUT` for the contents-write release action.

The fixes are in a separate follow-up commit after the test/report commit. The focused scenario suite
passes after the fix:

```text
Ran 9 tests ... OK
```

The existing signing-split suite also passes (`Ran 40 tests ... OK`), and the broader identity
collection passed (`Ran 332 tests ... OK`).

## Before-vs-new packet assessment

- **Also possible before W15g (single-job design):** provider-controlled output could already have
attempted metadata/tag/name injection, oversized artifacts, malformed ZIPs, signer/scheme tricks,
and path/symlink tricks. In a single job the provider additionally ran in the same job that held the
keystore/write-capable context, so any code execution or process/filesystem escape was intrinsically a
higher-impact threat. Existing tests and this report cover the data-boundary variants.
- **New with W15g:** the inter-job artifact boundary, exact unsigned-output binding, run/attempt
binding, explicit no-secret Verify gate, signer-pin check before `apksigner`, and keystore cleanup
finally make the hand-off-specific substitution/secret attacks testable and blocked. The A-06/A-08/A-18
findings were introduced or exposed by the new artifact/metadata hand-off paths; they were not
meaningful single-job inter-job attacks.

## Limitations

This is not an independent attestation against a malicious runner, compromised GitHub Actions,
compromised official SDK tooling, or a provider that can exploit a separate runner/kernel bug. The
fake tools test argv/environment and refusal behavior, not Android cryptographic validity. GitHub’s
own expression evaluation and release-action implementation were checked from the pinned workflow
configuration, not executed against GitHub. Hardlinks are accepted by `place` but do not provide an
outside write in the fresh-checkout sequence; rejecting them would be additional defense-in-depth.
