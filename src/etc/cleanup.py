#!/usr/bin/env python3
"""Routine cleanup: one preview, then one exact apply (packet W4, 8 Oct 2026; W9, 9 Oct 2026).

    python3 src/etc/cleanup.py preview [--out FILE]
    python3 src/etc/cleanup.py apply --token TOKEN [--receipt FILE]

What goes (owner rules, 9 Oct 2026):
  * releases: grouped by app (the tag before "-v<version>"); per app the newest by
    publication time stays (owner, 22 Oct 2026: one per app; it was two) and every older one goes, whatever its layout, author or marker.
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
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

REPO = 'govinda-rajulu/patch-factory'
BUILD_TAG = re.compile(r'^[a-z0-9-]+-v[0-9]+(?:\.[0-9]+)*-b[0-9]{8}(?:[0-9]{26})?$')
PAGES_ENV = 'github-pages'
KEEP = 3  # owner, 30 Oct 2026: keep the newest three releases per app
KEEP_DEPLOYMENTS = 3
MIN_RELEASE_AGE_DAYS = 7
PACKET = ('packet/', 'dev/')  # W16c: a merged dev branch (dev/w16) goes the same way
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


def release_time(row):
    """Return publication time, falling back to creation time when needed."""
    for value in (row.get('published_at'), row.get('created_at')):
        if not isinstance(value, str) or not value:
            continue
        try:
            parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    return None


def newest_first(row):
    parsed = release_time(row)
    return (parsed.isoformat() if parsed else '', row['id'])


# Fallback metadata is optional release-body data. A malformed or unavailable decoder
# fails closed to PRIMARY: an unreadable marker must never make the shelf lose its only
# known-good release.
_RELEASE_NOTES = None
try:
    _build_dir = pathlib.Path(__file__).resolve().parents[1] / 'build'
    _release_path = _build_dir / 'release_notes.py'
    _spec = importlib.util.spec_from_file_location('pf_release_notes', _release_path)
    if _spec and _spec.loader:
        # release_notes.py keeps its normal script import (build_identity) rather
        # than package imports, so provide that directory for this standalone tool.
        sys.path.insert(0, str(_build_dir))
        try:
            _RELEASE_NOTES = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_RELEASE_NOTES)
        finally:
            sys.path.remove(str(_build_dir))
except Exception:
    _RELEASE_NOTES = None


def _target_for_app(app):
    try:
        rows = json.loads(TARGETS.read_text(encoding='utf-8'))
        for row in rows:
            if isinstance(row, dict) and row.get('tag_prefix') == app:
                return row.get('id') or app
    except Exception:
        pass
    return app


def is_primary_release(app, row):
    """Decode pf-release-v1 defensively; absent/empty fallback means primary."""
    if _RELEASE_NOTES is None:
        return True
    try:
        doc = _RELEASE_NOTES.decode(row.get('body'), row['tag_name'], _target_for_app(app))
        return not bool(doc.get('fallback'))
    except Exception:
        return True


def asset_bytes(row):
    return sum(a.get('size', 0) for a in row.get('assets') or []
               if isinstance(a, dict) and type(a.get('size')) is int and a.get('size') >= 0)


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


RETIRED = pathlib.Path(__file__).resolve().parent / 'retired-builds.json'


def retired_builds(path=None):
    """W15i (owner, 23 Oct 2026: "for reddit, we can delete v42"): builds the owner retired by
    app, version and a published-before cutoff, so a later build of the same version stays."""
    try:
        rows = json.loads(pathlib.Path(path or RETIRED).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return []
    out = []
    for r in rows:
        if not (isinstance(r, dict) and re.fullmatch(r'[a-z0-9-]+', str(r.get('app', ''))) and
                re.fullmatch(r'[0-9]+(?:[.][0-9]+)*', str(r.get('version', ''))) and
                re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', str(r.get('published_before', ''))) and r.get('why')):
            raise SystemExit('STOP: src/etc/retired-builds.json has a malformed row; nothing changed')
        out.append(r)
    return out


def is_retired(app, r, retire):
    tag, when = str(r.get('tag_name') or ''), str(r.get('published_at') or r.get('created_at') or '')
    for x in retire or ():
        if app == x['app'] and tag.startswith(app + '-v' + x['version'] + '-b') and when and when < x['published_before']:
            return x
    return None


def plan(releases, tag_map, deploys=(), branch_rows=(), known=None, retire=(), now=None):
    """Build the guarded delete list.

    The newest KEEP rows are always protected. If all three are fallback builds, the
    newest readable primary is protected too. Older rows require a valid publication
    (or creation) timestamp at least MIN_RELEASE_AGE_DAYS old; malformed and young
    rows stay visible in ``kept`` so the preview explains why the shelf is larger.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    now = now.astimezone(dt.timezone.utc)
    groups, kept, rel = {}, [], []
    release_bytes = {}
    for r in releases:
        m = APP_TAG.match(str(r.get('tag_name') or ''))
        if not m:
            kept.append({'tag': r.get('tag_name'), 'reason': 'not an app build tag'})
            continue
        groups.setdefault(m[1], []).append(r)
    for app, rows in sorted(groups.items()):
        rows.sort(key=newest_first, reverse=True)
        primary = [r for r in rows if is_primary_release(app, r)]
        protected = {id(r) for r in rows[:KEEP]}
        if not any(id(r) in protected for r in primary) and primary:
            protected.add(id(primary[0]))
        for r in rows:
            rid = str(r['id'])
            release_bytes[rid] = asset_bytes(r)
            reason = None
            if id(r) in protected:
                if r in rows[:KEEP]:
                    reason = 'newest of ' + app
                else:
                    reason = 'newest primary of ' + app
            else:
                retired_row = is_retired(app, r, retire)
                published = release_time(r)
                if published is None:
                    reason = 'kept: missing or malformed publication date'
                elif now - published < dt.timedelta(days=MIN_RELEASE_AGE_DAYS):
                    reason = 'kept: younger than %d days' % MIN_RELEASE_AGE_DAYS
                else:
                    why = ('owner retired %s %s: %s' % (app, retired_row['version'], retired_row['why'])) if retired_row else ('retired app ' + app if known is not None and app not in known else 'older build of ' + app)
                    rel.append({'id': r['id'], 'tag': r['tag_name'], 'why': why})
                    continue
            kept.append({'tag': r['tag_name'], 'reason': reason})
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
                deployment_rows=drop_dep, kept_deployments=keep_dep, kept_branches=keep_br,
                release_asset_bytes=sum(release_bytes.get(str(r['id']), 0) for r in rel),
                release_asset_bytes_by_id=release_bytes)


def only_apps(p, apps):
    """W16w (owner, 28 Oct 2026: keep every release this week except LinkedIn): limit a plan to
    the releases and build tags of these app tag prefixes; no Pages records, no branches. The
    token is computed over the limited list, so an apply with it deletes nothing else."""
    want = set(apps)
    def ok(tag):
        m = APP_TAG.match(str(tag or ''))
        return bool(m) and m[1] in want
    body = {'releases': [r for r in p['releases'] if ok(r['tag'])], 'tags': [t for t in p['tags'] if ok(t)],
            'deployments': [], 'branches': []}
    token = hashlib.sha256(json.dumps(dict(body, apps=sorted(want)), sort_keys=True).encode()).hexdigest()[:16]
    kept = [k for k in p['kept'] if ok(k.get('tag'))]
    selected_ids = {str(r['id']) for r in body['releases']}
    return dict(body, token=token, protected=len(kept), kept=kept, orphan_tags=[t for t in p['orphan_tags'] if ok(t)],
                deployment_rows=[], kept_deployments=p['kept_deployments'], kept_branches=p['kept_branches'], apps=sorted(want),
                release_asset_bytes=sum(p.get('release_asset_bytes_by_id', {}).get(i, 0) for i in selected_ids),
                release_asset_bytes_by_id={i: p.get('release_asset_bytes_by_id', {}).get(i, 0) for i in selected_ids})


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
    print('Kept (newest %d per app, plus newest primary when needed; age guard %d days):' % (KEEP, MIN_RELEASE_AGE_DAYS))
    for k in p['kept']:
        print('  keep    %s  (%s)' % (k['tag'], k['reason']))
    print('Release asset bytes selected: %d' % p.get('release_asset_bytes', 0))
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
    ap.add_argument('--apps', default='', help='comma-separated app tag prefixes: only their releases and build tags (W16w)')
    a = ap.parse_args(argv)
    releases = inventory(run)
    tag_map = tags(run)
    deploys = deployments(run)
    branch_rows = branches(run)
    known = prefixes()
    if known is None:
        print('STOP: src/targets.json unreadable here; run cleanup.py from a repository checkout. Nothing changed.')
        return 1
    p = plan(releases, tag_map, deploys, branch_rows, known, retired_builds())
    apps = [x.strip() for x in a.apps.split(',') if x.strip()]
    if apps:
        bad = [x for x in apps if x not in known]
        if bad:
            print('STOP: --apps names no target tag prefix: %s. Nothing changed.' % ', '.join(bad))
            return 1
        p = only_apps(p, apps)
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
