#!/usr/bin/env python3
"""Prune stale GitHub Actions caches without touching a fresh cache.

A cache key prefix is the part before the right-most dash-separated segment that
is a version or hexadecimal hash.  For example, ``morphe-jar-a1b2c3d4`` has
prefix ``morphe-jar`` and ``tool-v2.4.1`` has prefix ``tool``.  If no segment
matches, the complete key is its own prefix.  This is deliberately conservative:
keys with an unknown suffix are never grouped with another key.

The newest cache (by ``created_at``) in each prefix is always retained.  A
remaining cache is eligible only when it was last accessed more than seven days
ago and was created more than 24 hours ago.  Missing or malformed timestamps
are retained rather than guessed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import Callable, Iterable

REPO = os.environ.get("GITHUB_REPOSITORY", "govinda-rajulu/patch-factory")
PAGE_SIZE = 100
STALE_DAYS = 7
FRESH_HOURS = 24
_HEX = re.compile(r"^[0-9a-fA-F]{7,64}$")
_VERSION = re.compile(r"^(?:v)?[0-9]+(?:\.[0-9]+)+(?:[-+][0-9A-Za-z.-]+)?$")


def cache_prefix(key: str) -> str:
    """Return the conservative grouping prefix for a cache key.

    Only a final-looking version/hash *segment* is removed: the right-most
    dash-separated segment matching a hexadecimal hash (7--64 chars) or a
    dotted numeric version (optionally beginning with ``v``).  Numeric-only
    run ids are intentionally not treated as versions, so synthetic/run caches
    stay isolated unless their key has an explicit version/hash suffix.
    """
    parts = key.split("-")
    for index in range(len(parts) - 1, 0, -1):
        segment = parts[index]
        if _HEX.fullmatch(segment) or _VERSION.fullmatch(segment):
            return "-".join(parts[:index])
    return key


def parse_time(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def gh(args: list[str], run: Callable = subprocess.run) -> str:
    result = run(["gh", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        detail = (result.stderr or "").strip().replace("\n", " ")[:300]
        raise RuntimeError("gh %s failed: %s" % (" ".join(args[:3]), detail))
    return result.stdout


def caches(repo: str, run: Callable = subprocess.run) -> list[dict]:
    """Read every cache page; never return a partial inventory."""
    rows: list[dict] = []
    seen: set[int] = set()
    for page in range(1, 101):
        endpoint = f"repos/{repo}/actions/caches?per_page={PAGE_SIZE}&page={page}"
        data = json.loads(gh(["api", endpoint], run))
        if not isinstance(data, dict) or not isinstance(data.get("actions_caches"), list):
            raise RuntimeError("cache response is not an actions_caches object")
        page_rows = data["actions_caches"]
        for row in page_rows:
            if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] in seen:
                raise RuntimeError("cache response has an invalid or duplicate row")
            if not isinstance(row.get("key"), str) or not row["key"]:
                raise RuntimeError("cache response has a missing key")
            seen.add(row["id"])
            rows.append(row)
        if len(page_rows) < PAGE_SIZE:
            return rows
    raise RuntimeError("more than 10000 caches; refusing a partial delete list")


def newest_by_prefix(rows: Iterable[dict]) -> dict[str, dict]:
    newest: dict[str, dict] = {}
    for row in rows:
        created = parse_time(row.get("created_at"))
        if created is None:
            continue
        prefix = cache_prefix(row["key"])
        prior = newest.get(prefix)
        if prior is None or (created, row["id"]) > (parse_time(prior["created_at"]), prior["id"]):
            newest[prefix] = row
    return newest


def candidates(rows: list[dict], now: dt.datetime) -> list[dict]:
    """Select stale, old, non-newest caches in deterministic id order."""
    keep = {row["id"] for row in newest_by_prefix(rows).values()}
    stale_before = now - dt.timedelta(days=STALE_DAYS)
    fresh_after = now - dt.timedelta(hours=FRESH_HOURS)
    selected = []
    for row in rows:
        if row["id"] in keep:
            continue
        accessed = parse_time(row.get("last_accessed_at"))
        created = parse_time(row.get("created_at"))
        if accessed is None or created is None:
            continue
        if accessed >= stale_before or created >= fresh_after:
            continue
        selected.append(row)
    return sorted(selected, key=lambda row: row["id"])


def delete_cache(repo: str, cache_id: int, run: Callable = subprocess.run) -> None:
    gh(["api", "--method", "DELETE", f"repos/{repo}/actions/caches/{cache_id}"], run)


def summary_text(repo: str, rows: list[dict], deleted: int, dry_run: bool) -> str:
    mode = "dry-run" if dry_run else "applied"
    return "### Actions cache pruning\n\n- Repository: `%s`\n- Mode: %s\n- Scanned: %d\n- %s: %d\n" % (
        repo, mode, len(rows), "Would delete" if dry_run else "Deleted", deleted)


def write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(text)


def main(argv: list[str] | None = None, run: Callable = subprocess.run, now: dt.datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--dry-run", action="store_true", help="report candidates without deleting")
    parser.add_argument("--now", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.now:
        now = parse_time(args.now)
        if now is None:
            parser.error("--now must be an ISO-8601 timestamp")
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = caches(args.repo, run)
    selected = candidates(rows, now)
    deleted = 0
    for row in selected:
        action = "would delete" if args.dry_run else "delete"
        print("%s cache id=%d key=%s prefix=%s" %
              (action, row["id"], row["key"], cache_prefix(row["key"])), flush=True)
        if not args.dry_run:
            delete_cache(args.repo, row["id"], run)
        deleted += 1
    text = summary_text(args.repo, rows, deleted, args.dry_run)
    print("cache summary: scanned=%d %s=%d" %
          (len(rows), "would_delete" if args.dry_run else "deleted", deleted))
    write_summary(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, json.JSONDecodeError, OSError) as exc:
        print("STOP: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
