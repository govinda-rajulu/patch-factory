#!/usr/bin/env python3
"""Bounded source-preparation coverage. Read-only, never build-selection authority."""
import os
from pathlib import Path
import re
import sys

import dependency_observation as dependency
import resolved_inputs as resolved
import shadow_inputs as shadow
import source_inputs as source

AUTHORITY = "shadow-only; never selects or skips builds"
STATES = ("MATCHED_SOURCE_SUBSET", "CHANGED_SOURCE_SUBSET", "UNKNOWN")
DOMAIN = "patch-factory/source-observation/v1"


def need(ok, why):
    if not ok:
        raise ValueError("source report: " + why)


def snapshot(doc, ident, identity):
    body = shadow.unseal(doc, "patch-factory/prepared-source-subset/v1")
    need(set(body) == {"domain", "schema", "target", "run", "apk", "limits"} and
         body["target"] == ident and body["run"] == identity and
         body["limits"] == source.LIMITS, "snapshot scope differs")
    need(shadow.byte_record(body["apk"]) == body["apk"] and
         1000000 < body["apk"]["bytes"] <= resolved.MAX_FILE, "invalid source bytes")
    return body


def observation(doc, ident, identity):
    body = shadow.unseal(doc, DOMAIN)
    need(set(body) == {"domain", "schema", "target", "run", "current", "baseline_tag",
                       "decision", "limits"} and body["target"] == ident and
         body["run"] == identity and body["limits"] == source.LIMITS, "observation scope differs")
    decision = body["decision"]
    need(isinstance(decision, dict) and set(decision) == {"state", "reason"} and
         decision["state"] in STATES and isinstance(decision["reason"], str) and
         re.fullmatch(r"[A-Z_]+", decision["reason"]), "invalid source decision")
    if body["current"] is not None:
        snapshot(body["current"], ident, identity)
    if body["baseline_tag"] is not None:
        need(isinstance(body["baseline_tag"], str) and
             re.fullmatch(r"[a-z0-9-]+-v[0-9.]+-b[0-9]{34}", body["baseline_tag"]),
             "invalid baseline tag")
    if decision["state"] != "UNKNOWN":
        need(body["current"] is not None and body["baseline_tag"] is not None and
             decision["reason"] == "VERIFIED_SOURCE_BYTES_COMPARISON", "comparison lacks source/baseline")
    return body


def preparation(doc, root, ident, identity):
    if isinstance(doc, dict) and doc.get("status") == "UNKNOWN":
        need(set(doc) == {"target", "status", "reason", "limits"} and
             doc["target"] == ident and doc["reason"] == "SOURCE_PREPARATION_FAILED" and
             doc["limits"] == source.LIMITS, "invalid failure marker")
        # This older marker has no run seal. It can report failure only, never success.
        return None
    body = shadow.unseal(doc, source.DOMAIN)
    need(set(body) == {"domain", "schema", "target", "run", "dependency_lock_sha256",
                       "apk", "metadata", "limits"} and body["target"] == ident and
         body["run"] == identity and body["limits"] == source.LIMITS and
         shadow.hash_ok(body["dependency_lock_sha256"]), "prepared source scope differs")
    row = body["apk"]
    need(set(row) == {"path", "bytes", "sha256"} and row["path"] == "source.apk" and
         1000000 < shadow.byte_record(row)["bytes"] <= resolved.MAX_FILE, "invalid prepared APK")
    source.validate_metadata(body["metadata"], shadow.target(root, ident))
    return shadow.byte_record(row)


def aggregate(root, env):
    root = Path(root).resolve()
    identity = resolved.identity(root, env)
    expected = dependency.expected_targets(root)
    folder = root / "source-observations"
    names = {f"source-observation-{ident}-{identity['GITHUB_RUN_ID']}-{identity['GITHUB_RUN_ATTEMPT']}": ident
             for ident in expected}
    issues, rows = [], []
    if folder.is_symlink() or folder.exists() and not folder.is_dir():
        issues.append("UNSAFE_ARTIFACT_ROOT")
    elif folder.exists():
        if any(p.name not in names or p.is_symlink() or not p.is_dir() for p in folder.iterdir()):
            issues.append("UNEXPECTED_OR_UNSAFE_ARTIFACT")
    for name, ident in names.items():
        row = {"target": ident, "observation": "INVALID_OR_MISSING", "preparation": "UNKNOWN",
               "state": "UNKNOWN", "reason": "MISSING_OR_INVALID_SOURCE_EVIDENCE", "baseline_tag": None}
        try:
            need(not issues, "invalid inventory")
            directory = folder / name
            need(directory.is_dir() and not directory.is_symlink() and
                 {p.name for p in directory.iterdir()} == {ident + ".json", ident + "-comparison.json"} and
                 all(p.is_file() and not p.is_symlink() for p in directory.iterdir()),
                 "missing or unexpected evidence files")
            prefix = "source-observations/" + name + "/"
            observed = observation(shadow.read(root, prefix + ident + "-comparison.json"), ident, identity)
            prepared = preparation(shadow.read(root, prefix + ident + ".json"), root, ident, identity)
            if observed["current"] is not None:
                need(prepared == observed["current"]["apk"], "prepared/observed source bytes differ")
            row.update(observation="VALID", preparation="PREPARED" if prepared else "UNKNOWN",
                       baseline_tag=observed["baseline_tag"], **observed["decision"])
            if prepared is None:
                need(observed["current"] is None and observed["decision"]["state"] == "UNKNOWN",
                     "failure marker conflicts with successful comparison")
                row["reason"] = "SOURCE_PREPARATION_FAILED"
        except (ValueError, TypeError, KeyError, OSError):
            row.update(observation="INVALID_OR_MISSING", preparation="UNKNOWN", state="UNKNOWN",
                       reason="ARTIFACT_INVENTORY_INVALID" if issues else "MISSING_OR_INVALID_SOURCE_EVIDENCE",
                       baseline_tag=None)
        rows.append(row)
    valid = sum(r["observation"] == "VALID" for r in rows)
    prepared = sum(r["preparation"] == "PREPARED" for r in rows)
    report = {"schema": 1, "run": identity, "authority": AUTHORITY, "limits": source.LIMITS,
              "expected_targets": len(expected), "validated_observations": valid,
              "prepared_targets": prepared,
              "coverage": "complete" if expected and valid == len(expected) and not issues else "incomplete",
              "preparation_coverage": "complete" if expected and prepared == len(expected) and not issues else "incomplete",
              "inventory_issues": sorted(set(issues)), "targets": rows,
              "counts": {state: sum(r["state"] == state for r in rows) for state in STATES}}
    shadow.write(root, "source-report/report.json", report)
    lines = ["## Prepared source APK coverage (shadow only)", "",
             "Complete observation coverage does not mean successful preparation or unchanged inputs.",
             "No build-selection authority; runtime/default closure and original authenticity remain unverified.", "",
             "| Target | Preparation | Comparison | Reason |", "| --- | --- | --- | --- |"]
    lines += ["| " + r["target"] + " | " + r["preparation"] + " | " + r["state"] + " | " +
              r["reason"] + " |" for r in rows]
    lines += ["", f"Validated observations: {valid}/{len(expected)}; prepared sources: {prepared}/{len(expected)}.",
              "UNKNOWN is not unchanged. JSON evidence, not green job badges, determines these counts.", ""]
    if env.get("GITHUB_STEP_SUMMARY"):
        with open(env["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write("\n".join(lines))
    return report


def main():
    try:
        need(len(sys.argv) == 1, "no arguments supported")
        report = aggregate(Path.cwd(), dict(os.environ))
        print("SOURCE_OBSERVATION_COVERAGE=" + report["coverage"])
        print("SOURCE_PREPARATION_COVERAGE=" + report["preparation_coverage"])
        return 0
    except (ValueError, TypeError, KeyError, OSError):
        print("::warning::source coverage report unavailable; no build-selection authority", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
