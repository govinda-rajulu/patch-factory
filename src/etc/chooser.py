# Build one editable file per patch dir from the Explore issues.
#   python3 src/etc/chooser.py            reads /tmp/pf/iss.json
# The prefix is ALWAYS the current repo state: + included, - excluded, space
# neither. BANNED and CONFIRM appear in the note column, never in the prefix,
# so leaving a line untouched changes nothing. That was a real bug once.
import json,os
NL=chr(10); TAB=chr(9); PIPE=chr(124)
I=json.load(open("/tmp/pf/iss.json"))
if not isinstance(I,list): raise SystemExit("API ERROR - not a list")
src={}
for it in I:
    t=it.get("title","")
    if not t.startswith("patches: ") or " via " not in t: continue
    pkg,repo=t[len("patches: "):].split(" via ",1)
    rows=[]
    for l in (it.get("body") or "").split(NL):
        if PIPE in l and not l.startswith("name "):
            n,d=l.rsplit(PIPE,1)
            if n.strip(): rows.append((n.strip(),d.strip()))
    if rows: src[(pkg.strip(),repo.strip().lower())]=rows
print("provider lists found:",len(src))
def keys(p): return [l.strip().lower() for l in open(p) if l.strip()]
ban=keys("src/patches/BANNED"); con=keys("src/patches/CONFIRM")
exc=set()
for l in open("src/patches/EXCEPTIONS"):
    p=l.split(PIPE)
    if len(p)>=2: exc.add((p[0].strip(),p[1].strip()))
def rd(p): return [l.strip() for l in open(p).read().split(NL) if l.strip()] if os.path.exists(p) else []
os.makedirs("/tmp/pf/choose",exist_ok=True)
miss=[]
for t in json.load(open("src/targets.json")):
    for c in t.get("candidates",[])+t.get("extra_bundles",[]):
        d=c.get("patch_dir")
        if not d: continue
        k=(t["package"],("%s/%s"%(c.get("owner","?"),c.get("repo","?"))).lower())
        rows=src.get(k)
        if rows is None: miss.append("%-14s %-24s %s"%(t["id"],d,k[1])); continue
        inc=rd("src/patches/%s/include-patches"%d); ex=rd("src/patches/%s/exclude-patches"%d)
        out=["# %s / %s   provider %s"%(t["id"],d,k[1]),
             "# edit the FIRST CHARACTER only. + include  - exclude  space neither",
             "# prefix is the CURRENT state. leaving a line alone changes nothing."]
        for n,dv in sorted(rows,key=lambda r:r[0].lower()):
            low=n.lower()
            p="+" if n in inc else ("-" if n in ex else " ")
            note="default:"+dv
            if any(x in low for x in ban):
                note += "  EXCEPTION-OK" if (d,n) in exc else "  BANNED-cannot-include"
            elif any(x in low for x in con): note+="  NEEDS-YOUR-CALL"
            out.append(p+TAB+n+TAB+note)
        open("/tmp/pf/choose/%s.txt"%d,"w").write(NL.join(out)+NL)
        print("%-24s %3d known  (+%d  -%d)"%(d,len(rows),len(inc),len(ex)))
if miss:
    print(NL+"NO PROVIDER LIST, curate by hand:")
    for m in miss: print("  "+m)
