import json, os, re, subprocess, sys, datetime
jars=sorted(f for f in os.listdir("/tmp") if f.startswith("morphe-desktop-") and f.endswith("-all.jar"))
if not jars: print("ABORT: no patcher jar in /tmp"); sys.exit(1)
JAR="/tmp/"+jars[-1]
REC=re.compile(r'^\s*(Index|Name|Description|Enabled):\s*(.*?)\s*$')
def offers(c,pkg):
    cmd=["java","-jar",JAR,"list-patches","--patches=https://github.com/%s/%s"%(c["owner"],c["repo"])]
    if c.get("channel")=="prerelease": cmd.append("--prerelease")
    cmd+=["-f",pkg]
    r=subprocess.run(cmd,capture_output=True,text=True)
    out,cur=[],{}
    for l in (r.stdout+r.stderr).split("\n"):
        m=REC.match(l)
        if not m: continue
        k,v=m.group(1),m.group(2)
        if k=="Index":
            if cur.get("Name"): out.append(cur)
            cur={}
        cur[k]=v
    if cur.get("Name"): out.append(cur)
    return out
def rd(p): return [l.strip() for l in open(p) if l.strip() and not l.startswith("#")] if os.path.exists(p) else []
def rules(n):
    p="src/patches/"+n
    return [re.sub(r'^(BAN|CFM)\s+','',l.strip()).lower() for l in open(p) if l.strip() and not l.startswith("#")] if os.path.exists(p) else []
BAN,CFM=rules("BANNED"),rules("CONFIRM")
def hit(name,rs):
    lo=name.lower()
    for k in rs:
        if k and k in lo: return k
    return ""

d=json.load(open("src/targets.json"))
rows=[]
for t in d:
    if t.get("enabled") is False: continue
    exc_mode=bool(t.get("exclusive"))
    for kind,c in [("cand",x) for x in (t.get("candidates") or [])]+[("extra",x) for x in (t.get("extra_bundles") or [])]:
        if c.get("host")=="gitlab": continue
        dirn=c.get("patch_dir") or (t["id"]+"-"+(c.get("name") or c.get("owner")))
        inc=set(rd("src/patches/%s/include-patches"%dirn))
        exc=set(rd("src/patches/%s/exclude-patches"%dirn))
        av=offers(c,t["package"])
        if not av: continue
        for p in av:
            n=p["Name"]
            if n in inc or n in exc: continue
            b,f=hit(n,BAN),hit(n,CFM)
            if b: rec="EXCLUDE"; why="banned rule: "+b
            elif f: rec="EXCLUDE"; why="confirm rule: "+f
            elif exc_mode: rec="?"; why="inert today (exclusive target)"
            elif p.get("Enabled")=="true": rec="?"; why="SHIPPING NOW, default ON, target not exclusive"
            else: rec="?"; why="default off, not applied"
            rows.append([rec,t["id"],dirn,n,p.get("Enabled","?"),why,(p.get("Description") or "")[:110]])

os.makedirs("docs/review",exist_ok=True)
out="docs/review/UNREVIEWED.tsv"
with open(out,"w") as fh:
    fh.write("# Decide the first column: INCLUDE, EXCLUDE, or leave ? to decide later.\n")
    fh.write("# Generated %s from live provider bundles. Regenerate any time; your decisions are read back by apply_review.py.\n" % datetime.date.today())
    fh.write("DECISION\ttarget\tbundle\tpatch\tprovider_default\tstatus\tdescription\n")
    for r in rows: fh.write("\t".join(str(x) for x in r)+"\n")
print("wrote %s: %d patches to review" % (out, len(rows)))
from collections import Counter
c=Counter(r[5].split(":")[0].split(",")[0] for r in rows)
for k,v in c.most_common(): print("  %-46s %d" % (k,v))
pre=[r for r in rows if r[0]=="EXCLUDE"]
print("\npre-decided EXCLUDE by your own rules: %d (no thought needed, just keep them)" % len(pre))
ship=[r for r in rows if "SHIPPING NOW" in r[5]]
print("SHIPPING NOW unreviewed: %d  <-- these are in your APK today" % len(ship))
for r in ship[:6]: print("   %-12s %s" % (r[1], r[3]))
if len(ship)>6: print("   ... and %d more" % (len(ship)-6))
