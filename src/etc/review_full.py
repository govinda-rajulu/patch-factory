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
def hit(n,rs):
    lo=n.lower()
    for k in rs:
        if k and k in lo: return k
    return ""

d=json.load(open("src/targets.json"))
rows=[]; skipped=[]
for t in d:
    if t.get("enabled") is False: continue
    excl=bool(t.get("exclusive"))
    for kind,c in [("cand",x) for x in (t.get("candidates") or [])]+[("extra",x) for x in (t.get("extra_bundles") or [])]:
        if c.get("host")=="gitlab":
            skipped.append((t["id"],c.get("name") or c.get("owner"),"gitlab, list-patches needs a repo URL")); continue
        dirn=c.get("patch_dir") or (t["id"]+"-"+(c.get("name") or c.get("owner")))
        inc,exc=set(rd("src/patches/%s/include-patches"%dirn)),set(rd("src/patches/%s/exclude-patches"%dirn))
        av=offers(c,t["package"])
        if not av:
            skipped.append((t["id"],dirn,"provider returned no patch names")); continue
        for p in av:
            n=p["Name"]; on=(p.get("Enabled")=="true")
            b,f=hit(n,BAN),hit(n,CFM)
            risk = ("BANNED:"+b) if b else (("CONFIRM:"+f) if f else "-")
            if excl:
                now = "IN" if n in inc else "out"
                dec = "IN" if n in inc else ("OUT" if (b or f) else "?")
            else:
                now = "out" if n in exc else "IN"
                dec = "OUT" if n in exc else ("OUT" if (b or f) else ("IN" if on else "?"))
            rows.append([dec,now,t["id"],dirn,n,("ON" if on else "off"),risk,("EXCL" if excl else "open"),(p.get("Description") or "").replace("\t"," ")[:150]])
def sk(r): return (r[2], 0 if r[6].startswith("BANNED") else (1 if r[6].startswith("CONFIRM") else 2), r[4])
rows.sort(key=sk)
os.makedirs("docs/review",exist_ok=True)
OUT="docs/review/PATCHES.tsv"
with open(OUT,"w") as fh:
    fh.write("# EVERY patch every wired provider offers, %s. Edit column 1 only.\n" % datetime.date.today())
    fh.write("# IN  = apply this patch.   OUT = do not apply.   ? = undecided, treated as OUT.\n")
    fh.write("# mode EXCL: the include list is authoritative, so IN means listed. mode open (youtube only): the exclude list is authoritative, so OUT means listed.\n")
    fh.write("# now  = what the repo does today. default = what the provider ships. risk = your BANNED/CONFIRM rules.\n")
    fh.write("DECISION\tnow\ttarget\tbundle\tpatch\tdefault\trisk\tmode\tdescription\n")
    for r in rows: fh.write("\t".join(str(x) for x in r)+"\n")
print("wrote %s: %d patches across %d bundles" % (OUT,len(rows),len({r[3] for r in rows})))
import collections
c=collections.Counter(r[2] for r in rows)
for k,v in sorted(c.items(), key=lambda kv:-kv[1]): print("  %-18s %3d" % (k,v))
print("\ndecision column starts as: IN=%d  OUT=%d  ?=%d" % (sum(1 for r in rows if r[0]=="IN"),sum(1 for r in rows if r[0]=="OUT"),sum(1 for r in rows if r[0]=="?")))
for a,b_,w in skipped: print("  SKIPPED %-18s %-26s %s" % (a,b_,w))
