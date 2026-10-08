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


def main(argv=None, env=os.environ):
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('--apply', action='store_true', help='rewrite updated pin lines in place')
    ap.add_argument('--report', help='write a markdown report here')
    ap.add_argument('--json', help='write the plan as JSON here')
    a = ap.parse_args(argv)
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
