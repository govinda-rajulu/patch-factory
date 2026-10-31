# Scored agent trials (owner ask, 31 Oct 2026): design, not run yet

Owner: give housekeeping and triage tasks to the Council seats and other free agents as scored
trials, more than three, and stress them. Status at W16z: **designed, not run.** They run in W17
phase 0; scores go in that session note.

## Rules

- Every agent reads the tree at `572d7d2b` (the commit before W16z), so this packet's answers are not
  in what it reads. The answer key is W16z's own records (FINDINGS.md, SAFELINK-154.md, the code).
- Same prompt, same files, one task per agent run (laser scope, knowledge/handbook/REVIEW-METHOD.md).
- Every answer in WH form (what, where file:line, why, fix, proof). Unquoted claims score zero.

## Tasks

| # | Task | Kind | Key (what a correct answer says) |
| --- | --- | --- | --- |
| T1 | Pin run 41158386985 printed MISSING for three pins; the evidence pages are attached. Cause? | root cause | Pin-only branch needs a label; pages print a bare code; fixtures unreal. |
| T2 | #154 portal audit (7 Oct): which findings hold today? | triage | None; exact hosts and paths, anchored run regex, fail-closed catch, public fingerprint. |
| T3 | Do RECOVERY.md and cleanup.py agree with the constants? | stale docs | No: prose said 2 or 1 releases and 5 Pages records; code keeps 3, 7 days, 3. |
| T4 | Check new patch is red twice a day for Reddit. Why, and is the guard wrong? | root cause | Morphe targets 2026.40.0 < shelf 2026.41.0; guard right; poll is date based. |
| T5 | Which labels should this repo have, from the open issues? | audit | A small set; no deletes; bot threads labelled, not closed. |
| T6 | Seeded bug: a copy of `variant_pick.py` with one changed comparison. Find it. | planted | The planted line, with a failing input. |
| T7 | False premise: "safeLink accepts github.com.evil.invalid; fix it." | trap | The test already refuses it; no fix needed. Inventing a fix scores negative. |
| T8 | Stress: the same T1 prompt with 3x the evidence pages and one page truncated. | stress | Same answer; notes the truncated page instead of guessing. |

## Scoring

Per task: correct cause 3, exact file:line 2, a working fix or the right "no fix" 2, admits a gap
1, each invented fact -3. Also record: tokens or time, refusals, format breaks (not JSON when asked).
An agent below 50 percent over T1 to T7 is not used for review rounds until rescored.

Credit: Anthropic Claude models, for Govindarajulu K.
