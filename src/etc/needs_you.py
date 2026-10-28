#!/usr/bin/env python3
"""Merge the five newest watch artifacts into one quiet, owner-facing issue.

Collectors remain responsible for evidence and any stateful delivery. This file
reads their latest Actions artifacts, groups work as decide/install/fix/FYI, and
edits one standing ``Needs you`` issue when the rendered body changes.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Iterable

import readable
import decisions

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
# W16j (owner, 25 Oct 2026: "group wherever possible ... easy to understand and act"): one line can
# answer a whole group (take G2), every item (take all), or accept every "my call" (yes all);
# keep means take; a provider take may name patches to leave out: take N-xxxxxx except "A", "B".
COMMAND_RE = re.compile(r"^\s*(take|keep|drop|hold)\s+(N-[0-9a-fA-F]{6}|G[1-8]|all)\b(?:\s+except\s+(.+?))?\s*$", re.I)
YES_ALL_RE = re.compile(r"^\s*yes\s+all\s*$", re.I)
GROUPS = {
    "G1": ("New providers for apps you build", "take = Explore opens an issue with its live patch list"),
    "G2": ("ALWAYS ON: hide patches with no in-app switch", "once built it stays on and the app has no setting to undo it; take only what you never want to see (owner, 28 Oct 2026: Hide feed content emptied Home)"),
    "G3": ("No description in the index", "the provider wrote nothing, so the bot cannot tell what it does"),
    "G4": ("Generic patches not written for this app", "the index ties them to no app"),
    "G5": ("Risky: spoof, proxy, DRM, signature, certificate", "account or server risk"),
    "G6": ("Held only for a word in the name", "branding, rename, option and similar words"),
    "G7": ("Waits on another rule", "one bundle per name, a reserved name or a paid word"),
    "G8": ("Other things to look at", "reports, fixes and reviews"),
}
RISKY = ("spoof", "proxy", "vpn", "widevine", "drm", "signature", "certificate", "integrity", "root", "firebase", "confirm")
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*([.][A-Za-z][A-Za-z0-9_]*)+$")
GITHUB_IDENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$")
GITLAB_IDENT_RE = re.compile(r"^[0-9]{1,12}$")
TARGET_IDENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


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


def _run_url(text: str) -> str:
    """Return the first Actions run URL embedded in a collector report."""
    match = re.search(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+(?:/attempts/[0-9]+)?", text or "")
    return match.group(0) if match else ""


def _one_line(value: object) -> str:
    """Turn recorded evidence into one safe, readable issue line."""
    text = re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()
    return text.replace("|", " / ")[:500]


def _evidence_reason(text: str, data) -> str:
    """Return a recorded failure reason, never a guess based on the status word."""
    candidates = []
    if isinstance(data, dict):
        for key in ("stop_code", "stopCode", "failure_reason", "failureReason", "reason", "reasons", "error", "message", "detail"):
            value = data.get(key)
            if isinstance(value, list):
                candidates.extend(value)
            elif value not in (None, "", {}):
                candidates.append(value)
        for key in ("watch", "report", "result", "failure"):
            value = data.get(key)
            if isinstance(value, dict):
                nested = _evidence_reason("", value)
                if nested:
                    candidates.append(nested)
    # Reports deliberately print machine-readable stop codes and error lines.
    # Do not turn a bare FAILED/UNKNOWN heading into a made-up explanation.
    for line in (text or "").splitlines():
        stripped = re.sub(r"^[#>*`\-\s]+", "", line).strip()
        # W16w (28 Oct 2026): a documented exception is not a failure reason (it named gg-photos
        # Change package name six times while the real cause was an unreadable provider list).
        if 'documented exception' in stripped.lower():
            continue
        # A fetched artifact can contain a JSON report beside its Markdown
        # report. Read scalar/list values without treating JSON punctuation as
        # a reason.
        json_match = re.match(r"^\"(?:stop_code|stopCode|failure_reason|failureReason|reason|error|message|detail|reasons)\"\s*:\s*(.*?)[,]?$", stripped)
        if json_match:
            try:
                value = json.loads(json_match.group(1))
                if isinstance(value, list):
                    candidates.extend(value)
                else:
                    candidates.append(value)
            except (TypeError, ValueError):
                pass
        elif re.fullmatch(r'\"[^\"]+\"[,]?', stripped):
            try:
                candidates.append(json.loads(stripped.rstrip(',')))
            except (TypeError, ValueError):
                pass
        if re.search(r"(?i)\b(stop[_ -]?code|failure[_ -]?reason|error|reason|could not|unable|exception)\b", stripped):
            value = re.sub(r"(?i)^[^:]{0,80}:\s*", "", stripped).strip()
            if value and value.lower() not in {"none", "unknown", "not recorded"}:
                candidates.append(value)
    for value in candidates:
        result = _one_line(value)
        if result and result.lower() not in {"failed", "failure", "unknown", "missing", "not read", "no reason recorded", "[]"}:
            return result
    return "no reason recorded"


def _held_row_from_line(line: str) -> dict | None:
    """Parse one detailed Selection row, not its grouped summary table."""
    if "held:" not in line.lower() or "`" not in line:
        return None
    match = re.search(r"[|\-]\s*(?:[^|]+\|\s*)?(?:\*\*[^*]+\*\*\s*)?([^|:/]+?)\s*/\s*([^:|]+):\s*`([^`]+)`", line)
    if not match:
        return None
    tail = line[match.end():]
    # W16h: a waiting new-name row ends with its Add/skip route after the
    # reason; without this the row stayed in the Selection table item.
    held = re.search(r"(?i)\(.*?held:\s*(.*?)\)(?:\.\s*Add:.*)?\s*\|?\s*$", tail)
    if not held:
        return None
    reason = held.group(1).strip()
    target, provider, patch = (html.unescape(x).strip() for x in match.groups())
    if not target or not provider or not patch or not reason:
        return None
    return {"target": target, "provider": provider, "name": patch, "why": _one_line(reason)}


def _held_rows(text: str, data=None) -> list[dict]:
    rows = []
    for line in (text or "").splitlines():
        row = _held_row_from_line(line)
        if row:
            rows.append(row)
    if isinstance(data, dict):
        for key in ("waiting", "backlog"):
            values = data.get(key) or []
            if not isinstance(values, list):
                continue
            for value in values:
                if not isinstance(value, dict) or not value.get("why") or not value.get("name"):
                    continue
                rows.append({"target": str(value.get("target", "")), "provider": str(value.get("provider", "")),
                             "name": str(value.get("name", "")), "why": _one_line(value.get("why"))})
    unique, seen = [], set()
    for row in rows:
        key = tuple(row.get(x, "") for x in ("target", "provider", "name"))
        if all(key) and key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def _selection_without_held(text: str) -> str:
    """Keep other Selection findings while removing per-name held rows."""
    lines = [line for line in (text or "").splitlines() if not _held_row_from_line(line)]
    # A table made solely of held rows should not become a useless aggregate item.
    meaningful = [line for line in lines if line.strip() and not re.match(r"^\|?\s*:?-{3,}", line)]
    if not any("|" not in line or not re.match(r"^\s*\|?\s*(kind|what to do)\s*\|", line, re.I)
               for line in meaningful):
        return ""
    return "\n".join(lines).strip()


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
            _add(bucket, "decide", _selection_without_held(need))
    # Community provider candidates are rendered from the checkout's index,
    # not from the report's old aggregate rank paragraph.
    if name == "tooling" and ("update" in low or "behind" in low or "to review" in low):
        _add(bucket, "install", "Review the tooling report and install any update listed there.")
    # W16j: judge by the report's own headline ('# Title: STATUS') when it has one. A healthy
    # report that merely says "missing" or "NOT compared" in a note (Provider: "Patch names only",
    # Nightly: the documented gg-photos exception) is not a fix item.
    head = re.search(r"(?m)^#{1,2} [^\n:]+:\s*(.+)$", plain)
    if head:
        state = head.group(1).lower()
        broken = any(x in state for x in ("failed", "unknown", "not read", "missing", "stop"))
    else:
        broken = any(x in low for x in ("failed", "unknown", "not read", "missing"))
    if name in ("nightly", "provider") and broken:
        reason = _evidence_reason(plain, data)
        recorded_url = data.get("run_url") if isinstance(data, dict) else ""
        url = _run_url(plain) or (recorded_url if isinstance(recorded_url, str) else "")
        suffix = " [run](%s)" % url if url else ""
        _add(bucket, "fix", "%s reported %s; inspect and rerun it.%s" % (name.capitalize(), reason, suffix))
    url = _run_url(plain)
    link = "[%s run](%s)" % (name.capitalize(), url) if url else "%s report (run link unavailable)" % name.capitalize()
    _add(bucket, "fyi", "- " + link)


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


def _load_targets(path: Path | list | None = None) -> list[dict]:
    if isinstance(path, list):
        data = path
    else:
        path = path or Path(__file__).resolve().parents[1] / "targets.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
    return [row for row in data if isinstance(row, dict) and row.get("enabled")]


def _load_value(value, default):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, Path):
        try:
            return json.loads(value.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default
    return default


def _compat_versions(record, package: str) -> list[str]:
    """Extract versions for one package from either index compatibility shape."""
    found = []
    if isinstance(record, dict):
        # New index shape: {"package.name": ["1.2.3"]}.
        if package in record:
            value = record[package]
            if isinstance(value, list):
                for row in value:
                    if isinstance(row, str) and row.strip():
                        found.append(row.strip())
                    elif isinstance(row, dict):
                        found.extend(_compat_versions(row, package))
            elif isinstance(value, str) and value.strip():
                found.append(value.strip())
            elif isinstance(value, dict):
                found.extend(_compat_versions(value, package))
        # A target record in the list shape can also be encountered here.
        if record.get("packageName") == package:
            targets = record.get("targets", [])
            for target in targets if isinstance(targets, list) else [targets]:
                if isinstance(target, dict):
                    value = target.get("version", target.get("versionName"))
                    if isinstance(value, str) and value.strip():
                        found.append(value.strip())
                    elif not target:
                        found.append("any version")
    elif isinstance(record, list):
        for row in record:
            found.extend(_compat_versions(row, package))
    return found


def _version_key(value: str):
    # Numeric components give a useful deterministic newest-version ordering;
    # preserve lexical text for unusual provider version names.
    return tuple(int(x) for x in re.findall(r"\d+", value)) or (0,)


def _provider_patch_info(bundle: dict, package: str, compatibilities: list) -> tuple[int, list[str]]:
    count, versions = 0, []
    target_apps = bundle.get("targetApps") or []
    for patch in bundle.get("patches", []):
        if not isinstance(patch, dict):
            continue
        key = patch.get("compatiblePackagesKey", patch.get("compatibilityKey"))
        applicable = False
        patch_versions = []
        if isinstance(key, int) and 0 <= key < len(compatibilities):
            patch_versions = _compat_versions(compatibilities[key], package)
            applicable = bool(patch_versions)
        if applicable:
            count += 1
            versions.extend(patch_versions)
    return count, versions


def _patch_rows(bundle: dict, package: str, compatibilities: list, have: set) -> list[list]:
    """W16j: [name, description, newest version, already have] for each patch the bundle offers this app."""
    apps = [a for a in (bundle.get("targetApps") or []) if isinstance(a, str)]
    single = bool(apps) and all(a == package or a.startswith(package + ".") for a in apps)
    out = []
    for patch in bundle.get("patches", []) or []:
        if not isinstance(patch, dict) or not patch.get("name"):
            continue
        key = patch.get("compatiblePackagesKey", patch.get("compatibilityKey"))  # both index shapes
        record = compatibilities[key] if isinstance(key, int) and 0 <= key < len(compatibilities) else None
        versions = _compat_versions(record, package) if record is not None else []
        if record is not None and not versions:
            continue
        if record is None and not single:
            continue
        newest = max(versions, key=lambda x: (_version_key(x), x)) if versions else "not listed"
        desc = " ".join(str(patch.get("description") or "").split())
        out.append([str(patch["name"]), desc, newest, decisions.norm(patch["name"]) in have])
    return out


def provider_items(index: Path | dict | None = None, targets: Path | list | None = None) -> list[dict]:
    """Render one actionable item for each unconfigured indexed provider/app pair."""
    if index is None:
        index = Path(__file__).resolve().parents[1] / "community" / "bundles.json"
    if targets is None:
        targets = Path(__file__).resolve().parents[1] / "targets.json"
    index_data = _load_value(index, {})
    if not isinstance(index_data, dict):
        index_data = {}
    target_data = _load_value(targets, [])
    if not isinstance(target_data, list):
        target_data = []
    compatibilities = index_data.get("compatibilities", [])
    if not isinstance(compatibilities, list):
        compatibilities = []
    bundles = index_data.get("bundles", [])
    if not isinstance(bundles, list):
        bundles = []
    out = []
    root = _root_of(targets)
    memory = decisions.load(root)
    for target in target_data:
        if not isinstance(target, dict) or not target.get("enabled"):
            continue
        package = target.get("package")
        if not isinstance(package, str) or not package:
            continue
        configured_rows = [p for p in (target.get("candidates", []) or []) + (target.get("extra_bundles", []) or [])
                           if isinstance(p, dict)]
        configured = {(str(p.get("owner", "")) + "/" + str(p.get("repo", ""))).lower()
                      for p in configured_rows}
        ours_row = configured_rows[0] if configured_rows else {}
        ours = str(ours_row.get("owner", "")) + "/" + str(ours_row.get("repo", ""))
        ours_count, ours_versions = None, []
        for bundle in bundles:
            if isinstance(bundle, dict) and str(bundle.get("repo", "")).lower() == ours.lower():
                ours_count, ours_versions = _provider_patch_info(bundle, package, compatibilities)
                break
        ours_newest = max(ours_versions, key=lambda x: (_version_key(x), x)) if ours_versions else None
        have = set()
        for row in configured_rows:
            path = (root or Path("/nonexistent")) / "src/patches" / str(row.get("patch_dir", "")) / "include-patches"
            if row.get("patch_dir") and path.is_file():
                have |= {decisions.norm(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
        # W16h: Truecaller read "we use bufferk with 7" while the build also takes
        # paresh and binarymend; name the extras so the comparison is honest.
        extra_text = []
        for row in (target.get("extra_bundles", []) or []):
            if not isinstance(row, dict):
                continue
            name = str(row.get("owner", "")) + "/" + str(row.get("repo", ""))
            hit = next((b for b in bundles if isinstance(b, dict) and str(b.get("repo", "")).lower() == name.lower()), None)
            n_extra = _provider_patch_info(hit, package, compatibilities)[0] if hit else None
            extra_text.append(name + (" (%d)" % n_extra if n_extra else ""))
        rows = []
        for bundle in bundles:
            if not isinstance(bundle, dict):
                continue
            repo = str(bundle.get("repo", ""))
            if not repo or repo.lower() in configured:
                continue
            count, versions = _provider_patch_info(bundle, package, compatibilities)
            if count < 1:
                continue
            newest = max(versions, key=lambda x: (_version_key(x), x)) if versions else "any version"
            # W16j: the owner's provider calls (src/patches/DECISIONS.json). A dropped provider is
            # never asked again; a watched one stays quiet until it lists our app version.
            state, _ = decisions.provider_state(memory, target.get("id"), repo)
            if state == "drop":
                continue
            ready = newest == "any version" or bool(ours_newest and ours_newest != "any version" and _version_key(newest) >= _version_key(ours_newest))
            if state == "watch" and not ready:
                continue
            rows.append((count, repo.lower(), bundle, newest, state))
        rows.sort(key=lambda row: (row[4] != "watch", -row[0], row[1]))
        remaining = max(0, len(rows) - 3)
        label = str(target.get("label") or target.get("id") or package)
        ours_text = ours if ours.strip("/") else "none configured"
        ours_phrase = ours_text + (" (not in the index)" if ours_count is None else " with %d" % ours_count)
        if extra_text:
            ours_phrase += ", plus extras " + ", ".join(extra_text)
        current = next((target.get(k) for k in ("current_version", "current_app_version", "app_version", "version", "max_app_version")
                        if isinstance(target.get(k), str) and target.get(k).strip()), None)
        selected = rows[:3]
        for position, (count, _, bundle, newest, state) in enumerate(selected):
            repo = str(bundle.get("repo"))
            count_word = "patch" if count == 1 else "patches"
            version_phrase = "its newest listed app version " + newest
            if current:
                version_phrase += ", ours " + current
            first = "%s: %s offers %d %s for it (we use: %s; %s)" % (
                label, repo, count, count_word, ours_phrase, version_phrase)
            source = str(bundle.get("source", "github")).lower()
            ident = bundle.get("project_id")
            if ident is None:
                ident = repo
            # W16h: the id is the app and provider only. It used to hash the whole
            # line, so a primary switch or a new version minted a new id and lost the
            # owner's drop or hold.
            item = {"id": item_id("decide", "provider|%s|%s" % (package, repo.lower())), "kind": "decide", "first_line": first,
                    "text": first, "description": first + " take = run Explore (a patches issue with the live list opens); drop = hide for good; hold = 14 days",
                    "action": "explore", "host": source, "ident": str(ident), "package": package,
                    "provider_label": label, "provider_more": remaining if position == len(selected) - 1 else 0,
                    "target": str(target.get("id", "")), "repo": repo, "count": count, "newest": newest,
                    "ours_version": ours_newest or "", "watched": state == "watch",
                    "patch_rows": _patch_rows(bundle, package, compatibilities, have)}
            out.append(item)
    return out


def _held_route(row: dict, targets: Path | list | None) -> dict:
    """Return the existing 5. Add target route when it can address this provider."""
    for target in _load_targets(targets):
        if str(target.get("id", "")) != row.get("target"):
            continue
        candidates = target.get("candidates", []) or []
        primary = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
        if str(primary.get("name", "")) != row.get("provider") or not primary.get("patch_dir"):
            return {}
        if not TARGET_IDENT_RE.fullmatch(row.get("target", "")):
            return {}
        name = row.get("name", "")
        if not name or any(ord(c) < 32 or ord(c) == 127 or c == ";" for c in name):
            return {}
        return {"action": "patch", "target": row["target"], "patches": name}
    return {}


# W16h (owner, 25 Oct 2026): a take on these cannot change the outcome. A BANNED
# name stays off by rule, and a second copy of a name waits for the bundle that
# offers it first. They are counted per app in FYI instead of offered as takes.
RULE_OFF = (("matches banned", "stay off by the BANNED rule"),
            ("another bundle", "wait for the bundle that offers them first (one bundle per name)"))


def _rule_off(why: str) -> str:
    low = (why or "").lower()
    return next((text for key, text in RULE_OFF if key in low), "")


def _root_of(targets) -> Path | None:
    """The checkout whose decision memory and include lists apply. A list of targets (tests,
    tools) has no checkout, so it gets no memory."""
    if isinstance(targets, Path):
        return targets.resolve().parents[1] if targets.name == "targets.json" else None
    if targets is None:
        return Path(__file__).resolve().parents[2]
    return None


def _held_details(targets, bundles) -> dict:
    """W16j: (target id, provider label, patch name) -> (description, newest app version)."""
    if bundles is None:
        bundles = Path(__file__).resolve().parents[1] / "community" / "bundles.json"
    index = _load_value(bundles, {})
    if not isinstance(index, dict):
        return {}
    comp = index.get("compatibilities", []) if isinstance(index.get("compatibilities"), list) else []
    by_repo = {str(b.get("repo", "")).lower(): b for b in index.get("bundles", []) or [] if isinstance(b, dict)}
    out = {}
    for t in _load_targets(targets):
        for c in (t.get("candidates") or []) + (t.get("extra_bundles") or []):
            if not isinstance(c, dict):
                continue
            b = by_repo.get(("%s/%s" % (c.get("owner", ""), c.get("repo", ""))).lower())
            if not b:
                continue
            for name, desc, ver, _ in _patch_rows(b, str(t.get("package", "")), comp, set()):
                out[(str(t.get("id")), str(c.get("name")), name)] = (desc, ver)
    return out


def held_items(path: Path | None, targets: Path | list | None = None, bundles: Path | dict | None = None) -> list[dict]:
    """Render each recorded held Selection name as its own actionable item."""
    details = _held_details(targets, bundles)
    text = read_report(path)
    data = load_json(path)
    out, off = [], {}
    memory = decisions.load(_root_of(targets))
    for row in _held_rows(text, data):
        # W16j: a name the owner already decided (src/patches/DECISIONS.json) is never asked
        # again; Selection watch applies the decision on its next run.
        if decisions.call(memory, row["target"], row["name"])[0]:
            continue
        why = _rule_off(row["why"])
        if why:
            off.setdefault((row["target"], row["provider"], why), []).append(row["name"])
            continue
        first = "%s: %s offers '%s' (held: %s)" % (row["target"], row["provider"], row["name"], row["why"])
        # The key deliberately excludes the reason: a changed explanation must
        # not erase an owner's prior take/drop/hold ledger decision.
        ident = item_id("decide", "held|%s|%s|%s" % (row["target"], row["provider"], row["name"]))
        route = _held_route(row, targets)
        if route:
            description = (first + " Take = the repo runs 5. Add target and adds it to this provider; "
                           "drop = hide for good; hold = 14 days.")
        else:
            description = (first + " Take = recorded, and the next packet adds it; "
                           "drop = hide for good; hold = 14 days.")
        desc, ver = details.get((row["target"], row["provider"], row["name"]), ("", ""))
        out.append({"id": ident, "kind": "decide", "first_line": first, "text": first,
                    "description": description, "held": dict(row, desc=desc, version=ver), **route})
    for (target, provider, why), names in sorted(off.items()):
        shown = ", ".join("`%s`" % x for x in sorted(names)[:12])
        more = " and %d more" % (len(names) - 12) if len(names) > 12 else ""
        line = "- %s / %s: %d name(s) %s: %s%s" % (target, provider, len(names), why, shown, more)
        out.append({"id": item_id("fyi", line), "kind": "fyi", "first_line": line, "text": line,
                    "description": line})
    return out


def _items(kind: str, texts: Iterable[str]) -> list[dict]:
    out = []
    for text in texts:
        first = _first_line(text)
        out.append({"id": item_id(kind, first), "kind": kind, "first_line": first,
                    "text": text, "description": _description(kind, first)})
    return out


def app_items(targets: Path | None = None) -> list[dict]:
    """Retired in W16j (owner, 25 Oct 2026): 'Keep building X?' for every app every day was
    noise. A broken app shows on the status page and in its Failing issue instead."""
    return []


def _old_app_items(targets: Path | None = None) -> list[dict]:
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


def load_ledger(path: Path | None, fail_closed: bool = False) -> list[dict]:
    if not path or not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        if fail_closed:
            raise ValueError("decision ledger is not valid JSON") from exc
        return []
    if not isinstance(data, list):
        if fail_closed:
            raise ValueError("decision ledger must be a JSON list")
        return []
    if fail_closed:
        # W16n review 2: a malformed row must stop, not make a repeated command look new.
        for row in data:
            if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                    or not re.fullmatch(r"N-[0-9a-fA-F]{6}", row["id"])
                    or row.get("verb") not in ("take", "drop", "hold")
                    or not ("except" not in row or (isinstance(row["except"], list)
                            and all(isinstance(x, str) for x in row["except"])))):
                raise ValueError("decision ledger has a malformed row")
    return data


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
    """Parse only complete command lines; prose and unknown ids are ignored.

    W16j: with the body's catalog (a dict of id -> metadata) a line may also name a group
    (take G2), every item (drop all) or accept every "My call" (yes all). keep = take. A later
    line about the same item wins, so `yes all` then `drop N-xxxxxx` works."""
    catalog = known_ids if isinstance(known_ids, dict) else None
    known = {x.upper() for x in known_ids} if known_ids is not None else None
    chosen = {}
    for line in (comment or "").splitlines():
        if catalog is not None and YES_ALL_RE.match(line):
            for ident, meta in catalog.items():
                if meta.get("mycall") in ("take", "drop", "hold"):
                    chosen.pop(ident, None)
                    chosen[ident] = meta["mycall"]
            continue
        match = COMMAND_RE.match(line)
        if not match:
            continue
        verb = match.group(1).lower()
        verb = "take" if verb == "keep" else verb
        ref = match.group(2).upper()
        if ref.startswith("N-"):
            if known is None or ref in known:
                chosen.pop(ref, None)
                chosen[ref] = verb
        elif catalog is not None:
            for ident, meta in catalog.items():
                if ref == "ALL" or str(meta.get("group", "")).upper() == ref:
                    chosen.pop(ident, None)
                    chosen[ident] = verb
    return [(verb, ident) for ident, verb in chosen.items()]


def parse_excepts(comment: str) -> dict[str, list[str]]:
    """W16j: take N-xxxxxx except "A", "B" -> {N-xxxxxx: [A, B]} (names to leave out)."""
    out = {}
    for line in (comment or "").splitlines():
        match = COMMAND_RE.match(line)
        if match and match.group(3) and match.group(2).upper().startswith("N-"):
            names = [n.strip() for n in re.findall(r'"([^"]{1,120})"', match.group(3))]
            if not names:
                names = [n.strip() for n in match.group(3).split(",") if n.strip()]
            out[match.group(2).upper()] = names[:40]
    return out


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
    """Apply review effects and dispatch Explore or the existing patch route."""
    if item.get("action") == "patch" and verb == "take":
        target = str(item.get("target", ""))
        patches = str(item.get("patches", ""))
        if not TARGET_IDENT_RE.fullmatch(target) or not patches or any(ord(c) < 32 or ord(c) == 127 or c == ";" for c in patches):
            return "patch refused: malformed app or patch name"
        result = gh(["workflow", "run", "add-target.yml", "--repo", repo, "-f", "action=patch",
                     "-f", "id=" + target, "-f", "patches=" + patches], run)
        if result.returncode != 0:
            raise OSError("Needs you patch dispatch failed")
        return "patch dispatched: next packet will add it"
    if item.get("action") == "explore" and verb == "take":
        host = str(item.get("host", "")).lower()
        ident = str(item.get("ident", ""))
        package = str(item.get("package", ""))
        valid_ident = ((host == "github" and bool(GITHUB_IDENT_RE.fullmatch(ident))) or
                       (host == "gitlab" and bool(GITLAB_IDENT_RE.fullmatch(ident))))
        if host not in ("github", "gitlab") or not valid_ident or not PACKAGE_RE.fullmatch(package) or len(package) > 120:
            return "Explore refused: malformed provider or package"
        result = gh(["workflow", "run", "explore.yml", "--repo", repo, "-f", "host=" + host,
                     "-f", "ident=" + ident, "-f", "package=" + package, "-f", "channel=prerelease"], run)
        if result.returncode != 0:
            raise OSError("Needs you Explore dispatch failed")
        return "Explore dispatched: patches issue will open"
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
           review: Path | None = None, bundles: Path | dict | None = None) -> str:
    if isinstance(ledger, Path):
        ledger = load_ledger(ledger)
    ledger = ledger or []
    buckets = {kind: [] for kind in ORDER}
    for name in ("selection", "tooling", "nightly", "provider", "community"):
        _source(reports.get(name), name, buckets)
    all_items = []
    for kind in ORDER:
        all_items.extend(_items(kind, buckets[kind]))
    # Provider choices come from the checked-out community index, not a stale
    # collector paragraph. They remain in Decide and have stable ids.
    all_items.extend(provider_items(bundles, targets))
    all_items.extend(held_items(reports.get("selection"), targets, bundles))
    all_items.extend(_review_items(review or reports.get("review")))
    all_items.extend(app_items(targets))
    visible = [item for item in all_items if decision_state(item, ledger, now) == "visible"]
    taken = [item for item in all_items if decision_state(item, ledger, now) == "taken"]
    actionable = sum(1 for item in visible if item["kind"] in ("decide", "install", "fix", "app", "review"))
    if not actionable and not taken:
        return "# Needs you: OK\n\n**Needs you:** nothing needs you today.\n"
    fingerprint = hashlib.sha256(json.dumps([(x["id"], x["text"]) for x in visible], sort_keys=True).encode()).hexdigest()[:16]
    return _grouped(visible, taken, actionable, fingerprint)


def group_of(item: dict) -> tuple[str, str]:
    """W16j: (group id, my call) for one item. My call is what `yes all` applies; '' means
    the owner's taste, which `yes all` leaves alone."""
    if item.get("action") == "explore":
        return "G1", "take" if item.get("watched") else ""
    held = item.get("held")
    if held:
        why = str(held.get("why", "")).lower()
        if "changes what the app shows" in why:
            return "G2", ""
        if "no description" in why:
            return "G3", "hold"
        if "universal patch" in why:
            return "G4", "drop"
        if "confirm" in why or any(w in (why + " " + str(held.get("name", "")).lower()) for w in RISKY):
            return "G5", "drop"
        if "hold word" in why:
            return "G6", ""
        return "G7", "hold"
    return "G8", ""


def _cell(value, limit=160) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text.replace("|", "\\|") or "-"


def _grouped(visible: list[dict], taken: list[dict], actionable: int, fingerprint: str) -> str:
    groups = {}
    for item in visible:
        if item["kind"] == "fyi":
            continue
        gid, mine = group_of(item)
        item["group"], item["mycall"] = gid, mine
        groups.setdefault(gid, []).append(item)
    calls = sum(1 for g in groups.values() for i in g if i["mycall"])
    lines = ["<!-- needs-you:%s -->" % fingerprint, "# Needs you: NEEDS YOU", "",
             "**What happened:** %d choice(s) wait: %s." % (actionable, ", ".join(
                 "%s %d" % (GROUPS[g][0].split(":")[0].lower(), len(groups[g])) for g in sorted(groups))),
             "**Does it need you:** yes.",
             "**What to do:** comment `yes all` to accept every \"My call\" (%d of them; rows without one stay). "
             "Or one line per group or item: `take G2`, `drop G4`, `take N-xxxxxx`, "
             "`take N-xxxxxx except \"Name\", \"Name\"`. `keep` means take; `take all` takes everything." % calls, ""]
    for gid in sorted(groups):
        items = groups[gid]
        title, note = GROUPS[gid]
        lines += ["## %s · %s (%d)" % (gid, title, len(items)), "", "_%s._" % note, ""]
        if gid == "G1":
            lines += ["| ID | App | Provider | Patches | App version | My call |", "|---|---|---|---|---|---|"]
            for i in items:
                rows = i.get("patch_rows") or []
                new = sum(1 for r in rows if not r[3])
                ver = str(i.get("newest") or "-") + ((" (ours %s)" % i["ours_version"]) if i.get("ours_version") else "")
                lines.append("| %s | %s | %s | %d (%d new to us) | %s | %s |" % (
                    i["id"], _cell(i.get("provider_label")), _cell(i.get("repo")), i.get("count", 0), new, _cell(ver),
                    (i["mycall"] + " (you took it; it now fits our version)") if i.get("watched") else "your call"))
            lines += ["- %s: and %d more in the index" % (i.get("provider_label", "This app"), i["provider_more"])
                      for i in items if i.get("provider_more")]
            lines.append("")
            for i in items:
                rows = [r for r in (i.get("patch_rows") or []) if not r[3]]
                if not rows:
                    continue
                shown = rows[:25]
                body = ["- **%s** (app %s): %s" % (_cell(r[0], 80), _cell(r[2], 30), _cell(r[1], 140)) for r in shown]
                if len(rows) > len(shown):
                    body.append("- and %d more" % (len(rows) - len(shown)))
                lines += ["<details><summary>%s %s: what its %d new patch(es) do</summary>" % (
                    i["id"], html.escape(str(i.get("repo", ""))), len(rows)), ""] + body + ["", "</details>", ""]
        elif gid == "G8":
            for i in items:
                lines.append("- **%s**: %s" % (i["id"], _cell(i.get("description"), 400)))
            lines.append("")
        else:
            lines += ["| ID | App | Provider | Patch | What it does | App version | My call |",
                      "|---|---|---|---|---|---|---|"]
            for i in items:
                h = i["held"]
                lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                    i["id"], _cell(h.get("target")), _cell(h.get("provider")), _cell(h.get("name"), 80),
                    _cell(h.get("desc") or "(no description in the index)"), _cell(h.get("version") or "not listed", 30),
                    i["mycall"] or "your taste"))
            lines.append("")
    fyi = [i for i in visible if i["kind"] == "fyi"]
    if fyi:
        lines += ["<details><summary>FYI (%d): nothing to do</summary>" % len(fyi), ""] + [i["first_line"] for i in fyi] + ["", "</details>", ""]
    if taken:
        lines += ["<details><summary>Taken, waiting for the next packet (%d)</summary>" % len(taken), ""]
        lines += ["- **%s** — %s" % (i["id"], i["first_line"]) for i in taken] + ["", "</details>", ""]
    for item in visible:
        if item["kind"] == "fyi":
            continue
        metadata_row = {"id": item["id"], "kind": item["kind"], "group": item["group"], "mycall": item["mycall"],
                        "first_line": item["first_line"][:300]}
        for field in ("title", "labels", "issue_number", "action", "host", "ident", "package", "target", "patches"):
            if field in item:
                metadata_row[field] = item[field]
        lines.append("<!-- needs-you-item:%s -->" % json.dumps(metadata_row, separators=(",", ":")))
    text = "\n".join(lines).rstrip() + "\n"
    if len(text.encode("utf-8")) > 64000:
        # GitHub refuses bodies over 65536 characters; the folded patch lists go first.
        text = re.sub(r"<details><summary>N-[0-9a-f]{6} .*?</details>\n\n", "", text, flags=re.S)
    return text


def gh(args: list[str], run=subprocess.run):
    return run(["gh"] + args, capture_output=True, text=True, timeout=120)


WORKFLOWS = {
    "nightly": ("watch.yml", ("nightly-report-",), ("nightly-report.txt", "nightly-report.json")),
    "provider": ("agent-watch.yml", ("provider-watch-",), ("report.md", "report.json")),
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
        # W16j (owner: "I get dizzy reading comments"): the body is the page; a comment only
        # when new items need an answer, listing just those.
        fresh = [i for i in dict.fromkeys(ID_RE.findall(body)) if i not in set(ID_RE.findall(old))]
        if not fresh:
            return "EDITED"
        lines = [l for l in body.splitlines() if any(i in l for i in fresh) and not l.startswith("<!--")]
        note = "**Needs you: %d new item(s)**\n\n%s\n\nAnswer on this issue (`yes all`, `take G2`, `take N-xxxxxx`)." % (
            len(fresh), "\n".join(lines[:30]) or ", ".join(fresh[:30]))
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
    ledger = load_ledger(ledger_path, fail_closed=True)
    commands = parse_decisions(body, catalog)
    if not commands:
        return "IGNORED"
    excepts = parse_excepts(body)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipts, batch = [], {}
    for verb, ident in commands:
        meta = catalog[ident]
        requested_except = excepts.get(ident, [])
        prior = next((row for row in reversed(ledger)
                      if str(row.get("id", "")).upper() == ident
                      and str(row.get("verb", "")).lower() == verb
                      and (row.get("except") or []) == requested_except), None)
        if prior is not None:
            receipts.append("%s %s: already recorded; no-op" % (verb, ident))
            continue
        record = {"id": ident, "verb": verb, "kind": meta.get("kind", "unknown"),
                  "first_line": meta.get("first_line", ""), "comment_url": comment_url, "time": stamp}
        if ident in excepts:
            record["except"] = excepts[ident]
        ledger.append(record)
        # W16j: a group take of held names runs 5. Add target once per app, not once per name.
        if meta.get("action") == "patch" and verb == "take":
            batch.setdefault(str(meta.get("target", "")), []).append((ident, str(meta.get("patches", ""))))
            continue
        effect = apply_effect(verb, meta, repo, run)
        receipts.append("%s %s — %s" % (verb, ident, effect))
    for target, rows in sorted(batch.items()):
        names = [n for _, n in rows]
        if len(rows) == 1 or any(";" in n for n in names):
            for ident, n in rows:
                receipts.append("take %s — %s" % (ident, apply_effect("take", {"action": "patch", "target": target, "patches": n}, repo, run)))
            continue
        joined = "; ".join(names)
        if not TARGET_IDENT_RE.fullmatch(target) or any(ord(c) < 32 or ord(c) == 127 for c in joined):
            receipts.append("take %s — patch refused: malformed app or patch name" % ", ".join(i for i, _ in rows))
            continue
        result = gh(["workflow", "run", "add-target.yml", "--repo", repo, "-f", "action=patch",
                     "-f", "id=" + target, "-f", "patches=" + joined], run)
        if result.returncode != 0:
            raise OSError("Needs you patch dispatch failed")
        receipts.append("take %s — one 5. Add target run for %s (%d names)" % (", ".join(i for i, _ in rows), target, len(rows)))
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
    r.add_argument("--bundles", type=Path)
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
        body = render({name: getattr(a, name) for name in ISSUES}, ledger=a.ledger, targets=a.targets, bundles=a.bundles, review=a.review)
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
