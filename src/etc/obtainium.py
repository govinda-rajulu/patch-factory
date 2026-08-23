#!/usr/bin/env python3
# Generate Obtainium import files from targets.json plus the live release list.
# Anonymous GitHub read. Writes docs/obtainium-govind.json and docs/obtainium-parents.json.
import json, re, urllib.request

REPO = "govinda-rajulu/patch-factory"
APP_URL = "https://github.com/" + REPO
AUTHOR = "govinda-rajulu"

LABELS = {
  "adguard": "AdGuard", "edge": "Microsoft Edge", "es-file": "ES File Explorer",
  "facebook": "Facebook", "gg-photos": "Google Photos", "hotstar": "JioHotstar",
  "instagram": "Instagram", "key-mapper": "Key Mapper", "mx-player": "MX Player Pro",
  "prime-video": "Prime Video", "reddit": "Reddit", "sonyliv": "SonyLIV",
  "tc-combo": "Truecaller", "telegram": "Telegram", "youtube-morphe": "YouTube",
  "zee5": "ZEE5",
}
SKIP = {
  "gg-photos": "Change package name is applied, so the installed id is unknown - add on device",
}
MINE = ["key-mapper", "telegram", "instagram", "reddit", "edge", "adguard", "tc-combo",
        "gg-photos", "es-file", "hotstar", "sonyliv", "zee5", "youtube-morphe"]
THEIRS = ["tc-combo", "prime-video", "facebook", "gg-photos", "es-file",
          "hotstar", "sonyliv", "zee5", "mx-player"]

targets = json.load(open("src/targets.json"))
pkg = {}
for t in targets:
    p = t.get("tag_prefix") or t["id"]
    assert re.fullmatch("[a-z0-9-]+", p), ("prefix has regex metachars", p)
    pkg[p] = t["package"]
for p in sorted(set(MINE + THEIRS)):
    assert p in LABELS, ("no label", p)
    assert p in pkg, ("no target", p)

req = urllib.request.Request(
  "https://api.github.com/repos/" + REPO + "/releases?per_page=100",
  headers={"Accept": "application/vnd.github+json", "User-Agent": "patch-factory"})
rel = json.load(urllib.request.urlopen(req, timeout=30))
assert isinstance(rel, list), "releases API did not return an array - throttled"
live = set()
for r in rel:
    m = re.fullmatch("([a-z0-9-]+)-v[0-9.]+-b[0-9]{8}", r["tag_name"])
    if m and any(a["name"].endswith("arm64-v8a.apk") for a in r["assets"]):
        live.add(m.group(1))
print("live:", " ".join(sorted(live)))

def entry(p):
    adds = {
      "includePrereleases": False,
      "fallbackToOlderReleases": True,
      "filterReleaseTitlesByRegEx": "^" + p + "-v[0-9.]+-b[0-9]+$",
      "apkFilterRegEx": "arm64-v8a[.]apk$",
      "versionExtractionRegEx": "-v([0-9.]+)-b[0-9]+$",
      "matchGroupToUse": "1",
      "trackOnly": False,
      "appName": LABELS[p],
    }
    return {"id": pkg[p], "url": APP_URL, "author": AUTHOR, "name": LABELS[p],
            "categories": ["patch-factory"], "preferredApkIndex": 0,
            "additionalSettings": json.dumps(adds)}

def write(path, wanted):
    ok = [p for p in wanted if p in live and p not in SKIP]
    ids = [pkg[p] for p in ok]
    assert ok, "refusing to write an empty import file: " + path
    assert len(ids) == len(set(ids)), ("two apps share a package id", ids)
    json.dump({"apps": [entry(p) for p in ok]}, open(path, "w"), indent=1)
    print(path, len(ok), "apps:", " ".join(ok))

write("docs/obtainium-govind.json", MINE)
write("docs/obtainium-parents.json", THEIRS)
for p in sorted(set(MINE + THEIRS)):
    if p in SKIP:
        print("SKIP", p, "-", SKIP[p])
    elif p not in live:
        print("NO RELEASE YET", p)
