# Micro-level audit: 27 September 2026

Line-level security and logic review of main `789d47a6` (after PR90). The review
looked for three things: concurrency and state, silent failure, and untrusted data
that crosses a file boundary without checks. Fixes ship in the same PR as this
record. `tests/audit_contracts.py` pins each fix, and every check has a negative
control built from a mutant of the real file.

**What this proves:** the source was read and fixed, and contract tests run in Validate.
**What it does not prove:** that the next scheduled build signs and publishes
correctly. The first daily run after merge is the runtime check. Phone behaviour
is untested.

## Fixed in this PR

| ID | Severity | File | Defect | Fix |
| --- | --- | --- | --- | --- |
| H1 | High | `src/build/check_sdk.sh`, reader 4 | If the three Android readers failed, the SDK gate ran an unpinned `pip install pyaxmlparser` from PyPI. At that point the job env held `KEYSTORE_PASS` and `KEYSTORE_ALIAS`, and `src/ks.keystore` was already on disk. Installing an unpinned package runs code from outside the repo. | Use the reader only if it is already installed; otherwise log that it was skipped. With all readers gone the gate still fails closed as `UNVERIFIED`. |
| M1 | Medium | `.github/workflows/manual-patch.yml`, job `env` | Signing password and alias were job-wide. Every step could read them: preflight, artifact download, source verify, the cache, setup-java and docker inside `preparing`, `connection.sh`, and `ncipollo/release-action` inside `release`. | Moved to the two steps whose code reads the keystore: **Patch apk** (build.sh signs; `artifact_identity.py capture-signer`) and **Verify finished APK identity** (`verify_final` re-exports the certificate). Release handoff is documented as needing no private-key reads, and the code confirms it. A contract walks the Python imports of every step without secrets. It fails if any of them reads a signing secret from the environment, calls a keystore reader, or builds the patch command without dummy credentials (`execution_inputs.py` passes `OMITTED`). |
| L1 | Low | `manual-patch.yml`, **Decode keystore** | `echo "${{ secrets.KEYSTORE_B64 }}"` pasted the secret into the generated script file. | The secret now arrives as step env; the script runs `printf '%s' "$KEYSTORE_B64" \| base64 -d`. |
| L2 | Low | `.github/workflows/keepalive.yml` | `git commit ... \|\| exit 0` turned any commit failure (identity, hooks, disk) into a green run. The monthly keepalive could then stop silently. | Exit quietly only when nothing is staged (`git diff --cached --quiet`). Commit and push failures now fail the run. |
| L3 | Low | `.github/workflows/watch.yml` | No concurrency group. A late schedule plus a manual run could both read-modify-write standing issue #27. | `group: nightly-watch`, `cancel-in-progress: false`. |
| L4a | Low | `.github/workflows/explore.yml`, **List patches** | `java ... \| tail -3` ran without `pipefail`, so a failed listing was hidden behind `tail`. | `set -o pipefail`. The jar path stays `${{ steps.patcher.outputs.jar }}`: our own verified-download step produces it, and `provider_watch_contracts` pins that exact text. |
| L4b | Low | `explore.yml`, **Open issue** | Provider-supplied patch names went into the issue body raw, so a name could `@mention` people or inject markup. | Names sit inside a `text` code fence, and backticks are replaced. |

`manual-patch.yml` and `check_sdk.sh` are in the input recipe. The first build after
merge therefore records new local inputs. That is expected, and it is shadow-only.

## Checked and rejected

- **Notifier and community markers "have one space".** This came from a fetch tool
  that strips HTML comments. The real markers are `<!-- pf-community:KEY -->` and
  `<!-- pf-notify... -->`: the separate notifier issues #65, #69 and #72 existed,
  and the community delivery read back 3 parts.
- **Nightly report "always UNKNOWN".** Reasons are appended only on real conditions.
  Nightly run 36301957919 on 27 September finished `PARTIAL`, as designed.

## Deferred, with reasons

| Item | Why not now |
| --- | --- |
| `add-target.yml`: unvalidated provider name/ident in paths, direct push to main outside `main-writer`, `jq -e . && mv` continuing on failure | Owner-only dispatch input. It needs its own reviewed packet against exact bytes. |
| `utils.sh` ignores some unzip/APKEditor failures and reuses `download/` | CI always uses fresh checkouts, and later gates recheck the APK. The file (31 KB) was not read end to end. |
| Extra-bundle `curl --location` without a final-host pin | The provider already controls the bytes, and pinning unknown CDN hosts risks breaking extras. |
| Identity TOCTOU on paths, non-atomic GitHub bundle receipt, duplicate JSON keys in release-note decode, no size cap in `verify_output` | Same runner, same run. There is no cross-trust boundary, so this is hardening only. |
| `GITHUB_TOKEN` is job-wide in `manual-patch.yml` | Resolver, fetch and release steps all need it. Scoping it is a larger change. |
| `poll.sh` reads only the first releases page | It already fails closed as `UNKNOWN`. |

## Issues

| Issue | Decision | Evidence |
| --- | --- | --- |
| #27 Nightly watch status | **Keep open.** A standing issue, rewritten by every Nightly run. L3 now stops two runs from racing on it. | By design, `src/etc/watch_issue.sh` |
| #35 ES File `Remove Debug Info` failure, 6 Sep | **Close as completed (mitigated).** The patch is in `src/patches/QUARANTINE`; it is not fixed upstream. | ES File published after the failure on 10, 11, 12, 13, 16 and 21 Sep (`es-file-v4.4.3.7` tags) |
| #5 anddea YouTube Explore report, 19 Aug | **Close as not planned.** A stale Explore output for a provider this repo does not use for YouTube (morphe is configured). | `src/targets.json` |
| #82, #83 | Keep open: the community report, and provider deltas that need owner classification. | |

## Coverage limits

- Read line by line: the build chain (build.sh, check_sdk.sh, artifact_identity.py,
  release_contract.py, input_recipe.py), all workflows, both composites, the watchers.
- Read in part: `utils.sh`, the lower half of `docs/portal.js` (the rendering code),
  and the tail of `shadow_inputs.py`.
- No APK, signing or dispatch was run for this audit. The contract tests are
  source-level; the first scheduled build after merge is the runtime check.
