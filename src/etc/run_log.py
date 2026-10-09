#!/usr/bin/env python3
"""Key lines from a GitHub Actions log, without the script text the log echoes (W9, 9 Oct 2026).

    gh run view RUN_ID --log > run.log
    python3 src/etc/run_log.py run.log VERSION_STEP_DOWN minSdkVersion "Release URL"

Each step's log starts with `##[group]Run <first script line>`, then the rest of the script,
its shell and env, then `##[endgroup]`. A grep for a notice name also matches the command
that prints it, so the W8 RESULT's key_lines held script lines as noise (lesson L042). This
drops every echoed block and the runner's own `##[...]` markers, then keeps lines that
contain any pattern (plain text, case-sensitive), in log order, at most --limit lines.
`gh run view --log` prefixes each line with `job<TAB>step<TAB>`; a raw job log does not.
Both shapes work. Output lines are `step | text` when the step is known.
"""
import argparse
import re
import sys

STAMP = re.compile(r'^\ufeff?\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z ?')
# Colour codes: a real ESC, or the two characters "^[" that gh writes in its place (W10).
COLOUR = re.compile(r'(?:\x1b|\^\[)\[[0-9;]*m')


def split(line):
    """(job, step, text) for one log line; job and step are '' for a raw job log."""
    parts = line.rstrip('\r\n').split('\t', 2)
    job, step, text = (parts if len(parts) == 3 else ('', '', parts[-1]))
    return job, step, STAMP.sub('', text, count=1)


def output_lines(text):
    """Every line a step printed, without echoed script blocks or runner markers."""
    echo = False
    for line in text.splitlines():
        job, step, body = split(line)
        if body.startswith('##[group]Run '):
            echo = True
            continue
        if echo:
            if body.startswith('##[endgroup]'):
                echo = False
            continue
        if body.startswith('##[group]') or body.startswith('##[endgroup]'):
            continue
        yield job, step, body


def key_lines(text, patterns, limit=80):
    out = []
    for job, step, body in output_lines(text):
        if any(p in body for p in patterns):
            out.append((step + ' | ' if step else '') + COLOUR.sub('', body).strip())
            if len(out) >= limit:
                break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log')
    ap.add_argument('patterns', nargs='+')
    ap.add_argument('--limit', type=int, default=80)
    a = ap.parse_args(argv)
    with open(a.log, encoding='utf-8', errors='replace') as f:
        rows = key_lines(f.read(), a.patterns, a.limit)
    for r in rows:
        print(r)
    return 0 if rows else 1


if __name__ == '__main__':
    sys.exit(main())
