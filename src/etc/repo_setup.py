#!/usr/bin/env python3
"""Repo setup (W16z, 31 Oct 2026): apply .github/labels.json and file .github/seed-issues.json once.

Labels are created or updated, never deleted. A seed issue is filed only when no issue (open or
closed) carries its marker. Uses the gh CLI with the workflow token; prints one SETUP line per
item and a REPO_SETUP summary. Any API failure stops with exit 1 after what was done is printed.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r'^[a-z0-9][a-z0-9 -]{0,48}$')
COLOR_RE = re.compile(r'^[0-9a-f]{6}$')
ID_RE = re.compile(r'^[a-z0-9-]{3,40}$')


def marker(ident):
    return '<!-- pf-seed:%s -->' % ident


def load(root=ROOT):
    labels = json.loads((root / '.github/labels.json').read_text(encoding='utf-8'))['labels']
    seeds = json.loads((root / '.github/seed-issues.json').read_text(encoding='utf-8'))['issues']
    names = set()
    for l in labels:
        if set(l) != {'name', 'color', 'description'} or not NAME_RE.match(l['name']) or not COLOR_RE.match(l['color']) \
                or not isinstance(l['description'], str) or not 0 < len(l['description']) <= 100 or l['name'] in names:
            raise ValueError('bad label record %r' % (l,))
        names.add(l['name'])
    ids = set()
    for s in seeds:
        if set(s) != {'id', 'title', 'labels', 'body'} or not ID_RE.match(s['id']) or s['id'] in ids \
                or not 10 <= len(s['title']) <= 120 or not s['body'].strip() or '@' in s['body'] \
                or not all(x in names for x in s['labels']):
            raise ValueError('bad seed record %r' % (s.get('id'),))
        ids.add(s['id'])
    return labels, seeds


def gh(args, run=subprocess.run):
    r = run(['gh'] + args, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout, r.stderr


def main(run=subprocess.run, root=ROOT, repo=None):
    repo = repo or os.environ.get('REPO', 'govinda-rajulu/patch-factory')
    labels, seeds = load(root)
    done = {'created': 0, 'updated': 0, 'same': 0, 'filed': 0, 'present': 0}
    rc, out, err = gh(['api', '--paginate', 'repos/%s/labels?per_page=100' % repo, '--jq', '.[] | [.name, .color, .description] | @json'], run)
    if rc != 0:
        print('REPO_SETUP STOP: labels unreadable'); return 1
    have = {}
    for line in out.splitlines():
        if line.strip():
            n, c, d = json.loads(line)
            have[n] = (c, d or '')
    for l in labels:
        if l['name'] not in have:
            args = ['api', '-X', 'POST', 'repos/%s/labels' % repo, '-f', 'name=' + l['name'], '-f', 'color=' + l['color'], '-f', 'description=' + l['description']]
            kind = 'created'
        elif have[l['name']] != (l['color'], l['description']):
            args = ['api', '-X', 'PATCH', 'repos/%s/labels/%s' % (repo, l['name'].replace(' ', '%20')), '-f', 'color=' + l['color'], '-f', 'description=' + l['description']]
            kind = 'updated'
        else:
            done['same'] += 1; print('SETUP label %s: unchanged' % l['name']); continue
        rc, _, _ = gh(args, run)
        if rc != 0:
            print('REPO_SETUP STOP: label %s not %s' % (l['name'], kind)); return 1
        done[kind] += 1; print('SETUP label %s: %s' % (l['name'], kind))
    rc, out, err = gh(['api', '--paginate', 'repos/%s/issues?state=all&per_page=100' % repo, '--jq', '.[] | select(.pull_request == null) | .body // ""'], run)
    if rc != 0:
        print('REPO_SETUP STOP: issues unreadable, nothing filed'); return 1
    for s in seeds:
        if marker(s['id']) in out:
            done['present'] += 1; print('SETUP issue %s: already filed' % s['id']); continue
        args = ['issue', 'create', '-R', repo, '--title', s['title'], '--body', s['body'] + '\n\n' + marker(s['id'])]
        for x in s['labels']:
            args += ['--label', x]
        rc, _, _ = gh(args, run)
        if rc != 0:
            print('REPO_SETUP STOP: issue %s not filed' % s['id']); return 1
        done['filed'] += 1; print('SETUP issue %s: filed' % s['id'])
    print('REPO_SETUP OK labels created=%(created)d updated=%(updated)d unchanged=%(same)d issues filed=%(filed)d already=%(present)d' % done)
    return 0


if __name__ == '__main__':
    sys.exit(main())
