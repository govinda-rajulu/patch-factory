#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import json, os, pathlib, re

def stop(message):
    raise SystemExit("batch plan: " + message)

def pairs(items):
    out = {}
    for key, value in items:
        if key in out: stop("duplicate JSON key")
        out[key] = value
    return out

def invalid_number(value):
    stop("nonfinite JSON number")

targets = json.loads(pathlib.Path("src/targets.json").read_text(),
                     object_pairs_hook=pairs, parse_constant=invalid_number)
if not isinstance(targets, list) or not targets: stop("targets must be a nonempty array")
known = {}
for target in targets:
    if not isinstance(target, dict): stop("invalid target record")
    ident = target.get("id")
    if not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9-]+", ident):
        stop("invalid configured target id")
    if ident in known: stop("duplicate configured target id")
    if type(target.get("enabled")) is not bool: stop("enabled must be boolean")
    known[ident] = target["enabled"]

raw = os.environ.get("RAW", "")
if not raw or len(raw) > 8192: stop("missing or oversized requested target list")
want = [part.strip() for part in raw.split(",")]
if any(not re.fullmatch(r"[a-z0-9-]+", ident) for ident in want):
    stop("empty or invalid requested target id")
if len(want) != len(set(want)): stop("duplicate requested target id")
if any(ident not in known for ident in want): stop("unknown requested target id")
if any(not known[ident] for ident in want): stop("disabled target requested")
dest = os.environ.get("GITHUB_OUTPUT")
if not dest: stop("GITHUB_OUTPUT missing")
matrix = json.dumps({"target": want}, separators=(",", ":"))
# Validate the complete plan before appending any output; no shared /tmp file.
with open(dest, "a", encoding="utf-8") as stream:
    stream.write("matrix=" + matrix + "\n")
print("planned " + str(len(want)) + " target(s): " + matrix)
PY
