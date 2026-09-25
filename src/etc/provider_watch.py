#!/usr/bin/env python3
"""Bounded patch-name observations, not version/options or build authority.

Reuses build transport. Failed/empty reads never enter the delta calculation.
Committed baselines are read-only, including when issue delivery fails.
"""
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/build"))
import github_bundle
import github_patcher
import extra_bundle

LIMIT = 2 * 1024 * 1024
SAFE = r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
LIMITS = [
    "Patch names only; supported-version, option and effective-default changes are NOT compared.",
    "Legacy committed name baselines have no bound provider digest; deltas require human review.",
    "No baseline advancement, patch selection, build scheduling or publication authority.",
    "Transport hashes are not independent publisher authenticity or device validation.",
]


class WatchError(ValueError):
    """Only fixed local error codes may enter the public report."""


def need(ok, message):
    if not ok:
        raise WatchError(message)


def field(value):
    need(isinstance(value, str) and re.fullmatch(SAFE, value), "INVALID_IDENTITY")
    return value


def inventory(targets):
    need(isinstance(targets, list) and targets, "EMPTY_CONFIG")
    rows, ids, keys = [], set(), set()
    for target in targets:
        need(isinstance(target, dict) and type(target.get("enabled")) is bool, "INVALID_TARGET")
        tid = field(target.get("id"))
        need(tid not in ids, "DUPLICATE_TARGET")
        ids.add(tid)
        if not target["enabled"]:
            continue
        package = field(target.get("package"))
        candidates, extras = target.get("candidates"), target.get("extra_bundles", [])
        need(isinstance(candidates, list) and candidates and isinstance(extras, list), "INVALID_PROVIDERS")
        for role, providers in (("candidate", candidates), ("extra", extras)):
            for provider in providers:
                need(isinstance(provider, dict), "INVALID_PROVIDER")
                name = field(provider.get("name"))
                host = provider.get("host", "github")
                need(host in ("github", "gitlab"), "UNSUPPORTED_HOST")
                owner, repo = field(provider.get("owner")), field(provider.get("repo"))
                channel = provider.get("channel")
                need(channel in ("prerelease", "latest"), "INVALID_CHANNEL")
                project = provider.get("project_id")
                if host == "gitlab":
                    need(type(project) is int and project > 0, "INVALID_PROJECT")
                baseline = name + "-" + package + ".names"
                need(baseline not in keys, "AMBIGUOUS_BASELINE_IDENTITY")
                keys.add(baseline)
                rows.append(dict(target=tid, package=package, role=role, name=name, host=host,
                                 owner=owner, repo=repo, channel=channel, project_id=project,
                                 patch_dir=field(provider.get("patch_dir")), baseline=baseline))
    need(0 < len(rows) <= 100, "EMPTY_OR_EXCESSIVE_COVERAGE")
    return rows


def names_from_output(data, returncode):
    need(returncode == 0, "LIST_COMMAND_FAILED")
    need(0 < len(data) <= LIMIT, "EMPTY_OR_OVERSIZED_OUTPUT")
    text = data.decode("utf-8")
    names = [line[6:] for line in text.splitlines() if line.startswith("Name: ")]
    need(names and len(names) <= 10000, "NO_PATCH_NAMES")
    need(all(n.strip() == n and n and len(n) <= 300 and
             not any(ord(c) < 32 or ord(c) == 127 for c in n) for n in names), "INVALID_PATCH_NAME")
    need(len(names) == len(set(names)), "DUPLICATE_PATCH_NAME")
    return sorted(names)


def delta(root, row, names):
    path = root / "docs/review/providers" / row["baseline"]
    need(not path.is_symlink(), "INVALID_BASELINE")
    if not path.exists():
        return dict(state="MISSING", added=None, removed=None)
    need(path.is_file() and 0 < path.stat().st_size <= LIMIT, "INVALID_BASELINE")
    old = path.read_text(encoding="utf-8").splitlines()
    need(old and all(n and n.strip() == n and len(n) <= 300 and
                    not any(ord(c) < 32 or ord(c) == 127 for c in n) for n in old)
         and len(old) == len(set(old)), "INVALID_BASELINE")
    return dict(state="LEGACY_NAMES", added=sorted(set(names) - set(old)),
                removed=sorted(set(old) - set(names)))


def fingerprint(path, expected):
    need(path.is_file() and not path.is_symlink(), "INPUT_FILE_INVALID")
    need(path.stat().st_size == expected["bytes"], "INPUT_SIZE_DRIFT")
    need(hashlib.sha256(path.read_bytes()).hexdigest() == expected["sha256"], "INPUT_HASH_DRIFT")


class Observer:
    def __init__(self, root, work):
        self.root, self.work = root, work
        self.patcher, self.cache = None, {}

    def __call__(self, row):
        if self.patcher is None:
            self.patcher = github_patcher.fetch(self.work / "patcher", os.environ)
        key = (row["host"], row["owner"], row["repo"], row["project_id"], row["channel"], row["role"])
        if key not in self.cache:
            directory = self.work / ("bundle-" + str(len(self.cache)))
            if row["role"] == "candidate" and row["host"] == "github":
                meta = github_bundle.fetch(row["owner"], row["repo"], row["channel"], directory, os.environ)
            else:
                ident = str(row["project_id"]) if row["host"] == "gitlab" else row["owner"] + "/" + row["repo"]
                path = directory / "bundle.mpp"
                meta = extra_bundle.fetch(row["host"], ident, row["channel"], path, os.environ)
                meta["path"] = str(path)
            self.cache[key] = meta
        meta = self.cache[key]
        jar, bundle = Path(self.patcher["path"]), Path(meta["path"])
        fingerprint(jar, self.patcher)
        fingerprint(bundle, meta)
        # Provider code executes without GitHub credentials in its environment.
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "JAVA_HOME", "HOME", "LANG", "LC_ALL")}
        argv = ["java", "-jar", str(jar), "list-patches", "--patches=" + str(bundle),
                "-x", "-u", "--with-packages", "--with-versions", "-f", row["package"]]
        with tempfile.TemporaryFile() as output:
            result = subprocess.run(argv, cwd=self.root, env=env, stdout=output,
                                    stderr=subprocess.DEVNULL, timeout=300)
            output.seek(0)
            names = names_from_output(output.read(LIMIT + 1), result.returncode)
        fingerprint(bundle, meta)
        fingerprint(jar, self.patcher)
        return dict(names=names,
                    bundle={k: meta.get(k) for k in ("sha256", "bytes", "tag", "asset_id", "host", "channel_semantics")},
                    patcher={k: self.patcher[k] for k in ("sha256", "bytes", "tag", "asset_id")})


def display(value):
    return html.escape(str(value), quote=True).replace("@", "&#64;").replace("`", "&#96;").replace("|", "&#124;")


def rollup(report):
    rows = report["sources"]
    expected = report["expected"]
    counts = {state: sum(r["status"] == state for r in rows) for state in ("OK", "FAILED", "PENDING")}
    report["coverage"] = dict(expected=expected, attempted=counts["OK"] + counts["FAILED"],
                              succeeded=counts["OK"], failed=counts["FAILED"], pending=counts["PENDING"])
    changed = any(r["status"] == "OK" and (r["delta"]["state"] == "MISSING" or
                  r["delta"]["added"] or r["delta"]["removed"]) for r in rows)
    report["status"] = ("FAILED" if report.get("error") or not expected or counts["OK"] == 0 else
                        "PARTIAL" if counts["FAILED"] or counts["PENDING"] else
                        "CHANGED" if changed else "OK")
    return report


def markdown(report):
    lines = ["# Provider watch: " + report["status"], "", report["run_url"], "",
             "Coverage: `" + json.dumps(report["coverage"], sort_keys=True) + "`", "",
             *LIMITS, "", "| Target / provider | Host | Observation |", "| --- | --- | --- |"]
    for row in report["sources"]:
        lines.append("| " + display(row["target"] + "/" + row["name"]) + " | " +
                     row["host"] + " | " + row["status"] + " |")
    if report.get("error"):
        lines += ["", "Collection error: `" + display(report["error"]) + "`"]
    for row in report["sources"]:
        if row["status"] != "OK":
            lines += ["", "## " + display(row["target"] + "/" + row["name"]),
                      "No delta: `" + display(row.get("error", "NOT_OBSERVED")) + "`."]
            continue
        change = row["delta"]
        if change["state"] == "MISSING" or change["added"] or change["removed"]:
            lines += ["", "## " + display(row["target"] + "/" + row["name"])]
            if change["state"] == "MISSING":
                lines += ["Baseline missing; observed " + str(len(row["observation"]["names"])) +
                          " names. This is NOT an all-added or unchanged result."]
            else:
                for label in ("added", "removed"):
                    lines += ["**" + label + "**: " +
                              (", ".join("`" + display(n) + "`" for n in change[label]) or "(none)")]
    lines += ["", "Read AGENTS.md before acting. Added names still need BANNED/CONFIRM review.",
              "No committed baseline or patch selection was modified."]
    return "\n".join(lines) + "\n"


def save_report(report, out):
    rollup(report)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in (("report.json", json.dumps(report, indent=2, sort_keys=True) + "\n"),
                       ("report.md", markdown(report))):
        candidate = out / (name + ".cand")
        candidate.write_text(text, encoding="utf-8")
        candidate.replace(out / name)


def run_identity(env):
    repo = env.get("GITHUB_REPOSITORY", "")
    need(repo == "govinda-rajulu/patch-factory", "WRONG_REPOSITORY")
    rid, attempt, head = (env.get(k, "") for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"))
    need(re.fullmatch(r"[1-9][0-9]*", rid) and re.fullmatch(r"[1-9][0-9]*", attempt)
         and re.fullmatch(r"[0-9a-f]{40}", head), "INVALID_RUN_IDENTITY")
    return dict(repository=repo, run_id=rid, attempt=attempt, head=head,
                run_url="https://github.com/" + repo + "/actions/runs/" + rid + "/attempts/" + attempt)


def collect(root, out, observe, identity):
    report = dict(schema="pf-provider-watch-v1", expected=None, sources=[], limits=LIMITS, **identity)
    try:
        rows = inventory(json.loads((root / "src/targets.json").read_text()))
        report["expected"] = len(rows)
        report["sources"] = [dict(row, status="PENDING") for row in rows]
        save_report(report, out)
        for row in report["sources"]:
            try:
                observation = observe(row)
                # Validate injected/runtime observer output before any delta, too.
                names = observation["names"]
                need(isinstance(names, list) and names_from_output(
                    "".join("Name: " + n + "\n" for n in names).encode(), 0) == names, "INVALID_OBSERVATION")
                change = delta(root, row, names)
                row.update(status="OK", observation=observation, delta=change)
            except Exception as error:
                # Never publish raw provider output, exception text, paths or credentials.
                row.update(status="FAILED", error=str(error) if isinstance(error, WatchError)
                           else type(error).__name__, delta=None)
            save_report(report, out)
    except Exception as error:
        report["error"] = str(error) if isinstance(error, WatchError) else type(error).__name__
        save_report(report, out)
    return report


def validate_report(report, root, identity):
    need(all(report.get(k) == v for k, v in identity.items()), "REPORT_IDENTITY_DRIFT")
    need(report.get("schema") == "pf-provider-watch-v1", "REPORT_SCHEMA_DRIFT")
    expected = inventory(json.loads((root / "src/targets.json").read_text()))
    need(type(report.get("expected")) is int and report["expected"] == len(expected) and
         len(report.get("sources", [])) == len(expected), "INCOMPLETE_REPORT")
    for actual, wanted in zip(report["sources"], expected):
        need(all(actual.get(k) == v for k, v in wanted.items()), "SOURCE_IDENTITY_DRIFT")
        need(actual.get("status") in ("OK", "FAILED", "PENDING"), "INVALID_SOURCE_STATUS")
        if actual["status"] == "OK":
            names = actual["observation"]["names"]
            need(isinstance(names, list) and names_from_output(
                 "".join("Name: " + n + "\n" for n in names).encode(), 0) == names, "INVALID_OBSERVATION")
            need(actual.get("delta") == delta(root, wanted, names), "DELTA_DRIFT")
        else:
            need(actual.get("delta") is None and "observation" not in actual, "FAILED_SOURCE_HAS_DELTA")
    old = (report.get("coverage"), report.get("status"))
    rollup(report)
    need(old == (report["coverage"], report["status"]), "ROLLUP_DRIFT")
    return report


def main():
    need(len(sys.argv) == 2 and sys.argv[1] in ("collect", "enforce", "issue"), "INVALID_COMMAND")
    out = ROOT / "provider-watch-evidence"
    identity = run_identity(os.environ)
    if sys.argv[1] == "collect":
        with tempfile.TemporaryDirectory(prefix="pf-provider-watch-") as work:
            report = collect(ROOT, out, Observer(ROOT, Path(work)), identity)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write(markdown(report))
        return 0  # Artifact/report first; enforce is the final workflow step.
    report = json.loads((out / "report.json").read_text())
    validate_report(report, ROOT, identity)
    if sys.argv[1] == "enforce":
        return 0 if report["status"] in ("OK", "CHANGED") else 1
    if report["status"] == "OK":
        return 0
    need((out / "report.md").read_bytes() == markdown(report).encode(), "REPORT_BODY_DRIFT")
    need((out / "report.md").stat().st_size <= 60000, "REPORT_TOO_LARGE_FOR_ISSUE")
    # Single attempt, no fallback/retry that could duplicate a successful write.
    result = subprocess.run(["gh", "issue", "create", "--repo", identity["repository"],
                             "--title", "provider watch: " + report["status"] + " run " +
                             identity["run_id"] + "/" + identity["attempt"],
                             "--body-file", str(out / "report.md")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    need(result.returncode == 0, "ISSUE_DELIVERY_FAILED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("Provider watch stopped: " + type(error).__name__, file=sys.stderr)
        sys.exit(2)
