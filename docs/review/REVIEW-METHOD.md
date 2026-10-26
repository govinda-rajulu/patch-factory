# How a handover is checked (written 26 Oct 2026, packet W16m)

The owner asked for this after the W16m handover needed six check rounds and each round found
more. It records what the assistant did before, what it does now, and what each round found, so
the next chat starts with the method and not with the habit.

## The old approach (rounds 1 to 4): the author checks his own work

- The assistant who wrote the records re-read them, grepped for things he thought of, ran the
  tests he remembered and stopped when his own checks passed.
- No inventory: nobody listed every open item, every chat fact or every doc first, so there was no
  way to know what was not looked at. Each "deeper" round only went deeper where the last one had
  been.
- Checks were partial without saying so: a link check that skipped one folder, a test file run as
  a plain script that ran zero tests, counts copied from memory instead of re-read from the API.
- Why it missed things: the author reads what he meant, not what he wrote; a check you did not
  think of is never run; "my checks pass" was the stop rule.

## The new approach (from round 5): independent reviewers, one lens each, full populations

1. **Freeze the packet.** Commit it; give reviewers a read-only clone and the exact diff.
2. **Reviewers are agents that never saw the chat.** Each gets one lens, a written brief, read-only
   access, and must write a report with file:line, a short quote, evidence (command and output)
   and an exact fix, plus a "checked and fine" list. Lenses used:
   - Independent reviewer: contradictions, false claims, stale text, unclear paths in the entry
     files.
   - Open-item miner: every open, next or pending item in every OPEN-WORK section, STATE, session
     and handover record, each marked carried, done (with evidence), superseded or missing.
   - Fresh-chat simulation: play the next chat's assistant from the opening message only, try the
     first real tasks on paper, list every point of doubt.
   - Chat coverage: the assistant writes what the chat knew as atomic facts; the agent marks each
     recorded, conflicting or absent. (Weak point: the assistant writes that list, so a fact he
     forgot is still lost. Compaction of a long chat loses detail too.)
   - Fact checker: every checkable number, sha, path, workflow, setting and count against the code.
   - Staleness sweep: every doc that describes current behaviour against the code and config.
3. **Exhaustive by brief.** A reviewer either covers its whole population or says exactly what it
   did not cover; an agent that runs out of steps is continued, not trusted.
4. **The author fixes, then a second pass checks the fixes.** New text is where new errors are:
   the second pass reads the diff of the fixes only.
5. **Exit rule.** Done when a fresh set of reviewers finds no HIGH or MED item on the final commit.
   Then the full suite (18 steps, `suite.sh`), the six controller rehearsals (plain, rerun, failed
   check, bot drift merged over, bot drift on a packet file, human drift) and a launcher built from
   that exact commit.
6. **Limits.** Agents work offline: GitHub run ids, issues and the live main are checked by the
   assistant through the public API. Reviewers see only the repository and the brief.

## Round log, W16m (26 Oct 2026, IST)

| Round | Asked | Method | Found |
| --- | --- | --- | --- |
| 1 (11:20) | move everything to the repo | built the packet; own suite, link check, rehearsals | (baseline) |
| 2 (11:47) | check once again thoroughly | own re-read | wrong overnight window, wrong-call pointers, sandbox wording, open issues missing |
| 3 (11:56) | go deeper | own grep of older checkpoints | W17 label already used (69), /tmp not cleaned (70), about 25 dropped older items, lessons L078 to L100 unpinned, stale ROADMAP and council schedule text |
| 4 (12:05) | take another look | live API recheck, repo-wide link check | 9 runs not 8 (71), thin overnight schedules, five links broken by the archive move (72) |
| 5 (12:16) | clean out the issues | first agents: independent reviewer, open-item miner (46 sections, 68 items), then a second reviewer pass | a docs test that ran nothing (73), a wrong W17 claim about bot pull requests (74), 11 missing long-term items, stale September sections, 298 vs 299 unexplained, plus 4 more on the fixes |
| 6 (12:36) | review once more | four lenses: fresh-chat simulation, chat coverage (136 facts), fact checker, staleness sweep (69 docs); second passes on the fixes | stale onboarding, council, APPS and ROADMAP text (75), W17 gaps (smoke cap, publish authority, provider issues), 5 chat facts absent, 7 wrong or unbacked claims, 6 new problems in the new text |
| 7 (12:56) | document the approach, check again | this file; six fresh agents: reviewer, open-item miner (repeated independently: same 68 rows and counts), fresh-chat simulation, chat coverage (160 facts: 156 recorded, 3 small conflicts, 1 absent), fact checker, staleness sweep | eleven more stale current docs (76: the handover had said "all fixed"), contradictory September text in OPEN-WORK, a Truecaller record contradicting its own list, pre-W16k statements in the 25 Oct audits, three dead FAQ images, two assistant-tooling style gaps (carried) |
| 8 (13:20) | exit check | four fresh agents: staleness in three shards (all 15 onboarding records; 40 council, knowledge and root docs; 81 Pages, review and workflow files), each finished its whole shard; a reviewer on the round-7 fixes | 32 more: stale current lines in 9 onboarding records, council README/SETUP/PROVIDERS/RUNNERS, the inherited FAQ, ICON-PROVENANCE, the T1 safety sentence, two counts in OPEN-ITEMS; low items carried (workflow comments, shared handbook) |
| 9 (13:35) | exit check | four fresh agents: the same three shards again (15, 25 and all undated review files) and a reviewer on the round-8 fixes | 1 HIGH (a Reddit record line still read as "build 42"), 10 MED: one of them an error the round-8 fix introduced (it said Focus Lock was in no Instagram list; piko has it), two stale guide lines, MCP status, schedule wording, a README generator nuance (carried). One agent suggestion was wrong (it said qualification is per candidate; qualify-baselines.yml runs only on a successful run) and was not applied |
| 10 (13:45) | exit check | fresh reviewer on the round-9 diff, the round table and the four docs contract tests | 0 HIGH, 2 MED: a cause stated without evidence (two Instagram names "dropped by the provider") and this row's own placeholder. Both fixed in wording, without an eleventh agent round; then the full suite and the six rehearsals on the final commit |

Where W16m stopped: rounds 8 to 10 covered every tracked doc in shards; the last round found only
two wording items. Known low items are carried in OPEN-WORK item 11 (workflow comments, shared
handbook, the README generator's Truecaller column, assistant tooling style).

Agents can be wrong too: every finding is checked against the code before it is applied.

Why round 8 still found so much: rounds 6 and 7 gave one agent the whole repository; it ran out of
steps after the files it reached first. Round 8 was the first sweep that covered every file.

Lesson from rounds 5 to 7: a single agent given a whole repository runs out of steps and says so; split
the population into shards small enough to finish (one folder or file family per agent).
