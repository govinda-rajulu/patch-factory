#!/bin/bash
set -uo pipefail
ID="${1:?usage: resolve.sh <target-id>}"
T=$(jq -c --arg id "$ID" '.[] | select(.id==$id)' src/targets.json)
[ -z "$T" ] && { echo "no target '$ID'"; exit 1; }
JAR=$(ls morphe-desktop-*.jar 2>/dev/null | head -1)
[ -z "$JAR" ] && { echo "no morphe-desktop jar in cwd"; exit 1; }
PKG=$(jq -r '.package' <<<"$T")
MAXVER=$(jq -r '.max_app_version // ""' <<<"$T")
MAXAGE=$(jq -r '.max_patch_age_days // 60' <<<"$T")
PIN=$(jq -r '.pin // ""' <<<"$T")
NOW=$(date +%s)
echo "=== resolving $ID ($PKG) ==="
bn=""; bv=""; bc=0; bd=0; bm=""
n=$(jq '.candidates | length' <<<"$T")
for i in $(seq 0 $((n-1))); do
  C=$(jq -c ".candidates[$i]" <<<"$T")
  NAME=$(jq -r '.name' <<<"$C"); OWNER=$(jq -r '.owner' <<<"$C")
  REPO=$(jq -r '.repo' <<<"$C"); CH=$(jq -r '.channel' <<<"$C")
  if [ -n "$PIN" ] && [ "$PIN" != "null" ] && [ "$NAME" != "$PIN" ]; then
    echo "  - $NAME: skipped (pinned to $PIN)"; continue; fi
  JSON=$(curl -sSL ${GITHUB_TOKEN:+-H "Authorization: token $GITHUB_TOKEN"} \
    "https://api.github.com/repos/$OWNER/$REPO/releases")
  if [ "$CH" = "prerelease" ]; then
    PUB=$(jq -r 'first(.[] | .published_at) // ""' <<<"$JSON")
  else
    PUB=$(jq -r 'first(.[] | select(.prerelease==false) | .published_at) // ""' <<<"$JSON")
  fi
  [ -z "$PUB" ] || [ "$PUB" = "null" ] && { echo "  - $NAME: DISQUALIFIED (no releases)"; continue; }
  PSEC=$(date -d "$PUB" +%s); AGE=$(( (NOW-PSEC)/86400 ))
  [ "$AGE" -gt "$MAXAGE" ] && { echo "  - $NAME: DISQUALIFIED (${AGE}d old)"; continue; }
  FLAG=""; [ "$CH" = "prerelease" ] && FLAG="--prerelease"
  OUT=$(java -jar "$JAR" list-versions --patches="https://github.com/$OWNER/$REPO" $FLAG -x -u -f "$PKG" 2>&1)
  VL=$(sed -n 's/^[[:space:]]*\([0-9][0-9.]*\)[[:space:]]*(\([0-9]*\) patch.*/\1 \2/p' <<<"$OUT")
  [ -z "$VL" ] && { echo "  - $NAME: no support for $PKG"; continue; }
  if [ -n "$MAXVER" ] && [ "$MAXVER" != "null" ]; then
    VER=$(awk '{print $1}' <<<"$VL" | sort -V | while read -r v; do
      [ "$(printf '%s\n%s\n' "$v" "$MAXVER" | sort -V | head -1)" = "$v" ] && echo "$v"; done | tail -1)
    [ -z "$VER" ] && { echo "  - $NAME: nothing <= $MAXVER"; continue; }
  else
    VER=$(awk '{print $1}' <<<"$VL" | sort -V | tail -1)
  fi
  CNT=$(awk -v v="$VER" '$1==v {print $2}' <<<"$VL" | head -1)
  MPP=$(ls -t morphe-data/patches/${OWNER}-${REPO}/*.mpp 2>/dev/null | head -1)
  echo "  - $NAME: app $VER, ${CNT:-0} patches, ${AGE}d ago"
  w=0
  if [ -z "$bv" ]; then w=1
  elif [ "$VER" != "$bv" ] && [ "$(printf '%s\n%s\n' "$bv" "$VER" | sort -V | tail -1)" = "$VER" ]; then w=1
  elif [ "$VER" = "$bv" ] && [ "${CNT:-0}" -gt "$bc" ]; then w=1
  elif [ "$VER" = "$bv" ] && [ "${CNT:-0}" -eq "$bc" ] && [ "$PSEC" -gt "$bd" ]; then w=1
  fi
  [ "$w" = 1 ] && { bn="$NAME"; bv="$VER"; bc="${CNT:-0}"; bd="$PSEC"; bm="$MPP"; }
done
[ -z "$bn" ] && { echo "RESULT: no viable provider"; exit 1; }
echo "WINNER=$bn"; echo "VERSION=$bv"; echo "PATCHES=$bc"; echo "MPP=$bm"
