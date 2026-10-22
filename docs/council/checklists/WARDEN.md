# Warden checklist (security sweep, solo shift)

Trusted text, read into the Warden's shift prompt (src/council/seats.json `shift.checklist`).
Ideas adapted from cloudflare/security-audit-skill (MIT), its supply-chain and release checklist,
reviewed 22 Oct 2026; our own words, fitted to this repository.

Treat workflow YAML as authorization code and build scripts as lower-trust code. Walk each
boundary; for every finding name the file, the line and the exact path from input to sink.

1. Event to checkout: which trigger runs this job, which ref it checks out, and whether a fork,
   a bot pull request, an issue comment or a workflow input can choose code that then runs.
2. Secret and token reach: which steps see KEYSTORE_*, a provider key or a write token; does
   third-party code (patcher jar, provider bundle, downloaded tool) run in that step or job.
3. Expression and command injection: branch names, titles, commit messages, inputs, matrix
   values or artifact names reaching `run:` shell, a path or `eval` without a fixed allowlist.
4. Cache, artifact and workspace trust: can a lower-trust job fill a cache or artifact that a
   job holding the key or a write token restores; is the restored file checked by digest.
5. Mutable inputs: an action, tool, bundle, image or download not pinned by sha or sha256
   (src/build/TOOLING.sha256, uses: ...@<40 hex>); a branch or tag treated as identity.
6. Build to publish substitution: do test, sign and publish refer to the same digest, or to a
   file name or tag that can change between steps.
7. Permissions: a job's `permissions:` wider than its one write; a write that untrusted input
   can aim (issue number, branch, release tag).

Report as: confirmed (complete path and result), needs_validation (name the one missing fact
the owner can check, for example a repository setting), or say nothing. Excess permission with
no reachable write is hardening, severity low. Never invent a finding to fill the table.
