#!/usr/bin/env python3
"""Tooling watch: keep the pinned build tools current, pre-releases included.

Packet W1, 8 Oct 2026. src/build/TOOLING.sha256 pins pup and APKEditor by URL and sha256.
This script reads each pin's GitHub releases (drafts skipped, pre-releases INCLUDED by
owner decision), picks the newest by publication time, finds the asset whose name is the
pinned asset name with the version swapped, downloads it, checks GitHub's own sha256
digest when the release publishes one, and with --apply rewrites only that pin line.

It never changes a build by itself: the tooling-watch workflow turns a rewrite into a
pull request that goes through Validate and the owner. morphe-desktop (the patcher) is
reported, not pinned: src/build/github_patcher.py takes the latest STABLE release on
every build on purpose; this report says when a newer pre-release exists.
W15h (22 Oct 2026): --upstreams reads every outside tool and source in src/etc/upstreams.json
and keeps the standing issue "Tooling watch" (L074: a report only in an artifact is unseen).
Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PINS = Path('src/build/TOOLING.sha256')
URL = re.compile(r'^https://github\.com/([\w.-]+)/([\w.-]+)/releases/download/([^/]+)/([^/]+)$')
PATCHER = ('MorpheApp', 'morphe-desktop')
MAX_BYTES = 128 * 1024 * 1024


def api(path, env):
    req = urllib.request.Request('https://api.github.com/' + path, headers={
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'pf-tooling-watch',
        **({'Authorization': 'Bearer ' + env['GITHUB_TOKEN']} if env.get('GITHUB_TOKEN') else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'pf-tooling-watch'})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('asset larger than %d bytes' % MAX_BYTES)
    return data


def parse_pins(text):
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        name, url, sha, out = line.split('|')
        m = URL.match(url)
        rows.append({'name': name, 'url': url, 'sha256': sha, 'out': out, 'line': line,
                     'owner': m and m[1], 'repo': m and m[2], 'tag': m and m[3], 'asset': m and m[4]})
    return rows


def version_of(tag):
    return re.sub(r'^[vV]', '', tag or '')


def newest(releases):
    """Newest non-draft release by publication time; pre-releases count."""
    live = [r for r in releases if isinstance(r, dict) and not r.get('draft') and r.get('published_at')
            and isinstance(r.get('tag_name'), str)]
    return max(live, key=lambda r: r['published_at']) if live else None


def asset_name(pinned_asset, old_tag, new_tag):
    old, new = version_of(old_tag), version_of(new_tag)
    if not old or old not in pinned_asset:
        return None
    return pinned_asset.replace(old, new)


def plan(pins, env, fetch_releases=None, fetch_bytes=None):
    fetch_releases = fetch_releases or (lambda o, r: api('repos/%s/%s/releases?per_page=20' % (o, r), env))
    fetch_bytes = fetch_bytes or download
    out = []
    for p in pins:
        row = {'name': p['name'], 'current': p['tag'], 'status': '', 'line': p['line']}
        if not p['owner']:
            row['status'] = 'NOT_GITHUB_RELEASE'
            out.append(row)
            continue
        rel = newest(fetch_releases(p['owner'], p['repo']))
        if rel is None:
            row['status'] = 'NO_RELEASES'
        elif rel['tag_name'] == p['tag']:
            row['status'] = 'CURRENT'
        else:
            want = asset_name(p['asset'], p['tag'], rel['tag_name'])
            assets = {a.get('name'): a for a in rel.get('assets') or [] if isinstance(a, dict)}
            row.update(latest=rel['tag_name'], prerelease=bool(rel.get('prerelease')),
                       published=rel['published_at'], release_url=rel.get('html_url'))
            if not want or want not in assets:
                row['status'] = 'ASSET_NOT_FOUND'
                row['wanted_asset'] = want
            else:
                a = assets[want]
                url = a.get('browser_download_url') or ''
                if not URL.match(url) or URL.match(url)[4] != want:
                    row['status'] = 'UNEXPECTED_ASSET_URL'
                else:
                    data = fetch_bytes(url)
                    sha = hashlib.sha256(data).hexdigest()
                    digest = a.get('digest')
                    if isinstance(digest, str) and digest.startswith('sha256:') and digest[7:] != sha:
                        row['status'] = 'DIGEST_MISMATCH'
                    else:
                        row.update(status='UPDATE', url=url, sha256=sha, bytes=len(data),
                                   github_digest=bool(digest),
                                   new_line='|'.join((p['name'], url, sha, p['out'])))
        out.append(row)
    return out


def patcher_report(env, fetch_releases=None):
    fetch_releases = fetch_releases or (lambda o, r: api('repos/%s/%s/releases?per_page=20' % (o, r), env))
    rels = [r for r in fetch_releases(*PATCHER) if isinstance(r, dict) and not r.get('draft')]
    stable = [r for r in rels if not r.get('prerelease') and r.get('published_at')]
    pre = newest(rels)
    s = max(stable, key=lambda r: r['published_at']) if stable else None
    return {'stable': s and s['tag_name'], 'newest': pre and pre['tag_name'],
            'newest_is_prerelease': bool(pre and pre.get('prerelease'))}


def report(rows, patcher):
    lines = ['## Tooling watch', '',
             'Pre-releases are included by owner decision (8 Oct 2026). Validate does not build an APK:',
             'before merging a tool update, dispatch one `manual-patch` build with `publish=false`.', '',
             '| tool | pinned | newest | pre-release | status |', '| --- | --- | --- | --- | --- |']
    for r in rows:
        lines.append('| %s | %s | %s | %s | %s |' % (r['name'], r['current'], r.get('latest', r['current']),
                                                   'yes' if r.get('prerelease') else 'no', r['status']))
    for r in rows:
        if r['status'] == 'UPDATE':
            lines += ['', '**%s** %s -> %s (%s, %d bytes, sha256 `%s`, GitHub digest %s)' % (
                r['name'], r['current'], r['latest'], r.get('release_url'), r['bytes'], r['sha256'],
                'verified' if r['github_digest'] else 'not published')]
    if patcher:
        lines += ['', 'Patcher (morphe-desktop, not pinned): builds use latest stable `%s`; newest release `%s`%s.' % (
            patcher['stable'], patcher['newest'], ' (pre-release)' if patcher['newest_is_prerelease'] else '')]
    return '\n'.join(lines) + '\n'


UPSTREAMS = Path('src/etc/upstreams.json')
STANDING = 'Tooling watch'
STATE = re.compile(r'<!-- pf-upstreams ([A-Za-z0-9+/=]*) -->')
QUIET_DAYS = 365


def load_upstreams(path=UPSTREAMS):
    rows = json.loads(path.read_text(encoding='utf-8'))['upstreams']
    for u in rows:
        if not (re.fullmatch(r'[\w.-]+/[\w.-]+', u.get('repo', '')) and u.get('kind') in ('release', 'commits')):
            raise ValueError('bad upstream entry: %r' % (u,))
    return rows


def read_upstream(u, env, fetch=None):
    """W15h: one upstream's newest release (pre-releases shown apart) or newest default-branch
    commit. Stable fields only (tags, dates, short shas), so an unchanged upstream renders the same."""
    fetch = fetch or (lambda path: api(path, env))
    row = {'id': u['id'], 'repo': u['repo'], 'role': u['role'], 'pinned': (u.get('pin') or {}).get('tag', '')}
    try:
        if u['kind'] == 'release':
            rels = [r for r in fetch('repos/%s/releases?per_page=10' % u['repo']) if isinstance(r, dict)
                    and not r.get('draft') and r.get('published_at')]
            stable = [r for r in rels if not r.get('prerelease')]
            s, n = (max(stable, key=lambda r: r['published_at']) if stable else None), newest(rels)
            if s is None and n is None:
                tags = fetch('repos/%s/tags?per_page=1' % u['repo'])
                row.update(latest=tags[0]['name'] if tags else '', date='', newest='')
            else:
                row.update(latest=s['tag_name'] if s else '', date=(s or n)['published_at'][:10],
                           newest=n['tag_name'] if n and n is not s and n.get('prerelease') else '')
        else:
            c = fetch('repos/%s/commits?per_page=1' % u['repo'])[0]
            row.update(latest=c['sha'][:7], date=c['commit']['committer']['date'][:10], newest='')
    except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
        row.update(latest='', date='', newest='', error=type(e).__name__)
    return row


def upstream_status(row, today):
    if row.get('error'):
        return 'UNREADABLE'
    if row['pinned'] and row['latest'] and row['latest'] != row['pinned']:
        return 'BEHIND'
    if row['date'] and (today - __import__('datetime').date.fromisoformat(row['date'])).days > QUIET_DAYS:
        return 'QUIET'
    return 'OK'


def upstream_body(rows, today, previous=None):
    """Standing-issue body. previous = {id: latest} from the last body; NEW marks a change."""
    import base64
    import readable
    previous = previous or {}
    for r in rows:
        r['status'] = upstream_status(r, today)
        if previous and r['latest'] and previous.get(r['id']) not in (None, r['latest']):
            r['status'] = 'NEW ' + previous[r['id']] + ' -> ' + r['latest'] + ('' if r['status'] == 'OK' else ', ' + r['status'])
    act = [r for r in rows if r['status'] != 'OK']
    lines = readable.headline(STANDING, 'OK' if not act else '%d to review' % len(act), 0)
    lines += ['Every tool and source this repository takes from outside, read daily. Items to review go to the next packet; '
              'nothing here needs the owner. Patch providers: Provider watch. Action pins: Dependabot.', '']
    head = ('tool', 'repository', 'newest stable', 'date', 'newer pre-release', 'pinned here', 'status', 'role')
    cells = lambda r: (r['id'], r['repo'], r['latest'] or '-', r['date'] or '-', r['newest'] or '-', r['pinned'] or '-',
                       r['status'], r['role'])
    if act:
        lines += ['## To review', ''] + readable.table(head, [cells(r) for r in act]) + ['']
    lines += readable.details('All %d upstreams' % len(rows), readable.table(head, [cells(r) for r in rows]))
    state = base64.b64encode(json.dumps({r['id']: r['latest'] for r in rows if r['latest']}, sort_keys=True).encode()).decode()
    return '\n'.join(lines).rstrip('\n') + '\n\n<!-- pf-upstreams ' + state + ' -->\n'


def previous_state(body):
    import base64
    m = STATE.search(body or '')
    if not m:
        return {}
    try:
        return json.loads(base64.b64decode(m[1]).decode())
    except ValueError:
        return {}


def gh(args, run=None):
    import subprocess
    run = run or subprocess.run
    return run(['gh'] + args, capture_output=True, text=True, timeout=120)


def deliver(repo, body_for, run_id, run=None):
    """One standing issue, edited in place; a comment only when the rendered body changed.
    body_for(previous_body) renders the new body. Single attempts, no retries (L071-style)."""
    import readable
    found = gh(['issue', 'list', '--repo', repo, '--state', 'open', '--limit', '100', '--search',
                'in:title "%s"' % STANDING, '--json', 'number,title,body'], run)
    if found.returncode != 0:
        raise OSError('issue list failed')
    rows = [r for r in json.loads(found.stdout or '[]') if r.get('title') == STANDING]
    old = rows[0]['body'] if rows else ''
    body = body_for(old)
    path = Path('tooling-upstreams.md')
    path.write_text(body, encoding='utf-8')
    if not rows:
        made = gh(['issue', 'create', '--repo', repo, '--title', STANDING, '--body-file', str(path)], run)
        if made.returncode != 0:
            raise OSError('issue create failed')
        return 'CREATED'
    number = str(rows[0]['number'])
    if old.strip() == body.strip():
        return 'UNCHANGED'
    if gh(['issue', 'edit', number, '--repo', repo, '--body-file', str(path)], run).returncode != 0:
        raise OSError('issue edit failed')
    # W16j (owner, 25 Oct 2026: "I get dizzy reading comments"): the body is always current; a
    # comment only when the headline changes to something to review, not for every reworded line.
    head = lambda t: next((l.strip() for l in (t or '').splitlines() if l.startswith('# ')), '')
    if head(body) != head(old) and not head(body).endswith(': OK'):
        note = '\n'.join(['**Changed by run %s**' % run_id, ''] + readable.changed_lines(old, body))
        gh(['issue', 'comment', number, '--repo', repo, '--body', note], run)
    return 'EDITED'


def upstream_main(env, today=None, fetch=None, run=None):
    import datetime
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    rows = [read_upstream(u, env, fetch) for u in load_upstreams()]
    for r in rows:
        if r.get('error'):
            print('::warning::upstream %s unreadable: %s' % (r['repo'], r['error']))
    result = deliver(env['REPO'], lambda old: upstream_body([dict(r) for r in rows], today, previous_state(old)),
                     env.get('RUN_ID', '?'), run)
    print('UPSTREAMS %s: %d read, %d unreadable' % (result, len(rows), sum(1 for r in rows if r.get('error'))))
    return 0


def main(argv=None, env=os.environ):
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('--apply', action='store_true', help='rewrite updated pin lines in place')
    ap.add_argument('--report', help='write a markdown report here')
    ap.add_argument('--json', help='write the plan as JSON here')
    ap.add_argument('--upstreams', action='store_true', help='W15h: read src/etc/upstreams.json and edit the standing issue')
    a = ap.parse_args(argv)
    if a.upstreams:
        return upstream_main(env)
    text = PINS.read_text(encoding='utf-8')
    rows = plan(parse_pins(text), env)
    try:
        pr = patcher_report(env)
    except (OSError, ValueError) as e:
        pr = None
        print('::warning::patcher report unavailable: ' + str(e))
    body = report(rows, pr)
    print(body)
    if a.report:
        Path(a.report).write_text(body, encoding='utf-8')
    if a.json:
        Path(a.json).write_text(json.dumps({'tools': rows, 'patcher': pr}, indent=1) + '\n', encoding='utf-8')
    updates = [r for r in rows if r['status'] == 'UPDATE']
    if a.apply and updates:
        for r in updates:
            if text.count(r['line']) != 1:
                raise SystemExit('pin line for %s is not unique; refusing' % r['name'])
            text = text.replace(r['line'], r['new_line'])
        PINS.write_text(text, encoding='utf-8')
    bad = [r for r in rows if r['status'] in ('DIGEST_MISMATCH', 'UNEXPECTED_ASSET_URL')]
    for r in bad:
        print('::error::%s: %s' % (r['name'], r['status']))
    print('TOOLING_WATCH %d update(s), %d problem(s)' % (len(updates), len(bad)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
