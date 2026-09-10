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
NEWEST=0; NEWEST_WHO=""; UNKNOWN=0
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
  [ -n "$D" ] && [ "$D" != "null" ] || { echo "::error::$n: provider date unknown"; UNKNOWN=1; continue; }
  S=$(date -d "$D" +%s) || { UNKNOWN=1; continue; }
  echo "  $n: $D"
  [ "$S" -gt "$NEWEST" ] && { NEWEST=$S; NEWEST_WHO="$n"; }
done <<< "$srcs"

if [ "$UNKNOWN" = 1 ] || [ "$NEWEST" = 0 ]; then
  echo "::error::$ID: freshness unknown; refusing to report up to date"
  echo "poll_state=unknown" >> "$GITHUB_OUTPUT"; exit 2
fi

# my newest release for this prefix
MINE=$(curl -sSL "${AUTH[@]}" \
  "https://api.github.com/repos/$REPO/releases?per_page=100" \
  | jq -r --arg p "$PREFIX-v" '[.[] | select(.tag_name | startswith($p))]
      | map(.assets[]?.updated_at) | sort | last // ""') || {
  echo "::error::$ID: release inventory unreadable"
  echo "poll_state=unknown" >> "$GITHUB_OUTPUT"; exit 2
}

if [ -z "$MINE" ] || [ "$MINE" = "null" ]; then
  echo "::warning::$ID: no existing release for prefix $PREFIX, refusing to auto-build"
  echo "new_patch=0" >> "$GITHUB_OUTPUT"; exit 0
fi

MS=$(date -d "$MINE" +%s)

# --- CFGSTAMP: my own selection config counts as a source ------------------
# poll.sh used to compare provider dates against my newest release only, so a change
# to include/exclude lists or an options file never triggered a rebuild. It does now.
CFGP=$(jq -r --arg id "$ID" '.[] | select(.id==$id)
       | [ ((.candidates // [])[] | "src/patches/" + .patch_dir),
           ((.candidates // [])[] | "src/options/" + .options + ".json"),
           ((.extra_bundles // [])[] | select(.patch_dir) | "src/patches/" + .patch_dir) ]
       | unique | .[]' src/targets.json)
CFGD=""
if [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
  echo "::warning::$ID: shallow clone, so a config change cannot be detected. ci.yml needs fetch-depth: 0"
elif [ -n "$CFGP" ]; then
  # shellcheck disable=SC2086
  CFGD=$(git log -1 --format=%cI -- $CFGP 2>/dev/null)
  [ -n "$CFGD" ] || echo "::warning::$ID: no commit touches $(echo $CFGP | tr '
' ' ')"
fi
if [ -n "$CFGD" ]; then
  CS=$(date -d "$CFGD" +%s)
  echo "$ID: config last changed $CFGD"
  if [ "$CS" -gt "$MS" ]; then
    echo "$ID: selection config is newer than my release, building"
    echo "new_patch=1" >> "$GITHUB_OUTPUT"; exit 0
  fi
fi
echo "$ID: newest source $NEWEST_WHO $(date -u -d @$NEWEST +%FT%TZ) | mine $MINE"
if [ "$NEWEST" -gt "$MS" ]; then
  echo "$ID: source is newer, building"
  echo "new_patch=1" >> "$GITHUB_OUTPUT"
else
  echo "$ID: up to date, not building"
  echo "new_patch=0" >> "$GITHUB_OUTPUT"
fi
