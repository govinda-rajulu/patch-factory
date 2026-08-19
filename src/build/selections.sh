#!/bin/bash
# Emit patch selection flags grouped per bundle, in load order.
# Selections in morphe-desktop bind to the preceding -p, so order is the contract.
set -uo pipefail
ID="${1:?usage: selections.sh TARGET_ID WINNER}"
WIN="${2:?usage: selections.sh TARGET_ID WINNER}"
T=$(jq -c --arg id "$ID" '.[] | select(.id==$id)' src/targets.json)
[ -n "$T" ] || { echo "no target $ID" >&2; exit 1; }
declare -A PD
PD["$WIN"]=$(jq -r --arg n "$WIN" '.candidates[] | select(.name==$n) | .patch_dir' <<<"$T")
while IFS=$'\t' read -r n d; do PD["$n"]="$d"; done \
  < <(jq -r '(.extra_bundles // [])[] | [.name, (.patch_dir // "-")] | @tsv' <<<"$T")
LIST=$( { ls ./*.mpp 2>/dev/null; ls ./extra/*.mpp 2>/dev/null; } \
  | awk -F/ '{print $NF"\t"$0}' | sort | cut -f2- )
[ -n "$LIST" ] || { echo "no bundles on disk" >&2; exit 1; }
OUT=""; N=0; FIRST=1
for M in $LIST; do
  B=$(basename "$M" .mpp); NM="${B#*-}"
  D="${PD[$NM]:--}"
  S=""
  if [ "$D" != "-" ]; then
    [ -d "src/patches/$D" ] || { echo "missing src/patches/$D for bundle $NM" >&2; exit 1; }
    for side in include exclude; do
      [ -f "src/patches/$D/$side-patches" ] || { echo "missing $D/$side-patches" >&2; exit 1; }
      sed -i 's/\r$//' "src/patches/$D/$side-patches"
    done
    while IFS= read -r l || [ -n "$l" ]; do
      [ -n "$l" ] && S="$S -d \"$l\""
    done < "src/patches/$D/exclude-patches"
    while IFS= read -r l || [ -n "$l" ]; do
      [ -n "$l" ] || continue
      S="$S -e \"${l%%|*}\""; N=$((N+1))
    done < "src/patches/$D/include-patches"
  fi
  if [ "$FIRST" = 1 ]; then OUT="$OUT$S"; FIRST=0; else OUT="$OUT -p $M$S"; fi
  echo "BUNDLE=$NM dir=$D" >&2
done
echo "WANT=$N"
echo "SEL=$OUT"
