#!/usr/bin/env python3
"""Resolve the patcher, verify asset bytes, then atomically install.

GitHub metadata digest is a transport integrity anchor, not independent publisher
attestation. Invalid cached bytes never become a fallback. Latest stable remains the
default policy, while optional PATCHER_TAG_PIN/PATCHER_SHA256_PIN values fail closed.
"""
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
from github_bundle import api_json, require

OWNER = 'MorpheApp'
REPO = 'morphe-desktop'
LATEST = 'https://api.github.com/repos/' + OWNER + '/' + REPO + '/releases/latest'
MAX_BYTES = 256 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
MAX_ENTRIES = 100000
PIN_TAG_ENV = 'PATCHER_TAG_PIN'
PIN_SHA_ENV = 'PATCHER_SHA256_PIN'


def select_asset(release, env=None):
    env = env or {}
    require(isinstance(release, dict) and release.get('draft') is False
            and release.get('prerelease') is False and release.get('published_at')
            and isinstance(release.get('tag_name'), str), 'invalid latest stable patcher release')
    assets = release.get('assets')
    require(isinstance(assets, list) and all(isinstance(a, dict) for a in assets), 'invalid patcher asset inventory')
    jars = [a for a in assets if re.fullmatch(r'morphe-desktop-[A-Za-z0-9_.+-]+-all[.]jar', a.get('name', ''))]
    require(len(jars) == 1, 'latest release must have exactly one runnable all.jar asset')
    asset = jars[0]
    require(asset.get('state') == 'uploaded' and type(asset.get('id')) is int and asset['id'] > 0,
            'patcher asset is not uploaded or has invalid identity')
    require(type(asset.get('size')) is int and 1000000 < asset['size'] <= MAX_BYTES,
            'patcher asset size outside inspection bounds')
    require(isinstance(asset.get('digest'), str) and re.fullmatch(r'sha256:[0-9a-f]{64}', asset['digest']),
            'latest patcher lacks a usable GitHub SHA-256 digest; refusing unverified download')
    u = urlparse(asset.get('browser_download_url', ''))
    require(u.scheme == 'https' and u.netloc == 'github.com' and not u.query and not u.fragment
            and u.path.startswith('/MorpheApp/morphe-desktop/releases/download/')
            and u.path.rsplit('/', 1)[-1] == asset['name'], 'unexpected patcher asset URL')
    tag_pin = env.get(PIN_TAG_ENV) or None  # '' is unset (Actions expressions)
    sha_pin = env.get(PIN_SHA_ENV) or None
    # W16o: optional pins preserve Morphe's intentional latest-stable policy (H4).
    require((tag_pin is None) == (sha_pin is None),
            'patcher pin requires both PATCHER_TAG_PIN and PATCHER_SHA256_PIN')
    if tag_pin is not None:
        require(re.fullmatch(r'[A-Za-z0-9_.+-]+', tag_pin), 'invalid PATCHER_TAG_PIN')
        require(re.fullmatch(r'[0-9a-f]{64}', sha_pin), 'invalid PATCHER_SHA256_PIN')
        require(release['tag_name'] == tag_pin and asset['digest'] == 'sha256:' + sha_pin,
                'patcher release or digest differs from optional pin')
    return asset


def validate(path, asset):
    require(path.is_file() and not path.is_symlink(), 'missing or symlinked patcher file')
    size = path.stat().st_size
    require(size == asset['size'], 'patcher byte count differs from GitHub metadata: ' + str(size))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    require('sha256:' + h.hexdigest() == asset['digest'], 'patcher SHA-256 differs from GitHub metadata')
    with zipfile.ZipFile(path) as archive:
        items = archive.infolist();names = [i.filename for i in items]
        require(0 < len(items) <= MAX_ENTRIES and len(names) == len(set(names)), 'empty, duplicate or oversized JAR inventory')
        require(sum(i.file_size for i in items) <= MAX_EXPANDED, 'JAR expansion exceeds inspection limit')
        for i in items:
            require(not (i.flag_bits & 1), 'encrypted JAR member')
            require(i.file_size <= MAX_BYTES, 'oversized JAR member')
        require('META-INF/MANIFEST.MF' in names, 'JAR manifest missing')
        info = archive.getinfo('META-INF/MANIFEST.MF')
        require(info.file_size <= 65536, 'JAR manifest too large')
        manifest = archive.read(info).decode('utf-8').replace('\r\n', '\n')
        # Main attributes end at the first blank line. Continuation lines unfold.
        main = manifest.split('\n\n', 1)[0].replace('\n ', '')
        classes = re.findall(r'^Main-Class: ([A-Za-z_$][A-Za-z0-9_$.]*)$', main, re.M)
        require(len(classes) == 1, 'JAR needs exactly one valid Main-Class')
        class_path = classes[0].replace('.', '/') + '.class'
        require(class_path in names, 'JAR Main-Class bytecode missing')
        with archive.open(class_path) as stream:
            require(stream.read(4) == b'\xca\xfe\xba\xbe', 'JAR Main-Class has invalid bytecode header')
        require(archive.testzip() is None, 'JAR CRC verification failed')
    return h.hexdigest()


def fetch(directory, env):
    release = api_json(LATEST, env, OWNER + '/' + REPO)
    asset = select_asset(release, env)
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / asset['name']
    require(not dest.is_symlink(), 'symlinked patcher destination refused')
    cached = False
    if dest.exists():
        try:
            fingerprint = validate(dest, asset)
            cached = True
        except (ValueError, OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
            print('PATCHER_CACHE_REJECTED ' + json.dumps({'name': asset['name'], 'reason': str(error)}), file=sys.stderr)
    if not cached:
        # Retry a complete transfer once after corruption as well as curl failures.
        # Each attempt writes a new candidate, never truncates the cached JAR.
        errors = []
        for attempt in (1, 2):
            fd, temp = tempfile.mkstemp(prefix='patcher-', suffix='.cand', dir=directory)
            os.close(fd);temp = pathlib.Path(temp)
            try:
                result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                    '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '20',
                    '--max-time', '180', '--retry', '2', '--retry-delay', '2', '--output', str(temp),
                    asset['browser_download_url']], capture_output=True, timeout=600)
                require(result.returncode == 0, 'patcher transfer failed (curl exit ' + str(result.returncode) + ')')
                fingerprint = validate(temp, asset)
                os.replace(temp, dest)
                break
            except (ValueError, OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError, subprocess.TimeoutExpired) as error:
                diag = {'attempt': attempt, 'bytes': temp.stat().st_size if temp.exists() else None, 'reason': str(error)}
                print('PATCHER_DOWNLOAD_REJECTED ' + json.dumps(diag), file=sys.stderr)
                errors.append(str(error))
                if attempt == 2:
                    raise ValueError('patcher verification failed twice; no cache fallback: ' + '; '.join(errors)) from error
            finally:
                temp.unlink(missing_ok=True)
    result = {'name': asset['name'], 'path': str(dest), 'bytes': asset['size'], 'sha256': fingerprint,
              'tag': release['tag_name'], 'asset_id': asset['id'], 'cache_hit_verified': cached,
              'github_digest_verified': True, 'jar_structure_verified': True,
              'pin': {'tag': env.get(PIN_TAG_ENV), 'sha256': env.get(PIN_SHA_ENV)}
                      if env.get(PIN_TAG_ENV) else None,
              'policy': 'GitHub latest stable unless optional PATCHER_TAG_PIN/PATCHER_SHA256_PIN is set',
              'trust': 'GitHub metadata/transport integrity, not independent publisher attestation'}
    # W16o H4: retain the resolved tag beside the verified JAR so the final input
    # ledger can state exactly which latest release supplied the tool. The sidecar
    # is only emitted for a checkout root, not resolver scratch payloads.
    if (directory / 'src' / 'targets.json').is_file():
        sidecar = dest.with_name(dest.name + '.json')
        fd, candidate = tempfile.mkstemp(prefix=sidecar.name + '.', suffix='.cand', dir=sidecar.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(result, stream, sort_keys=True, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.replace(candidate, sidecar)
        finally:
            pathlib.Path(candidate).unlink(missing_ok=True)
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(fetch(sys.argv[1], os.environ), sort_keys=True))
    except (ValueError, OSError, KeyError, IndexError, TypeError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print('::error::patcher fetch: ' + str(error), file=sys.stderr)
        sys.exit(2)
