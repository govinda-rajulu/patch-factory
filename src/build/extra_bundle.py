#!/usr/bin/env python3
"""Atomic extra-bundle transport. GitLab link metadata has no trusted digest.

Preserves channel policy and caller-assigned bundle filenames. Does not execute
bundle code, select patches, or claim publisher authenticity from a local hash.
"""
import datetime
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
from github_bundle import choose_release, require

MAX_BYTES = 128 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024
MAX_ENTRIES = 10000


def text(value, label):
    require(isinstance(value, str) and value and not any(ord(c) < 32 or ord(c) == 127 for c in value),
            'invalid ' + label)
    return value


def gitlab_page(project, page):
    # Public GitLab reads carry no GitHub token, even when one exists in env.
    url = 'https://gitlab.com/api/v4/projects/' + project + '/releases?per_page=100&page=' + str(page)
    r = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--proto', '=https',
                        '--connect-timeout', '20', '--max-time', '120', '--retry', '2',
                        '--retry-delay', '2', url], capture_output=True, text=True, timeout=400)
    require(r.returncode == 0, 'GitLab release API failed; no cached fallback')
    rows = json.loads(r.stdout)
    require(isinstance(rows, list), 'GitLab release API returned a non-array')
    return rows


def select(host, ident, channel, env):
    require(channel in ('prerelease', 'latest'), 'unsupported extra-bundle channel')
    if host == 'github':
        require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', ident), 'invalid GitHub repository')
        owner, repo = ident.split('/')
        release = choose_release(owner, repo, channel, env)
        assets = release.get('assets')
        date = release.get('published_at')
    elif host == 'gitlab':
        require(re.fullmatch(r'[1-9][0-9]*', ident), 'GitLab project must be numeric')
        release = None
        for page in range(1, 11):
            rows = gitlab_page(ident, page)
            for candidate in rows:
                require(isinstance(candidate, dict), 'invalid GitLab release record')
                tag = text(candidate.get('tag_name'), 'GitLab release tag')
                if channel == 'latest' and '-dev' in tag:
                    continue  # existing GitLab stable policy, not a new semver rule
                release = candidate
                break
            if release is not None or len(rows) < 100:
                break
        require(release is not None, 'no matching GitLab release in bounded search')
        assets = release.get('assets', {}).get('links')
        date = release.get('released_at')
    else:
        raise ValueError('unsupported extra-bundle host')
    tag = text(release.get('tag_name'), 'release tag')
    date = text(date, 'release date')
    parsed_date = datetime.datetime.fromisoformat(date.replace('Z', '+00:00'))
    require(parsed_date.tzinfo is not None, 'release date has no timezone')
    require(isinstance(assets, list) and all(isinstance(a, dict) for a in assets), 'invalid release asset inventory')
    matches = [a for a in assets if isinstance(a.get('name'), str) and a['name'].endswith('.mpp')]
    require(len(matches) == 1, 'release must contain exactly one .mpp asset/link')
    asset = matches[0]
    name = text(asset.get('name'), 'asset name')
    require(re.fullmatch(r'[A-Za-z0-9_.+-]+[.]mpp', name), 'unsafe bundle asset name')
    require(type(asset.get('id')) is int and asset['id'] > 0, 'invalid asset/link id')
    url = text(asset.get('browser_download_url') if host == 'github' else asset.get('url'), 'asset URL')
    u = urlparse(url)
    require(u.scheme == 'https' and u.netloc == host + '.com' and not u.query and not u.fragment,
            'unexpected extra-bundle URL origin')
    require(u.path.rsplit('/', 1)[-1] == name, 'bundle URL filename mismatch')
    if host == 'github':
        require(u.path.startswith('/' + ident + '/releases/download/'), 'bundle URL belongs to another repository')
        require(type(asset.get('size')) is int and 10000 < asset['size'] <= MAX_BYTES, 'invalid GitHub bundle size')
        expected_size = asset['size']
        expected_digest = asset.get('digest')
        if expected_digest is not None:
            require(isinstance(expected_digest, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', expected_digest), 'invalid GitHub asset digest')
    else:
        # Observed link from project82031658 on10Sep2026. No filename/version pin.
        require(re.fullmatch(r'/-/project/' + ident + r'/uploads/[A-Za-z0-9]+/' + re.escape(name), u.path),
                'GitLab link must be a project-scoped upload; new layouts require review')
        expected_size = None
        expected_digest = None
    return {'host': host, 'identity': ident, 'tag': tag, 'published_at': date, 'asset_id': asset['id'],
            'asset_name': name, 'url': url, 'expected_size': expected_size, 'expected_digest': expected_digest}


def verify_zip(path):
    size = path.stat().st_size
    require(10000 < size <= MAX_BYTES, 'extra bundle size outside inspection limits')
    with zipfile.ZipFile(path) as archive:
        items = archive.infolist()
        names = [item.filename for item in items]
        require(0 < len(items) <= MAX_ENTRIES and len(names) == len(set(names)), 'empty/duplicate/oversized bundle ZIP inventory')
        require(sum(i.file_size for i in items) <= MAX_EXPANDED, 'bundle ZIP expansion exceeds inspection limits')
        for i in items:
            require(not i.flag_bits & 1, 'encrypted bundle member')
            require(not i.filename.startswith('/') and '\\' not in i.filename
                    and '..' not in pathlib.PurePosixPath(i.filename).parts, 'unsafe bundle member path')
            require((i.external_attr >> 16) & 0o170000 != 0o120000, 'bundle ZIP symlink refused')
            require(i.file_size <= MAX_BYTES, 'bundle member exceeds inspection limits')
        require(archive.testzip() is None, 'bundle ZIP CRC verification failed')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return size, h.hexdigest()


def fetch(host, ident, channel, out, env):
    meta = select(host, ident, channel, env)
    out = pathlib.Path(out)
    require(out.suffix == '.mpp' and not out.is_symlink(), 'invalid or symlinked bundle destination')
    out.parent.mkdir(parents=True, exist_ok=True)
    errors = []
    for attempt in (1, 2):
        fd, tmp = tempfile.mkstemp(prefix='extra-', suffix='.cand', dir=out.parent)
        os.close(fd);tmp = pathlib.Path(tmp)
        try:
            r = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--proto', '=https',
                '--proto-redir', '=https', '--connect-timeout', '20', '--max-time', '180', '--retry', '2',
                '--retry-delay', '2', '--max-filesize', str(MAX_BYTES), '--output', str(tmp), meta['url']],
                capture_output=True, text=True, timeout=600)
            require(r.returncode == 0, 'extra bundle transfer failed (curl exit ' + str(r.returncode) + ')')
            size, digest = verify_zip(tmp)
            require(meta['expected_size'] is None or size == meta['expected_size'], 'bundle size differs from GitHub metadata')
            require(meta['expected_digest'] is None or 'sha256:' + digest == meta['expected_digest'], 'bundle digest differs from GitHub metadata')
            result = dict(meta, bytes=size, sha256=digest, zip_verified=True,
                          upstream_digest_verified=meta['expected_digest'] is not None,
                          upstream_size_verified=meta['expected_size'] is not None,
                          trust='transport/archive checks; local SHA-256 is not publisher authenticity')
            os.replace(tmp, out)
            return result
        except (ValueError, OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError, subprocess.TimeoutExpired) as error:
            errors.append(str(error))
            print('EXTRA_DOWNLOAD_REJECTED ' + json.dumps({'attempt': attempt, 'reason': str(error)}), file=sys.stderr)
            if attempt == 2:
                raise ValueError('extra bundle failed twice; destination not replaced: ' + '; '.join(errors)) from error
        finally:
            tmp.unlink(missing_ok=True)


def main():
    result = fetch(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], os.environ)
    print('PUB=' + result['published_at'])
    print('TAG=' + result['tag'])
    print('SIZE=' + str(result['bytes']))
    print('SHA256=' + result['sha256'])
    print('EXTRA_BUNDLE_VERIFIED ' + json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, IndexError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print('FB_ERROR ' + str(error), file=sys.stderr)
        sys.exit(1)
