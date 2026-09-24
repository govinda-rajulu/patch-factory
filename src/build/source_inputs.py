#!/usr/bin/env python3
"""Exact patcher-input transport; not original-publisher authentication."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import artifact_identity as identity
import input_recipe as recipe
import resolved_inputs as resolved
import shadow_inputs as shadow

DOMAIN = "patch-factory/source-apk/v1"
LOCK = "source-inputs/lock.json"
LIMITS = ["patcher-input bytes, possibly merged from a store bundle",
          "original publisher authenticity not established",
          "runtime transitive closure and default execution remain incomplete",
          "shadow-only; no build-selection authority"]


def need(ok, why):
    if not ok:
        raise ValueError("source inputs: " + why)


def clean_env(env):
    result = resolved.safe_env(env)
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if key in env:
            result[key] = env[key]
    return result


def apk_record(root, path):
    row = resolved.regular(root, path)
    need(row["bytes"] > 1000000, "APK below existing build size gate")
    with zipfile.ZipFile(Path(root) / path) as z:
        need(z.namelist().count("AndroidManifest.xml") == 1, "missing or duplicate manifest")
    return row


def validate_metadata(meta, target):
    need(isinstance(meta, dict) and set(meta) == {"package", "version_name", "version_code", "min_sdk"},
         "invalid manifest coverage")
    need(meta["package"] == target["package"] and
         isinstance(meta["version_name"], str) and
         re.fullmatch(r"[0-9]+(?:[.][0-9]+)*", meta["version_name"]) and
         isinstance(meta["version_code"], str) and re.fullmatch(r"[0-9]+", meta["version_code"]) and
         type(meta["min_sdk"]) is int and 1 <= meta["min_sdk"] <= target["min_sdk_ceiling"],
         "invalid APK identity/SDK")


def verify(root, ident, env):
    root = Path(root).resolve()
    dep = resolved.verify(root, ident, env)
    doc = recipe.read_json(root, LOCK)
    body = shadow.unseal(doc, DOMAIN)
    need(set(body) == {"domain", "schema", "target", "run", "dependency_lock_sha256",
                       "apk", "metadata", "limits"}, "unexpected packet fields")
    need(body["target"] == ident and body["run"] == dep["run"] and
         body["dependency_lock_sha256"] == dep["sha256"], "dependency/run binding differs")
    need(body["limits"] == LIMITS, "overstated evidence")
    directory = root / "source-inputs"
    need(not directory.is_symlink() and
         {p.name for p in directory.iterdir()} == {"lock.json", "source.apk"}, "unexpected packet files")
    need(body["apk"] == apk_record(directory, "source.apk"), "APK bytes differ")
    validate_metadata(body["metadata"], shadow.target(root, ident))
    return doc


def prepare(root, ident, env, run=None, metadata=None):
    root = Path(root).resolve()
    dep = resolved.verify(root, ident, env)
    t = shadow.target(root, ident)
    need(re.fullmatch(r"[A-Za-z0-9_-]+", t["apk_name"]), "unsafe APK name")
    # Fresh read-only resolution checkout; preserve all previous output/dirt.
    for name in ("source-inputs", "download", "release", "APKEditor.jar", "pup", "pup.zip"):
        p = root / name
        need(not p.exists() and not p.is_symlink(), "existing preparation output")
    clean = clean_env(env)
    result = (run or subprocess.run)(
        ["bash", "src/build/source_download.sh", ident, dep["material"]["version"]],
        cwd=root, env=clean, capture_output=True, timeout=1200, check=False)
    need(result.returncode == 0, "existing store fetcher refused")
    relative = "download/" + t["apk_name"] + ".apk"
    before = apk_record(root, relative)
    observed = (metadata or identity.metadata)(root, root / relative, clean)
    meta = {k: observed[k] for k in ("package", "version_name", "version_code", "min_sdk")}
    validate_metadata(meta, t)
    need(before == apk_record(root, relative), "APK changed during inspection")
    need(resolved.verify(root, ident, env) == dep, "dependencies changed during fetch")
    with tempfile.TemporaryDirectory(prefix="pf-source-", dir=root) as directory:
        payload = Path(directory) / "packet"
        payload.mkdir()
        shutil.copyfile(root / relative, payload / "source.apk")
        row = apk_record(payload, "source.apk")
        need(all(row[k] == before[k] for k in ("bytes", "sha256")), "copy differs")
        doc = shadow.seal({"domain": DOMAIN, "schema": 1, "target": ident, "run": dep["run"],
                           "dependency_lock_sha256": dep["sha256"], "apk": row,
                           "metadata": meta, "limits": LIMITS})
        (payload / "lock.json").write_bytes(recipe.canonical(doc) + b"\n")
        os.rename(payload, root / "source-inputs")
    verify(root, ident, env)
    return doc


def install(root, ident, env):
    root = Path(root).resolve()
    doc = verify(root, ident, env)
    relative = "download/" + shadow.target(root, ident)["apk_name"] + ".apk"
    need(re.fullmatch(r"download/[A-Za-z0-9_-]+[.]apk", relative), "unsafe destination")
    directory = root / "download"
    need(not directory.is_symlink() and
         (not directory.exists() or (directory.is_dir() and not any(directory.iterdir()))),
         "existing store download; preserve it")
    directory.mkdir(exist_ok=True)
    with (root / "source-inputs/source.apk").open("rb") as src:
        with (root / relative).open("xb") as dst:
            shutil.copyfileobj(src, dst)
    actual = apk_record(root, relative)
    need(all(actual[k] == doc["apk"][k] for k in ("bytes", "sha256")),
         "installed APK differs; preserve partial work")
    return doc


def consumed(root, ident, captured, env):
    doc = verify(root, ident, env)
    need(captured["target"] == ident and
         all(captured["patcher_input_apk"][k] == doc["apk"][k] for k in ("bytes", "sha256")),
         "consumed APK differs from preparation")
    return {"status": "MATCH", "lock_sha256": doc["sha256"],
            "apk": shadow.byte_record(doc["apk"])}


def snapshot(root, ident, env):
    doc = verify(root, ident, env)
    return shadow.seal({"domain": "patch-factory/prepared-source-subset/v1", "schema": 1,
                        "target": ident, "run": doc["run"],
                        "apk": shadow.byte_record(doc["apk"]), "limits": LIMITS})


def receipt_snapshot(receipt):
    if "prepared_source" not in receipt:
        return None
    doc = receipt["prepared_source"]
    body = shadow.unseal(doc, "patch-factory/prepared-source-subset/v1")
    need(set(body) == {"domain", "schema", "target", "run", "apk", "limits"} and
         body["target"] == receipt["target"] and body["limits"] == LIMITS and
         body["run"] == {"GITHUB_SHA": receipt["source_commit"], "GITHUB_RUN_ID": receipt["run_id"],
                         "GITHUB_RUN_ATTEMPT": receipt["attempt"], "GITHUB_REPOSITORY": receipt["repository"]},
         "source snapshot belongs to another publication")
    need(shadow.byte_record(body["apk"]) == body["apk"] and
         1000000 < body["apk"]["bytes"] <= resolved.MAX_FILE, "invalid source snapshot bytes")
    return doc


def observe(root, ident, env, api=None):
    run = resolved.identity(root, env)
    current, tag = None, None
    decision = {"state": "UNKNOWN", "reason": "PREPARED_SOURCE_UNAVAILABLE"}
    try:
        current = snapshot(root, ident, env)
        api = api or shadow.API(run["GITHUB_REPOSITORY"], resolved.safe_env(env))
        baseline, reason = shadow.latest_baseline(api, ident, shadow.target(root, ident)["tag_prefix"])
        decision["reason"] = reason
        if baseline is not None:
            need(reason in ("VERIFIED", "VERIFIED_DURABLE_ACTIONS_RECORD"), "unverified baseline")
            previous = receipt_snapshot(baseline)
            tag = baseline["tag"]
            if previous is None:
                decision["reason"] = "LATEST_PUBLICATION_HAS_NO_SOURCE_SUBSET"
            else:
                need(previous["target"] == ident and
                     previous["run"]["GITHUB_REPOSITORY"] == run["GITHUB_REPOSITORY"],
                     "source comparison identity differs")
                decision = {"state": "MATCHED_SOURCE_SUBSET" if previous["apk"] == current["apk"]
                            else "CHANGED_SOURCE_SUBSET", "reason": "VERIFIED_SOURCE_BYTES_COMPARISON"}
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError, zipfile.BadZipFile):
        decision = {"state": "UNKNOWN", "reason": "SOURCE_OR_BASELINE_UNAVAILABLE"}
        tag = None
    doc = shadow.seal({"domain": "patch-factory/source-observation/v1", "schema": 1,
                       "target": ident, "run": run, "current": current, "baseline_tag": tag,
                       "decision": decision, "limits": LIMITS})
    shadow.write(Path(root), "source-observation/" + ident + "-comparison.json", doc)
    return doc


def main():
    mode, ident = "", ""
    try:
        need(len(sys.argv) == 3, "usage: source_inputs.py prepare|verify|install|observe TARGET")
        mode, ident = sys.argv[1:]
        need(mode in ("prepare", "verify", "install", "observe"), "invalid mode")
        doc = {"prepare": prepare, "verify": verify, "install": install, "observe": observe}[mode](
            Path.cwd(), ident, dict(os.environ))
        if mode == "prepare":
            shadow.write(Path.cwd(), "source-observation/" + ident + ".json", doc)
        print(doc["metadata"]["version_name"] if mode == "install" else
              "SOURCE_OBSERVATION_RECORDED" if mode == "observe" else "SOURCE_APK_VERIFIED")
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError, zipfile.BadZipFile):
        if mode == "prepare" and re.fullmatch(r"[a-z0-9-]+", ident):
            try:
                shadow.write(Path.cwd(), "source-observation/" + ident + ".json",
                             {"target": ident, "status": "UNKNOWN", "reason": "SOURCE_PREPARATION_FAILED",
                              "limits": LIMITS})
            except (ValueError, OSError):
                pass
        print("::warning::source APK preparation unavailable or invalid; no full unchanged claim",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
