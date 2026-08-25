#!/bin/bash
# What each target is NOT using. Local only, needs a morphe-desktop jar in cwd.
set -uo pipefail
J=$(ls morphe-desktop-*.jar 2>/dev/null | head -1)
[ -n "$J" ] || { echo "no morphe-desktop jar in cwd"; exit 1; }
while IFS=$'\t' read -r ID PKG OWNER REPO CHAN PDIR; do
  [ -n "$PDIR" ] || continue
  INC="src/patches/$PDIR/include-patches"
  [ -f "$INC" ] || continue
  O="/tmp/hr-$PDIR.txt"
  FLAG=""; [ "$CHAN" = "prerelease" ] && FLAG="--prerelease"
  timeout 300 java -jar "$J" list-patches --patches="https://github.com/$OWNER/$REPO" $FLAG -f "$PKG" > "$O" 2>&1
  grep -E "^Name:" "$O" | sed 's/^Name: //' | sort -u > "$O.all"
  [ -s "$O.all" ] || { echo "?? $ID/$PDIR unreadable"; continue; }
  printf "\n=== %s / %s  using %s of %s\n" "$ID" "$PDIR" "$(grep -c . "$INC")" "$(wc -l < "$O.all")"
  comm -13 <(grep -v '^$' "$INC" | sort -u) "$O.all" | while IFS= read -r n; do
    low=$(printf '%s' "$n" | tr 'A-Z' 'a-z'); tag="   "
    while IFS= read -r b; do [ -n "$b" ] && case "$low" in *"$b"*) tag="BAN";; esac; done < src/patches/BANNED
    [ "$tag" = "   " ] && while IFS= read -r c; do [ -n "$c" ] && case "$low" in *"$c"*) tag="CFM";; esac; done < src/patches/CONFIRM
    printf "  %s  %s\n" "$tag" "$n"
  done
done 3< <(jq -r '.[] | .id as $i | .package as $p | (.candidates[]?, .extra_bundles[]?) | select((.host=="github") or (.host|not)) | [$i,$p,.owner,.repo,.channel,.patch_dir] | @tsv' src/targets.json) <&3
