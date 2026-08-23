#!/bin/bash
# One rule for every target. BANNED patches may not appear in any include list
# unless EXCEPTIONS names that dir and patch. CONFIRM patches are reported and
# awaiting Govind's decision; they never fail the run. Exclude lists are not
# checked: naming a banned patch there is the point.
# Same script here and in "3. Validate".
set -uo pipefail
B=src/patches/BANNED; C=src/patches/CONFIRM; X=src/patches/EXCEPTIONS
[ -s "$B" ] || { echo "::error::$B missing or empty"; exit 1; }
[ -f "$C" ] || { echo "::error::$C missing"; exit 1; }
[ -f "$X" ] || { echo "::error::$X missing"; exit 1; }
DIRS=$(jq -r '.[] | (.candidates // [])[] , (.extra_bundles // [])[] | .patch_dir // empty' src/targets.json | sort -u)
[ -n "$DIRS" ] || { echo "::error::no patch_dir in src/targets.json"; exit 1; }
FAIL=0; N=0; NB=0; NC=0; NX=0
for d in $DIRS; do
 F="src/patches/$d/include-patches"
 [ -f "$F" ] || { echo "::error::missing $F"; FAIL=1; continue; }
 N=$((N+1))
 while IFS= read -r l || [ -n "$l" ]; do
 [ -n "$l" ] || continue
 LOW=$(printf '%s' "$l" | tr 'A-Z' 'a-z')
 while IFS= read -r k || [ -n "$k" ]; do
 [ -n "$k" ] || continue
 case "$LOW" in *"$k"*)
 if [ "$(grep -cF "$d|$l|" "$X")" != "0" ]; then
 echo "documented exception: $d / $l"; NX=$((NX+1))
 else
 echo "::error::$d includes a banned patch: $l  (matched: $k)"; FAIL=1; NB=$((NB+1))
 fi ;;
 esac
 done < "$B"
 while IFS= read -r k || [ -n "$k" ]; do
 [ -n "$k" ] || continue
 case "$LOW" in *"$k"*) echo "::warning::$d: awaiting your call on: $l"; NC=$((NC+1)) ;; esac
 done < "$C"
 done < "$F"
done
echo "scanned $N include lists: $NB banned, $NC awaiting confirm, $NX documented exceptions"
exit $FAIL
