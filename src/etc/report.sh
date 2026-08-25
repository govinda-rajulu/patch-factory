#!/bin/bash
# One entry point for every read-only repo check.
#   report.sh fast   - no network, safe in a git hook
#   report.sh full   - adds provider lookups, needs a morphe-desktop jar
set -uo pipefail
MODE="${1:-fast}"
FAIL=0
echo "### bancheck"
bash src/etc/bancheck.sh || FAIL=1
echo
echo "### targets integrity"
python3 - <<'PY' || FAIL=1
import json, os, glob
d=json.load(open("src/targets.json"))
ids=[t["id"] for t in d]
assert len(ids)==len(set(ids)), "duplicate target ids"
bad=[]
for t in d:
    for c in t.get("candidates",[]) + t.get("extra_bundles",[]):
        p=c.get("patch_dir")
        if p and not os.path.isdir("src/patches/"+p): bad.append((t["id"],p))
    if not t.get("label"): bad.append((t["id"],"missing label"))
    if t.get("exclusive") and not t.get("candidates"): bad.append((t["id"],"no candidates"))
print("targets:", len(d), " dirs:", len([x for x in glob.glob("src/patches/*") if os.path.isdir(x)]))
assert not bad, bad
print("ok")
PY
echo
echo "### release coverage"
curl -sS "https://api.github.com/repos/govinda-rajulu/patch-factory/releases?per_page=100" \
  | jq -r '[.[].tag_name | capture("^(?
[a-z0-9-]+)-v") .p] | unique | .[]' > /tmp/rp.txt 2>/dev/null || echo "(release read failed)"
python3 - <<'PY'
import json
try: have=set(open("/tmp/rp.txt").read().split())
except Exception: have=set()
d=json.load(open("src/targets.json"))
miss=[t["id"] for t in d if (t.get("tag_prefix") or t["id"]) not in have]
print("released:", len(have), " never built:", miss)
PY
if [ "$MODE" = "full" ]; then
  echo; echo "### namecheck"; bash src/etc/namecheck.sh || FAIL=1
  echo; echo "### headroom";  bash src/etc/headroom.sh  || true
fi
echo; echo "report mode=$MODE fail=$FAIL"
exit "$FAIL"
