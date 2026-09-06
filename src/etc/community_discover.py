import json, os, re, sys, datetime, collections
SNAP = "src/community/bundles.json"
IDX  = sys.argv[1] if len(sys.argv) > 1 else SNAP
if not os.path.exists(IDX): print("ABORT: %s not found" % IDX); sys.exit(1)
d = json.load(open(IDX))
bundles = d.get("bundles") or []
compat  = d.get("compatibilities") or []

def pkgs_for(key):
    if key is None: return []
    if isinstance(compat, list):
        if isinstance(key, int) and 0 <= key < len(compat):
            v = compat[key]
            return v if isinstance(v, list) else [v]
        return []
    if isinstance(compat, dict):
        v = compat.get(str(key)) or compat.get(key)
        if v is None: return []
        return v if isinstance(v, list) else [v]
    return []

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
        if c.get("host") == "gitlab":
            wired.add(("gitlab", str(c.get("project_id"))))
        else:
            wired.add(("github", ("%s/%s" % (c.get("owner"), c.get("repo"))).lower()))

def key(b):
    return (b.get("source","github"), str(b.get("repo","")).lower())

print("index: %d bundles, %d distinct packages, %d compatibility rows" % (len(bundles), len(allpkgs), len(compat)))
print("yours: %d enabled targets, %d wired bundles\n" % (len(mine), len(wired)))

print("="*76)
print("A. PROVIDERS YOU ARE MISSING for apps you already build")
print("="*76)
miss = 0
for pkg, x in sorted(mine.items(), key=lambda kv: kv[1]["id"]):
    offers = bypkg.get(pkg) or []
    have = [b for b,_ in offers if key(b) in wired]
    lack = [(b,ps) for b,ps in offers if key(b) not in wired]
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
