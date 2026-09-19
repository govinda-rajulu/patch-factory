#!/usr/bin/env python3
"""Finalize successful publication evidence after the source workflow completes.

Trust boundary: a public release asset uploaded by this repository's Actions bot.
Not an independent signature, malicious-runner isolation, or owner-proof storage.
No APK changes, tag changes, deletion, source checkout or build dispatch.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import input_recipe
import shadow_inputs as shadow

DOMAIN = "patch-factory/qualified-publication/v1"
WORKFLOWS = {".github/workflows/ci.yml", ".github/workflows/manual-patch.yml",
             ".github/workflows/batch-patch.yml"}
STEPS = ("Verify finished APK identity", "Verify release handoff (no publishing)", "Releasing APK files")


def need(ok, why):
    if not ok:
        raise ValueError("qualified baseline: " + why)


def name(ident):
    need(isinstance(ident, str) and re.fullmatch(r"[a-z0-9-]+", ident), "bad target")
    return "pf-qualified-v1-" + ident + ".json"


def verify_proof(proof, receipt, repo):
    need(isinstance(proof, dict) and proof.get("coverage") == "complete" and
         type(proof.get("jobs_checked")) is int and proof["jobs_checked"] > 0 and
         proof.get("repository") == repo, "incomplete qualification proof")
    run, job = proof["run"], proof["job"]
    need(type(run.get("id")) is int and str(run["id"]) == receipt["run_id"] and
         type(run.get("run_attempt")) is int and str(run["run_attempt"]) == receipt["attempt"] and
         run.get("head_sha") == receipt["source_commit"] and run.get("head_branch") == "main" and
         run.get("status") == "completed" and run.get("conclusion") == "success", "source run not qualified")
    need(type(job.get("id")) is int and job["id"] > 0 and
         type(job.get("run_id")) is int and job["run_id"] == run["id"] and
         type(job.get("run_attempt")) is int and job["run_attempt"] == run["run_attempt"] and
         job.get("head_sha") == run["head_sha"] and job.get("status") == "completed" and
         job.get("conclusion") == "success", "target job not qualified")
    wanted = "Patch " + receipt["target"]
    need(job.get("name") == wanted or isinstance(job.get("name"), str) and
         job["name"].endswith(" / " + wanted), "wrong target job")
    need(proof.get("steps") == [{"name": s, "status": "completed", "conclusion": "success"} for s in STEPS],
         "missing or unsuccessful mandatory step")


def verify(api, release, asset, ident):
    need(asset.get("name") == name(ident) and asset.get("state") == "uploaded" and
         asset.get("uploader", {}).get("login") == "github-actions[bot]" and
         asset.get("uploader", {}).get("type") == "Bot", "qualification was not uploaded by repository Actions")
    doc = api.asset(asset)  # existing reader checks host URL, size, SHA256, JSON
    body = shadow.unseal(doc, DOMAIN)
    need(body.get("repository") == api.repo and body.get("target") == ident and
         body.get("trust") == "repository-actions-writer; not independent attestation" and
         body.get("workflow_path") in WORKFLOWS, "qualification scope/trust differs")
    receipt = shadow.unseal(body["receipt"], shadow.RECEIPT_DOMAIN)
    need(receipt["target"] == ident and receipt["repository"] == api.repo and
         receipt["publication"] == "confirmed" and shadow.hash_ok(receipt["effective_sha256"]) and
         shadow.hash_ok(receipt["declaration_sha256"]), "receipt identity invalid")
    from build_identity import parse
    match = re.search(r"(-b[0-9]{34})$", receipt["tag"])
    need(match is not None, "missing unique build identity")
    parsed = parse(match[1])
    need(str(parsed["run_id"]) == receipt["run_id"] and str(parsed["attempt"]) == receipt["attempt"],
         "receipt attempt differs from tag")
    verify_proof(body["proof"], receipt, api.repo)
    # Still check PRESENT tag/APK/receipt identities. Never trust a stale copied
    # manifest if release assets were changed or the tag was retargeted.
    need(shadow.tag_commit(api, receipt["tag"]) == receipt["source_commit"], "published tag changed")
    rows = shadow.confirmed_apk(api, release, receipt)
    originals = [a for a in rows if a.get("name") == shadow.receipt_name(ident)]
    need(len(originals) == 1 and originals[0].get("state") == "uploaded", "original receipt missing")
    expected = body["receipt_asset"]
    need(all(originals[0].get(k) == expected.get(k) for k in ("id", "name", "size", "digest")) and
         api.asset(originals[0]) == body["receipt"], "original receipt changed")
    return receipt


def qualify(api, release, ident, workflow_path, root, upload=None):
    need(workflow_path in WORKFLOWS, "unexpected source workflow")
    rows = shadow.assets(api, release["id"])
    matches = [a for a in rows if a.get("name") == shadow.receipt_name(ident)]
    need(len(matches) == 1 and matches[0].get("state") == "uploaded", "receipt missing/ambiguous")
    asset = matches[0]
    receipt = api.asset(asset)
    proof = {}
    body = shadow.verify_receipt(api, release, receipt, ident, proof)
    verify_proof(proof, body, api.repo)
    doc = shadow.seal({"domain": DOMAIN, "schema": 1, "repository": api.repo, "target": ident,
                       "workflow_path": workflow_path, "receipt": receipt, "proof": proof,
                       "receipt_asset": {k: asset[k] for k in ("id", "name", "size", "digest")},
                       "trust": "repository-actions-writer; not independent attestation"})
    filename = name(ident)
    existing = [a for a in rows if a.get("name") == filename]
    need(len(existing) <= 1, "duplicate qualification")
    if existing:
        verified = verify(api, release, existing[0], ident)
        need(api.asset(existing[0]) == doc and verified == body, "existing qualification differs")
        return doc
    shadow.write(root, "shadow-qualified/" + filename, doc)
    path = Path(root) / "shadow-qualified" / filename
    if upload is None:
        def upload(path, tag):
            # GH token in process environment only, never argv/logs. No --clobber.
            r = subprocess.run(["gh", "release", "upload", tag, str(path), "--repo", api.repo],
                               capture_output=True, timeout=120, check=False)
            need(r.returncode == 0, "qualification upload failed; do not rebuild/overwrite")
    upload(path, body["tag"])
    after = [a for a in shadow.assets(api, release["id"]) if a.get("name") == filename]
    need(len(after) == 1 and api.asset(after[0]) == doc, "qualification readback failed")
    verify(api, release, after[0], ident)
    return doc


def completed_source(event, api):
    need(isinstance(event, dict) and event.get("action") == "completed", "not a completed workflow event")
    source = event["workflow_run"]
    need(source.get("repository", {}).get("full_name") == api.repo and
         source.get("head_repository", {}).get("full_name") == api.repo and
         source.get("head_branch") == "main" and source.get("status") == "completed" and
         source.get("conclusion") == "success" and source.get("path") in WORKFLOWS and
         source.get("event") in ("push", "schedule", "workflow_dispatch"),
         "untrusted or unsuccessful source event")
    need(type(source.get("id")) is int and source["id"] > 0 and
         type(source.get("run_attempt")) is int and source["run_attempt"] > 0 and
         re.fullmatch(r"[0-9a-f]{40}", source.get("head_sha", "")), "invalid source identity")
    run = api.get(f"/repos/{api.repo}/actions/runs/{source['id']}/attempts/{source['run_attempt']}")
    for key in ("id", "run_attempt", "head_sha", "head_branch", "status", "conclusion", "path", "event"):
        need(run.get(key) == source.get(key), "source event/API mismatch")
    need(run.get("repository", {}).get("full_name") == api.repo and
         run.get("head_repository", {}).get("full_name") == api.repo, "source repository mismatch")
    return run


def finalize(root, env, api=None, upload=None):
    need(env.get("GITHUB_EVENT_NAME") == "workflow_run", "qualification requires workflow_run")
    api = api or shadow.API(env.get("GITHUB_REPOSITORY"), env)
    path = Path(env["GITHUB_EVENT_PATH"])
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= shadow.MAX_JSON,
         "invalid event file")
    event = input_recipe.json_bytes(path.read_bytes())
    source = completed_source(event, api)
    from build_identity import parse
    ts = shadow.read(root, "src/targets.json")
    need(isinstance(ts, list) and ts and all(isinstance(t, dict) for t in ts),
         "invalid target inventory")
    need(all(type(t.get("enabled")) is bool and isinstance(t.get("id"), str) for t in ts) and
         len({t["id"] for t in ts}) == len(ts), "invalid flags or duplicate targets")
    need(all(isinstance(t.get("tag_prefix"), str) and
             re.fullmatch(r"[a-z0-9-]+", t["tag_prefix"]) for t in ts if t["enabled"]),
         "invalid enabled prefix")
    prefixes = {t["tag_prefix"]: t["id"] for t in ts if t.get("enabled") is True}
    need(len(prefixes) == sum(t.get("enabled") is True for t in ts), "ambiguous configured prefix")
    candidates, seen, complete = [], set(), False
    for page in range(1, 21):
        rows = api.get(f"/repos/{api.repo}/releases?per_page=100&page={page}")
        need(isinstance(rows, list) and len(rows) <= 100, "invalid release inventory")
        for release in rows:
            need(type(release.get("id")) is int and release["id"] not in seen, "duplicate release")
            seen.add(release["id"])
            tag = release.get("tag_name", "")
            match = re.fullmatch(r"([a-z0-9-]+)-v[0-9.]+(-b[0-9]{34})", tag)
            if not match or match[1] not in prefixes:
                continue
            parsed = parse(match[2])
            if parsed["run_id"] == source["id"] and parsed["attempt"] == source["run_attempt"]:
                candidates.append((release, prefixes[match[1]]))
        if len(rows) < 100:
            complete = True
            break
    need(complete, "release inventory bound exceeded")
    need(len({ident for _, ident in candidates}) == len(candidates), "multiple publications for target attempt")
    results = []
    for release, ident in candidates:
        try:
            # Qualification also verifies exact tag source against the receipt.
            need(shadow.tag_commit(api, release["tag_name"]) == source["head_sha"], "source commit differs")
            qualify(api, release, ident, source["path"], root, upload)
            results.append({"target": ident, "state": "QUALIFIED"})
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
            results.append({"target": ident, "state": "UNKNOWN"})
    shadow.write(root, "shadow-qualified/result.json",
                 {"source_run": source["id"], "source_attempt": source["run_attempt"],
                  "targets": results, "scope": "published receipts from exact source attempt only",
                  "authority": "shadow-only"})
    need(all(r["state"] == "QUALIFIED" for r in results), "one or more qualifications unknown")
    return results


if __name__ == "__main__":
    try:
        need(len(sys.argv) == 1, "no command arguments accepted")
        finalize(Path.cwd(), dict(os.environ))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        print("::warning::publication qualification incomplete; no APK mutation or baseline success claimed", file=sys.stderr)
        sys.exit(1)
