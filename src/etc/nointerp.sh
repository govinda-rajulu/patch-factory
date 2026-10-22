#!/bin/bash
# A workflow_dispatch input interpolated straight into a run: block is a shell injection.
# Inputs must reach shell through env:, so this fails if ${{ inputs.* }} or
# ${{ github.event.inputs.* }} appears inside a run: block anywhere in .github/workflows.
set -uo pipefail
FAIL=0; N=0
for f in .github/workflows/*.yml .github/actions/*/action.yml; do
  [ -f "$f" ] || continue
  N=$((N+1))
  python3 - "$f" <<'PY' || FAIL=1
import re,sys
f=sys.argv[1]
bad=[]; inrun=False; ind=0
for i,l in enumerate(open(f,encoding='utf-8'),1):
    l=l.rstrip('\n')
    # W15d: also the list-item form "- run: |" and folded ">" blocks, which the old pattern skipped.
    m=re.match(r'^(\s*)(?:-\s+)?run:\s*[|>]?[-+]?\s*$',l)
    if m: inrun=True; ind=len(m.group(1)); continue
    # W15d (AUDIT 4): a one-line run: is a shell command too.
    one=re.match(r'^\s*(?:-\s+)?run:\s*(\S.*)$',l)
    if one and re.search(r'\$\{\{\s*(inputs\.|github\.event\.inputs\.)',one.group(1)):
        bad.append((i,l.strip()[:100])); continue
    if inrun and l.strip() and (len(l)-len(l.lstrip()))<=ind: inrun=False
    if inrun and re.search(r'\$\{\{\s*(inputs\.|github\.event\.inputs\.)',l):
        bad.append((i,l.strip()[:100]))
for i,t in bad:
    print("::error file=%s,line=%d::dispatch input interpolated into a shell command. Pass it through env: instead. %s"%(f,i,t))
sys.exit(1 if bad else 0)
PY
done
[ "$FAIL" = 0 ] && echo "no interpolated inputs in $N workflow file(s)"
exit $FAIL
