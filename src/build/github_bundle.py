#!/usr/bin/env python3
"""Fetch once with explicit GitHub API auth, then use the returned local bytes."""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import urlparse


def require(ok, message):
    if not ok:
        raise ValueError(message)


def api_page(owner, repo, page, env):
    url = 'https://api.github.com/repos/' + owner + '/' + repo + '/releases?per_page=100&page=' + str(page)
    headers = ['Accept: application/vnd.github+json']
    token = env.get('GITHUB_TOKEN') or env.get('GH_TOKEN')
    if token:
        require('\n' not in token and '\r' not in token, 'invalid auth token')
        headers.append('Authorization: Bearer ' + token)
    # Header values via stdin, never argv or logs. No redirects with API credentials.
    config = ''.join('header = ' + json.dumps(h) + '\n' for h in headers)
    result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--connect-timeout', '20',
                             '--max-time', '120', '--retry', '2', '--retry-delay', '2', '--config', '-', url],
                            input=config, capture_output=True, text=True, timeout=400)
    require(result.returncode == 0, 'GitHub release API request failed for ' + owner + '/' + repo
            + ' (curl exit ' + str(result.returncode) + '); not a version-compatibility result')
    data = json.loads(result.stdout)
    require(isinstance(data, list), 'GitHub release API returned a non-array; refusing provider election')
    return data


def choose_release(owner, repo, channel, env):
    require(channel in ('prerelease', 'latest'), 'unsupported release channel')
    # Preserve the existing build downloader: prerelease means newest published
    # release including stable, latest means stable only. Now resolution uses those
    # exact same bytes rather than independently selecting a dev bundle.
    for page in range(1, 11):
        rows = api_page(owner, repo, page, env)
        for release in rows:
            require(isinstance(release, dict), 'invalid release record')
            if release.get('draft') or not release.get('published_at'):
                continue
            if channel == 'latest' and release.get('prerelease') is not False:
                continue
            return release
        if len(rows) < 100:
            break
    raise ValueError('No matching published release in bounded 1000-release search')


def fetch(owner, repo, channel, directory, env):
    require(re.fullmatch(r'[A-Za-z0-9_.-]+', owner) and re.fullmatch(r'[A-Za-z0-9_.-]+', repo), 'unsafe repository identity')
    release = choose_release(owner, repo, channel, env)
    assets = [a for a in release.get('assets', []) if a.get('name', '').endswith('.mpp')]
    require(len(assets) == 1, 'selected release must contain exactly one .mpp asset')
    asset = assets[0]
    name = asset['name']
    require(re.fullmatch(r'[A-Za-z0-9_.+-]+\.mpp', name), 'unsafe bundle filename')
    url = asset['browser_download_url']
    parsed = urlparse(url)
    require(parsed.scheme == 'https' and parsed.hostname == 'github.com'
            and parsed.path.startswith('/' + owner + '/' + repo + '/releases/download/'), 'unexpected bundle download URL')
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='bundle-', suffix='.cand', dir=directory)
    os.close(fd)
    temporary = pathlib.Path(temporary)
    try:
        # Public asset redirects carry NO Authorization header.
        r = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--proto', '=https',
                            '--proto-redir', '=https', '--connect-timeout', '20', '--max-time', '180',
                            '--retry', '2', '--retry-delay', '2', '--output', str(temporary), url],
                           capture_output=True, text=True, timeout=600)
        require(r.returncode == 0, 'bundle asset download failed; no cached fallback used')
        size = temporary.stat().st_size
        require(isinstance(asset.get('size'), int) and size == asset['size'] and size > 10000, 'bundle byte count differs from release asset metadata')
        with zipfile.ZipFile(temporary) as archive:
            require(archive.namelist() and archive.testzip() is None, 'bundle ZIP verification failed')
        fingerprint = hashlib.sha256(temporary.read_bytes()).hexdigest()
        upstream_digest = asset.get('digest')
        if upstream_digest:
            require(upstream_digest == 'sha256:' + fingerprint, 'GitHub asset digest mismatch')
        dest = directory / name
        os.replace(temporary, dest)
        result = {'path': str(dest), 'sha256': fingerprint, 'bytes': size,
                  'tag': release['tag_name'], 'published_at': release['published_at'],
                  'asset_id': asset['id'], 'url': url,
                  'channel_semantics': 'newest-published-including-stable' if channel == 'prerelease' else 'stable-only'}
        dest.with_suffix(dest.suffix + '.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        print(json.dumps(fetch(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], os.environ)))
    except (ValueError, KeyError, OSError, IndexError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print('::error::bundle fetch: ' + str(error), file=sys.stderr)
        sys.exit(2)
