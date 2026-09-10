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
bn=""; bv=""; bc=0; bd=0; bm=""; bh=""; bt=""
n=$(jq '.candidates | length' <<<"$T")
for i in $(seq 0 $((n-1))); do
  C=$(jq -c ".candidates[$i]" <<<"$T")
  NAME=$(jq -r '.name' <<<"$C"); OWNER=$(jq -r '.owner' <<<"$C")
  REPO=$(jq -r '.repo' <<<"$C"); CH=$(jq -r '.channel' <<<"$C")
  if [ -n "$PIN" ] && [ "$PIN" != "null" ] && [ "$NAME" != "$PIN" ]; then
    echo "  - $NAME: skipped (pinned to $PIN)"; continue; fi
  FETCH=$(python3 src/build/github_bundle.py "$OWNER" "$REPO" "$CH" "morphe-data/resolved/$OWNER-$REPO") || exit 2
  PUB=$(jq -r '.published_at' <<<"$FETCH")
  MPP=$(jq -r '.path' <<<"$FETCH")
  HASH=$(jq -r '.sha256' <<<"$FETCH")
  TAG=$(jq -r '.tag' <<<"$FETCH")
  [ -z "$PUB" ] || [ "$PUB" = "null" ] && { echo "  - $NAME: DISQUALIFIED (no releases)"; continue; }
  PSEC=$(date -d "$PUB" +%s); AGE=$(( (NOW-PSEC)/86400 ))
  # AGE IS A WARNING, NOT A DISQUALIFICATION.
  # A bundle that still applies is still good, and the build already proves that: it compares
  # requested patches against applied ones BY NAME and refuses to release on any gap. Age was a
  # guess at the same question, and a wrong guess turned a working target into no target at all.
  # Kept as a loud warning so a genuinely abandoned provider is still visible in the log.
  [ "$AGE" -gt "$MAXAGE" ] && echo "::warning::$NAME is ${AGE}d old, past its ${MAXAGE}d cap. Building anyway; the applied-count gate decides."
  echo "   - $NAME: channel=$CH exact bundle=$TAG sha256=$HASH"
  OUT=$(java -jar "$JAR" list-versions --patches="$MPP" -x -u -f "$PKG" 2>&1)
  JRC=$?
  if [ "$JRC" -ne 0 ]; then
    echo "::error::$NAME: local list-versions failed (exit=$JRC); refusing version fallback"
    printf '%s\n' "$OUT"
    exit 2
  fi
  VL=$(sed -n 's/^[[:space:]]*\([0-9][0-9.]*\).*(\([0-9]\{1,\}\) patch.*/\1 \2/p' <<<"$OUT")
  if [ -z "$VL" ]; then
    echo "   - $NAME: could not parse a version. list-versions exit=$JRC"
    echo "   --- PATCHER OUTPUT ($(printf '%s\n' "$OUT" | wc -l) lines), verbatim:"
    printf '%s\n' "$OUT" | sed 's/^/     | /'
    echo "   --- end PATCHER OUTPUT"
  fi
  if [ -z "$VL" ] && { [ -z "$MAXVER" ] || [ "$MAXVER" = "null" ]; }; then
    echo "   - $NAME: no max_app_version to fall back on - cannot pick a version"; continue
  fi
  [ -z "$VL" ] && { echo "   - $NAME: successful bundle read but no version parsed; using configured ceiling $MAXVER, applicability remains unverified until patching"; VL="$MAXVER 0"; }
  [ -z "$VL" ] && { echo "  - $NAME: no support for $PKG"; continue; }
  if [ -n "$MAXVER" ] && [ "$MAXVER" != "null" ]; then
    VER=$(awk '{print $1}' <<<"$VL" | sort -V | while read -r v; do
      [ "$(printf '%s\n%s\n' "$v" "$MAXVER" | sort -V | head -1)" = "$v" ] && echo "$v"; done | tail -1)
    [ -z "$VER" ] && { echo "  - $NAME: nothing <= $MAXVER"; continue; }
  else
    VER=$(awk '{print $1}' <<<"$VL" | sort -V | tail -1)
  fi
  CNT=$(awk -v v="$VER" '$1==v {print $2}' <<<"$VL" | head -1)
  echo "  - $NAME: app $VER, ${CNT:-0} patches, ${AGE}d ago"
  w=0
  if [ -z "$bv" ]; then w=1
  elif [ "$VER" != "$bv" ] && [ "$(printf '%s\n%s\n' "$bv" "$VER" | sort -V | tail -1)" = "$VER" ]; then w=1
  elif [ "$VER" = "$bv" ] && [ "${CNT:-0}" -gt "$bc" ]; then w=1
  elif [ "$VER" = "$bv" ] && [ "${CNT:-0}" -eq "$bc" ] && [ "$PSEC" -gt "$bd" ]; then w=1
  fi
  [ "$w" = 1 ] && { bn="$NAME"; bv="$VER"; bc="${CNT:-0}"; bd="$PSEC"; bm="$MPP"; bh="$HASH"; bt="$TAG"; }
done
[ -z "$bn" ] && { echo "RESULT: no viable provider"; exit 1; }
echo "WINNER=$bn"; echo "VERSION=$bv"; echo "PATCHES=$bc"; echo "MPP=$bm"
echo "MPP_SHA256=$bh"; echo "BUNDLE_TAG=$bt"
