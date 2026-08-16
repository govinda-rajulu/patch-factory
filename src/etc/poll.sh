#!/bin/bash
# Per-target freshness check. Usage: poll.sh TARGET_ID
# Prints new_patch=0|1 to GITHUB_OUTPUT. Builds only when some source bundle is
# newer than my newest release for this target's tag_prefix.
set -uo pipefail
ID="${1:?usage: poll.sh TARGET_ID}"
REPO="${repository:?repository env required}"
T=$(jq -c --arg id "$ID" '.[] | select(.id==$id)' src/targets.json)
[ -n "$T" ] || { echo "::error::no target $ID"; exit 1; }
PREFIX=$(jq -r '.tag_prefix // .id' <<<"$T")
AUTH=()
[ -n "${GITHUB_TOKEN:-}" ] && AUTH=(-H "Authorization: token $GITHUB_TOKEN")

# newest source bundle date across every candidate and extra
NEWEST=0; NEWEST_WHO=""
srcs=$(jq -r '[(.candidates[] | {h:(.host//"github"), p:(.project_id//"-"), o:.owner, r:.repo, n:.name}),
              ((.extra_bundles // [])[] | {h:(.host//"github"), p:(.project_id//"-"), o:.owner, r:.repo, n:.name})]
             | .[] | [.n,.h,.p,.o,.r] | @tsv' <<<"$T")
while IFS=$'\t' read -r n h p o r; do
  [ -n "$n" ] || continue
  if [ "$h" = "gitlab" ]; then
    D=$(curl -sSL "https://gitlab.com/api/v4/projects/$p/releases?per_page=5" \
        | jq -r 'first(.[]) | .released_at // ""')
  else
    D=$(curl -sSL "${AUTH[@]}" \
        "https://api.github.com/repos/$o/$r/releases" \
        | jq -r 'first(.[] | .assets[] | select(.name | test("[.]mpp$")) | .updated_at) // ""')
  fi
  [ -n "$D" ] && [ "$D" != "null" ] || { echo "  $n: no date, skipped"; continue; }
  S=$(date -d "$D" +%s)
  echo "  $n: $D"
  [ "$S" -gt "$NEWEST" ] && { NEWEST=$S; NEWEST_WHO="$n"; }
done <<< "$srcs"

if [ "$NEWEST" = 0 ]; then
  echo "::warning::$ID: could not read any provider date, not building"
  echo "new_patch=0" >> "$GITHUB_OUTPUT"; exit 0
fi

# my newest release for this prefix
MINE=$(curl -sSL "${AUTH[@]}" \
  "https://api.github.com/repos/$REPO/releases?per_page=100" \
  | jq -r --arg p "$PREFIX-v" '[.[] | select(.tag_name | startswith($p))]
      | map(.assets[]?.updated_at) | sort | last // ""')

if [ -z "$MINE" ] || [ "$MINE" = "null" ]; then
  echo "::warning::$ID: no existing release for prefix $PREFIX, refusing to auto-build"
  echo "new_patch=0" >> "$GITHUB_OUTPUT"; exit 0
fi

MS=$(date -d "$MINE" +%s)
echo "$ID: newest source $NEWEST_WHO $(date -u -d @$NEWEST +%FT%TZ) | mine $MINE"
if [ "$NEWEST" -gt "$MS" ]; then
  echo "$ID: source is newer, building"
  echo "new_patch=1" >> "$GITHUB_OUTPUT"
else
  echo "$ID: up to date, not building"
  echo "new_patch=0" >> "$GITHUB_OUTPUT"
fi
