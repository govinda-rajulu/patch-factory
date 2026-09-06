#!/bin/bash
# A quarantined patch broke a real build. It must stay out of include-patches and
# stay in exclude-patches, in the dir named, forever, until someone deletes its
# QUARANTINE line on purpose. Run by "3. Validate" on every push to src/**.
set -uo pipefail
Q=src/patches/QUARANTINE
[ -f "$Q" ] || { echo "no $Q, nothing quarantined"; exit 0; }
FAIL=0; N=0
while IFS='|' read -r d p rest || [ -n "${d:-}" ]; do
  case "$d" in ''|'#'*) continue ;; esac
  [ -n "${p:-}" ] || { echo "::error::$Q: malformed line for dir '$d'"; FAIL=1; continue; }
  N=$((N+1))
  I="src/patches/$d/include-patches"; X="src/patches/$d/exclude-patches"
  [ -f "$I" ] || { echo "::error::$Q names $d but $I is missing"; FAIL=1; continue; }
  [ -f "$X" ] || { echo "::error::$Q names $d but $X is missing"; FAIL=1; continue; }
  if [ "$(sed 's/|.*//; s/[[:space:]]*$//' "$I" | grep -cxF "$p")" != "0" ]; then
    echo "::error::$d: quarantined patch is back in include-patches: $p"; FAIL=1
  fi
  if [ "$(sed 's/[[:space:]]*$//' "$X" | grep -cxF "$p")" = "0" ]; then
    echo "::error::$d: quarantined patch is not in exclude-patches: $p"; FAIL=1
  fi
done < "$Q"
[ "$FAIL" = 0 ] && echo "quarantine OK: $N patches held out"
exit $FAIL
