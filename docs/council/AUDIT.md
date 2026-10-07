# Council audit prompt

Owner-approved changes only. `src/council/council.py` sends the text below the marker to every
seat, followed by trusted repository context and one part of one audit shard as an untrusted
DATA block. Shards: `src/council/shards.json`. Jobs and lanes: [SETUP.md](SETUP.md).

----- prompt below -----
Task: audit one part of the patch-factory repository as an independent seat. These files are
already on main; nothing here is a proposed change. The owner has no coding background; gates
and reviews are his only quality control. Each file in the DATA block starts with a line
"=== FILE <path>".

Look for, in this order:
1. Anything AGENTS.md forbids, or a safety rule that the code no longer enforces.
2. Ways a wrong or unsafe APK could ship: selection mistakes, skipped or weakened gates,
   secrets exposed beyond the steps that read them, runtime installs, unpinned actions.
3. Silent failures: errors swallowed, "|| true", missing pipefail, UNKNOWN treated as unchanged.
4. Workflow and script risks: shell injection from inputs, broad permissions, unsafe temp files.
5. Plain bugs, dead code and stale documentation that contradicts the code; nits last.

Rules: every finding copies one exact line of the cited file into "quote"; a finding whose
quote is not in that file is dropped. Report only what these files show. Prefer no finding to
a speculative one; generic advice ("add retries", "add a timeout") without a quoted line is not
a finding. Never claim tests or builds pass. At most 8 findings, most severe first. Caveman
style: short plain words; issue and fix at most 100 characters each.

Answer with exactly one JSON object. verdict is looks_ok, needs_changes or unsure; severity is
high, medium, low or nit; line counts from the file's first line; fix and rule may be "".
{"summary": "one short sentence", "verdict": "needs_changes", "findings": [{"severity": "medium",
 "file": "src/build/build.sh", "line": 12, "quote": "exact text of that line", "issue": "what is wrong",
 "fix": "smallest safe fix", "rule": "AGENTS.md or lesson id"}]}
