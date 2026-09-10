import json, os, re, sys, datetime, collections
import re
PKG=re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$')
def names(v, out=None):
    if out is None: out=[]
    if v is None: return out
    if isinstance(v,str):
        if PKG.match(v): out.append(v)
        return out
    if isinstance(v,dict):
        for k in ("name","package","packageName","pkg","id"):
            if isinstance(v.get(k),str) and PKG.match(v[k]): out.append(v[k]); return out
        for x in v.values(): names(x,out)
        return out
    if isinstance(v,(list,tuple)):
        for x in v: names(x,out)
        return out
    return out
SNAP = "src/community/bundles.json"
IDX  = sys.argv[1] if len(sys.argv) > 1 else SNAP
if not os.path.exists(IDX): print("ABORT: %s not found" % IDX); sys.exit(1)
d = json.load(open(IDX))
bundles = d.get("bundles") or []
compat  = d.get("compatibilities") or []

_PN = {}
if isinstance(compat, dict):
    for k, v in compat.items(): _PN[str(k)] = names(v)
else:
    for i, v in enumerate(compat): _PN[str(i)] = names(v)

def pkgs_for(key):
    if key is None: return []
    return _PN.get(str(key), [])

# package -> list of (bundle, [patch names])
bypkg = collections.defaultdict(list)
allpkgs = set()
for b in bundles:
    seen = collections.defaultdict(list)
    for p in (b.get("patches") or []):
        for pkg in pkgs_for(p.get("compatiblePackagesKey")):
            seen[pkg].append(p)
            allpkgs.add(pkg)
    for pkg, ps in seen.items():
        bypkg[pkg].append((b, ps))

t = json.load(open("src/targets.json"))
mine, wired = {}, set()
for x in t:
    if x.get("enabled") is False: continue
    mine[x["package"]] = x
    for c in (x.get("candidates") or []) + (x.get("extra_bundles") or []):
        wired.add((x["package"], c.get("host", "github"),
                   ("%s/%s" % (c.get("owner"), c.get("repo"))).lower()))

def wired_hit(b, pkg):
    # Exact target-scoped repository identity; author similarity is not wiring.
    return (pkg, b.get("source", "github"),
            str(b.get("repo", "")).lower()) in wired

print("compatibility rows parsed: %d, packages found: %d" % (len(_PN), len({p for v in _PN.values() for p in v})))
print("index: %d bundles, %d distinct packages, %d compatibility rows" % (len(bundles), len(allpkgs), len(compat)))
print("yours: %d enabled targets, %d wired bundles\n" % (len(mine), len(wired)))

print("="*76)
print("A. PROVIDERS YOU ARE MISSING for apps you already build")
print("="*76)
miss = 0
for pkg, x in sorted(mine.items(), key=lambda kv: kv[1]["id"]):
    offers = bypkg.get(pkg) or []
    have = [b for b,_ in offers if wired_hit(b, pkg)]
    lack = [(b,ps) for b,ps in offers if not wired_hit(b, pkg)]
    print("\n%-18s %s" % (x["id"], pkg))
    print("   index knows %d bundle(s); you have %d wired" % (len(offers), len(have)))
    for b, ps in sorted(lack, key=lambda z: -(z[0].get("patchCount") or 0)):
        miss += 1
        print("   MISSING  %-34s %-22s %d patches for this app" % (b.get("repo"), (b.get("name") or "")[:22], len(ps)))
        for p in ps[:6]:
            print("            %-44s default=%s" % (p.get("name","?")[:44], p.get("default")))
        if len(ps) > 6: print("            ... and %d more" % (len(ps)-6))
    if not offers: print("   (index has no bundle for this package)")
print("\ntotal unwired bundles covering your apps: %d" % miss)

print("\n" + "="*76)
print("B. NEW APPS: packages with the most community support that you do not build")
print("="*76)
cand = [(pkg, v) for pkg, v in bypkg.items() if pkg not in mine]
def score(v): return (len(v), sum(len(ps) for _, ps in v))
for pkg, v in sorted(cand, key=lambda kv: score(kv[1]), reverse=True)[:15]:
    tot = sum(len(ps) for _, ps in v)
    who = ", ".join((b.get("repo") or "?") for b, _ in v[:3])
    print("  %-44s %d bundle(s), %3d patches   %s" % (pkg, len(v), tot, who))
print("  (%d packages in the index you do not build)" % len(cand))

os.makedirs("src/community", exist_ok=True)
if IDX != SNAP:
    json.dump(d, open(SNAP, "w"), separators=(",",":"), sort_keys=True)
    print("\nsnapshot written to %s (%d bytes)" % (SNAP, os.path.getsize(SNAP)))
