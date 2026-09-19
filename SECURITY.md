# Security and trust boundaries

Patch Factory fetches third-party Android APKs and patch bundles, modifies APKs,
signs them with its configured CI key, and can publish them. Checks reduce
specific failure modes; they do not establish that every input, patched app,
runner or account interaction is safe.

## Inputs and checks

| Input | Existing control | Remaining boundary |
| --- | --- | --- |
| `pup` and APKEditor | SHA-256 entries in `src/build/TOOLING.sha256` | Pin review and upstream provenance still matter |
| Patcher | Validated latest-stable GitHub asset, size/hash when supplied, archive/Main-Class checks and cache verification | Moving version is intentional; host metadata is not independent authenticity |
| Primary and extra bundles | Exact selected bytes reused; validated GitHub/GitLab transport and bounded archives | Providers can change code/defaults; some upstream assets lack an advertised digest |
| Store APK | Container, package, minimum Android API and finished-output checks | Original publisher identity, exact source availability and device behavior are separate questions |
| Prepared dependencies | Same-run packet identity and consumed-byte checks | Full source APK/runtime/transitive semantic coverage remains incomplete |
| Patch selections | BANNED/CONFIRM substring rules, quarantine, per-bundle binding and requested/applied checks | CONFIRM warns; unresolved owner choices and effective/default approval coverage remain open |
| Finished APK | Manifest/native-payload/signing identity and checked release handoff | CI signer is not original-publisher or installed-app signer proof |

Do not infer provenance from a filename, matching timestamp, same patch names,
or the presence of a publication/qualification JSON file. Retention recognition
is metadata classification only. Qualified baselines are repository-bot
evidence, not independently signed or owner-immutable attestations.

## Signing and permissions

Signing material is supplied to trusted build jobs through Actions secrets and
decoded on the runner. It is not stored in Git, but saying it "never leaves the
owner" would be false. Protect the runner, workflow code, dependencies, logs and
secret configuration accordingly. GitHub secrets are not a retrievable backup.
See [RECOVERY](RECOVERY.md) for a separate, nonpublishing restore process.

Read-only diagnostics must not inherit signing credentials. APK build jobs have
signing access, and publication/qualification jobs require write permissions.
Review permissions and consumers per workflow; a top-level declaration alone
does not prove least privilege or complete isolation. Required-check and bypass
settings must be inspected separately from repository source.

Use reviewed PRs and exact-head validation, not direct-main pushes. Do not feed
untrusted event text into shell commands, trust a fork artifact as a signed
baseline, or grant an agent broader permissions to bypass a failed gate.

## Transport diagnostics and logs

Store downloads now suppress the observed wget URL logging path. Page probes
emit bounded counts/booleans rather than raw HTML, cookies or signed URLs.
These are scoped controls, not a claim that all historic logs or third-party
tools are sanitized. Treat existing logs as potentially sensitive and avoid
reposting signed download URLs.

HTTP 200 is not download success. A challenge/unavailable marker is a heuristic,
not a diagnosis. Do not weaken source/version/signature gates to bypass a
download failure. A patch count does not establish behavioral compatibility.

## Distribution and device risks

Modified APK redistribution can be restricted by licensing, service terms and
applicable law. Review rights before publishing or promoting a build; technical
success does not grant distribution permission. Do not claim that releases in
a public GitHub repository can be made individually private.

Account restrictions and device/data loss remain possible; timing alone does
not prove which patch caused an account action. Avoid guarantees that a patch
is undetectable, a same-key update preserves data, or a checksum makes software
safe. Never recommend routine uninstall, data clearing or device-protection
bypass to force an update.

Obtainium imports require user confirmation and may replace tracking settings.
MicroG is optional upstream software, not a build signed here. A new same-version
release does not necessarily trigger an Obtainium update.

## Reporting

Use a minimal public issue only for non-sensitive reproduction details. Do not
post keystores, passwords, tokens, signed URLs, raw private logs or personal
backup locations. This repository has no stated private disclosure channel or
service-level guarantee. Suspected exposed credentials need scoped containment
and rotation planning, not a public dump of the evidence.
