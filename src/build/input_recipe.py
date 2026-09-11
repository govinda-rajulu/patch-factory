#!/usr/bin/env python3
"""Local recipe manifest, not a complete dynamic build/published fingerprint.

Capture configured primary/extra inputs and resources, the active shared recipe,
and the consumed identity/store mapping. Exact downloaded bytes remain in the
existing input ledger. No network, writes, private key reads or approval decisions.
This module does NOT change polling, bootstrap old releases, or apply extra options.
"""
import hashlib
import json
import os
import pathlib
import re
import stat
import sys

SCHEMA = 1
DOMAIN = "patch-factory/local-input-recipe/v1"
SHARED = (
    "src/build/build.sh", "src/build/resolve.sh", "src/build/patch_target.py",
    "src/build/selections.sh", "src/build/utils.sh", "src/build/check_sdk.sh",
    "src/build/artifact_identity.py", "src/build/verify_output.py",
    "src/build/native_payloads.py", "src/build/release_contract.py",
    "src/build/build_identity.py", "src/build/github_bundle.py",
    "src/build/github_patcher.py", "src/build/extra_bundle.py",
    "src/build/fetch_bundle.sh", "src/build/tooling.sh",
    "src/build/TOOLING.sha256", "src/build/input_recipe.py",
    "src/etc/preflight.py", "src/etc/bancheck.sh", "src/etc/quarantine.sh",
    "src/patches/BANNED", "src/patches/CONFIRM",
    "src/patches/EXCEPTIONS", "src/patches/QUARANTINE",
    ".github/workflows/manual-patch.yml", ".github/actions/preparing/action.yml",
    ".github/actions/release/action.yml",
)

def need(condition, message):
    if not condition:
        raise ValueError("input recipe: " + message)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def pairs(items):
    out = {}
    for key, value in items:
        need(key not in out, "duplicate JSON key")
        out[key] = value
    return out

def json_bytes(b):
    def invalid(_):
        raise ValueError("input recipe: nonfinite JSON number")
    return json.loads(b, object_pairs_hook=pairs, parse_constant=invalid)

def safe_file(root, relative):
    need(isinstance(relative, str) and bool(relative), "missing file path")
    parts = relative.split("/")
    need(not relative.startswith("/") and "\\" not in relative
         and not any(x in ("", ".", "..", ".git") for x in parts)
         and not any(ord(c) < 32 or ord(c) == 127 for c in relative),
         "unsafe file path")
    node = root
    for part in parts:
        node = node / part
        need(not node.is_symlink(), "symlink in file path: " + relative)
    need(node.is_file(), "required file missing: " + relative)
    need(node.resolve().is_relative_to(root.resolve()), "file outside checkout")
    need(node.stat().st_size <= 4 * 1024 * 1024, "input too large")
    with node.open("rb") as stream:
        b = stream.read(4 * 1024 * 1024 + 1)
    need(len(b) <= 4 * 1024 * 1024, "input too large")
    mode = "100755" if node.stat().st_mode & stat.S_IXUSR else "100644"
    return b, mode

def component(root, path, kind="bytes", value=None):
    b, mode = safe_file(root, path)
    if value is not None:
        encoded = canonical(value)
    elif kind == "json":
        encoded = canonical(json_bytes(b))
    else:
        encoded = b
    return {"path": path, "mode": mode, "encoding": kind,
            "sha256": hashlib.sha256(encoded).hexdigest()}

def read_json(root, path):
    return json_bytes(safe_file(root, path)[0])

def name(value):
    need(isinstance(value,str) and re.fullmatch(r"[A-Za-z0-9_-]+",value),
         "unsafe or missing bundle/option name")
    return value

def resource_paths(value, key=""):
    """Only current file-valued option semantics and explicit repo-relative paths.

    Unknown option payloads remain in canonical JSON; this is not a transitive
    external-URL resolver. hosts/filePathOption are the supported file-valued keys.
    """
    result = set()
    if isinstance(value, dict):
        for k, v in value.items():
            result.update(resource_paths(v, k))
    elif isinstance(value, list):
        for v in value:
            result.update(resource_paths(v, key))
    elif isinstance(value, str):
        file_key = key in ("hosts", "filePathOption")
        explicit = value.startswith(("./", "src/", "../", "/"))
        if file_key or explicit:
            need(bool(value) and "://" not in value, "unsupported file resource location")
            path = value[2:] if value.startswith("./") else value
            result.add(path)
    return result

def create(root, ident, winner, env=None):
    root = pathlib.Path(root).resolve()
    targets = read_json(root, "src/targets.json")
    need(isinstance(targets,list) and bool(targets), "targets must be nonempty array")
    ids = [t.get("id") for t in targets]
    need(all(isinstance(x,str) for x in ids) and len(ids)==len(set(ids)),
         "duplicate or invalid target IDs")
    matches = [t for t in targets if t["id"]==ident and t.get("enabled") is True]
    need(len(matches)==1, "unknown, disabled or ambiguous target")
    t = matches[0]
    candidates, extras = t.get("candidates"), t.get("extra_bundles", [])
    need(isinstance(candidates,list) and bool(candidates) and isinstance(extras,list),
         "invalid bundle collections")
    bundles = candidates + extras
    names = [name(b.get("name")) for b in bundles]
    need(len(names)==len(set(names)), "duplicate bundle names")
    need(sum(c["name"]==winner for c in candidates)==1, "winner not a candidate")
    # Keep every unknown config field conservatively. Only note is explicitly non-behavioral.
    config = {k:v for k,v in t.items() if k!="note"}
    parts = [component(root,"src/targets.json","target-json",config)]
    roles = []
    resources = set()
    for b in bundles:
        is_extra = b in extras
        role = {"name": b["name"],
                "role": "extra" if is_extra else "candidate",
                "options_state": "absent"}
        pd = name(b.get("patch_dir"))
        for side in ("include","exclude"):
            path = "src/patches/"+pd+"/"+side+"-patches"
            text = safe_file(root,path)[0].decode("utf-8")
            lines = [x for x in text.splitlines() if x]
            if side=="include": lines = [x.split("|",1)[0] for x in lines]
            need(all(x and x==x.strip() for x in lines)
                 and len(lines)==len(set(lines)), "invalid/duplicate patch names")
            parts.append(component(root,path,"selection-list",lines))
        op = b.get("options")
        need(is_extra or op is not None, "candidate options absent")
        if op is not None:
            path = "src/options/"+name(op)+".json"
            value = read_json(root,path)
            need(isinstance(value,list), "options must be array")
            parts.append(component(root,path,"json"))
            resources.update(resource_paths(value))
            # Real argv currently passes only the winning candidate's options file.
            role["options_state"] = ("configured-not-passed-by-current-argv" if is_extra else
                                     "consumed" if b["name"]==winner else "candidate-not-selected")
        roles.append(role)
    for path in sorted(resources):
        parts.append(component(root,path))
    for path in SHARED:
        parts.append(component(root,path))
    apps = read_json(root,"docs/obtainium-govind.json")
    entries = [a for a in apps["apps"] if a.get("name")==t.get("label")]
    need(len(entries)==1 and isinstance(entries[0].get("id"),str),
         "missing or ambiguous installation identity")
    parts.append(component(root,"docs/obtainium-govind.json","identity-map",
                           {"name":entries[0]["name"],"id":entries[0]["id"]}))
    stores = read_json(root,"src/build/helper/apps.json")
    store = t.get("source","apkmirror")
    need(store in ("apkmirror","apkpure"), "unsupported APK source")
    need(store in stores and t["package"] in stores[store], "missing selected store mapping")
    parts.append(component(root,"src/build/helper/apps.json","store-map",
                           {store:{t["package"]:stores[store][t["package"]]}}))
    unique = {}
    for item in parts:
        key = (item["path"],item["encoding"])
        need(key not in unique or unique[key]==item, "conflicting file records")
        unique[key] = item
    # COE is the only current public runtime switch added to patch argv.
    # Persist its boolean effect, never the raw environment or signing values.
    env = os.environ if env is None else env
    body = {"domain":DOMAIN,"schema":SCHEMA,"target":ident,"winner":winner,
            "continue_on_error":bool(env.get("COE")),
            "bundle_roles":roles,"resource_paths":sorted(resources),
            "components":sorted(unique.values(),key=lambda x:(x["path"],x["encoding"]))}
    return dict(body,sha256=digest(body))

def verify(root, ident, winner, manifest, env=None):
    need(isinstance(manifest,dict) and manifest.get("domain")==DOMAIN
         and manifest.get("schema")==SCHEMA, "missing/unsupported manifest")
    need(manifest.get("target")==ident and manifest.get("winner")==winner,
         "manifest target/winner mismatch")
    body = {k:v for k,v in manifest.items() if k!="sha256"}
    need(manifest.get("sha256")==digest(body), "manifest digest mismatch")
    need(create(root,ident,winner,env)==manifest, "local inputs changed since capture")

if __name__=="__main__":
    try:
        need(len(sys.argv)==3, "usage: input_recipe.py TARGET WINNER")
        print(json.dumps(create(pathlib.Path.cwd(),sys.argv[1],sys.argv[2]),sort_keys=True))
    except (ValueError,KeyError,TypeError,OSError,UnicodeError) as error:
        print("::error::"+str(error),file=sys.stderr)
        sys.exit(1)
