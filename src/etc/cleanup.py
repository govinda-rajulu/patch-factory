#!/usr/bin/env python3
"""Obsolete releases and tags: one preview, then one exact apply (packet W4, 8 Oct 2026).

    python3 src/etc/cleanup.py preview [--out FILE]
    python3 src/etc/cleanup.py apply --token TOKEN [--receipt FILE]

Obsolete means:
  * a release src/etc/release_retention.py lists as a candidate: an older dated CI build of an
    app that still has its two newest releases. Frozen, manual, pre-release, unknown-prefix and
    marked releases are protected there and never touched here;
  * that release's tag;
  * a build tag (PREFIX-vVERSION-bDIGITS) whose release is already gone.
Any other tag stays. Apply re-reads GitHub, rebuilds the same list and refuses unless its
token equals the preview's, so nothing that appeared after the preview can be deleted. Before
deleting it writes a receipt (tag, commit, assets with sizes and sha256). It stops at the
first failed delete. Needs gh logged in as the repository owner.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_retention as rr  # noqa: E402

REPO = 'govinda-rajulu/patch-factory'
BUILD_TAG = re.compile(r'^[a-z0-9-]+-v[0-9]+(?:\.[0-9]+)*-b[0-9]{8}(?:[0-9]{26})?$')


def gh(args, run=subprocess.run):
    r = run(['gh'] + args, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise SystemExit('STOP: gh %s failed: %s' % (' '.join(args[:3]), (r.stderr or '').strip()[:300]))
    return r.stdout


def tags(run=subprocess.run):
    r = run(['git', 'ls-remote', '--tags', 'https://github.com/%s.git' % REPO], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise SystemExit('STOP: tag list unreadable; nothing changed')
    out = {}
    for line in r.stdout.splitlines():
        sha, ref = line.split('\t')
        if ref.startswith('refs/tags/') and not ref.endswith('^{}'):
            out[ref[len('refs/tags/'):]] = sha
    return out


def plan(releases, tag_map, targets):
    p = rr.preview(releases, targets, REPO)
    have = {r['tag_name'] for r in releases}
    rel = [{'id': c['release_id'], 'tag': c['tag']} for c in p['candidates']]
    gone = sorted(t for t in tag_map if t not in have and BUILD_TAG.match(t))
    drop_tags = sorted({c['tag'] for c in rel if c['tag'] in tag_map} | set(gone))
    body = {'releases': sorted(rel, key=lambda x: x['tag']), 'tags': drop_tags}
    token = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    return dict(body, token=token, protected=len(p['protected']), orphan_tags=gone)


def receipt(releases, tag_map, chosen):
    by_id = {r['id']: r for r in releases}
    rows = []
    for c in chosen['releases']:
        r = by_id[c['id']]
        rows.append({'tag': c['tag'], 'release_id': c['id'], 'name': r.get('name'), 'published_at': r.get('published_at'),
                     'commit': tag_map.get(c['tag']),
                     'assets': [{'name': a.get('name'), 'size': a.get('size'), 'digest': a.get('digest')} for a in r.get('assets') or []]})
    return {'repo': REPO, 'token': chosen['token'], 'releases': rows,
            'tags': [{'tag': t, 'commit': tag_map.get(t)} for t in chosen['tags']]}


def show(p):
    print('Cleanup preview: %d release(s) and %d tag(s) to delete; %d release(s) protected.'
          % (len(p['releases']), len(p['tags']), p['protected']))
    for r in p['releases']:
        print('  release ' + r['tag'])
    for t in p['tags']:
        print('  tag     ' + t)
    print('TOKEN ' + p['token'])


def main(argv=None, run=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['preview', 'apply'])
    ap.add_argument('--token')
    ap.add_argument('--out')
    ap.add_argument('--receipt', default='cleanup-receipt.json')
    a = ap.parse_args(argv)
    targets = json.loads(pathlib.Path('src/targets.json').read_text(encoding='utf-8'))
    rr.subprocess.run = run
    releases = rr.inventory(REPO)
    tag_map = tags(run)
    p = plan(releases, tag_map, targets)
    if a.mode == 'preview':
        show(p)
        if a.out:
            pathlib.Path(a.out).write_text(json.dumps(p, indent=1) + '\n', encoding='utf-8')
        return 0
    if a.token != p['token']:
        show(p)
        print('STOP: token %s does not match the list above (%s); GitHub changed since the preview. Nothing deleted.'
              % (a.token, p['token']))
        return 1
    pathlib.Path(a.receipt).write_text(json.dumps(receipt(releases, tag_map, p), indent=1) + '\n', encoding='utf-8')
    done = 0
    for r in p['releases']:
        gh(['api', '-X', 'DELETE', 'repos/%s/releases/%d' % (REPO, r['id'])], run)
        done += 1
    for t in p['tags']:
        gh(['api', '-X', 'DELETE', 'repos/%s/git/refs/tags/%s' % (REPO, t)], run)
        done += 1
    print('RESULT OK: deleted %d release(s) and %d tag(s). Receipt: %s' % (len(p['releases']), len(p['tags']), a.receipt))
    return 0


if __name__ == '__main__':
    sys.exit(main())
