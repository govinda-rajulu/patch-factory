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
import tempfile
from datetime import datetime, timedelta, timezone
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
ORDER = ("decide", "install", "fix", "app", "fyi")
LABELS = {"decide": "Decide", "install": "Install", "fix": "Fix", "app": "Keep building", "fyi": "FYI"}

# `gh issue list --json` fields documented at
# https://cli.github.com/manual/gh_issue_list; `gh pr list` fields are
# documented at https://cli.github.com/manual/gh_pr_list.  The contract test
# keeps these allow-lists in sync with every invocation in src/ and .github/.
ISSUE_JSON_FIELDS = {
    "assignees", "author", "body", "closed", "closedAt", "closedByPullRequestsReferences",
    "comments", "createdAt", "id", "isPinned", "labels", "milestone", "number",
    "projectCards", "projectItems", "reactionGroups", "state", "stateReason", "title", "updatedAt", "url",
}
PR_JSON_FIELDS = {
    "additions", "assignees", "author", "baseRefName", "baseRefOid", "body", "changedFiles",
    "closed", "closedAt", "closingIssuesReferences", "commits", "createdAt", "deletions", "files",
    "fullDatabaseId", "headRefName", "headRefOid", "id", "isCrossRepository", "isDraft", "labels",
    "latestReviews", "maintainerCanModify", "mergeCommit", "mergeStateStatus", "mergeable", "mergedAt",
    "mergedBy", "milestone", "number", "projectCards", "projectItems", "reactionGroups", "reviewDecision",
    "reviewRequests", "reviews", "state", "statusCheckRollup", "title", "updatedAt", "url",
}
ID_RE = re.compile(r"\bN-[0-9a-fA-F]{6}\b")
DECISION_RE = re.compile(r"^\s*(take|drop|hold)\s+(N-[0-9a-fA-F]{6})\s*$", re.I)


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
    _add(bucket, "fyi", "### %s\n\n%s" % (name.capitalize(), plain))


def item_id(kind: str, first_line: str) -> str:
    """Return the stable owner-facing id for one rendered item."""
    return "N-" + hashlib.sha256((kind + first_line).encode("utf-8")).hexdigest()[:6]


def _first_line(text: str) -> str:
    return next((line.strip() for line in clean(text).splitlines() if line.strip()), "item")


def _description(kind: str, first: str) -> str:
    if kind == "app":
        return first + " Take = keep building it; drop = stop building it in the next packet; hold = revisit it in 14 days."
    return (first + " Take = record it for the next packet; drop = hide it permanently; "
            "hold = hide it for 14 days.")


def _load_targets(path: Path | None = None) -> list[dict]:
    path = path or Path(__file__).resolve().parents[1] / "targets.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [row for row in data if isinstance(row, dict) and row.get("enabled")]


def _items(kind: str, texts: Iterable[str]) -> list[dict]:
    out = []
    for text in texts:
        first = _first_line(text)
        out.append({"id": item_id(kind, first), "kind": kind, "first_line": first,
                    "text": text, "description": _description(kind, first)})
    return out


def app_items(targets: Path | None = None) -> list[dict]:
    return [_items("app", ["Keep building %s?" % row.get("label", row.get("id", "this app"))])[0]
            for row in _load_targets(targets)]


def _parse_time(value: str | None, now: datetime | None = None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _latest_decision(item_id_value: str, ledger: list[dict]) -> dict | None:
    wanted = str(item_id_value).upper()
    rows = [row for row in ledger if str(row.get("id", "")).upper() == wanted]
    rows.sort(key=lambda row: _parse_time(row.get("time")) or datetime.min.replace(tzinfo=timezone.utc))
    return rows[-1] if rows else None


def decision_state(item: dict, ledger: list[dict], now: datetime | None = None) -> str:
    """Return visible, held, taken, or dropped for an item."""
    row = _latest_decision(item["id"], ledger)
    if not row:
        return "visible"
    verb = str(row.get("verb", "")).lower()
    if verb in ("drop", "take"):
        return "dropped" if verb == "drop" else "taken"
    if verb == "hold":
        # App questions are one-shot: any owner answer retires that app item.
        if item.get("kind") == "app":
            return "dropped"
        stamp = _parse_time(row.get("time"))
        now = now or datetime.now(timezone.utc)
        if stamp and now < stamp + timedelta(days=14):
            return "held"
    return "visible"


def load_ledger(path: Path | None) -> list[dict]:
    if not path or not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _catalog_comment(body: str) -> dict[str, dict]:
    """Read machine-readable item metadata embedded in a rendered body."""
    catalog = {}
    for match in re.finditer(r"<!-- needs-you-item:(\{.*?\}) -->", body or ""):
        try:
            row = json.loads(match.group(1))
        except ValueError:
            continue
        if row.get("id"):
            catalog[str(row["id"]).upper()] = row
    return catalog


def parse_decisions(comment: str, known_ids: Iterable[str] | None = None) -> list[tuple[str, str]]:
    """Parse only complete command lines; prose and unknown ids are ignored."""
    known = {x.upper() for x in known_ids} if known_ids is not None else None
    found = []
    for line in (comment or "").splitlines():
        match = DECISION_RE.match(line)
        if not match:
            continue
        verb, ident = match.group(1).lower(), match.group(2).upper()
        if known is None or ident in known:
            found.append((verb, ident))
    return found


def authorized_comment(event: dict, owner: str) -> bool:
    comment = event.get("comment") or {}
    user = comment.get("user") or {}
    return (event.get("issue", {}).get("title") == TITLE and
            user.get("login") == owner and
            comment.get("author_association") == "OWNER" and
            user.get("type") != "Bot")


def _review_item(item: dict) -> bool:
    title = str(item.get("title", item.get("first_line", ""))).lower()
    labels = {str(x).lower() for x in item.get("labels", [])}
    return item.get("kind") == "review" or ("review" in labels and title.startswith("review:"))


def apply_effect(verb: str, item: dict, repo: str, run=subprocess.run) -> str:
    """Apply the only live effects; all other item kinds are ledger-only."""
    if not _review_item(item):
        return "recorded only"
    number = item.get("issue_number")
    if not number:
        match = re.search(r"(?:#|issues/)(\d+)", str(item.get("first_line", "")))
        number = match.group(1) if match else None
    if not number:
        return "recorded only (review issue number unavailable)"
    if verb == "drop":
        args = ["issue", "close", str(number), "--repo", repo, "--comment", "Closed by the owner's Needs you decision."]
    elif verb == "hold":
        args = ["issue", "edit", str(number), "--repo", repo, "--add-label", "hold"]
    elif verb == "take":
        args = ["issue", "edit", str(number), "--repo", repo, "--add-label", "accepted"]
    else:
        return "recorded only"
    result = gh(args, run)
    if result.returncode != 0:
        raise OSError("Needs you review effect failed")
    return {"drop": "closed review issue", "hold": "added hold label", "take": "added accepted label"}[verb]


def _review_items(path: Path | None) -> list[dict]:
    rows = load_json(path)
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        title = str(row.get("title", ""))
        labels = [x.get("name", x) if isinstance(x, dict) else x for x in row.get("labels", [])]
        if not title.lower().startswith("review:") or "review" not in {str(x).lower() for x in labels}:
            continue
        first = _first_line(title)
        body = row.get("body") or title
        out.append({"id": item_id("review", first), "kind": "review", "first_line": first,
                    "text": body, "title": title, "labels": labels,
                    "issue_number": row.get("number"), "description": _description("decide", first)})
    return out


def render(reports: dict[str, Path | None], ledger: list[dict] | Path | None = None,
           now: datetime | None = None, targets: Path | None = None,
           review: Path | None = None) -> str:
    if isinstance(ledger, Path):
        ledger = load_ledger(ledger)
    ledger = ledger or []
    buckets = {kind: [] for kind in ORDER}
    for name in ("selection", "tooling", "nightly", "provider", "community"):
        _source(reports.get(name), name, buckets)
    all_items = []
    for kind in ORDER:
        all_items.extend(_items(kind, buckets[kind]))
    all_items.extend(_review_items(review or reports.get("review")))
    all_items.extend(app_items(targets))
    visible = [item for item in all_items if decision_state(item, ledger, now) == "visible"]
    taken = [item for item in all_items if decision_state(item, ledger, now) == "taken"]
    actionable = sum(1 for item in visible if item["kind"] in ("decide", "install", "fix", "app", "review"))
    if not actionable and not taken:
        return "# Needs you: OK\n\n**Needs you:** nothing needs you today.\n"
    fingerprint = hashlib.sha256(json.dumps([(x["id"], x["text"]) for x in visible], sort_keys=True).encode()).hexdigest()[:16]
    lines = ["<!-- needs-you:%s -->" % fingerprint, "# Needs you: NEEDS YOU", "",
             "Comment one command per line: `take N-xxxxxx`, `drop N-xxxxxx`, or `hold N-xxxxxx`. Commands are case-insensitive; other text is ignored.", "",
             "**Needs you:** %d item(s), listed first below." % actionable, ""]
    for kind in ORDER:
        items = [item for item in visible if item["kind"] == kind or (kind == "decide" and item["kind"] == "review")]
        if not items:
            continue
        lines += ["## " + LABELS[kind], ""]
        for item in items:
            metadata_row = {"id": item["id"], "kind": item["kind"], "first_line": item["first_line"]}
            for field in ("title", "labels", "issue_number"):
                if field in item:
                    metadata_row[field] = item[field]
            metadata = json.dumps(metadata_row, separators=(",", ":"))
            lines += ["<!-- needs-you-item:%s -->" % metadata,
                      "<details><summary>%s</summary>" % readable.cell(item["first_line"], 180), "",
                      "**%s** — %s" % (item["id"], item["description"]), "", item["text"], "", "</details>", ""]
    if taken:
        lines += ["## Taken, waiting for the next packet", "", "These items were taken and are hidden from the action list until the next packet.", ""]
        for item in taken:
            lines.append("- **%s** — %s" % (item["id"], item["first_line"]))
        lines.append("")
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

def fetch_review_items(repo: str = REPO, run=subprocess.run) -> list[dict]:
    """Read open weekly-council review issues for the owner decision list."""
    result = gh(["issue", "list", "--repo", repo, "--state", "open", "--label", "review",
                 "--search", 'in:title "review:"', "--limit", "100",
                 "--json", "number,title,body,labels,url"], run)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout or "[]")
    except ValueError:
        return []
    return data if isinstance(data, list) else []


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
                 "--search", 'in:title "' + TITLE + '"', "--json", "number,title,body,author"], run)
    if found.returncode != 0:
        raise OSError("Needs you issue list failed")
    rows = [r for r in json.loads(found.stdout or "[]") if r.get("title") == TITLE]
    if len(rows) > 1:
        raise ValueError("duplicate Needs you issues")
    if rows:
        row = rows[0]
        author = row.get("author") or {}
        if not (author.get("is_bot") is True or author.get("login") in ("app/github-actions", "github-actions[bot]")):
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



def decide(comment_path: Path, ledger_path: Path, repo: str = REPO, comment_url: str = "",
           owner: str = "", run=subprocess.run) -> str:
    """Record an authorized owner comment and apply any review-issue effect."""
    body = comment_path.read_text(encoding="utf-8", errors="replace")
    found = gh(["issue", "list", "--repo", repo, "--state", "open", "--limit", "100",
                "--search", 'in:title "' + TITLE + '"', "--json", "number,title,body,author"], run)
    if found.returncode != 0:
        raise OSError("Needs you issue list failed")
    rows = [row for row in json.loads(found.stdout or "[]") if row.get("title") == TITLE]
    if len(rows) != 1:
        raise ValueError("Needs you issue is missing or duplicated")
    issue = rows[0]
    author = issue.get("author") or {}
    if not (author.get("is_bot") is True or author.get("login") in ("app/github-actions", "github-actions[bot]")):
        raise ValueError("Needs you issue is not bot-owned")
    catalog = _catalog_comment(issue.get("body") or "")
    commands = parse_decisions(body, catalog)
    if not commands:
        return "IGNORED"
    ledger = load_ledger(ledger_path)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipts = []
    for verb, ident in commands:
        meta = catalog[ident]
        record = {"id": ident, "verb": verb, "kind": meta.get("kind", "unknown"),
                  "first_line": meta.get("first_line", ""), "comment_url": comment_url, "time": stamp}
        ledger.append(record)
        effect = apply_effect(verb, meta, repo, run)
        receipts.append("%s %s — %s" % (verb, ident, effect))
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = "**Needs you receipt**\n\n" + "\n".join("- " + row for row in receipts)
    commented = gh(["issue", "comment", str(issue["number"]), "--repo", repo, "--body", receipt], run)
    if commented.returncode != 0:
        raise OSError("Needs you receipt failed")
    return "RECORDED"

def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("render")
    for name in ISSUES:
        r.add_argument("--" + name, type=Path)
    r.add_argument("--output", type=Path)
    r.add_argument("--ledger", type=Path)
    r.add_argument("--targets", type=Path)
    r.add_argument("--review", type=Path)
    f = sub.add_parser("fetch")
    f.add_argument("--output-dir", type=Path, required=True)
    f.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", REPO))
    d = sub.add_parser("deliver")
    d.add_argument("--body", type=Path, required=True)
    d.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", REPO))
    q = sub.add_parser("decide")
    q.add_argument("--comment-file", type=Path, required=True)
    q.add_argument("--ledger", type=Path, required=True)
    q.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", REPO))
    q.add_argument("--comment-url", default=os.environ.get("NEEDS_YOU_COMMENT_URL", ""))
    q.add_argument("--owner", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    a = ap.parse_args(argv)
    if a.command == "render":
        body = render({name: getattr(a, name) for name in ISSUES}, ledger=a.ledger, targets=a.targets, review=a.review)
        if a.output:
            a.output.write_text(body, encoding="utf-8")
        else:
            print(body, end="")
        return 0
    if a.command == "fetch":
        paths = write_fetched(a.output_dir, fetch_artifact_reports(a.repo, root=a.output_dir))
        (a.output_dir / "review.json").write_text(json.dumps(fetch_review_items(a.repo), indent=2) + "\n", encoding="utf-8")
        print("fetched %d watch report(s)" % len(paths))
        return 0
    if a.command == "decide":
        # The event body enters only through env; Python writes the file consumed above.
        a.comment_file.parent.mkdir(parents=True, exist_ok=True)
        a.comment_file.write_text(os.environ.get("NEEDS_YOU_COMMENT_BODY", ""), encoding="utf-8")
        return 0 if decide(a.comment_file, a.ledger, a.repo, a.comment_url, a.owner) in ("RECORDED", "IGNORED") else 1
    return 0 if deliver(a.body.read_text(encoding="utf-8"), a.repo) in ("CREATED", "EDITED", "UNCHANGED") else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("Needs you stopped: " + type(exc).__name__, file=os.sys.stderr)
        raise SystemExit(2)
