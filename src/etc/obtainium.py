#!/usr/bin/env python3
# Generate one deterministic public import for enabled targets; no network access.
# --check compares bytes without writing. Release availability is separate.
import json, re, sys, pathlib

REPO = "govinda-rajulu/patch-factory"
APP_URL = "https://github.com/" + REPO
AUTHOR = "govinda-rajulu"

LABELS = {}  # filled from targets.json below
SKIP = {}
# Everyone uses the same enabled-target catalog. Subsets are selected in the page,
# never a hard-coded person/device distribution list in the generator.
targets = json.load(open("src/targets.json"))
pkg = {}
for t in targets:
    if not t.get("enabled"):
        continue
    p = t.get("tag_prefix") or t["id"]
    assert re.fullmatch("[a-z0-9-]+", p), ("prefix has regex metachars", p)
    pkg[p] = t["package"]
    LABELS[p] = t.get("label") or p
pkg["gg-photos"] = "app.morphe.android.apps.photos"
pkg["youtube-morphe"] = "app.morphe.android.youtube" # GmsCore support renames the package  # Change package name patch default
ALL_APPS = sorted(LABELS)
for p in ALL_APPS:
    assert p in LABELS, ("no label", p)
    assert p in pkg, ("no target", p)

live = set(LABELS)
# Imports describe configured enabled targets; availability is a separate live concern.
CHECK = "--check" in sys.argv

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
    content = json.dumps({"apps": [entry(p) for p in ok]}, indent=1)
    dest = pathlib.Path(path)
    if CHECK:
        if not dest.exists() or dest.read_text() != content:
            raise SystemExit("STALE: " + path + "; run python3 src/etc/obtainium.py")
    else:
        dest.write_text(content)
    print(path, len(ok), "apps:", " ".join(ok))

write("docs/obtainium.json", ALL_APPS)
for p in ALL_APPS:
    if p in SKIP:
        print("SKIP", p, "-", SKIP[p])
    elif p not in live:
        print("NO RELEASE YET", p)
