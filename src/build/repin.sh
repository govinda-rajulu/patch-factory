#!/bin/bash
# Recompute every pin from its own URL. Run deliberately by hand, never in a build.
set -uo pipefail
P=src/build/TOOLING.sha256
T=$(mktemp)
while IFS= read -r l || [ -n "$l" ]; do
  case "$l" in ''|'#'*) printf '%s\n' "$l" >> "$T"; continue ;; esac
  IFS='|' read -r n u w o <<<"$l"
  f=$(mktemp)
  if wget -q -O "$f" "$u"; then
    g=$(sha256sum "$f" | awk '{print $1}')
    if [ "$g" = "$w" ]; then echo "  unchanged $n"; else echo "  REPINNED  $n: ${w:0:16} -> ${g:0:16}"; fi
    printf '%s|%s|%s|%s\n' "$n" "$u" "$g" "$o" >> "$T"
  else
    echo "  FAILED    $n ($u) - keeping the old pin"; printf '%s\n' "$l" >> "$T"
  fi
  rm -f "$f"
done < "$P"
mv "$T" "$P"
