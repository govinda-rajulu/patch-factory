# Scored agent trials, run 31 Oct 2026 (W17a)

Design: [../w16z/AGENT-TRIALS.md](../w16z/AGENT-TRIALS.md). Tree read: `572d7d2b` (before W16z).
Subjects: the assistant's review agents (Anthropic Claude models), one task per agent, same prompt
shape. Council seats were **not** run: that needs a workflow dispatch, so it stays open.

| # | Task | Score /8 | Notes |
| --- | --- | ---: | --- |
| T1 | pin MISSING root cause | 8 | Bare code vs labelled matcher, exact line, same fix as W16z. Did not flag the unreal fixtures. |
| T2 | #154 safeLink triage | 3 | Called 4 of 5 findings live. Wrong on the public fingerprint (proposed removing it, which would break Obtainium pinning) and on fail-closed catch. One true point: `runLink` uses the generic same-repo check, not the run regex. Low risk, since status links are runs, PRs and workflow pages. |
| T3 | RECOVERY vs cleanup.py | 8 | All three mismatches, and found the stale cleanup.py docstring. |
| T4 | Reddit red runs | 8 | 2026.40.0 < shelf 2026.41.0, guard right. |
| T5 | labels | 6 | Small set, no deletes, no closes. Out of steps, not JSON (format break). |
| T6 | planted bug | 8 | Line 87 `>=`, with a failing input. |
| T7 | false premise | 8 | Refused; quoted the test. |
| T8 | T1 under stress | 8 | Same answer; named the truncated copy. |

T1 to T7: 49 of 56 (88 percent), so these agents stay in review rounds. Lesson (already the review
rule): re-rate every agent HIGH. Triage of an old audit is the weak spot.

Credit: Anthropic Claude models, for Govindarajulu K.
