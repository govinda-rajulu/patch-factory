#!/bin/bash
# Resolve every include-patches name against its provider's real patch list.
# Local only for now: needs a morphe-desktop jar in the repo root.
set -uo pipefail
J=$(ls morphe-desktop-*.jar 2>/dev/null | head -1)
[ -n "$J" ] || { echo "no morphe-desktop jar in cwd - skipping"; exit 0; }
FAIL=0; CHECKED=0
while IFS=$'\t' read -r ID PKG OWNER REPO CHAN PDIR; do
  [ -n "$PDIR" ] || continue
  INC="src/patches/$PDIR/include-patches"
  [ -s "$INC" ] || continue
  OUT="/tmp/nc-$PDIR.txt"
  FLAG=""; [ "$CHAN" = "prerelease" ] && FLAG="--prerelease"
  timeout 300 java -jar "$J" list-patches --patches="https://github.com/$OWNER/$REPO" $FLAG -f "$PKG" > "$OUT" 2>&1
  grep -E "^Name:" "$OUT" | sed 's/^Name: //' | sort -u > "$OUT.names"
  if [ ! -s "$OUT.names" ]; then echo "?? $ID/$PDIR: provider list unreadable - UNVERIFIED"; continue; fi
  CHECKED=$((CHECKED+1))
  MISS=$(comm -23 <(grep -v '^$' "$INC" | sort -u) "$OUT.names")
  if [ -n "$MISS" ]; then
    echo "$MISS" | sed "s|^|-- $ID/$PDIR MISSING: |"; FAIL=$((FAIL+1))
  else
    echo "ok $ID/$PDIR ($(grep -c . "$INC") names)"
  fi
done 3< <(jq -r '.[] | .id as $i | .package as $p | (.candidates[]? | select(.host=="github" or (.host|not)) | [$i,$p,.owner,.repo,.channel,.patch_dir] | @tsv)' src/targets.json) \
  <&3
echo "checked=$CHECKED dirs_with_missing_names=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
