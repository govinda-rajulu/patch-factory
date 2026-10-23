#!/usr/bin/env python3
"""Merge the five newest watch artifacts into one quiet, owner-facing issue.

Collectors remain responsible for evidence and any stateful delivery. This file
reads their latest Actions artifacts, groups work as decide/install/fix/FYI, and
edits one standing ``Needs you`` issue when the rendered body changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Iterable

import readable

TITLE = "Needs you"
REPO = "govinda-rajulu/patch-factory"
ISSUES = {
    "nightly": "watch: repo and provider status",
    "provider": "provider watch",
    "tooling": "Tooling watch",
    "selection": "Selection watch",
    "community": "community: index changed for apps you build",
}
ORDER = ("decide", "install", "fix", "fyi")
LABELS = {"decide": "Decide", "install": "Install", "fix": "Fix", "fyi": "FYI"}


def clean(text: str) -> str:
    """Remove old disclaimer-only blocks, never report/data lines."""
    out, skip = [], False
    for line in (text or "").splitlines():
        if line.startswith("## "):
            low = line.lower()
            skip = any(x in low for x in ("what this watch does not check", "evidence and recovery limits",
                                           "what this report does not", "limitations and recovery"))
        if not skip:
            out.append(line.rstrip())
    return "\n".join(out).strip()


def read_report(path: Path | None) -> str:
    if path is None:
        return ""
    if path.is_dir():
        for name in ("report.md", "nightly-report.txt", "body.md"):
            candidate = path / name
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8", errors="replace")
        return ""
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def load_json(path: Path | None):
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _add(bucket: dict[str, list[str]], kind: str, text: str) -> None:
    text = clean(text)
    if text.strip():
        bucket[kind].append(text)


def _section(text: str, heading: str) -> str:
    m = re.search(r"(?ms)^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |\Z)", text)
    return m.group(1).strip() if m else ""


def _source(path: Path | None, name: str, bucket: dict[str, list[str]]) -> None:
    text = read_report(path)
    data = load_json(path)
    if not text and data is None:
        _add(bucket, "fix", "%s report was not produced; rerun the watch." % name)
        return
    plain = text or json.dumps(data, indent=2, sort_keys=True)
    low = plain.lower()
    # The action is the first thing shown, while the complete cleaned report is
    # retained below as evidence so a finding cannot disappear in summarising.
    if name == "selection":
        need = _section(plain, "Needs you")
        if need and "nothing blocked" not in need.lower():
            _add(bucket, "decide", need)
    if name == "community":
        rank = re.findall(r"(?mi)^[-*] \*\*(?:[^*]+)\*\*:.*(?:better|configured|provider).*", plain)
        if rank or "choose whether to switch" in low:
            _add(bucket, "decide", "\n".join(rank) or "Review the provider ranker and choose whether to switch.")
    if name == "tooling" and ("update" in low or "behind" in low or "to review" in low):
        _add(bucket, "install", "Review the tooling report and install any update listed there.")
    if name in ("nightly", "provider") and any(x in low for x in ("failed", "unknown", "not read", "missing")):
        _add(bucket, "fix", "%s reported a read or run problem; inspect and rerun it." % name.capitalize())
    # A changed report is useful context even when it needs no decision. This
    # folded copy carries every collector line after disclaimer-only blocks.
    _add(bucket, "fyi", "### %s\n\n%s" % (name.capitalize(), plain))


def render(reports: dict[str, Path | None]) -> str:
    buckets = {kind: [] for kind in ORDER}
    for name in ("selection", "tooling", "nightly", "provider", "community"):
        _source(reports.get(name), name, buckets)
    # Missing reports are a fix signal; a complete run with no action remains a
    # genuinely one-line empty day, not a daily report spam comment.
    actionable = sum(len(buckets[k]) for k in ("decide", "install", "fix"))
    if not actionable:
        return "# Needs you: OK\n\n**Needs you:** nothing needs you today.\n"
    fingerprint = hashlib.sha256("\n".join("\n".join(buckets[k]) for k in ORDER).encode()).hexdigest()[:16]
    lines = ["<!-- needs-you:%s -->" % fingerprint, "# Needs you: NEEDS YOU", "",
             "**Needs you:** %d item(s), listed first below." % actionable, ""]
    for kind in ORDER:
        if not buckets[kind]:
            continue
        lines += ["## " + LABELS[kind], ""]
        for item in buckets[kind]:
            lines += ["<details><summary>" + readable.cell(item.splitlines()[0], 180) + "</summary>", "", item, "", "</details>", ""]
    return "\n".join(lines).rstrip() + "\n"


def gh(args: list[str], run=subprocess.run):
    return run(["gh"] + args, capture_output=True, text=True, timeout=120)


WORKFLOWS = {
    "nightly": ("watch.yml", ("nightly-report-",), ("nightly-report.txt",)),
    "provider": ("agent-watch.yml", ("provider-watch-",), ("report.md",)),
    "tooling": ("tooling-watch.yml", ("tooling-watch-",), ("tooling-report.md", "tooling-upstreams.md")),
    "selection": ("selection-watch.yml", ("selection-watch-",), ("report.md",)),
    # Community must retain its issue readback: advance() uses it as the receipt
    # that authorizes changing bundles.json and watch-state.json.
    "community": ("community-watch.yml", ("community-watch-delivery-", "community-watch-"), ("report.md",)),
}


def _json_api(path: str, repo: str, run=subprocess.run):
    result = gh(["api", "repos/" + repo + "/" + path], run)
    if result.returncode != 0:
        raise OSError("GitHub API failed: " + path)
    try:
        return json.loads(result.stdout or "{}")
    except (TypeError, ValueError) as exc:
        raise OSError("GitHub API returned invalid JSON: " + path) from exc


def _zip_api(path: str, repo: str, run=subprocess.run) -> bytes:
    result = run(["gh", "api", "repos/" + repo + "/" + path], capture_output=True, timeout=120)
    if result.returncode != 0:
        raise OSError("GitHub artifact download failed: " + path)
    return result.stdout or b""


def _safe_extract(data: bytes, root: Path) -> list[Path]:
    import io
    import zipfile
    root.mkdir(parents=True, exist_ok=True)
    found = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            name = Path(member.filename)
            if name.is_absolute() or ".." in name.parts or member.is_dir():
                continue
            target = (root / name).resolve()
            if root.resolve() not in target.parents:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
            found.append(target)
    return found


def fetch_artifact_reports(repo: str = REPO, run=subprocess.run, root: Path | None = None) -> dict[str, str]:
    """Read the newest completed artifact for each collector through Actions API."""
    root = root or Path(".needs-you-artifacts")
    result = {}
    for name, (workflow, prefixes, wanted) in WORKFLOWS.items():
        runs = _json_api("actions/workflows/" + workflow + "/runs?branch=main&status=completed&per_page=20", repo, run)
        rows = runs.get("workflow_runs", []) if isinstance(runs, dict) else []
        rows = [r for r in rows if r.get("conclusion") not in ("cancelled", "skipped")]
        rows.sort(key=lambda r: (r.get("run_started_at") or r.get("created_at") or "", int(r.get("id", 0))), reverse=True)
        artifact = None
        # Use the newest completed run only. Falling back to an older artifact
        # would hide a collector failure or a missing evidence upload.
        if rows:
            row = rows[0]
            listing = _json_api("actions/runs/%s/artifacts?per_page=100" % row["id"], repo, run)
            candidates = listing.get("artifacts", []) if isinstance(listing, dict) else []
            candidates = [a for a in candidates if not a.get("expired") and any(str(a.get("name", "")).startswith(p) for p in prefixes)]
            candidates.sort(key=lambda a: (a.get("created_at") or "", int(a.get("id", 0))), reverse=True)
            if candidates:
                artifact = candidates[0]
        if not artifact:
            continue
        files = _safe_extract(_zip_api("actions/artifacts/%s/zip" % artifact["id"], repo, run), root / name)
        selected = []
        for filename in wanted:
            selected += [p for p in files if p.name == filename]
        if selected:
            result[name] = "\n\n".join(p.read_text(encoding="utf-8", errors="replace") for p in selected)
    return result


def fetch_reports(repo: str = REPO, run=subprocess.run) -> dict[str, str]:
    # Compatibility name retained for callers/tests; production reads artifacts,
    # never the five standing issue bodies.
    return fetch_artifact_reports(repo, run)

def write_fetched(root: Path, reports: dict[str, str]) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, text in reports.items():
        path = root / (name + ".md")
        path.write_text(text, encoding="utf-8")
        out[name] = path
    return out


def deliver(body: str, repo: str = REPO, run=subprocess.run) -> str:
    found = gh(["issue", "list", "--repo", repo, "--state", "open", "--limit", "100",
                 "--search", 'in:title "' + TITLE + '"', "--json", "number,title,body,user"], run)
    if found.returncode != 0:
        raise OSError("Needs you issue list failed")
    rows = [r for r in json.loads(found.stdout or "[]") if r.get("title") == TITLE]
    if len(rows) > 1:
        raise ValueError("duplicate Needs you issues")
    if rows:
        row = rows[0]
        if row.get("user", {}).get("type") not in (None, "Bot"):
            raise ValueError("Needs you issue is not bot-owned")
        old = row.get("body") or ""
        if old.strip() == body.strip():
            return "UNCHANGED"
        number = str(row["number"])
        edited = gh(["issue", "edit", number, "--repo", repo, "--body", body], run)
        if edited.returncode != 0:
            raise OSError("Needs you issue edit failed")
        note = "**Needs you changed**\n\n" + "\n".join(readable.changed_lines(old, body))
        commented = gh(["issue", "comment", number, "--repo", repo, "--body", note], run)
        if commented.returncode != 0:
            raise OSError("Needs you issue comment failed")
        return "EDITED"
    made = gh(["issue", "create", "--repo", repo, "--title", TITLE, "--body", body], run)
    if made.returncode != 0:
        raise OSError("Needs you issue create failed")
    return "CREATED"


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("render")
    for name in ISSUES:
        r.add_argument("--" + name, type=Path)
    r.add_argument("--output", type=Path)
    f = sub.add_parser("fetch")
    f.add_argument("--output-dir", type=Path, required=True)
    f.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", REPO))
    d = sub.add_parser("deliver")
    d.add_argument("--body", type=Path, required=True)
    d.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", REPO))
    a = ap.parse_args(argv)
    if a.command == "render":
        body = render({name: getattr(a, name) for name in ISSUES})
        if a.output:
            a.output.write_text(body, encoding="utf-8")
        else:
            print(body, end="")
        return 0
    if a.command == "fetch":
        paths = write_fetched(a.output_dir, fetch_artifact_reports(a.repo, root=a.output_dir))
        print("fetched %d watch report(s)" % len(paths))
        return 0
    return 0 if deliver(a.body.read_text(encoding="utf-8"), a.repo) in ("CREATED", "EDITED", "UNCHANGED") else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("Needs you stopped: " + type(exc).__name__, file=os.sys.stderr)
        raise SystemExit(2)
