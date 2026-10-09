#!/usr/bin/env python3
"""Routine cleanup: one preview, then one exact apply (packet W4, 8 Oct 2026; W9, 9 Oct 2026).

    python3 src/etc/cleanup.py preview [--out FILE]
    python3 src/etc/cleanup.py apply --token TOKEN [--receipt FILE]

What goes (owner rules, 9 Oct 2026):
  * releases: grouped by app (the tag before "-v<version>"); per app the two newest by
    publication time stay and every older one goes, whatever its layout, author or marker.
    A release whose app prefix is no target's tag_prefix in src/targets.json belongs to a
    retired app and goes too (owner, 9 Oct 2026: one Truecaller, the tc-combo build);
  * the tags of those releases, and any build tag (PREFIX-vVERSION-bDIGITS) whose release
    is already gone. Any other tag stays;
  * Pages deployment records (environment github-pages): the newest 5 stay, older ones go.
    They hold only an id, a date and a commit; the site itself is rebuilt from the branch.
    GitHub deletes only inactive records, so apply first posts an `inactive` status
    (W10: the W9 apply stopped on HTTP 422 without it);
  * merged packet branches: a `packet/...` branch whose head commit is already in main and
    which no open pull request uses. Every other branch stays (main, status, anything else).
Apply re-reads GitHub, rebuilds the same list and refuses unless its token equals the
preview's, so nothing that appeared after the preview can be deleted. Before deleting it
writes a receipt (releases with tag, commit and assets with sizes and sha256; tags with
commits; deployment ids, dates and commits; branch names and head commits, each restorable
with `git push origin <sha>:refs/heads/<name>` because the commit is in main). It stops at
the first failed delete and says how far it got. Needs gh logged in as the repository owner.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

REPO = 'govinda-rajulu/patch-factory'
BUILD_TAG = re.compile(r'^[a-z0-9-]+-v[0-9]+(?:\.[0-9]+)*-b[0-9]{8}(?:[0-9]{26})?$')
PAGES_ENV = 'github-pages'
KEEP = 2
KEEP_DEPLOYMENTS = 5
PACKET = 'packet/'
APP_TAG = re.compile(r'^([a-z0-9-]+?)-v[0-9][0-9.]*(?:-b[0-9]+)?$')


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


def listing(path, what, run=subprocess.run, key='id'):
    """Every row of a paged list, or stop: a partial list must never become a delete list."""
    rows, seen = [], set()
    sep = '&' if '?' in path else '?'
    for page in range(1, 101):
        data = json.loads(gh(['api', '%s%sper_page=100&page=%d' % (path, sep, page)], run))
        if not isinstance(data, list):
            raise SystemExit('STOP: the %s list is not a list; nothing changed' % what)
        for row in data:
            if not isinstance(row, dict) or row.get(key) in seen or not row.get(key):
                raise SystemExit('STOP: invalid or duplicate row in the %s list; nothing changed' % what)
            if key == 'id' and type(row['id']) is not int:
                raise SystemExit('STOP: invalid or duplicate row in the %s list; nothing changed' % what)
            seen.add(row[key])
            rows.append(row)
        if len(data) < 100:
            return rows
    raise SystemExit('STOP: more than 10000 rows in the %s list; nothing changed' % what)


def inventory(run=subprocess.run):
    return listing('repos/%s/releases' % REPO, 'release', run)


def deployments(run=subprocess.run):
    rows = listing('repos/%s/deployments?environment=%s' % (REPO, PAGES_ENV), 'deployment', run)
    for r in rows:
        if r.get('environment') != PAGES_ENV:
            raise SystemExit('STOP: deployment %s is not %s; nothing changed' % (r.get('id'), PAGES_ENV))
    return rows


def branches(run=subprocess.run):
    """Packet branches with their head commit, whether main contains it, and open PR heads."""
    rows = listing('repos/%s/branches' % REPO, 'branch', run, key='name')
    pulls = listing('repos/%s/pulls?state=open' % REPO, 'pull request', run)
    open_heads = {(p.get('head') or {}).get('ref') for p in pulls
                  if ((p.get('head') or {}).get('repo') or {}).get('full_name') == REPO}
    out = []
    for b in rows:
        name, sha = b['name'], (b.get('commit') or {}).get('sha') or ''
        row = {'name': name, 'sha': sha, 'open_pr': name in open_heads, 'in_main': None}
        if name.startswith(PACKET) and not row['open_pr']:
            if not re.match(r'^[0-9a-f]{40}$', sha):
                raise SystemExit('STOP: branch %s has no readable head; nothing changed' % name)
            status = gh(['api', 'repos/%s/compare/%s...main?per_page=1' % (REPO, sha), '--jq', '.status'], run).strip()
            row['in_main'] = status in ('ahead', 'identical')
        out.append(row)
    return out


def newest_first(row):
    return (str(row.get('published_at') or row.get('created_at') or ''), row['id'])


# The checkout this script lives in, wherever it is run from (the apply line runs it from ~).
TARGETS = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'targets.json'


def prefixes(path=None):
    """Every configured tag_prefix, enabled or not; None when the file cannot be read."""
    try:
        rows = json.loads(pathlib.Path(path or TARGETS).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    out = {t.get('tag_prefix') for t in rows if isinstance(t, dict) and t.get('tag_prefix')}
    return out or None


def plan(releases, tag_map, deploys=(), branch_rows=(), known=None):
    groups, kept, rel = {}, [], []
    for r in releases:
        m = APP_TAG.match(str(r.get('tag_name') or ''))
        if not m:
            kept.append({'tag': r.get('tag_name'), 'reason': 'not an app build tag'})
            continue
        groups.setdefault(m[1], []).append(r)
    for app, rows in sorted(groups.items()):
        rows.sort(key=newest_first, reverse=True)
        retired = known is not None and app not in known
        for i, r in enumerate(rows):
            if retired:
                rel.append({'id': r['id'], 'tag': r['tag_name'], 'why': 'retired app ' + app})
            elif i < KEEP:
                kept.append({'tag': r['tag_name'], 'reason': 'two newest of ' + app})
            else:
                rel.append({'id': r['id'], 'tag': r['tag_name'], 'why': 'older build of ' + app})
    have = {r['tag_name'] for r in releases}
    gone = sorted(t for t in tag_map if t not in have and BUILD_TAG.match(t))
    drop_tags = sorted({c['tag'] for c in rel if c['tag'] in tag_map} | set(gone))
    order = sorted(deploys, key=lambda d: (str(d.get('created_at') or ''), d['id']), reverse=True)
    keep_dep = [{'id': d['id'], 'created_at': d.get('created_at'), 'sha': d.get('sha')} for d in order[:KEEP_DEPLOYMENTS]]
    drop_dep = sorted(({'id': d['id'], 'created_at': d.get('created_at'), 'sha': d.get('sha')}
                       for d in order[KEEP_DEPLOYMENTS:]), key=lambda d: d['id'])
    drop_br, keep_br = [], []
    for b in sorted(branch_rows, key=lambda b: b['name']):
        if not b['name'].startswith(PACKET):
            keep_br.append({'name': b['name'], 'reason': 'not a packet branch'})
        elif b.get('open_pr'):
            keep_br.append({'name': b['name'], 'reason': 'an open pull request uses it'})
        elif b.get('in_main') is not True:
            keep_br.append({'name': b['name'], 'reason': 'head is not in main'})
        else:
            drop_br.append({'name': b['name'], 'sha': b['sha']})
    body = {'releases': sorted(rel, key=lambda x: x['tag']), 'tags': drop_tags,
            'deployments': [d['id'] for d in drop_dep], 'branches': drop_br}
    token = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    stay = sorted(kept, key=lambda x: str(x['tag']))
    return dict(body, token=token, protected=len(stay), kept=stay, orphan_tags=gone,
                deployment_rows=drop_dep, kept_deployments=keep_dep, kept_branches=keep_br)


def receipt(releases, tag_map, chosen, deploys=()):
    by_id = {r['id']: r for r in releases}
    rows = []
    for c in chosen['releases']:
        r = by_id[c['id']]
        rows.append({'tag': c['tag'], 'release_id': c['id'], 'name': r.get('name'), 'published_at': r.get('published_at'),
                     'commit': tag_map.get(c['tag']),
                     'assets': [{'name': a.get('name'), 'size': a.get('size'), 'digest': a.get('digest')} for a in r.get('assets') or []]})
    dep = {d['id']: d for d in deploys}
    return {'repo': REPO, 'token': chosen['token'], 'releases': rows,
            'tags': [{'tag': t, 'commit': tag_map.get(t)} for t in chosen['tags']],
            'deployments': [{'id': i, 'environment': dep[i].get('environment'), 'created_at': dep[i].get('created_at'),
                             'sha': dep[i].get('sha'), 'ref': dep[i].get('ref'), 'task': dep[i].get('task')}
                            for i in chosen['deployments']],
            'kept_deployments': chosen['kept_deployments'],
            'branches': [dict(b, restore='git push origin %s:refs/heads/%s' % (b['sha'], b['name'])) for b in chosen['branches']]}


def show(p):
    print('Cleanup preview: %d release(s), %d tag(s), %d Pages deployment record(s) and %d merged packet branch(es) to delete; %d release(s) kept.'
          % (len(p['releases']), len(p['tags']), len(p['deployments']), len(p['branches']), p['protected']))
    for r in p['releases']:
        print('  release %s  (%s)' % (r['tag'], r.get('why', '')))
    for t in p['tags']:
        print('  tag     ' + t)
    d = p['deployment_rows']
    if d:
        print('  deploy  %d record(s), created %s to %s' % (len(d), min(x['created_at'] or '' for x in d), max(x['created_at'] or '' for x in d)))
    for b in p['branches']:
        print('  branch  %s  (%s, in main)' % (b['name'], b['sha'][:12]))
    print('Kept (two newest per app):')
    for k in p['kept']:
        print('  keep    %s  (%s)' % (k['tag'], k['reason']))
    print('Kept (newest %d Pages deployment records):' % KEEP_DEPLOYMENTS)
    for k in p['kept_deployments']:
        print('  keep    deployment %s  %s  %s' % (k['id'], k['created_at'], (k['sha'] or '')[:8]))
    print('Kept branches:')
    for k in p['kept_branches']:
        print('  keep    %s  (%s)' % (k['name'], k['reason']))
    print('TOKEN ' + p['token'])


def main(argv=None, run=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['preview', 'apply'])
    ap.add_argument('--token')
    ap.add_argument('--out')
    ap.add_argument('--receipt', default='cleanup-receipt.json')
    a = ap.parse_args(argv)
    releases = inventory(run)
    tag_map = tags(run)
    deploys = deployments(run)
    branch_rows = branches(run)
    known = prefixes()
    if known is None:
        print('STOP: src/targets.json unreadable here; run cleanup.py from a repository checkout. Nothing changed.')
        return 1
    p = plan(releases, tag_map, deploys, branch_rows, known)
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
    pathlib.Path(a.receipt).write_text(json.dumps(receipt(releases, tag_map, p, deploys), indent=1) + '\n', encoding='utf-8')
    steps = ([('release', r['tag'], 'repos/%s/releases/%d' % (REPO, r['id'])) for r in p['releases']]
             + [('tag', t, 'repos/%s/git/refs/tags/%s' % (REPO, t)) for t in p['tags']]
             + [s for i in p['deployments'] for s in (
                 ('deployment', str(i), ['-X', 'POST', 'repos/%s/deployments/%d/statuses' % (REPO, i), '-f', 'state=inactive']),
                 ('deployment', str(i), 'repos/%s/deployments/%d' % (REPO, i)))]
             + [('branch', b['name'], 'repos/%s/git/refs/heads/%s' % (REPO, b['name'])) for b in p['branches']])
    for done, (kind, name, path) in enumerate(steps):
        try:
            gh(['api'] + (path if isinstance(path, list) else ['-X', 'DELETE', path]), run)
        except SystemExit as e:
            print(str(e))
            print('STOP: deleted %d of %d; failed at %s %s. Receipt %s lists the whole plan; nothing after it was tried.'
                  % (done, len(steps), kind, name, a.receipt))
            return 1
    print('RESULT OK: deleted %d release(s), %d tag(s), %d Pages deployment record(s) and %d branch(es). Receipt: %s'
          % (len(p['releases']), len(p['tags']), len(p['deployments']), len(p['branches']), a.receipt))
    return 0


if __name__ == '__main__':
    sys.exit(main())
