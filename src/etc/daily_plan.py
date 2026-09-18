#!/usr/bin/env python3
"""Validate existing polling evidence before emitting a complete daily matrix.

No semantic-fingerprint or publishing-policy change. Each enabled opted-in
target must emit exactly one new_patch=0|1 record, or the entire Plan fails.
"""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

MAX_CONFIG = 4 * 1024 * 1024
MAX_OUTPUT = 64 * 1024
POLL_TIMEOUT = 180

class PlanError(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise PlanError(message)

def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate configuration key")
        result[key] = value
    return result

def reject_constant(_):
    raise PlanError("nonfinite configuration value")

def regular_bytes(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode), "nonregular evidence file")
        need(info.st_size <= limit, "evidence exceeds size limit")
        data = stream.read(limit + 1)
    need(len(data) <= limit, "evidence exceeds size limit")
    return data

def target_ids(data):
    config = json.loads(data, object_pairs_hook=pairs,
                        parse_constant=reject_constant)
    need(isinstance(config, list) and bool(config), "targets must be a nonempty array")
    seen, selected = set(), []
    for target in config:
        need(isinstance(target, dict), "target must be an object")
        ident = target.get("id")
        need(isinstance(ident, str) and re.fullmatch(r"[a-z0-9-]+", ident),
             "invalid target identifier")
        need(ident not in seen, "duplicate target identifier")
        seen.add(ident)
        need(type(target.get("enabled")) is bool, "enabled must be boolean")
        need(type(target.get("poll", False)) is bool, "poll must be boolean")
        if target["enabled"] and target.get("poll", False):
            selected.append(ident)
    return selected

def poll_result(data):
    need(len(data) <= MAX_OUTPUT, "oversized poll result")
    match = re.fullmatch(rb"new_patch=([01])(?:\r?\n)?", data)
    need(match is not None,
         "poll must emit exactly one new_patch=0 or new_patch=1 record")
    return match.group(1) == b"1"

def collect(root, ids, environment, timeout=POLL_TIMEOUT, runner=None):
    run = subprocess.run if runner is None else runner
    wanted, failures = [], []
    with tempfile.TemporaryDirectory(prefix="pf-daily-plan-") as scratch:
        for index, ident in enumerate(ids):
            evidence = Path(scratch) / (str(index) + ".out")
            evidence.touch(mode=0o600, exist_ok=False)
            env = dict(environment, GITHUB_OUTPUT=str(evidence))
            try:
                # Existing poll diagnostics still go to the runner. Do not print
                # argv, environments or raw output records from this wrapper.
                result = run(["bash", "src/etc/poll.sh", ident], cwd=root,
                             env=env, timeout=timeout, check=False)
                need(result.returncode == 0, "poll exited unsuccessfully")
                changed = poll_result(regular_bytes(evidence, MAX_OUTPUT))
                print("daily plan: " + ident + ": " +
                      ("build requested" if changed else "unchanged"))
                if changed:
                    wanted.append(ident)
            except (PlanError, OSError, UnicodeError, subprocess.TimeoutExpired):
                failures.append(ident)
                print("::error::daily plan: " + ident +
                      ": poll failed, timed out, or produced invalid evidence",
                      file=sys.stderr)
    need(not failures, str(len(failures)) + " poll(s) unknown; no build plan emitted")
    return wanted

def emit(output, wanted):
    payload = ("count=" + str(len(wanted)) + "\n" +
               "matrix=" + json.dumps({"target": wanted},
                                      separators=(",", ":")) + "\n").encode()
    fd = os.open(output, os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "r+b") as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_OUTPUT,
             "invalid workflow output destination")
        old = stream.read(MAX_OUTPUT + 1)
        need(len(old) <= MAX_OUTPUT, "workflow output exceeds size limit")
        need(not any(re.match(rb"^(count|matrix)(=|<<)", line)
                     for line in old.splitlines()), "workflow output already contains a plan")
        need(not old or old.endswith(b"\n"), "workflow output must end with a newline")
        need(stream.write(payload) == len(payload), "short workflow output write")
        stream.flush()
    # I/O failure may leave a partial append, but exits nonzero. The dependent
    # build job must remain gated by successful completion of this Plan job.
    print("planned " + str(len(wanted)) + " target(s)")

def main(root=None, environment=None):
    root = Path.cwd() if root is None else Path(root)
    environment = dict(os.environ if environment is None else environment)
    try:
        dest = environment.get("GITHUB_OUTPUT")
        need(isinstance(dest, str) and bool(dest), "GITHUB_OUTPUT missing")
        output = Path(dest)
        if not output.is_absolute():
            output = root / output
        regular_bytes(output, MAX_OUTPUT)
        config = root / "src/targets.json"
        data = regular_bytes(config, MAX_CONFIG)
        ids = target_ids(data)
        print("opted in: " + (" ".join(ids) if ids else "(none)"))
        wanted = collect(root, ids, environment)
        need(regular_bytes(config, MAX_CONFIG) == data,
             "target configuration changed during polling")
        emit(output, wanted)
        return 0
    except (PlanError, OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        print("::error::daily plan refused invalid or incomplete inputs; "
              "no successful plan claimed", file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 1:
        print("::error::daily plan accepts no arguments", file=sys.stderr)
        sys.exit(1)
    sys.exit(main())
