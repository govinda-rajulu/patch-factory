#!/usr/bin/env python3
"""Compare prepared dependency bytes before patching, including unbuilt targets.

MATCHED_SUBSET is not a full input fingerprint or authority to skip/build.
No APK resolution, signing, dispatch, release mutation or baseline advancement.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import input_recipe as recipe
import resolved_inputs as resolved
import shadow_inputs as shadow

DOMAIN = "patch-factory/prepared-dependency-subset/v1"
OBSERVATION = "patch-factory/dependency-observation/v1"
AUTHORITY = "shadow-only; never selects or skips builds"
LIMITS = ["source APK bytes not compared", "runtime/OS/transitive closure not compared",
          "effective/default patch execution not compared",
          "repository Actions evidence, not independent attestation"]
STATES = ("MATCHED_SUBSET", "CHANGED_SUBSET", "UNKNOWN")


def need(ok, why):
    if not ok:
        raise ValueError("dependency observation: " + why)


def run_identity(env):
    need(isinstance(env, dict), "invalid run identity object")
    patterns = {"GITHUB_SHA": r"[0-9a-f]{40}", "GITHUB_RUN_ID": r"[1-9][0-9]{0,19}",
                "GITHUB_RUN_ATTEMPT": r"[1-9][0-9]{0,5}", "GITHUB_REPOSITORY": shadow.REPO_PATTERN}
    need(all(isinstance(env.get(k), str) and re.fullmatch(v, env[k]) for k, v in patterns.items()),
         "invalid run identity")
    return {k: env[k] for k in patterns}


def validate_snapshot(doc):
    body = shadow.unseal(doc, DOMAIN)
    need(set(body) == {"domain", "schema", "target", "run", "material", "subset_sha256",
                       "lock_sha256", "dependency_sha256", "authority", "limits"},
         "unexpected subset fields")
    need(body["run"] == run_identity(body["run"]), "unexpected run fields")
    need(body["authority"] == AUTHORITY and body["limits"] == LIMITS, "overstated dependency coverage")
    ident, m = body["target"], body["material"]
    need(isinstance(ident, str) and re.fullmatch(r"[a-z0-9-]+", ident), "invalid target")
    need(isinstance(m, dict) and set(m) == {"target", "winner", "version", "local_effective_sha256",
                                          "patcher", "bundles"} and m["target"] == ident,
         "invalid subset material")
    need(isinstance(m["winner"], str) and re.fullmatch(r"[A-Za-z0-9_-]+", m["winner"]) and
         isinstance(m["version"], str) and re.fullmatch(r"[0-9]+(?:[.][0-9]+)*", m["version"]),
         "invalid resolved selection")
    need(all(shadow.hash_ok(body[k]) for k in ("subset_sha256", "dependency_sha256", "lock_sha256")) and
         shadow.hash_ok(m["local_effective_sha256"]), "invalid digest")
    need(shadow.byte_record(m["patcher"]) == m["patcher"], "invalid patcher record")
    rows = m["bundles"]
    need(isinstance(rows, list) and 0 < len(rows) <= 9 and all(isinstance(r, dict) for r in rows),
         "invalid bundle inventory")
    need(all(set(r) == {"slot", "role", "bytes", "sha256"} and
             isinstance(r["slot"], str) and re.fullmatch(r"0[1-9]-[A-Za-z0-9_-]+[.]mpp", r["slot"]) and
             r["role"] in ("extra", "winner") for r in rows), "invalid bundle slot")
    need([r["slot"] for r in rows] == sorted({r["slot"] for r in rows}), "duplicate or unordered slots")
    need([r["slot"] for r in rows if r["role"] == "winner"] == ["09-" + m["winner"] + ".mpp"],
         "invalid winning slot")
    extras = [r for r in rows if r["role"] == "extra"]
    need(all(r["slot"].startswith(str(i).zfill(2) + "-") for i, r in enumerate(extras, 1)),
         "noncontiguous extra order")
    for row in rows:
        shadow.byte_record(row)
        need(row["bytes"] <= resolved.MAX_FILE, "oversized bundle")
    need(m["patcher"]["bytes"] <= resolved.MAX_FILE and
         m["patcher"]["bytes"] + sum(r["bytes"] for r in rows) <= resolved.MAX_TOTAL,
         "oversized dependency set")
    need(body["subset_sha256"] == recipe.digest(m), "subset digest differs")
    return body


def snapshot(root, ident, env, captured=None):
    lock = resolved.verify(root, ident, env)
    if captured is not None:
        need(captured.get("resolution") == resolved.verify_consumed(root, ident, captured, env),
             "publication did not consume this dependency lock")
    m = lock["material"]
    material = {"target": ident, "winner": m["winner"], "version": m["version"],
                "local_effective_sha256": recipe.digest(shadow.semantics(root, ident, m["winner"])),
                "patcher": shadow.byte_record(m["patcher"]),
                "bundles": [{"slot": r["slot"], "role": r["role"], **shadow.byte_record(r)}
                            for r in sorted(m["bundles"], key=lambda r: r["slot"])]}
    doc = shadow.seal({"domain": DOMAIN, "schema": 1, "target": ident, "run": lock["run"],
                       "material": material, "subset_sha256": recipe.digest(material),
                       "lock_sha256": lock["sha256"], "dependency_sha256": lock["dependency_sha256"],
                       "authority": AUTHORITY, "limits": LIMITS})
    validate_snapshot(doc)
    return doc


def receipt_snapshot(receipt):
    """Optional migration field: old receipts remain usable, not comparable here."""
    if "prepared_dependencies" not in receipt:
        return None
    doc = receipt["prepared_dependencies"]
    body = validate_snapshot(doc)
    expected = {"GITHUB_SHA": receipt["source_commit"], "GITHUB_RUN_ID": receipt["run_id"],
                "GITHUB_RUN_ATTEMPT": receipt["attempt"], "GITHUB_REPOSITORY": receipt["repository"]}
    need(body["target"] == receipt["target"] and body["run"] == expected,
         "receipt subset belongs to another source/run/attempt/target")
    return doc


def compare(current, previous):
    a, b = validate_snapshot(current), validate_snapshot(previous)
    need(a["target"] == b["target"], "comparison target differs")
    need(a["run"]["GITHUB_REPOSITORY"] == b["run"]["GITHUB_REPOSITORY"], "comparison repository differs")
    fields = ("winner", "version", "local_effective_sha256", "patcher", "bundles")
    changes = [key for key in fields if a["material"][key] != b["material"][key]]
    return {"state": "CHANGED_SUBSET" if changes else "MATCHED_SUBSET",
            "reason": "VERIFIED_PREPARED_SUBSET_COMPARISON",
            "changed_components": changes}


def observe(root, ident, env, api=None):
    root = Path(root).resolve()
    identity = resolved.identity(root, env)
    target = shadow.target(root, ident)
    current = None
    baseline_tag = None
    trust = None
    decision = {"state": "UNKNOWN", "reason": "PREPARED_DEPENDENCIES_UNAVAILABLE_OR_INVALID",
                "changed_components": []}
    try:
        current = snapshot(root, ident, env)
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        pass
    if current is not None:
        try:
            api = api or shadow.API(identity["GITHUB_REPOSITORY"], resolved.safe_env(env))
            baseline, reason = shadow.latest_baseline(api, ident, target["tag_prefix"])
            if baseline is None:
                decision["reason"] = reason
            else:
                need(reason in ("VERIFIED", "VERIFIED_DURABLE_ACTIONS_RECORD"), "unverified baseline")
                previous = receipt_snapshot(baseline)
                baseline_tag, trust = baseline["tag"], reason
                if previous is None:
                    decision["reason"] = "LATEST_PUBLICATION_HAS_NO_PREPARED_SUBSET"
                else:
                    decision = compare(current, previous)
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
            baseline_tag, trust = None, None
            decision["reason"] = "BASELINE_UNAVAILABLE_OR_INVALID"
    doc = shadow.seal({"domain": OBSERVATION, "schema": 1, "target": ident, "run": identity,
                       "current": current, "decision": decision, "baseline_tag": baseline_tag,
                       "baseline_trust": trust, "authority": AUTHORITY, "limits": LIMITS})
    shadow.write(root, "resolved-observation/" + ident + "-comparison.json", doc)
    return doc


def expected_targets(root):
    rows = shadow.read(root, "src/targets.json")
    need(isinstance(rows, list) and rows and all(isinstance(t, dict) for t in rows), "invalid targets")
    ids = [t.get("id") for t in rows]
    need(all(isinstance(i, str) and re.fullmatch(r"[a-z0-9-]+", i) for i in ids) and
         len(set(ids)) == len(ids) and
         all(type(t.get("enabled")) is bool and type(t.get("poll", False)) is bool for t in rows),
         "invalid target flags or duplicate identity")
    return [t["id"] for t in rows if t["enabled"] and t.get("poll", False)]


def observation(doc, ident, identity):
    body = shadow.unseal(doc, OBSERVATION)
    need(set(body) == {"domain", "schema", "target", "run", "current", "decision",
                       "baseline_tag", "baseline_trust", "authority", "limits"} and
         body["target"] == ident and body["run"] == identity and
         body["authority"] == AUTHORITY and body["limits"] == LIMITS, "observation identity/scope differs")
    decision = body["decision"]
    need(isinstance(decision, dict) and set(decision) == {"state", "reason", "changed_components"} and
         decision["state"] in STATES and isinstance(decision["reason"], str) and
         re.fullmatch(r"[A-Z_]+", decision["reason"]), "invalid decision")
    changes = decision["changed_components"]
    need(isinstance(changes, list) and all(isinstance(k, str) for k in changes) and
         len(set(changes)) == len(changes) and
         all(k in ("winner", "version", "local_effective_sha256", "patcher", "bundles") for k in changes),
         "invalid comparison components")
    if body["current"] is not None:
        current = validate_snapshot(body["current"])
        need(current["target"] == ident and current["run"] == identity, "current snapshot identity differs")
    if decision["state"] != "UNKNOWN":
        need(body["current"] is not None and body["baseline_trust"] in
             ("VERIFIED", "VERIFIED_DURABLE_ACTIONS_RECORD") and
             isinstance(body["baseline_tag"], str) and
             re.fullmatch(r"[a-z0-9-]+-v[0-9.]+-b[0-9]{34}", body["baseline_tag"]) and
             decision["reason"] == "VERIFIED_PREPARED_SUBSET_COMPARISON",
             "comparison lacks qualified baseline")
        need(bool(changes) == (decision["state"] == "CHANGED_SUBSET"), "decision differs from changes")
    return body


def aggregate(root, env):
    """Read one namespaced artifact per expected target; missing != healthy zero."""
    root = Path(root).resolve()
    identity = resolved.identity(root, env)
    expected = expected_targets(root)
    directory = root / "dependency-observations"
    prefixes = {("resolved-observation-" + ident + "-" + identity["GITHUB_RUN_ID"] + "-" +
                 identity["GITHUB_RUN_ATTEMPT"]): ident for ident in expected}
    rows, issues = [], []
    if directory.is_symlink():
        issues.append("UNSAFE_ARTIFACT_ROOT")
    elif directory.exists():
        if not directory.is_dir():
            issues.append("INVALID_ARTIFACT_ROOT")
        else:
            for p in directory.iterdir():
                if p.name not in prefixes or p.is_symlink() or not p.is_dir():
                    issues.append("UNEXPECTED_OR_UNSAFE_ARTIFACT")
    valid = 0
    for artifact, ident in prefixes.items():
        row = {"target": ident, "state": "UNKNOWN", "reason": "MISSING_OR_INVALID_OBSERVATION",
               "changed_components": []}
        try:
            folder = root / "dependency-observations" / artifact
            need(not folder.is_symlink() and folder.is_dir() and
                 all(p.name in (ident + ".json", ident + "-comparison.json") and
                     p.is_file() and not p.is_symlink() for p in folder.iterdir()),
                 "artifact contents differ")
            path = "dependency-observations/" + artifact + "/" + ident + "-comparison.json"
            body = observation(shadow.read(root, path), ident, identity)
            need(body["current"] is None or body["current"]["material"]["local_effective_sha256"] ==
                 recipe.digest(shadow.semantics(root, ident, body["current"]["material"]["winner"])),
                 "current local recipe differs")
            row.update(body["decision"], baseline_tag=body["baseline_tag"])
            valid += 1
        except (ValueError, KeyError, TypeError, OSError):
            pass
        rows.append(row)
    if issues:
        for row in rows:
            row.update(state="UNKNOWN", reason="ARTIFACT_INVENTORY_INVALID", changed_components=[])
    report = {"schema": 1, "run": identity, "authority": AUTHORITY, "limits": LIMITS,
              "expected_targets": len(expected), "validated_observations": valid,
              "coverage": "complete" if valid == len(expected) and not issues and expected else "incomplete",
              "inventory_issues": sorted(set(issues)), "targets": rows,
              "counts": {state: sum(r["state"] == state for r in rows) for state in STATES}}
    shadow.write(root, "dependency-report/report.json", report)
    lines = ["## Prepared dependency comparison (shadow only)", "",
             "This never selects or skips a build. Matching patcher/bundle bytes are only a subset.",
             "APK bytes, runtime closure and effective/default patch execution remain uncompared.", "",
             "| Target | Result | Reason | Changed components |",
             "| --- | --- | --- | --- |"]
    lines += ["| " + r["target"] + " | " + r["state"] + " | " + r["reason"] + " | " +
              (", ".join(r["changed_components"]) or "none reported") + " |" for r in rows]
    lines += ["", "Coverage: " + report["coverage"] + ". Valid observations: " + str(valid) +
              "/" + str(len(expected)) + ". UNKNOWN is not unchanged.", ""]
    summary = "\n".join(lines)
    if env.get("GITHUB_STEP_SUMMARY"):
        with open(env["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(summary)
    return report


def main():
    try:
        root, env = Path.cwd(), dict(os.environ)
        if len(sys.argv) == 3 and sys.argv[1] == "observe":
            doc = observe(root, sys.argv[2], env)
            print("DEPENDENCY_SUBSET=" + doc["decision"]["state"])
        elif len(sys.argv) == 2 and sys.argv[1] == "aggregate":
            report = aggregate(root, env)
            print("DEPENDENCY_OBSERVATION_COVERAGE=" + report["coverage"])
        else:
            raise ValueError("usage")
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        print("::warning::prepared dependency comparison unavailable; no build-selection authority",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
