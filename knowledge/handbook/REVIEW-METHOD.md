# Review method (every packet and every handover export, all repositories)

Written 26 Oct 2026 at the owner's request to give every repository the same review method.
The SOLO-REPO-ENGINEERING skill points here. Repository-specific round logs live in
that repository's own review records (patch-factory: docs/review/REVIEW-METHOD.md).

## Order of work

1. **Evidence first.** Read the live repository and the owner's bundle; for a red run, read its
   log or artifact before naming a cause. A probe comes before a patch; a probe's isolation is part
   of the test (run it once against the real tool).
2. **Inventory, then shards.** List the population (files, workflows, open items, facts) and split
   it so each agent can finish its shard: one folder, one file family or one workflow per agent.
   An agent given a whole repository runs out of steps after the files it reaches first.
3. **One lens per agent.** Security, behaviour, cross-file (shared resources: branches, concurrency
   groups, tokens, issue writers, files two jobs write), staleness, fact check, open items, fresh
   chat simulation. Agents never saw the chat: the brief carries scope, intent to verify, and the
   report format.
4. **WH findings.** Each finding states what (file:line and a short quote), why it matters, how it
   was shown (command and output, or an official doc and quote), and the exact fix, with a
   severity, plus a "checked and fine" list and a "not covered" list.
5. **Re-rate before applying.** Agents overclaim. Every HIGH is re-read against the code; a HIGH
   must break a run or a security property in practice. Wrong agent claims are recorded, not used.
6. **Live-verify** what can be checked live (pins, digests, run results, issue comments) through
   official sources; say UNVERIFIED when it could not be.
7. **Fix, then review the fixes.** New text is where new errors are: a fresh round reads the
   diff of the fixes and the final commit.
8. **Exit rule.** Done when fresh reviewers find no HIGH or MED item on the final commit. Then the
   full suite, the controller rehearsals and a launcher built from that exact commit.
9. **Handovers use the same method**: the export is frozen, then independent reviewers check it
   (open-item miner, fresh-chat simulation, fact checker, staleness sweep) until the exit rule.

## Habits the method replaced

- The author checking his own work and stopping when his own checks pass.
- Partial checks reported as full (a test file run as a script that ran zero tests).
- Stating an impact before reading the population it claims to describe.
- Guessing a failure cause from the shape of the job instead of its stderr.
