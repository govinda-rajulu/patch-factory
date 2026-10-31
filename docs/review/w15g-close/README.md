# W15g close-out folder (31 Oct 2026)

Everything the W15g planning and build session produced outside the code, kept so a new chat
needs nothing from the old one. Records, not instructions: verify live before acting.

- `plan/`: the 31 Oct planning reports. SIGNING.md is the pre-build W15g plan (built and merged;
  HANDOVER-2026-10-31-W15g.md is what shipped). PORTAL.md, HOUSEKEEPING.md, PROVIDERS.md and
  ISSUES.md (+ .csv) are the W16z inputs. CONSOLE-W17.md is the W17 owner console design.
- `audit/`: the closed issue and pull request audit (owner collector, 31 Oct, 282 records):
  A and B are the two closed-issue shards (150 total: 62 done, 52 bot noise, 35 duplicates,
  1 wrong close: #262); P is the 124 pull requests with promises and follow-ups (105 done,
  11 superseded, 4 partial: #75, #78, #81, #282). The 8 open items (bot threads #27, #182, #213,
  #218, #276; #154, #233, #280) are in `plan/ISSUES.md` (+ `.csv`).
- `reviews/`: W15g review rounds R1 to R8 and the R7/R8 disposition, plus MORPHE-SOURCE.md
  (Morphe patcher source read: `--unsigned`, alignment, signing rule) and APKSIGNER-FACTS.md.
  Early rounds list findings later fixed or re-rated; R6 and the disposition are the final word.
- `scenarios/`: round 4 (four scoped testers, 31 Oct) and SUMMARY.md with the re-rating. The two
  "BLOCKER" labels in A-zip.md and the tag-date fix in C-attack.md were re-rated (LOW / rejected);
  SUMMARY.md says why.
- `scenarios/tests/`: the four testers' scenario files, kept as evidence, not run by the suite
  (scenario_zip_contracts.py deliberately fails on the two re-rated findings; three attack tests
  expect the rejected hardening). Promote a case into `tests/` only with its re-rating applied.
- `tools/`: `chain_rehearsal.py` (Patch to Sign to Publish with fake Android tools that drop
  directory and source-stamp entries like apksig; `PF_REPO=. python3 .../chain_rehearsal.py`,
  9 cases), the three rehearsal matrices used for W15g, its fix and this records packet
  (`PF_REPO`, `PF_WORK` set the paths), and `replay_entry_lists.py` (replays real APK entry lists
  from a pf-sp zip through the byte compare).
- `earlier/`: 30 Oct design notes not filed elsewhere: AUTOMATION-MAP (provider digest, patch age,
  pin probe, model catalogue watcher, fallback attempt eligibility), STORAGE-PLAN (artifact storage
  baseline, retention options), TELEGRAM-FALLBACKS (Hush survey; the Hush-primary advice was
  superseded by the owner's non-Hush choice; the generic fallback-recovery idea is still open).
- `LESSON-PROPOSALS.md`: L115 and L116, waiting for the owner's yes before the ledger.
- `LEFTOVERS-AUDIT.md`: the close-out sweep of every 28 to 31 Oct sandbox note against the repo;
  its MISSING items are now in OPEN-WORK.
- Smoke probe used for the first live STOP: `docs/review/controllers/owner-probes/pf-sp.py`
  (read-only; waits for packet-branch smokes, reads each Sign job, lists signer-dropped entries).

Credit: Anthropic Claude models, for Govindarajulu K.
