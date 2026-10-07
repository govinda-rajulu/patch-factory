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

Rules: cite the file and the line number counted from its "=== FILE" line for every finding.
Report only what these files show; do not guess about files you cannot see. Prefer no finding
to a speculative one. Never claim tests or builds pass. At most 8 findings, most severe first.

Answer with exactly one JSON object with exactly these keys:
{"summary": "one or two sentences", "verdict": "looks_ok|needs_changes|unsure",
 "findings": [{"severity": "high|medium|low|nit", "file": "path", "line": integer or null,
 "issue": "what is wrong", "fix": "smallest safe fix, or empty string", "rule": "AGENTS.md line or lesson id, or empty string"}]}
