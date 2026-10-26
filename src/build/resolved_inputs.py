#!/usr/bin/env python3
"""Resolve exact patcher/bundle bytes once; transport and consume a checked lock.

This does not resolve the store APK, runtime closure or durable publication trust.
It never emits UNCHANGED or selects a build matrix. Missing shadow preparation
leaves the old resolver active, with the missing resolution explicitly recorded.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

import github_patcher
import extra_bundle
import input_recipe
import shadow_inputs
import bundle_version

DOMAIN = "patch-factory/resolved-dependencies/v1"
# W15b (20 Oct 2026, #141): Facebook 583 merged to 301,471,185 bytes on 19 Oct, past the old
# 256 MiB bound, so shadow preparation refused it and the publication receipt was never stored.
# GitHub release assets stop at 2 GiB; 1 GiB per file keeps every built app with room.
MAX_FILE = 1024 * 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024 * 1024
LOCK = "resolved-inputs/lock.json"


def need(ok, message):
    if not ok:
        raise ValueError("resolved inputs: " + message)

# resolve.sh summary lines this script may repeat in a public log. Each is built only
# from targets.json names, version digits and fixed words, never upstream text.
RESOLVER_SUMMARY = tuple(re.compile(p) for p in (
    r" - [a-z0-9-]+: skipped \(pinned to [a-z0-9-]+\)",
    r" - [a-z0-9-]+: fallback only \(built when the primary build fails\)",
    r" - [a-z0-9-]+: DISQUALIFIED \(no releases\)",
    r" - [a-z0-9-]+: nothing <= [0-9]+(?:[.][0-9]+)*",
    r" - [a-z0-9-]+: no max_app_version to fall back on - cannot pick a version",
    r" - [a-z0-9-]+: any app version, the store's newest, -?[0-9]+d ago",
    r" - [a-z0-9-]+: could not parse a version[.] list-versions exit=[0-9]+",
    r" - [a-z0-9-]+: app [0-9]+(?:[.][0-9]+)*, [0-9]+ patches, -?[0-9]+d ago",
    r"::error::[a-z0-9-]+: local list-versions failed \(exit=-?[0-9]+\); refusing version fallback",
    r"COVERAGE [a-z0-9-]+: app [0-9]+(?:[.][0-9]+)* covers [0-9]+ of [0-9]+ chosen patches; newest [0-9]+(?:[.][0-9]+)* covers [0-9]+(?: \(exact version_code pin: version kept\))?",
    r"RESULT: no viable provider",
    r"need exactly one morphe-desktop jar",
    r"invalid exact patcher path",
))
REASON = re.compile(r"resolved inputs: [A-Za-z0-9 ._,:;()<=/'-]{1,600}")

def resolver_summary(stdout, returncode):
    """Allowlisted resolve.sh lines only; anything else is counted, not shown."""
    kept, hidden = [], 0
    for line in (stdout or "").splitlines()[:400]:
        if any(p.fullmatch(line) for p in RESOLVER_SUMMARY):
            kept.append(line.strip().replace("::error::", ""))
        elif line.strip():
            hidden += 1
    return "; ".join(kept[:8] + ["exit=%d" % returncode, "%d other line(s) withheld" % hidden])

def listed(names):
    """W15i: file names for a public reason; only plain names are shown, others are counted."""
    plain = sorted(n for n in names if re.fullmatch(r"[A-Za-z0-9._-]{1,80}", n))
    rest = len(names) - len(plain)
    return ", ".join(plain[:6] + (["%d more" % (len(plain) - 6)] if len(plain) > 6 else [])
                     + (["%d unnamed" % rest] if rest else [])) or "none"


def public_reason(error):
    """This script's own fixed reason text, or only the exception type."""
    text = str(error) if isinstance(error, ValueError) else ""
    return text if REASON.fullmatch(text) else type(error).__name__


def safe_env(env):
    # Only public tool configuration and the caller's read-only API token.
    # Never inherit signing secrets, COE, proxy variables or arbitrary JAVA_OPTS.
    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "JAVA_HOME", "TMPDIR",
               "GITHUB_TOKEN", "GH_TOKEN", "PATCHER_TAG_PIN", "PATCHER_SHA256_PIN")
    clean = {k: env[k] for k in allowed if k in env}
    tag, digest = clean.get("PATCHER_TAG_PIN"), clean.get("PATCHER_SHA256_PIN")
    # W16o: preserve the optional patcher pins on the prepared path (MED-2),
    # validating their pair before passing them to the isolated resolver.
    need((tag is None) == (digest is None),
         "patcher pin requires both PATCHER_TAG_PIN and PATCHER_SHA256_PIN")
    if tag is not None:
        need(re.fullmatch(r"[A-Za-z0-9_.+-]+", tag) is not None, "invalid PATCHER_TAG_PIN")
        need(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "invalid PATCHER_SHA256_PIN")
    return clean


def patcher_provenance(meta):
    """Return only validated patcher identity metadata, or None for old fixtures."""
    if not isinstance(meta, dict):
        return None
    required = ("name", "bytes", "sha256", "tag")
    if not all(k in meta for k in required):
        return None
    need(re.fullmatch(r"morphe-desktop-[A-Za-z0-9_.+-]+-all[.]jar", meta["name"]) is not None,
         "invalid patcher provenance name")
    need(type(meta["bytes"]) is int and 0 < meta["bytes"] <= MAX_FILE and
         re.fullmatch(r"[0-9a-f]{64}", meta["sha256"]) is not None and
         isinstance(meta["tag"], str) and bool(meta["tag"]) and
         re.fullmatch(r"[A-Za-z0-9_.+-]+", meta["tag"]) is not None,
         "invalid patcher provenance")
    return {k: meta[k] for k in ("name", "bytes", "sha256", "tag", "asset_id",
                                 "github_digest_verified", "jar_structure_verified", "pin",
                                 "policy", "trust") if k in meta}


def pin_values(env):
    tag, digest = env.get("PATCHER_TAG_PIN"), env.get("PATCHER_SHA256_PIN")
    need((tag is None) == (digest is None),
         "patcher pin requires both PATCHER_TAG_PIN and PATCHER_SHA256_PIN")
    if tag is not None:
        need(re.fullmatch(r"[A-Za-z0-9_.+-]+", tag) is not None, "invalid PATCHER_TAG_PIN")
        need(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, "invalid PATCHER_SHA256_PIN")
    return tag, digest


def pin_set(env):
    return pin_values(env)[0] is not None


def validate_patcher_provenance(provenance, material, env):
    """Bind lock metadata to the locked JAR and optional operator pins."""
    tag, digest = pin_values(env)
    need(provenance is not None or tag is None,
         "patcher provenance unavailable while a pin is set")
    if provenance is None:
        print("::warning::PATCHER_PROVENANCE_UNKNOWN resolved lock has no validated patcher metadata", file=sys.stderr)
        return None
    expected = material["patcher"]
    need(provenance["name"] == Path(expected["path"]).name and
         provenance["bytes"] == expected["bytes"] and
         provenance["sha256"] == expected["sha256"],
         "patcher provenance differs from locked JAR")
    if tag is not None:
        need(provenance["tag"] == tag and provenance["sha256"] == digest,
             "patcher provenance differs from configured pin")
    return provenance


def identity(root, env):
    values = {}
    for key, pattern in (("GITHUB_SHA", r"[0-9a-f]{40}"),
                         ("GITHUB_RUN_ID", r"[1-9][0-9]{0,19}"),
                         ("GITHUB_RUN_ATTEMPT", r"[1-9][0-9]{0,5}"),
                         ("GITHUB_REPOSITORY", r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")):
        value = env.get(key, "")
        need(isinstance(value, str) and re.fullmatch(pattern, value), "missing run identity")
        values[key] = value
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                            text=True, timeout=15, check=True)
    need(result.stdout.strip() == values["GITHUB_SHA"], "checkout differs from source commit")
    return values


def regular(root, relative):
    need(isinstance(relative, str) and re.fullmatch(r"[A-Za-z0-9_.+/-]+", relative),
         "invalid file path")
    parts = relative.split("/")
    need(not relative.startswith("/") and all(p not in ("", ".", "..", ".git") for p in parts),
         "unsafe file path")
    node = Path(root)
    for part in parts:
        node = node / part
        need(not node.is_symlink(), "symlink in path")
    fd = os.open(node, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_FILE,
             "nonregular, empty or oversized input")
        h = hashlib.sha256()
        size = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            need(size <= MAX_FILE, "growing/oversized input")
            h.update(chunk)
    need(size == info.st_size, "input changed while reading")
    return {"path": relative, "bytes": size, "sha256": h.hexdigest()}


def fields(text):
    required = ("WINNER", "VERSION", "MPP", "MPP_SHA256", "BUNDLE_TAG")
    result = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key in required:
            need(key not in result and (value or key == "VERSION"), "duplicate or empty resolver field")
            result[key] = value
    need(set(result) == set(required), "incomplete resolver output")
    # W15i: an empty VERSION is resolve.sh's any-version answer (the store's newest is taken at
    # build time, as the live build does). Accepted only when the resolver said so for this
    # very winner; the lock then pins the patcher and bundles and records version "".
    any_version = ("  - %s: any app version, the store's newest, " % result.get("WINNER", "")) in text
    need(re.fullmatch(r"[A-Za-z0-9_-]+", result["WINNER"]) and
         (re.fullmatch(r"[0-9]+(?:[.][0-9]+)*", result["VERSION"]) or
          (result["VERSION"] == "" and any_version)) and
         re.fullmatch(r"[0-9a-f]{64}", result["MPP_SHA256"]), "malformed resolver identity")
    need(not any(ord(c) < 32 or ord(c) == 127 for c in result["BUNDLE_TAG"]), "invalid tag")
    return result


def declaration(root, ident):
    # Bind this producer/consumer too, without recursion through its output.
    return input_recipe.digest({
        "local": shadow_inputs.declaration(root, ident),
        "resolver": input_recipe.component(root, "src/build/resolved_inputs.py")
    })


def prepare(root, ident, env, patcher_fetch=None, run=None, extra_fetch=None):
    root = Path(root).resolve()
    run_id = identity(root, env)
    t = shadow_inputs.target(root, ident)
    before = declaration(root, ident)
    dest = root / "resolved-inputs"
    need(not dest.exists() and not dest.is_symlink(), "output already exists")
    fetch = patcher_fetch or github_patcher.fetch
    execute = run or subprocess.run
    fetch_extra = extra_fetch or extra_bundle.fetch
    clean = safe_env(env)
    # Temporary payload is isolated; only validated listed bytes are published.
    with tempfile.TemporaryDirectory(prefix="pf-resolve-", dir=root) as directory:
        scratch = Path(directory)
        payload = scratch / "payload"
        payload.mkdir()
        meta = fetch(payload, clean)
        provenance = patcher_provenance(meta)
        need(provenance is not None or not pin_set(clean),
             "patcher provenance unavailable while a pin is set")
        if provenance is None:
            print("::warning::PATCHER_PROVENANCE_UNKNOWN prepared resolution has no validated patcher metadata", file=sys.stderr)
        jar = payload / meta["name"]
        record = regular(payload, meta["name"])
        need(record["bytes"] == meta["bytes"] and record["sha256"] == meta["sha256"],
             "patcher changed after fetch")
        need(re.fullmatch(r"morphe-desktop-[A-Za-z0-9_.+-]+-all[.]jar", meta["name"]),
             "invalid patcher filename")
        # W15i (L076): morphe-desktop 1.19.0 keeps its data beside its JAR ("Morphe data root:
        # <jar dir>/morphe-data (JAR-adjacent)", owner Cloud Shell probe 23 Oct 2026), so running
        # the payload JAR wrote morphe-data/ into the payload and verify refused every lock as an
        # unlisted file. The resolver runs a byte-identical copy in its own tool folder.
        tool = scratch / "tool"
        tool.mkdir()
        shutil.copyfile(jar, tool / meta["name"])
        tool_record = regular(tool, meta["name"])
        need(tool_record["sha256"] == record["sha256"] and tool_record["bytes"] == record["bytes"],
             "resolver tool copy differs from the fetched patcher")
        local_env = dict(clean, PF_RESOLVE_JAR=str(tool / meta["name"]),
                         PF_RESOLVE_DIR=str(scratch / "candidates"))
        result = execute(["bash", "src/build/resolve.sh", ident], cwd=root, env=local_env,
                         capture_output=True, text=True, timeout=1200, check=False)
        need(result.returncode == 0, "candidate resolution failed: " +
         resolver_summary(result.stdout, result.returncode))
        parsed = fields(result.stdout)
        need(sorted(p.name for p in payload.iterdir()) == [meta["name"]],
             "resolver wrote into the payload: " + listed(set(p.name for p in payload.iterdir()) - {meta["name"]}))
        winner = next((c for c in t["candidates"] if c["name"] == parsed["WINNER"]), None)
        need(winner is not None and (not t.get("pin") or t["pin"] == parsed["WINNER"]),
             "winner differs from candidate/pin policy")
        source = Path(parsed["MPP"])
        need(source.is_absolute() and source.is_relative_to(scratch / "candidates"),
             "resolved path outside candidate area")
        r = regular(scratch, str(source.relative_to(scratch)))
        need(r["sha256"] == parsed["MPP_SHA256"], "winner changed after resolution")
        primary = "09-" + parsed["WINNER"] + ".mpp"
        shutil.copyfile(source, payload / primary)
        rows = [{"slot": primary, "role": "winner",
                 **regular(payload, primary)}]
        extra_metadata = []
        for i, extra in enumerate(t.get("extra_bundles", []), 1):
            need(i < 9, "unsupported bundle slot count")
            name = input_recipe.name(extra["name"])
            slot = str(i).zfill(2) + "-" + name + ".mpp"
            host = extra.get("host", "github")
            upstream = str(extra["project_id"]) if host == "gitlab" else extra["owner"] + "/" + extra["repo"]
            observed = fetch_extra(host, upstream, extra.get("channel", "prerelease"),
                                   payload / slot, clean)
            row = regular(payload, slot)
            need(row["sha256"] == observed["sha256"] and row["bytes"] == observed["bytes"],
                 "extra changed after fetch")
            rows.append({"slot": slot, "role": "extra", **row})
            # Persist identities only, not arbitrary upstream strings/URLs/logs.
            extra_metadata.append({"slot": slot, "host": host,
                                   "upstream_digest_verified": observed["upstream_digest_verified"]})
        need(declaration(root, ident) == before, "declaration changed during resolution")
        material = {"declaration_sha256": before, "target": ident,
                    "winner": parsed["WINNER"], "version": parsed["VERSION"],
                    "patcher": record, "bundles": sorted(rows, key=lambda x: x["slot"])}
        need(sum(r["bytes"] for r in rows) + record["bytes"] <= MAX_TOTAL, "payload exceeds bound")
        body = {"domain": DOMAIN, "schema": 1, "run": run_id, "material": material,
                # W16o MED-1: bind the resolved tag/digest into the lock so the
                # prepared path can install the same provenance beside its JAR.
                "patcher_provenance": provenance,
                "dependency_sha256": input_recipe.digest(material),
                "bundle_tag": parsed["BUNDLE_TAG"],
                # W15d: the same reader as the downloading path, prerelease suffix kept.
                "patch_version": bundle_version.version_of(source.name),
                "extra_provenance": extra_metadata,
                "state": "RESOLVED_DEPENDENCIES_ONLY",
                "authority": "shadow-only; no build selection",
                "unresolved": ["source APK bytes", "effective/default patch execution",
                               "runtime/OS/transitive closure", "durable published baseline"]}
        doc = dict(body, sha256=input_recipe.digest(body))
        b = input_recipe.canonical(doc) + b"\n"
        (payload / "lock.json").write_bytes(b)
        # Atomic rename exposes a whole packet, never a half-filled destination.
        os.rename(payload, dest)
    verify(root, ident, env)
    return doc


def verify(root, ident, env):
    root = Path(root).resolve()
    run_id = identity(root, env)
    data = input_recipe.safe_file(root, LOCK)[0]
    doc = input_recipe.json_bytes(data)
    need(isinstance(doc, dict) and doc.get("domain") == DOMAIN and doc.get("schema") == 1,
         "unsupported lock")
    body = {k: v for k, v in doc.items() if k != "sha256"}
    need(doc.get("sha256") == input_recipe.digest(body), "lock digest mismatch")
    need(doc.get("run") == run_id, "lock run/attempt/source/repository differs")
    need(doc.get("state") == "RESOLVED_DEPENDENCIES_ONLY" and
         doc.get("authority") == "shadow-only; no build selection" and
         doc.get("unresolved") == ["source APK bytes", "effective/default patch execution",
                                  "runtime/OS/transitive closure", "durable published baseline"],
         "lock overstates evidence")
    need(isinstance(doc.get("patch_version"), str) and
         (doc["patch_version"] == "unknown" or bundle_version.PATTERN.fullmatch(doc["patch_version"])),
         "invalid patch version")
    m = doc["material"]
    provenance = patcher_provenance(doc.get("patcher_provenance"))
    validate_patcher_provenance(provenance, m, env)
    need(m["target"] == ident and m["declaration_sha256"] == declaration(root, ident),
         "lock target/declaration drift")
    need(doc["dependency_sha256"] == input_recipe.digest(m), "dependency digest differs")
    t = shadow_inputs.target(root, ident)
    need(any(c["name"] == m["winner"] for c in t["candidates"]), "winner not configured")
    need(not t.get("pin") or t["pin"] == m["winner"], "pin drift")
    need(re.fullmatch(r"[0-9]+(?:[.][0-9]+)*", m["version"]) or m["version"] == "",
         "invalid resolved version")
    need(re.fullmatch(r"morphe-desktop-[A-Za-z0-9_.+-]+-all[.]jar", m["patcher"]["path"]),
         "invalid patcher path")
    expected = {"09-" + m["winner"] + ".mpp": "winner"}
    expected.update({str(i).zfill(2) + "-" + b["name"] + ".mpp": "extra"
                     for i, b in enumerate(t.get("extra_bundles", []), 1)})
    need(isinstance(m["bundles"], list) and len(m["bundles"]) == len(expected),
         "bundle count differs")
    need({r["slot"]: r["role"] for r in m["bundles"]} == expected and
         all(r["path"] == r["slot"] for r in m["bundles"]), "bundle roles/order differ")
    records = [m["patcher"]] + m["bundles"]
    need(sum(r["bytes"] for r in records) <= MAX_TOTAL, "oversized locked payload")
    directory = root / "resolved-inputs"
    present, wanted = set(p.name for p in directory.iterdir()), {"lock.json"} | {r["path"] for r in records}
    need(present == wanted, "unlisted/missing payload file (unlisted: %s; missing: %s)"
         % (listed(present - wanted), listed(wanted - present)))
    for r in records:
        actual = regular(directory, r["path"])
        need(type(r["bytes"]) is int and actual["bytes"] == r["bytes"] and
             actual["sha256"] == r["sha256"], "locked payload bytes differ")
    return doc


def install(root, ident, env):
    root = Path(root).resolve()
    doc = verify(root, ident, env)
    m = doc["material"]
    records = [m["patcher"]] + m["bundles"]
    # No default cleanup, replacement or glob selection. Existing dirt refuses.
    need(not list(root.glob("morphe-desktop-*.jar")) and not list(root.glob("*.mpp")),
         "existing patcher/bundle files; use clean checkout")
    need(not (root / "extra").is_symlink() and
         (not (root / "extra").exists() or not any((root / "extra").iterdir())),
         "existing extra-bundle contents")
    for r in records:
        need(not (root / r["path"]).exists() and not (root / r["path"]).is_symlink(),
             "destination collision")
    # All identities/destinations have passed before the first copy.
    for r in records:
        with (root / "resolved-inputs" / r["path"]).open("rb") as src:
            with (root / r["path"]).open("xb") as dst:
                shutil.copyfileobj(src, dst)
        actual = regular(root, r["path"])
        need(actual["sha256"] == r["sha256"] and actual["bytes"] == r["bytes"],
             "installed bytes differ; preserve partial work")
    provenance = patcher_provenance(doc.get("patcher_provenance"))
    sidecar = root / (Path(m["patcher"]["path"]).name + ".json")
    if provenance is not None:
        if sidecar.is_file() and not sidecar.is_symlink():
            try:
                existing = patcher_provenance(json.loads(sidecar.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                raise ValueError("invalid existing patcher provenance sidecar: " + str(error)) from error
            validate_patcher_provenance(existing, m, env)
        need(not sidecar.exists() and not sidecar.is_symlink(), "patcher provenance destination collision")
        fd, candidate = tempfile.mkstemp(prefix=sidecar.name + ".", suffix=".cand", dir=root)
        try:
            payload = dict(provenance, path=str(root / m["patcher"]["path"]))
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True, indent=2); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
            os.chmod(candidate, 0o600)
            os.replace(candidate, sidecar)
        finally:
            Path(candidate).unlink(missing_ok=True)
    elif pin_set(env):
        raise ValueError("resolved inputs: patcher provenance unavailable while a pin is set")
    else:
        print("::warning::PATCHER_PROVENANCE_UNKNOWN installed prepared JAR has no validated metadata", file=sys.stderr)
    return doc


def verify_consumed(root, ident, captured, env):
    doc = verify(root, ident, env)
    m = doc["material"]
    need(captured["target"] == ident and captured["winner"] == m["winner"],
         "consumed target/winner differs")
    actual = {Path(r["path"]).name: r for r in captured["bundles"]}
    need(set(actual) == {r["slot"] for r in m["bundles"]}, "consumed bundle set differs")
    for r in m["bundles"]:
        need(all(actual[r["slot"]][k] == r[k] for k in ("bytes", "sha256")),
             "consumed bundle differs from resolved bytes")
    jar = captured["tools"][0]
    need(Path(jar["path"]).name == m["patcher"]["path"] and
         all(jar[k] == m["patcher"][k] for k in ("bytes", "sha256")), "consumed patcher drift")
    return {"status": "MATCH", "dependency_sha256": doc["dependency_sha256"],
            "lock_sha256": doc["sha256"], "unresolved": doc["unresolved"]}


def main():
    mode, ident = "", ""
    try:
        need(len(sys.argv) == 3, "usage: resolved_inputs.py prepare|verify|install TARGET")
        mode, ident = sys.argv[1:]
        root, env = Path.cwd(), dict(os.environ)
        need(mode in ("prepare", "verify", "install"), "invalid mode")
        doc = {"prepare": prepare, "verify": verify, "install": install}[mode](root, ident, env)
        if mode == "prepare":
            shadow_inputs.write(root, "resolved-observation/" + ident + ".json", doc)
        if mode == "install":
            m = doc["material"]
            print("WINNER=" + m["winner"])
            print("VERSION=" + m["version"])
            print("PV=" + doc["patch_version"])
        else:
            print("RESOLVED_DEPENDENCIES_VERIFIED")
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        if mode == "prepare" and isinstance(ident, str) and re.fullmatch(r"[a-z0-9-]+", ident):
            try:
                shadow_inputs.write(Path.cwd(), "resolved-observation/" + ident + ".json",
                                    {"target": ident, "state": "UNKNOWN",
                                     "reason": "EXACT_DEPENDENCY_RESOLUTION_FAILED",
                                     "authority": "shadow-only"})
            except (ValueError, OSError):
                pass
        # Never print upstream output/env/signing values from a rejected packet. Only
        # this script's own fixed reason (or the exception type) names the failure.
        print("::warning::exact dependency lock unavailable or invalid; no unchanged claim", file=sys.stderr)
        print("resolved inputs failure: " + public_reason(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
