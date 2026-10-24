#!/usr/bin/env python3
"""Validate the bounded JSONL output of the manual MCP scout.

The model is a discovery aid only.  This checker accepts no prose, URLs or
unknown target ids, and writes canonical JSONL for a human owner to review.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
APP = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_LINE = 4096
MAX_REASON = 1000


def target_ids(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("targets.json must be a list")
    ids = {row.get("id") for row in data if isinstance(row, dict) and isinstance(row.get("id"), str)}
    return {value for value in ids if APP.fullmatch(value)}


def check(input_path, targets_path, output_path, summary_path=None):
    ids = target_ids(targets_path)
    accepted = []
    dropped = 0
    total = 0
    for raw in Path(input_path).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        total += 1
        try:
            if len(raw) > MAX_LINE:
                raise ValueError("line too long")
            row = json.loads(raw)
            if not isinstance(row, dict) or set(row) != {"app", "repo", "reason"}:
                raise ValueError("schema")
            if not isinstance(row["app"], str) or row["app"] not in ids:
                raise ValueError("unknown app")
            if not isinstance(row["repo"], str) or not REPO.fullmatch(row["repo"]):
                raise ValueError("repo shape")
            if (not isinstance(row["reason"], str) or not row["reason"].strip()
                    or len(row["reason"]) > MAX_REASON or any(ord(c) < 32 for c in row["reason"])):
                raise ValueError("reason")
        except (ValueError, TypeError, json.JSONDecodeError):
            dropped += 1
            continue
        accepted.append({"app": row["app"], "repo": row["repo"], "reason": row["reason"].strip()})

    with Path(output_path).open("w", encoding="utf-8") as stream:
        for row in accepted:
            stream.write(json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n")
    message = "MCP scout validation: %d accepted, %d dropped (of %d non-empty lines)." % (
        len(accepted), dropped, total)
    print(message)
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write("### MCP scout validation\n\n" + message + "\n\n")
            stream.write("Validated candidate lines are in the `mcp-scout-results` artifact.\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--targets", default="src/targets.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary")
    args = parser.parse_args(argv)
    return check(args.input, args.targets, args.output, args.summary)


if __name__ == "__main__":
    sys.exit(main())
