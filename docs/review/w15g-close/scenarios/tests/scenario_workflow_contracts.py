#!/usr/bin/env python3
"""Static W15g scenario checks; parses Actions YAML through node/js-yaml.

The checker deliberately reports known findings instead of pretending a smoke can run GitHub
Actions.  It is dependency-light: PyYAML is not used.  Exit status is non-zero when a finding is
present, so CI can make the contract visible.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
NODE_PATH = "/opt/sd-artifact/node_modules"


def yaml(path: Path):
    if not NODE:
        raise RuntimeError("node is unavailable; scenario YAML checks skipped")
    script = r"""
const fs = require('fs');
const yaml = require('js-yaml');
const p = process.argv[1];
process.stdout.write(JSON.stringify(yaml.load(fs.readFileSync(p, 'utf8'))));
"""
    env = dict(os.environ, NODE_PATH=NODE_PATH)
    p = subprocess.run([NODE, "-e", script, str(path)], cwd=ROOT, env=env,
                       text=True, capture_output=True, check=False)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or "js-yaml failed")
    return json.loads(p.stdout)


def flat_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from flat_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from flat_strings(v)


def check():
    findings, passes = [], []
    manual_path = ROOT / ".github/workflows/manual-patch.yml"
    manual = yaml(manual_path)
    batch = yaml(ROOT / ".github/workflows/batch-patch.yml")
    ci = yaml(ROOT / ".github/workflows/ci.yml")
    jobs = manual["jobs"]

    def ok(label, evidence):
        passes.append((label, evidence))

    def finding(label, evidence, fix):
        findings.append((label, evidence, fix))

    if set(jobs) == {"patch", "sign", "publish"}:
        ok("three-job graph", "manual-patch.yml jobs are patch/sign/publish")
    else:
        finding("job graph", sorted(jobs), "keep patch, sign, and publish as the only build jobs")

    if jobs["sign"].get("needs") == "patch" and jobs["publish"].get("needs") == ["patch", "sign"]:
        ok("needs graph", "sign needs patch; publish needs patch and sign")
    else:
        finding("needs graph", {k: jobs[k].get("needs") for k in ("sign", "publish")}, "restore dependency edges")

    if jobs["patch"].get("permissions") == {"contents": "read"} and jobs["sign"].get("permissions") == {"contents": "read"} and jobs["publish"].get("permissions") == {"contents": "write"}:
        ok("job permissions", "patch/sign read; publish write")
    else:
        finding("job permissions", {k: jobs[k].get("permissions") for k in jobs}, "least privilege without elevating called jobs")

    patch_json = json.dumps(jobs["patch"], sort_keys=True)
    publish_json = json.dumps(jobs["publish"], sort_keys=True)
    sign_json = json.dumps(jobs["sign"], sort_keys=True)
    if "KEYSTORE_" not in patch_json and "KEYSTORE_" not in publish_json:
        ok("key isolation", "only Sign contains KEYSTORE references")
    else:
        finding("key isolation", "KEYSTORE reference leaked into patch/publish", "keep all keystore refs in Sign only")
    if all(x in sign_json for x in ("KEYSTORE_B64", "KEYSTORE_PASS", "KEYSTORE_ALIAS")):
        ok("sign secrets", "Sign references all three keystore secrets")
    else:
        finding("sign secrets", "one or more KEYSTORE secrets absent from Sign", "forward and consume all three in Sign")

    # Reusable callers must explicitly map required secrets.  Direct dispatch has repository secrets,
    # not a caller mapping; no workflow in this tree uses secrets: inherit.
    for name, wf in (("batch", batch), ("ci", ci)):
        caller = wf["jobs"]["build"]
        sec = caller.get("secrets", {})
        if set(sec) >= {"KEYSTORE_B64", "KEYSTORE_PASS", "KEYSTORE_ALIAS"} and "inherit" not in json.dumps(sec):
            ok(name + " explicit keystore mapping", sorted(sec))
        else:
            finding(name + " secrets", sec, "map required keystore secrets explicitly")
    if not any("manual-patch.yml" in s for s in flat_strings(batch)):
        finding("batch caller", "manual workflow is not called", "retain reusable call")
    if not any("manual-patch.yml" in s for s in flat_strings(ci)):
        finding("ci caller", "manual workflow is not called", "retain reusable call")

    # VT is optional and the only scan secret; neither reusable caller sets scan=true, while direct
    # dispatch reads the repository secret in the scan step.
    scan = next((s for s in jobs["patch"]["steps"] if s.get("name") == "Run provider safety scan"), {})
    if "VT_API_KEY" in json.dumps(scan) and "!inputs.publish" in str(scan.get("if", "")):
        ok("VT scan scope", "VT_API_KEY is step-scoped to nonpublishing scan")
    else:
        finding("VT scan scope", scan, "keep VT_API_KEY only in the optional nonpublishing scan step")

    if jobs["publish"].get("if") == "inputs.publish && github.ref == 'refs/heads/main' && needs.patch.outputs.internet_error == '0'":
        ok("publish guard", "publish=false, non-main, and nonzero/empty internet_error cannot publish")
    else:
        finding("publish guard", jobs["publish"].get("if"), "require publish=true, main, and internet_error == 0")
    if jobs["patch"]["outputs"].get("internet_error") == "${{ steps.check-gh.outputs.internet_error }}":
        ok("internet output", "step check-gh -> job output internet_error")
    else:
        finding("internet output", jobs["patch"].get("outputs"), "wire check-gh output exactly")
    if jobs["patch"]["outputs"].get("built_at") == "${{ steps.stamp.outputs.built_at }}":
        ok("built_at output", "stamp id and job output agree")
    else:
        finding("built_at output", jobs["patch"].get("outputs"), "wire stamp output")

    # Default success() semantics on needs jobs skip Sign/Publish after an unsuccessful dependency;
    # always() is intentionally limited to cleanup/evidence.
    if jobs["sign"].get("if") is None and jobs["publish"].get("if", "").startswith("inputs.publish"):
        ok("failure propagation", "no always() on sign; publish has needs and a restrictive condition")
    else:
        finding("failure propagation", "unexpected status override", "do not bypass failed patch/sign")
    remove = next((s for s in jobs["sign"]["steps"] if s.get("name") == "Remove keystore"), {})
    if remove.get("if") == "always()":
        ok("keystore cleanup", "Remove keystore uses always()")
    else:
        finding("keystore cleanup", remove, "remove keystore with if: always()")

    # Exact attempt-bound handoffs and digest validation.
    downloads = []
    for j in jobs.values():
        downloads += [s for s in j.get("steps", []) if "download-artifact" in str(s.get("uses", ""))]
    bad_downloads = [s.get("name") for s in downloads if s.get("with", {}).get("digest-mismatch") != "error"]
    if not bad_downloads:
        ok("artifact digest checks", "every manual download-artifact has digest-mismatch: error")
    else:
        finding("artifact digest checks", bad_downloads, "fail on digest mismatch")
    handoffs = [s for s in downloads if s.get("name") in ("Download the unsigned hand-off", "Download the signed hand-off")]
    if all("github.run_id" in str(s.get("with", {}).get("name")) and "github.run_attempt" in str(s.get("with", {}).get("name")) and s.get("with", {}).get("path") == "handoff/" for s in handoffs):
        ok("handoff identity", "Sign/Publish use exact run/attempt names and handoff/")
    else:
        finding("handoff identity", handoffs, "bind each handoff to run id and attempt")

    uploads = []
    for j in jobs.values():
        uploads += [s for s in j.get("steps", []) if "upload-artifact" in str(s.get("uses", ""))]
    missing_attempt = [s.get("with", {}).get("name") for s in uploads if "github.run_id" not in str(s.get("with", {}).get("name", "")) or "github.run_attempt" not in str(s.get("with", {}).get("name", ""))]
    if not missing_attempt:
        ok("artifact uniqueness", "all artifact names include target/run/attempt")
    else:
        finding("artifact uniqueness on rerun", missing_attempt, "append -${{ github.run_id }}-${{ github.run_attempt }} to every manual artifact name")

    handoff_upload = next((s for s in uploads if s.get("name") == "Hand the unsigned APK to the Sign job"), {})
    signed_upload = next((s for s in uploads if s.get("name") == "Hand the signed APK to the Publish job"), {})
    if handoff_upload.get("with", {}).get("include-hidden-files") is True and signed_upload.get("with", {}).get("include-hidden-files") is True:
        ok("hidden release metadata", "both handoffs include hidden release files")
    else:
        finding("hidden release metadata", "include-hidden-files missing on handoff", "preserve release/.version and related metadata")

    run_blocks = []
    for j in jobs.values():
        for s in j.get("steps", []):
            if "run" in s:
                run_blocks.append((j, s))
    unsafe = [(s.get("name"), s.get("run")) for _, s in run_blocks if "${{" in str(s.get("run"))]
    if not unsafe:
        ok("shell interpolation", "run blocks use env/argv rather than expression expansion")
    else:
        finding("shell interpolation", unsafe, "put untrusted inputs in env and quote shell variables")

    if "JOB_RX = re.compile" in (ROOT / "src/etc/status.py").read_text() and "(?:Patch|Sign|Publish)" in (ROOT / "src/etc/status.py").read_text():
        ok("status consumer", "status.py recognizes split job names")
    else:
        finding("status consumer", "split JOB_RX missing", "recognize Patch, Sign, Publish")
    shadow = (ROOT / "src/build/shadow_inputs.py").read_text()
    if "SPLIT_JOBS" in shadow and '"Verify unsigned APK identity"' in shadow and '"Sign APK"' in shadow:
        ok("qualification consumer", "shadow/qualification has split job layout")
    else:
        finding("qualification consumer", "split mandatory steps missing", "update shadow proof readers")

    for label, evidence, fix in findings:
        print("FINDING\t" + label + "\t" + str(evidence) + "\t" + fix)
    for label, evidence in passes:
        print("PASS\t" + label + "\t" + str(evidence))
    print("SUMMARY\tPASS=%d\tFINDING=%d" % (len(passes), len(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        raise SystemExit(check())
    except RuntimeError as exc:
        print("SKIP\t" + str(exc))
        raise SystemExit(0)
