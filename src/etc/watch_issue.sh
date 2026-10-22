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
# W15e (owner, 22 Oct 2026): tables, not an indented dump (src/etc/nightly_body.py).
case "${GITHUB_REPOSITORY:-}" in govinda-rajulu/patch-factory) ;; *) echo "::error::invalid watch run identity"; exit 1;; esac
case "${GITHUB_RUN_ID:-}" in ''|*[!0-9]*) echo "::error::invalid watch run identity"; exit 1;; esac
URL="https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
BODY=$(python3 "$(dirname "$0")/nightly_body.py" render "$R" "$SUM" "$URL") || exit 1
if [ -n "$NUM" ] && [ "$NUM" != "null" ]; then
  # The comment says only what changed; the body has everything.
  OLDF=$(mktemp); NEWF=$(mktemp)
  printf '%s\n' "${PRIOR:-}" > "$OLDF"; printf '%s\n' "$BODY" > "$NEWF"
  NOTE=$(python3 "$(dirname "$0")/nightly_body.py" changes "$OLDF" "$NEWF") || exit 1
  rm -f "$OLDF" "$NEWF"
  gh issue comment "$NUM" --body "$NOTE" && gh issue edit "$NUM" --body "$BODY" || exit 1
  echo "updated issue $NUM"
else
  gh issue create --title "$TITLE" --body "$BODY" && echo "opened a new issue" || exit 1
fi
