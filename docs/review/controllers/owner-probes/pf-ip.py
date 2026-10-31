#!/usr/bin/env python3
"""Read-only issue and pull request collector (W15g close-out, 31 Oct 2026).

Writes every issue and pull request (open and closed), issue comments, review comments and labels of
govinda-rajulu/patch-factory as JSONL into ~/work/run-logs/pf-ip-<UTC stamp>/ and zips it. Uses the
logged-in gh CLI; changes nothing on GitHub. Used for the 31 Oct audit of 282 records
(docs/review/w15g-close/audit/). Upload the zip it names.
"""
import datetime, json, pathlib, shutil, subprocess, sys

REPO = 'govinda-rajulu/patch-factory'
QUERIES = (('issues', 'repos/%s/issues?state=all&per_page=100' % REPO),
           ('pulls', 'repos/%s/pulls?state=all&per_page=100' % REPO),
           ('comments', 'repos/%s/issues/comments?per_page=100' % REPO),
           ('reviewcomments', 'repos/%s/pulls/comments?per_page=100' % REPO),
           ('labels', 'repos/%s/labels?per_page=100' % REPO))


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = pathlib.Path.home() / 'work' / 'run-logs' / ('pf-ip-' + stamp)
    out.mkdir(parents=True)
    counts = {}
    for name, path in QUERIES:
        r = subprocess.run(['gh', 'api', '--paginate', path, '--jq', '.[]'], capture_output=True, text=True, timeout=900)
        rows = [l for l in r.stdout.splitlines() if l.strip()]
        for l in rows:
            json.loads(l)  # every line must be one JSON object
        (out / (name + '.jsonl')).write_text('\n'.join(rows) + ('\n' if rows else ''))
        counts[name] = len(rows)
        print('%s rc=%d rows=%d' % (name, r.returncode, len(rows)), flush=True)
        if r.returncode != 0:
            print('STOP: gh api %s failed: %s. Folder kept: %s' % (name, r.stderr.strip()[:200], out))
            return 1
    z = pathlib.Path(shutil.make_archive(str(out), 'zip', out.parent, out.name))
    print('COLLECT OK issues+prs=%d prs=%d comments=%d zip=%d' % (counts['issues'], counts['pulls'], counts['comments'], z.stat().st_size))
    print('RESULT OK. Upload %s' % z)
    return 0


if __name__ == '__main__':
    sys.exit(main())
