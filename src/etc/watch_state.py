#!/usr/bin/env python3
"""Read and update the small shared state branch used by the watch workflows.

The branch is deliberately updated through GitHub's contents API.  Each PUT changes
one path in the branch, so concurrent writers do not replace the other watch's file.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess

BRANCH = "watch-state"
MAX_BYTES = 2 * 1024 * 1024
ALLOWED = {"state.json", "needs-you-decisions.json"}


def _repo() -> str:
    repo = os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY")
    if not repo or not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
        raise ValueError("REPO must be owner/name")
    return repo


def _endpoint(repo: str, name: str) -> str:
    return "repos/%s/contents/%s?ref=%s" % (repo, name, BRANCH)


def _run(args: list[str], *, input_bytes: bytes | None = None):
    return subprocess.run(["gh", *args], input=input_bytes, capture_output=True, timeout=120)


def _text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value or "")


def _bytes(value) -> bytes:
    return value if isinstance(value, bytes) else str(value or "").encode("utf-8")


def _status(result) -> str:
    """Return an explicit HTTP status mentioned by gh, never an incidental number."""
    text = _text(getattr(result, "stdout", "")) + " " + _text(getattr(result, "stderr", ""))
    match = re.search(r"\bHTTP(?:\s+status)?\s*[:=]?\s*(\d{3})\b", text, re.I)
    if not match:
        match = re.search(r'"status"\s*:\s*(\d{3})\b', text, re.I)
    if not match and text.strip() in {"404", "409", "422"}:
        return text.strip()
    return match.group(1) if match else ""


def _is_404(result) -> bool:
    return _status(result) == "404"


def _is_conflict(result) -> bool:
    return _status(result) in {"409", "422"}


def _scrub(text: str) -> str:
    """W16n review 2: never echo a token from gh stderr."""
    for key in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(key)
        if value:
            text = text.replace(value, "***")
    return re.sub(r"x-access-token:[^@\s]+@", "x-access-token:***@", text)


def _stop(message: str, code: int = 1) -> int:
    print("STOP watch-state " + message)
    return code


def _check_name(name: str) -> None:
    if name not in ALLOWED:
        raise ValueError("refusing path outside watch-state allowlist: " + name)


def get(name: str, destination: Path) -> int:
    _check_name(name)
    repo = _repo()
    result = _run(["api", "-H", "Accept: application/vnd.github.raw", _endpoint(repo, name)])
    if result.returncode != 0:
        if _is_404(result):
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
            return _stop("get %s missing" % name, 3)
        detail = _text(result.stderr).strip().splitlines()[-1:] or ["gh api failed"]
        return _stop("get %s failed: %s" % (name, _scrub(detail[0])[:240]))
    try:
        if len(_bytes(result.stdout)) > MAX_BYTES:
            return _stop("get %s exceeds 2 MiB" % name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_bytes(result.stdout))
    except OSError as exc:
        return _stop("get %s could not write destination: %s" % (name, exc))
    print("OK watch-state get %s %d bytes" % (name, len(_bytes(result.stdout))))
    return 0


def _read_sha(repo: str, name: str):
    result = _run(["api", _endpoint(repo, name)])
    if result.returncode == 0:
        try:
            data = json.loads(_text(result.stdout))
        except (UnicodeDecodeError, ValueError):
            return "error", None
        sha = data.get("sha") if isinstance(data, dict) else None
        return ("ok", sha) if isinstance(sha, str) and sha else ("error", None)
    if _is_404(result):
        return "missing", None
    return "error", None


def _branch_exists(repo: str) -> bool | None:
    result = _run(["api", "repos/%s/git/ref/heads/%s" % (repo, BRANCH)])
    if result.returncode == 0:
        return True
    if _is_404(result):
        return False
    return None


def _put_once(repo: str, name: str, payload: dict):
    return _run(["api", "-X", "PUT", _endpoint(repo, name), "--input", "-"],
                 input_bytes=json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def put(name: str, source: Path, message: str) -> int:
    _check_name(name)
    repo = _repo()
    try:
        content = source.read_bytes()
    except OSError as exc:
        return _stop("put %s could not read source: %s" % (name, exc))
    if len(content) > MAX_BYTES:
        return _stop("put %s exceeds 2 MiB" % name)

    state, sha = _read_sha(repo, name)
    if state == "error":
        return _stop("put %s could not read current file" % name)
    if state == "missing":
        # A missing file can be created, but a missing branch cannot be created safely
        # without first making a commit.  The branch is provisioned by the repository.
        exists = _branch_exists(repo)
        if exists is not True:
            if exists is False:
                return _stop("put %s branch %s does not exist; refusing to create an orphan branch" % (name, BRANCH))
            return _stop("put %s could not check branch %s" % (name, BRANCH))

    encoded = base64.b64encode(content).decode("ascii")
    payload = {"message": message, "content": encoded, "branch": BRANCH}
    if sha:
        payload["sha"] = sha
    result = _put_once(repo, name, payload)
    if result.returncode != 0 and _is_conflict(result):
        # Another writer won the race.  Re-read its sha and retry this one path once.
        # A first write can also lose to another file's commit: then the path is still missing
        # and the create is retried without a sha.
        state, sha = _read_sha(repo, name)
        if state == "ok":
            payload["sha"] = sha
        elif state == "missing":
            payload.pop("sha", None)
        else:
            return _stop("put %s conflict retry could not read current file" % name)
        result = _put_once(repo, name, payload)
    if result.returncode != 0:
        detail = _text(result.stderr).strip().splitlines()[-1:] or ["gh api failed"]
        return _stop("put %s failed: %s" % (name, _scrub(detail[0])[:240]))
    print("OK watch-state put %s %d bytes" % (name, len(content)))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    get_parser = sub.add_parser("get")
    get_parser.add_argument("name")
    get_parser.add_argument("dest", type=Path)
    put_parser = sub.add_parser("put")
    put_parser.add_argument("name")
    put_parser.add_argument("src", type=Path)
    put_parser.add_argument("message")
    args = parser.parse_args(argv)
    try:
        if args.command == "get":
            return get(args.name, args.dest)
        return put(args.name, args.src, args.message)
    except (ValueError, OSError) as exc:
        return _stop(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
