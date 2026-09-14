#!/bin/bash
# Compare tonight's report against the last one recorded in an issue.
set -uo pipefail
R="${WATCH_REPORT:-/tmp/report.txt}"
[ -s "$R" ] || { echo "::error::watch report missing or empty"; exit 1; }
# Include MISSING/UNVERIFIED lines and untagged patch additions, not only summary headings.
SUM=$(sha256sum "$R" | cut -d ' ' -f1) || exit 1
TITLE="watch: repo and provider status"
NUM=$(gh issue list --state all --limit 100 --search "$TITLE in:title" --json number,title,body \
      --jq 'if length >= 100 then error("issue search coverage ambiguous") else
        [.[] | select(.title == "watch: repo and provider status")] |
        if length > 1 then error("duplicate exact issue titles") else .[0].number // empty end end') \
      || { echo "::error::issue inventory unreadable or ambiguous"; exit 1; }
OLD=""
if [ -n "$NUM" ] && [ "$NUM" != "null" ]; then
  PRIOR=$(gh issue view "$NUM" --json body -q .body) || exit 1
  OLD=$(printf '%s\n' "$PRIOR" | grep -oE "fingerprint: [a-f0-9]+" | head -1 | awk '{print $2}')
fi
echo "fingerprint now=$SUM last=${OLD:-none}"
if [ "$SUM" = "$OLD" ]; then echo "unchanged, staying quiet"; exit 0; fi
BODY=$(WATCH_FINGERPRINT="$SUM" python3 - "$R" <<'PY'
import os, pathlib, re, sys
text=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
repo=os.environ["GITHUB_REPOSITORY"]; run=os.environ["GITHUB_RUN_ID"]
if repo!="govinda-rajulu/patch-factory" or not re.fullmatch(r"[0-9]+",run):
    raise SystemExit("invalid watch run identity")
url="https://github.com/"+repo+"/actions/runs/"+run
print("fingerprint: "+os.environ["WATCH_FINGERPRINT"]+"\n\nRun: "+url)
print("\nFull redacted report and structured coverage: this run's nightly-report artifact (30 days).")
print("Execution success does not establish complete provider coverage.\n")
if len(text.encode("utf-8")) > 45000:
    print("Report exceeds the issue preview limit. Full report is in the artifact; no tail-only result substituted.")
else:
    print("\n".join("    "+line for line in text.splitlines()))
PY
) || exit 1
if [ -n "$NUM" ] && [ "$NUM" != "null" ]; then
  gh issue comment "$NUM" --body "$BODY" && gh issue edit "$NUM" --body "$BODY" || exit 1
  echo "updated issue $NUM"
else
  gh issue create --title "$TITLE" --body "$BODY" && echo "opened a new issue" || exit 1
fi
