# patch-factory knowledge base

Moved into the repo on 29 Sep 2026 because chat sessions are deleted daily. This folder is
**history and lessons, not facts**: `AGENTS.md` still applies ("facts you may not rely on:
anything you remember, and any number typed into prose"). Generated, CI-gated files win.

## Read in this order

1. `../AGENTS.md`: hard limits and the selection rules. It overrides everything here.
2. [WORKING-AGREEMENT.md](WORKING-AGREEMENT.md): how work is handed to the owner, gates, privacy.
3. [STATE.md](STATE.md): the latest dated checkpoint and where to start.
4. `../docs/review/OPEN-WORK.md`: what is actually open (CI-checked phrases).
5. The newest `../docs/review/SESSION-*.md`: per-session records (closed ones in
   `../docs/review/history/`).
6. `../docs/council/LESSONS.md`: numbered lessons the council reads by tag (hash-pinned in
   `tests/council_contracts.py`; append only, never edit an entry).
7. [LESSONS.md](LESSONS.md): cross-session lessons that are not in the council file.

## Reference

- [handbook/](handbook/): the owner's general engineering handbook (verification, gates,
  repo writes, CI diagnosis, scope, handovers, free LLM agents). Same files in openskip.
- [archive/skills/](archive/skills/): the assistant skill notes this knowledge came from,
  verbatim, written between 23 and 29 Sep 2026. **Historical**; see
  [archive/README.md](archive/README.md). Their F01 to F20 findings, R01 to R18 requests,
  F05/F06 acceptance contract and wrong-call list are the fullest record that exists.

## Keeping it current

- Session records go in `docs/review/SESSION-<date>.md` (indexed), council lessons in
  `docs/council/LESSONS.md`, and a dated line at the top of STATE.md here.
- Do not rewrite history; mark superseded claims as superseded.
