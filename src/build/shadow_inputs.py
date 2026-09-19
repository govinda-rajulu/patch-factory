#!/usr/bin/env python3
"""Connected SHADOW evidence, never authority to skip or publish a build.

Plan declaration -> prepared dependencies -> Build-consumed key -> publication.
The existing resolver prepares patcher/bundles for daily builds; source APK and
runtime closure remain incomplete. Missing or unverified baselines stay UNKNOWN.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

import input_recipe as recipe

DOMAIN = "patch-factory/shadow-inputs/v1"
RECEIPT_DOMAIN = "patch-factory/published-inputs/v1"
MAX_JSON = 4 * 1024 * 1024
LIMIT = 1 * 1024 * 1024
REPO_PATTERN = r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"

def need(ok, why):
    if not ok:
        raise ValueError("shadow inputs: " + why)

def sha(value):
    return recipe.digest(value)

def hash_ok(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None

def seal(body):
    return dict(body, sha256=sha(body))

def unseal(doc, domain):
    need(isinstance(doc, dict) and doc.get("domain") == domain and doc.get("schema") == 1,
         "unsupported evidence schema")
    body = {k:v for k,v in doc.items() if k != "sha256"}
    need(hash_ok(doc.get("sha256")) and sha(body) == doc["sha256"], "evidence digest mismatch")
    return body

def read(root, path):
    return recipe.read_json(Path(root), path)

def write(root, path, doc):
    root = Path(root).resolve()
    dest = root / path
    need(dest.parent.resolve().is_relative_to(root) and not dest.is_symlink(), "unsafe evidence destination")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".cand")
    need(not tmp.exists() and not tmp.is_symlink(), "candidate already exists")
    b = json.dumps(doc, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    need(len(b) <= MAX_JSON, "evidence too large")
    with tmp.open("xb") as f:
        f.write(b)
    tmp.chmod(0o600)
    need(tmp.read_bytes() == b, "evidence read-back mismatch")
    os.replace(tmp, dest)

def target(root, ident):
    need(isinstance(ident, str) and re.fullmatch(r"[a-z0-9-]+", ident), "invalid target")
    ts = read(root, "src/targets.json")
    need(isinstance(ts, list) and ts and all(isinstance(t, dict) for t in ts), "invalid target inventory")
    ids = [t.get("id") for t in ts]
    need(all(isinstance(i, str) for i in ids) and len(ids) == len(set(ids)), "duplicate target inventory")
    found = [t for t in ts if t.get("id") == ident and t.get("enabled") is True]
    need(len(found) == 1, "unknown or disabled target")
    return found[0]

def semantics(root, ident, winner=None):
    """Local declared key. Effective form excludes unconsumed alternative config.

    Unknown config fields remain conservatively included. Shared code/workflow
    byte changes invalidate; comments in code are not semantically parsed.
    """
    t = target(root, ident)
    candidates = t["candidates"]
    need(isinstance(candidates, list) and candidates, "no candidates")
    chosen = candidates if winner is None else [c for c in candidates if c["name"] == winner]
    need(chosen and (winner is None or len(chosen) == 1), "winner invalid")
    config = {k:v for k,v in t.items() if k not in ("note", "label", "poll", "max_patch_age_days")}
    if winner is not None:
        config["candidates"] = chosen
        config.pop("pin", None)  # election policy, not changed consumed bytes
    paths = {}
    selected_bundles = chosen + t.get("extra_bundles", [])
    selected_paths = set()
    selected_resources = set()
    for b in selected_bundles:
        for side in ("include", "exclude"):
            selected_paths.add("src/patches/" + b["patch_dir"] + "/" + side + "-patches")
        if b.get("options"):
            option_path = "src/options/" + b["options"] + ".json"
            selected_paths.add(option_path)
            selected_resources.update(recipe.resource_paths(read(root, option_path)))
    for c in chosen:
        local = recipe.create(root, ident, c["name"], {})
        for item in local["components"]:
            p = item["path"]
            if p == "src/targets.json":
                continue
            if p.startswith(("src/patches/", "src/options/")) and p not in recipe.SHARED:
                if p not in selected_paths and p not in selected_resources:
                    continue
            if p in local["resource_paths"] and p not in selected_resources:
                continue
            if item["encoding"] == "identity-map":
                apps = read(root, "docs/obtainium.json")["apps"]
                matching = [a for a in apps if a.get("name") == t["label"]]
                need(len(matching) == 1, "installation mapping ambiguous")
                item = dict(item, sha256=sha({"id": matching[0]["id"]}))
            paths[(p, item["encoding"])] = item
    # Explicitly bind the new consumer and daily workflow, which the existing
    # same-run input_recipe predates. No unrelated docs or community index.
    for path in ("src/build/shadow_inputs.py", "src/build/resolved_inputs.py",
                 "src/build/dependency_observation.py", ".github/workflows/ci.yml"):
        item = recipe.component(root, path)
        paths[(path, item["encoding"])] = item
    return {"target": ident, "config": config,
            "components": sorted(paths.values(), key=lambda x:(x["path"], x["encoding"]))}

def declaration(root, ident):
    body = semantics(root, ident)
    return seal({"domain": DOMAIN, "schema": 1, "kind": "declaration", **body})

def byte_record(row, allow_empty=False):
    need(isinstance(row, dict) and hash_ok(row.get("sha256")) and
         type(row.get("bytes")) is int and row["bytes"] >= (0 if allow_empty else 1), "invalid consumed bytes")
    return {"bytes": row["bytes"], "sha256": row["sha256"]}

def realized(root, captured, env):
    ident, winner = captured["target"], captured["winner"]
    declared = declaration(root, ident)
    expected = env.get("PF_SHADOW_PLAN_KEY", "")
    need(not expected or hash_ok(expected), "malformed planned key")
    binding = "MATCH" if expected == declared["sha256"] else "DRIFT" if expected else "NO_PLAN"
    if env.get("PF_SHADOW_PLAN_REQUIRED", "false").lower() == "true" and not expected:
        binding = "MISSING_REQUIRED_PLAN"
    t = target(root, ident)
    bundles = [next(c for c in t["candidates"] if c["name"] == winner)] + t.get("extra_bundles", [])
    expected_names = ["09-" + winner + ".mpp"] + [
        str(i).zfill(2) + "-" + b["name"] + ".mpp" for i,b in enumerate(t.get("extra_bundles", []), 1)]
    observed = captured["bundles"]
    need(len(observed) == len(bundles), "consumed bundle count mismatch")
    byname = {}
    for r in observed:
        name = Path(r["path"]).name
        need(name not in byname, "duplicate consumed bundle")
        byname[name] = r
    need(set(byname) == set(expected_names), "consumed bundle names differ")
    # Actual patch CLI processes lexically staged numbered bundles.
    ordered = [{"slot": name, **byte_record(byname[name])} for name in sorted(expected_names)]
    tools = captured["tools"]
    need(len(tools) == 3, "tool coverage incomplete")
    tool_names = [Path(r["path"]).name for r in tools]
    need(tool_names[0].startswith("morphe-desktop-") and tool_names[0].endswith(".jar") and
         tool_names[1:] == ["APKEditor.jar", "pup"], "tool identity/order differs")
    material = {
        "local_effective": semantics(root, ident, winner),
        "winner": winner, "bundles": ordered,
        "tools": [{"role": role, **byte_record(r)} for role,r in zip(("patcher","apkeditor","pup"), tools)],
        "apk": byte_record(captured["patcher_input_apk"]),
        "requested": byte_record(captured["requested_ledger"], allow_empty=True),
        "package": captured["expected_package"],
        "certificate_sha256": captured["expected_certificate_sha256"],
        "continue_on_error": bool(env.get("COE")),
    }
    need(hash_ok(material["certificate_sha256"]), "invalid certificate identity")
    resolution = captured.get("resolution", {"status": "NOT_REQUESTED"})
    need(isinstance(resolution, dict) and resolution.get("status") in
         ("MATCH", "UNAVAILABLE", "NOT_REQUESTED"), "invalid resolution state")
    if resolution["status"] == "MATCH":
        import resolved_inputs
        need(resolved_inputs.verify_consumed(root, ident, captured, env) == resolution,
             "consumed resolution changed")
    elif env.get("PF_RESOLVED_REQUESTED", "false").lower() == "true":
        resolution = {"status": "UNAVAILABLE",
                      "reason": "PREPARED_DEPENDENCIES_UNAVAILABLE_OR_INVALID"}
    return seal({"domain": DOMAIN, "schema": 1, "kind": "consumed", "target": ident,
                 "declaration_sha256": declared["sha256"], "plan_sha256": expected or None,
                 "binding": binding, "material": material, "effective_sha256": sha(material),
                 "resolution": resolution,
                 "limits": ["shadow only; same-run evidence, not independent attestation",
                            "runtime/OS/container transitive identities are incomplete",
                            "source APK publisher authenticity not established"]})

def verify_consumed(root, captured, doc, env):
    unseal(doc, DOMAIN)
    need(doc.get("kind") == "consumed", "wrong evidence kind")
    need(realized(root, captured, env) == doc, "consumed or local declaration changed")
    need(doc["effective_sha256"] == sha(doc["material"]), "effective key mismatch")

class API:
    """Bounded GitHub-only JSON reads. Auth headers never follow redirects."""
    def __init__(self, repo, env):
        need(isinstance(repo, str) and re.fullmatch(REPO_PATTERN, repo), "invalid repo")
        self.repo, self.env = repo, env

    def get(self, path, limit=MAX_JSON):
        need(isinstance(path, str) and path.startswith("/repos/" + self.repo + "/") and
             not any(c in path for c in ("\n", "\r", "\\", "#")), "unsafe API path")
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "patch-factory-shadow"}
        token = self.env.get("GITHUB_TOKEN") or self.env.get("GH_TOKEN")
        if token:
            need("\n" not in token and "\r" not in token, "invalid auth")
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request("https://api.github.com" + path, headers=headers)
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            need(response.status == 200, "unexpected API response")
            b = response.read(limit + 1)
        need(len(b) <= limit, "API response oversized")
        return recipe.json_bytes(b)

    def asset(self, asset):
        # Public assets fetched without credentials; verify GitHub digest and
        # follow only GitHub's release download infrastructure.
        url = asset.get("browser_download_url", "")
        u = urllib.parse.urlparse(url)
        need(u.scheme == "https" and u.netloc == "github.com" and
             u.path.startswith("/" + self.repo + "/releases/download/") and not u.query and not u.fragment,
             "unexpected manifest asset URL")
        class SafeRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                dest = urllib.parse.urlparse(newurl)
                need(dest.scheme == "https" and dest.hostname in
                     ("github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com") and
                     dest.username is None and dest.password is None and dest.port in (None, 443),
                     "unsafe manifest redirect")
                return super().redirect_request(req, fp, code, msg, headers, newurl)
        with urllib.request.build_opener(SafeRedirect).open(
                urllib.request.Request(url, headers={"User-Agent": "patch-factory-shadow"}), timeout=30) as r:
            b = r.read(LIMIT + 1)
        need(len(b) <= LIMIT and len(b) == asset["size"], "receipt size mismatch")
        need(asset.get("digest") == "sha256:" + hashlib.sha256(b).hexdigest(), "receipt download digest mismatch")
        return recipe.json_bytes(b)

def receipt_name(ident):
    need(isinstance(ident, str) and re.fullmatch(r"[a-z0-9-]+", ident), "bad target")
    return "pf-publication-v1-" + ident + ".json"

def assets(api, release_id):
    need(type(release_id) is int and release_id > 0, "invalid release ID")
    result, seen = [], set()
    for page in range(1, 21):
        rows = api.get(f"/repos/{api.repo}/releases/{release_id}/assets?per_page=100&page={page}")
        need(isinstance(rows, list) and len(rows) <= 100, "bad release assets")
        for a in rows:
            need(type(a.get("id")) is int and a["id"] > 0 and a["id"] not in seen, "duplicate asset")
            seen.add(a["id"]); result.append(a)
        if len(rows) < 100:
            return result
    raise ValueError("shadow inputs: asset coverage exceeded bound")

def confirmed_apk(api, release, receipt):
    need(release.get("draft") is False and release.get("prerelease") is False and
         release.get("published_at") and release.get("tag_name") == receipt["tag"], "release not published")
    need(release["id"] == receipt["release_id"], "release identity mismatch")
    rows = assets(api, release["id"])
    apk = receipt["apk"]
    need(hash_ok(apk.get("sha256")) and type(apk.get("bytes")) is int and apk["bytes"] > 1000000,
         "invalid published APK identity")
    match = [a for a in rows if a.get("name") == apk["name"]]
    need(len(match) == 1, "published APK missing/ambiguous")
    a = match[0]
    need(a.get("state") == "uploaded" and a["id"] == apk["id"] and
         a.get("size") == apk["bytes"] and a.get("digest") == "sha256:" + apk["sha256"],
         "published APK metadata does not match verified bytes")
    return rows

def tag_commit(api, tag):
    need(isinstance(tag, str) and re.fullmatch(r"[a-z0-9-]+-v[0-9.]+-b[0-9]{34}", tag), "invalid publication tag")
    obj = api.get("/repos/" + api.repo + "/git/ref/tags/" + tag)["object"]
    for _ in range(5):
        if obj.get("type") == "commit":
            need(re.fullmatch(r"[0-9a-f]{40}", obj.get("sha", "")), "invalid tag commit")
            return obj["sha"]
        need(obj.get("type") == "tag" and re.fullmatch(r"[0-9a-f]{40}", obj.get("sha", "")), "invalid annotated tag")
        obj = api.get("/repos/" + api.repo + "/git/tags/" + obj["sha"])["object"]
    raise ValueError("shadow inputs: tag chain too deep")

def verify_receipt(api, release, doc, ident, proof_out=None):
    body = unseal(doc, RECEIPT_DOMAIN)
    import dependency_observation
    dependency_observation.receipt_snapshot(body)
    need(body["target"] == ident and body["repository"] == api.repo and
         body["publication"] == "confirmed" and hash_ok(body["effective_sha256"]) and
         hash_ok(body["declaration_sha256"]), "receipt identity invalid")
    need(tag_commit(api, body["tag"]) == body["source_commit"], "receipt/tag source mismatch")
    from build_identity import parse
    match = re.search(r"(-b[0-9]{34})$", body["tag"])
    need(match, "receipt build identity missing")
    parsed = parse(match[1])
    need(str(parsed["run_id"]) == body["run_id"] and str(parsed["attempt"]) == body["attempt"],
         "receipt/run tag mismatch")
    confirmed_apk(api, release, body)
    # A receipt can be stored before the enclosing workflow finishes. It is NOT
    # baseline-eligible until this exact run/attempt and its publication job succeed.
    run = api.get(f"/repos/{api.repo}/actions/runs/{body['run_id']}/attempts/{body['attempt']}")
    need(str(run.get("id")) == body["run_id"] and str(run.get("run_attempt")) == body["attempt"] and
         run.get("head_sha") == body["source_commit"] and run.get("head_branch") == "main" and
         run.get("repository", {}).get("full_name") == api.repo and
         run.get("status") == "completed" and run.get("conclusion") == "success",
         "publication run not completed successfully")
    found, count, total, seen = [], 0, None, set()
    for page in range(1, 21):
        data = api.get(f"/repos/{api.repo}/actions/runs/{body['run_id']}/attempts/{body['attempt']}/jobs?per_page=100&page={page}")
        need(isinstance(data.get("jobs"), list) and type(data.get("total_count")) is int,
             "invalid publication jobs")
        if total is None:
            total = data["total_count"]
        need(total == data["total_count"] and total > 0 and len(data["jobs"]) <= 100,
             "job inventory changed or empty")
        for job in data["jobs"]:
            need(type(job.get("id")) is int and job["id"] not in seen and
                 str(job.get("run_id")) == body["run_id"] and
                 str(job.get("run_attempt")) == body["attempt"] and job.get("head_sha") == body["source_commit"],
                 "publication job identity mismatch")
            seen.add(job["id"]); count += 1
            if job.get("name") == "Patch " + ident or str(job.get("name","")).endswith(" / Patch " + ident):
                found.append(job)
        need(count <= total, "excess publication jobs")
        if count == total:
            break
        need(len(data["jobs"]) == 100, "publication job coverage incomplete")
    need(count == total and len(found) == 1, "publication target job absent/ambiguous")
    job = found[0]
    need(job.get("status") == "completed" and job.get("conclusion") == "success", "target job failed")
    for step in ("Verify finished APK identity", "Verify release handoff (no publishing)", "Releasing APK files"):
        matching = [s for s in job.get("steps", []) if s.get("name") == step]
        need(len(matching) == 1 and matching[0].get("status") == "completed" and
             matching[0].get("conclusion") == "success", "publication step not successful")
    if proof_out is not None:
        # Store only public verification fields, not arbitrary job logs/env/URLs.
        proof_out.update({
            "run": {k: run[k] for k in ("id", "run_attempt", "head_sha", "head_branch",
                                       "status", "conclusion")},
            "repository": api.repo,
            "job": {k: job[k] for k in ("id", "run_id", "run_attempt", "head_sha", "name",
                                       "status", "conclusion")},
            "steps": [{"name": step, "status": "completed", "conclusion": "success"}
                      for step in ("Verify finished APK identity",
                                   "Verify release handoff (no publishing)", "Releasing APK files")],
            "jobs_checked": count,
            "coverage": "complete"
        })
    return body

def latest_baseline(api, ident, prefix):
    """Latest published build for this prefix must have a valid receipt.

    Never skip a newer legacy/no-receipt build and silently trust an older one.
    Full bounded release pagination; an exceeded bound is UNKNOWN.
    """
    need(re.fullmatch(r"[a-z0-9-]+", prefix), "bad prefix")
    releases, seen = [], set()
    complete = False
    for page in range(1, 21):
        part = api.get(f"/repos/{api.repo}/releases?per_page=100&page={page}")
        need(isinstance(part, list) and len(part) <= 100, "invalid release page")
        for r in part:
            need(type(r.get("id")) is int and r["id"] not in seen, "duplicate release")
            seen.add(r["id"])
            if r.get("draft") is False and r.get("prerelease") is False and str(r.get("tag_name", "")).startswith(prefix + "-v"):
                need(isinstance(r.get("published_at"), str), "missing publication time")
                releases.append(r)
        if len(part) < 100:
            complete = True; break
    need(complete, "release coverage exceeded bound")
    if not releases:
        return None, "NO_PUBLISHED_BASELINE"
    # ISO timestamps parsed rather than comparing caller-supplied strings.
    import datetime
    releases.sort(key=lambda r:(datetime.datetime.fromisoformat(r["published_at"].replace("Z","+00:00")),
                               r["id"]), reverse=True)
    r = releases[0]
    rows = assets(api, r["id"])
    qualified = [a for a in rows if a.get("name") == "pf-qualified-v1-" + ident + ".json"]
    if qualified:
        need(len(qualified) == 1, "ambiguous qualified baseline")
        import qualified_baselines
        return qualified_baselines.verify(api, r, qualified[0], ident), "VERIFIED_DURABLE_ACTIONS_RECORD"
    matches = [a for a in rows if a.get("name") == receipt_name(ident)]
    if not matches:
        return None, "LATEST_RELEASE_HAS_NO_RECEIPT"
    need(len(matches) == 1 and matches[0].get("state") == "uploaded", "ambiguous receipt")
    return verify_receipt(api, r, api.asset(matches[0]), ident), "VERIFIED"

def compare(consumed, baseline, reason):
    unseal(consumed, DOMAIN)
    need(consumed.get("kind") == "consumed", "not consumed evidence")
    need(consumed.get("binding") in ("MATCH", "NO_PLAN", "DRIFT", "MISSING_REQUIRED_PLAN") and
         consumed.get("effective_sha256") == sha(consumed["material"]), "invalid effective evidence")
    if consumed["binding"] == "DRIFT":
        return {"state": "BLOCKED", "reason": "PLAN_BUILD_DECLARATION_DRIFT", "authority": "shadow-only"}
    if consumed["binding"] == "MISSING_REQUIRED_PLAN":
        return {"state": "UNKNOWN", "reason": "REQUIRED_PLAN_UNAVAILABLE", "authority": "shadow-only"}
    if consumed.get("resolution", {}).get("status") == "UNAVAILABLE":
        return {"state": "UNKNOWN", "reason": "PREPARED_DEPENDENCIES_UNAVAILABLE_OR_INVALID", "authority": "shadow-only"}
    if baseline is None:
        return {"state": "UNKNOWN", "reason": reason, "authority": "shadow-only"}
    need(baseline["target"] == consumed["target"], "comparison target mismatch")
    return {"state": "UNCHANGED" if baseline["effective_sha256"] == consumed["effective_sha256"] else "BUILD",
            "reason": "VERIFIED_CONSUMED_KEY_COMPARISON", "authority": "shadow-only"}

def plan(root, env):
    ts = read(root, "src/targets.json")
    need(isinstance(ts, list) and ts and all(isinstance(t, dict) for t in ts), "empty or invalid plan targets")
    ids = [t.get("id") for t in ts]
    need(all(isinstance(i, str) and re.fullmatch(r"[a-z0-9-]+", i) for i in ids) and
         len(set(ids)) == len(ids), "invalid or duplicate plan IDs")
    need(all(type(t.get("enabled")) is bool and type(t.get("poll", False)) is bool for t in ts),
         "invalid plan flags")
    keys, rows = {}, []
    for t in ts:
        if t.get("enabled") is True and t.get("poll") is True:
            ident = t["id"]
            need(ident not in keys, "duplicate planned target")
            doc = declaration(root, ident)
            keys[ident] = doc["sha256"]
            rows.append({"target": ident, "declaration_sha256": doc["sha256"],
                         "state": "RESOLVE", "reason": "REMOTE_CONSUMED_IDENTITIES_NOT_YET_KNOWN"})
    write(root, "shadow-evidence/plan.json", {"mode": "shadow-only", "targets": rows,
          "limits": "This stage does not elect/download remote inputs or alter the legacy matrix."})
    # Fixed safe hash/ID JSON only, bounded to GitHub output size.
    text = ("keys=" + json.dumps(keys, separators=(",", ":")) + "\n" +
            "resolution_matrix=" + json.dumps({"target": list(keys)}, separators=(",", ":")) + "\n")
    need(len(text.encode()) < 60000 and env.get("GITHUB_OUTPUT"), "shadow output unavailable")
    with open(env["GITHUB_OUTPUT"], "a") as f:
        f.write(text)
    return keys

def observe(root, ident, env, api=None):
    captured = read(root, ".build-inputs.json")
    from artifact_identity import verify_records
    recipe.verify(root, captured["target"], captured["winner"], captured["local_input_recipe"], env)
    verify_records(Path(root), captured["tools"] + captured["bundles"] +
                   [captured["patcher_input_apk"], captured["requested_ledger"]])
    doc = realized(root, captured, env)
    need(captured["target"] == ident, "capture target differs")
    api = api or API(env.get("GITHUB_REPOSITORY"), env)
    try:
        baseline, reason = latest_baseline(api, ident, target(root, ident)["tag_prefix"])
        decision = compare(doc, baseline, reason)
    except (ValueError, KeyError, TypeError, OSError):
        baseline = None
        decision = {"state": "UNKNOWN", "reason": "BASELINE_UNAVAILABLE_OR_INVALID", "authority": "shadow-only"}
    if doc["binding"] == "DRIFT":
        decision = {"state": "BLOCKED", "reason": "PLAN_BUILD_DECLARATION_DRIFT", "authority": "shadow-only"}
    elif doc["binding"] == "MISSING_REQUIRED_PLAN":
        decision = {"state": "UNKNOWN", "reason": "REQUIRED_PLAN_UNAVAILABLE", "authority": "shadow-only"}
    result = {"mode": "shadow-only", "target": ident, "consumed": doc, "decision": decision,
              "baseline_tag": baseline["tag"] if baseline else None}
    write(root, "shadow-evidence/" + ident + ".json", result)
    return result

def publish_receipt(root, ident, env, api=None, upload=None):
    """Runs only after Release succeeded. Never uploads APKs, overwrites or prunes."""
    import release_contract
    from build_identity import verify_run
    need(env.get("GITHUB_REF") == "refs/heads/main", "receipt requires main publication")
    fields = release_contract.verify(root, ident)
    verify_run(fields["suffix"], env)
    report = read(root, "build-evidence/" + ident + ".json")
    captured = report["inputs"]
    doc = realized(root, captured, env)
    need(doc["binding"] in ("MATCH", "NO_PLAN"), "missing or drifting plan cannot advance baseline")
    need(doc.get("resolution", {}).get("status") != "UNAVAILABLE",
         "unavailable prepared inputs cannot advance baseline")
    # Recheck the actual consumed files, not just the identity report assertions.
    from artifact_identity import verify_records
    verify_records(Path(root), captured["tools"] + captured["bundles"] +
                   [captured["patcher_input_apk"], captured["requested_ledger"]])
    api = api or API(env.get("GITHUB_REPOSITORY"), env)
    r = api.get("/repos/" + api.repo + "/releases/tags/" + fields["tag"])
    need(tag_commit(api, fields["tag"]) == captured["source_commit"], "published tag not build commit")
    rows = assets(api, r["id"])
    found = [a for a in rows if a.get("name") == fields["apkname"]]
    need(len(found) == 1, "published APK absent/ambiguous")
    body = {"domain": RECEIPT_DOMAIN, "schema": 1, "target": ident, "repository": api.repo,
            "publication": "confirmed", "source_commit": captured["source_commit"],
            "run_id": env["GITHUB_RUN_ID"], "attempt": env["GITHUB_RUN_ATTEMPT"],
            "tag": fields["tag"], "release_id": r["id"],
            "declaration_sha256": doc["declaration_sha256"],
            "effective_sha256": doc["effective_sha256"],
            "apk": {"id": found[0]["id"], "name": fields["apkname"],
                    "bytes": report["output"]["bytes"], "sha256": fields["sha256"]},
            "eligibility": "REQUIRES_COMPLETED_SUCCESSFUL_RUN_AND_TARGET_JOB",
            "limits": ["same-run recorded evidence, not an independent signature or trust anchor",
                       "runtime/OS/container transitive dependencies incomplete"]}
    if doc.get("resolution", {}).get("status") == "MATCH":
        import dependency_observation
        body["prepared_dependencies"] = dependency_observation.snapshot(root, ident, env, captured)
    confirmed_apk(api, r, body)
    receipt = seal(body)
    name = receipt_name(ident)
    existing = [a for a in rows if a.get("name") == name]
    need(len(existing) <= 1, "duplicate publication receipt")
    if existing:
        need(api.asset(existing[0]) == receipt, "existing receipt differs; never overwrite")
        return receipt
    write(root, "shadow-evidence/" + name, receipt)
    path = Path(root) / "shadow-evidence" / name
    if upload is None:
        def upload(path, tag):
            # Token supplied via gh environment, never argv or public logs.
            p = subprocess.run(["gh", "release", "upload", tag, str(path), "--repo", api.repo],
                               env=env, capture_output=True, timeout=120)
            need(p.returncode == 0, "receipt upload failed after APK publication; do not overwrite/rebuild")
    upload(path, fields["tag"])
    # A successful upload response alone is not persistence evidence.
    after = [a for a in assets(api, r["id"]) if a.get("name") == name]
    need(len(after) == 1 and api.asset(after[0]) == receipt, "receipt read-back failed; publication is partial")
    return receipt

def main():
    root, env = Path.cwd(), dict(os.environ)
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        mode = sys.argv[1]
        if mode == "plan":
            plan(root, env)
        elif mode == "observe":
            result = observe(root, sys.argv[2], env)
            print("SHADOW_STATE=" + result["decision"]["state"])
        elif mode == "receipt":
            publish_receipt(root, sys.argv[2], env)
            print("PUBLICATION_RECEIPT_STORED_PENDING_SUCCESSFUL_RUN")
        else:
            raise ValueError("unknown shadow mode")
        return 0
    except (ValueError, KeyError, TypeError, OSError, IndexError, subprocess.TimeoutExpired):
        # Retain bounded non-secret failure evidence even when capture/reader
        # validation prevents producing a consumed key.
        try:
            ident = sys.argv[2] if len(sys.argv) > 2 else None
            if mode == "plan":
                dest = "shadow-evidence/plan.json"
            elif mode in ("observe", "receipt") and isinstance(ident, str) and re.fullmatch(r"[a-z0-9-]+", ident):
                dest = "shadow-evidence/" + ident + "-" + mode + "-unknown.json"
            else:
                dest = None
            if dest:
                write(root, dest, {"mode":"shadow-only", "stage":mode, "target":ident,
                                  "state":"UNKNOWN", "reason":"INPUT_OR_PUBLICATION_EVIDENCE_UNAVAILABLE"})
        except (ValueError, OSError):
            pass
        print("::warning::shadow evidence unavailable or invalid; no unchanged/baseline success claimed",
              file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
