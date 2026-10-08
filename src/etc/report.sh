#!/bin/bash
# One entry point for every read-only repo check.
#   report.sh fast   - no provider lookups, safe in a git hook
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
rm -f /tmp/rp.txt /tmp/rp.all
RAUTH=()
[ -n "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ] && RAUTH=(-H "Authorization: Bearer ${GH_TOKEN:-${GITHUB_TOKEN:-}}")
# Authenticated: an anonymous read on a shared runner IP is rate limited (Nightly #99).
# 8 Oct 2026 (W2): every page, not the newest 100 only (older apps looked "never built"),
# and a failed read is UNKNOWN instead of an empty list.
RP_OK=0
: > /tmp/rp.all
for P in $(seq 1 30); do
  if ! OUT=$(curl -sfS "${RAUTH[@]}" "https://api.github.com/repos/govinda-rajulu/patch-factory/releases?per_page=100&page=$P"); then break; fi
  if ! N=$(printf '%s' "$OUT" | jq 'length' 2>/dev/null); then break; fi
  printf '%s' "$OUT" | jq -r '.[].tag_name' | sed -n 's/-v[0-9.]*-b[0-9]*$//p' >> /tmp/rp.all
  if [ "$N" -lt 100 ]; then RP_OK=1; break; fi
done
if [ "$RP_OK" = 1 ]; then
  sort -u /tmp/rp.all > /tmp/rp.txt
else
  echo "::warning::release list unreadable or longer than 3000 (throttled, offline or capped); release coverage is UNKNOWN"
fi
python3 - <<'PY'
import json, os
d=json.load(open("src/targets.json"))
if not os.path.exists("/tmp/rp.txt"):
    print("released: UNKNOWN (release list unreadable)")
    print("never built: UNKNOWN")
else:
    have=set(open("/tmp/rp.txt").read().split())
    miss=sorted(t["id"] for t in d if (t.get("tag_prefix") or t["id"]) not in have)
    print("released:", len(have), sorted(have))
    print("never built:", miss)
PY
if [ "$MODE" = "full" ]; then
  # One exact-bundle read per provider, as the build reads it (includes extras and GitLab).
  echo; echo "### namecheck"; python3 src/etc/selection_names.py || FAIL=1
fi
echo; echo "report mode=$MODE fail=$FAIL"
exit "$FAIL"
