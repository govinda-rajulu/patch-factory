#!/bin/bash
# Report a patch dir that no target references. NEVER deletes: src/patches/_attic is an
# archive, so being unreferenced is its purpose. Rules in src/etc/cleanup_guard.md.
# Warns only, so this can never fail a push for keeping something on purpose.
set -uo pipefail
REF=$(jq -r '.[]|(.candidates//[])[],(.extra_bundles//[])[]|.patch_dir//empty' src/targets.json | sort -u)
N=0; A=0
for d in $(ls -d src/patches/*/ 2>/dev/null | sed 's|src/patches/||; s|/$||'); do
  if [ "$d" = "_attic" ]; then
    A=$(find src/patches/_attic -name include-patches 2>/dev/null | wc -l)
    echo "archive: src/patches/_attic holds $A archived selection list(s), deliberately unreferenced"
    continue
  fi
  printf '%s\n' "$REF" | grep -qxF "$d" && continue
  C=$(grep -c . "src/patches/$d/include-patches" 2>/dev/null); C=${C:-0}
  if [ "$C" -eq 0 ]; then
    echo "::warning::src/patches/$d is unreferenced and empty; safe to delete by hand"
  else
    echo "::warning::src/patches/$d is unreferenced but holds $C selection(s); kept on purpose, delete it yourself if you mean to"
  fi
  N=$((N+1))
done
echo "$N unreferenced patch dir(s) outside the archive, 0 deleted by CI"
exit 0
