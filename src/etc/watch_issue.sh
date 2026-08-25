#!/bin/bash
# Compare tonight's report against the last one recorded in an issue.
set -uo pipefail
R=/tmp/report.txt
[ -s "$R" ] || { echo "no report, nothing to do"; exit 0; }
SUM=$(grep -E "^(ok|report|released:|targets:|  BAN|  CFM|=== )" "$R" | sha256sum | cut -c1-12)
TITLE="watch: repo and provider status"
NUM=$(gh issue list --state all --search "$TITLE in:title" --json number,body \
      --jq '.[0].number' 2>/dev/null || true)
OLD=""
[ -n "$NUM" ] && OLD=$(gh issue view "$NUM" --json body -q .body | grep -oE "fingerprint: [a-f0-9]+" | head -1 | awk '{print $2}')
echo "fingerprint now=$SUM last=${OLD:-none}"
if [ "$SUM" = "$OLD" ]; then echo "unchanged, staying quiet"; exit 0; fi
BODY=$(printf 'fingerprint: %s\n\nRun: %s/%s/actions/runs/%s\n\n```\n%s\n```\n' \
  "$SUM" "https://github.com" "$GITHUB_REPOSITORY" "$GITHUB_RUN_ID" "$(tail -120 "$R")")
if [ -n "$NUM" ]; then
  gh issue comment "$NUM" --body "$BODY" && gh issue edit "$NUM" --body "$BODY"
  echo "updated issue $NUM"
else
  gh issue create --title "$TITLE" --body "$BODY" && echo "opened a new issue"
fi
