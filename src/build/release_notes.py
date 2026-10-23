"""Visitor-facing notes from verified current evidence and optional release metadata.

Previous release prose is publisher-reported, not independently signed evidence.
It never authorizes a build skip, APK selection, patch approval or publication.
"""
import base64
import html
import json
import os
import re
import subprocess
from build_identity import parse

REPO = 'govinda-rajulu/patch-factory'
WEB = 'https://github.com/' + REPO
MARKER = r'(?m)^\[pf-release-v1\]: # "([A-Za-z0-9+/=]+)"[ \t]*$'


def checked(doc):
    if not isinstance(doc, dict) or doc.get('schema') != 1:
        raise ValueError('unsupported release summary')
    for key, pattern in [('target', r'[a-z0-9-]+'), ('version', r'[0-9]+(?:[.][0-9]+)*'),
                         ('source', r'[0-9a-f]{40}'), ('sha256', r'[0-9a-f]{64}'),
                         ('signer', r'[0-9a-f]{64}'), ('package', r'[A-Za-z][A-Za-z0-9_.]+')]:
        if not isinstance(doc.get(key), str) or not re.fullmatch(pattern, doc[key]):
            raise ValueError('invalid release summary ' + key)
    for key in ('tag', 'provider', 'bundle', 'apk', 'label', 'arch'):
        value = doc.get(key)
        if not isinstance(value, str) or not value or len(value) > 1000 or any(ord(c) < 32 for c in value):
            raise ValueError('invalid release summary text')
    if not isinstance(doc.get('patches'), list) or not 0 < len(doc['patches']) <= 1000:
        raise ValueError('invalid applied patch list')
    if any(not isinstance(x, str) or not x or len(x) > 500 or any(ord(c) < 32 for c in x) for x in doc['patches']):
        raise ValueError('invalid applied patch name')
    # W13: optional. Lost patches the build went without, and a fallback provider note.
    if 'dropped' in doc and (not isinstance(doc['dropped'], list) or len(doc['dropped']) > 200 or any(
            not isinstance(x, str) or not x or len(x) > 500 or any(ord(c) < 32 for c in x) for x in doc['dropped'])):
        raise ValueError('invalid dropped patch list')
    if 'fallback' in doc and (not isinstance(doc['fallback'], str) or not doc['fallback'] or len(doc['fallback']) > 1000
                              or any(ord(c) < 32 for c in doc['fallback'])):
        raise ValueError('invalid fallback note')
    if type(doc.get('min_sdk')) is not int or not 0 < doc['min_sdk'] < 100:
        raise ValueError('invalid Android minimum')
    if type(doc.get('bytes')) is not int or doc['bytes'] <= 1000000:
        raise ValueError('invalid APK size')
    if doc['arch'] not in ('arm64-v8a', 'no-native-libraries'):
        raise ValueError('invalid native architecture')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*[.]apk', doc['apk']):
        raise ValueError('invalid APK filename')
    if not re.fullmatch(r'[a-z0-9-]+-v' + re.escape(doc['version']) + r'-b[0-9]+', doc['tag']):
        raise ValueError('invalid tag/version binding')
    parse('-b' + doc['tag'].split('-b')[-1])
    return doc


def snapshot(fields, report, target):
    extra = {}
    if fields.get('dropped'):
        extra['dropped'] = fields['dropped'].splitlines()
    if fields.get('fallback'):
        extra['fallback'] = fields['fallback']
    return checked(dict(extra, schema=1, target=report['target'], label=target.get('label', report['target']),
                        tag=fields['tag'], version=fields['version'],
                        package=report['manifest']['package'], min_sdk=report['manifest']['min_sdk'],
                        arch=report['architecture']['classification'], provider=fields['provider'],
                        bundle=fields['patchver'], patches=report['applied_patch_names'],
                        sha256=fields['sha256'], signer=report['signature']['certificate_sha256'],
                        source=report['inputs']['source_commit'], apk=fields['apkname'],
                        bytes=report['output']['bytes']))


def decode(body, tag, target):
    if not isinstance(body, str) or len(body.encode()) > 250000:
        raise ValueError('missing or oversized release body')
    matches = re.findall(MARKER, body)
    if len(matches) != 1:
        raise ValueError('no unique structured summary')
    doc = checked(json.loads(base64.b64decode(matches[0], validate=True)))
    if doc['tag'] != tag or doc['target'] != target:
        raise ValueError('release summary identity mismatch')
    return doc


def choose_previous(rows, current):
    """Use the immediate previous app release, never an older convenient record."""
    prefix = current['tag'].split('-v' + current['version'] + '-b', 1)[0]
    eligible = []
    for row in rows:
        if not isinstance(row, dict) or row.get('draft') or row.get('prerelease'):
            continue
        tag = row.get('tag_name', '')
        match = re.fullmatch(re.escape(prefix) + r'-v([0-9]+(?:[.][0-9]+)*)(-b[0-9]+)', tag)
        if not match:
            continue
        try:
            parse(match[2])
        except ValueError:
            continue
        eligible.append((match[2][2:], row, match[1]))
    if not eligible:
        return None, 'No earlier comparable app release was found.'
    _, row, version = max(eligible, key=lambda item: item[0])
    if sum(item[0] == row['tag_name'].split('-b')[-1] for item in eligible) != 1:
        return None, 'Ambiguous previous release order; comparison unavailable.'
    tag = row['tag_name']
    if tag == current['tag'] or tag.split('-b')[-1] >= current['tag'].split('-b')[-1]:
        return None, 'Release ordering changed; comparison unavailable.'
    try:
        previous = decode(row.get('body'), tag, current['target'])
        apks = [a for a in row.get('assets', []) if isinstance(a, dict) and str(a.get('name', '')).endswith('.apk')]
        if len(apks) != 1:
            raise ValueError('ambiguous previous APK')
        a = apks[0]
        if (previous['version'] != version or a.get('name') != previous['apk'] or
                a.get('size') != previous['bytes'] or a.get('state') != 'uploaded' or
                a.get('browser_download_url') != WEB + '/releases/download/' + tag + '/' + previous['apk'] or
                a.get('digest') not in (None, 'sha256:' + previous['sha256'])):
            raise ValueError('previous asset summary mismatch')
        return previous, 'Compared with the immediate previous app release; previous metadata is publisher-reported.'
    except (ValueError, TypeError, KeyError):
        return {'tag': tag, 'version': version, 'legacy': True}, 'Previous release lacks comparable structured patch metadata.'


def inventory():
    """Every release (GET only, at most 20 pages of 100), or None when the read is incomplete."""
    env = {key: os.environ[key] for key in ('PATH', 'HOME') if key in os.environ}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        env['GH_TOKEN'] = token
    rows, ids = [], set()
    try:
        for page in range(1, 21):
            result = subprocess.run(['gh', 'api', 'repos/' + REPO + '/releases?per_page=100&page=' + str(page)],
                                    env=env, capture_output=True, timeout=10)
            if result.returncode != 0 or len(result.stdout) > 8000000:
                raise ValueError('unavailable inventory')
            batch = json.loads(result.stdout)
            if not isinstance(batch, list):
                raise ValueError('invalid inventory')
            for row in batch:
                if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] in ids:
                    raise ValueError('changing inventory')
                ids.add(row['id'])
            rows.extend(batch)
            if len(batch) < 100:
                return rows
        raise ValueError('incomplete inventory')
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return None


def previous_release(current, rows=False):
    """Optional GET-only history read. Errors become explicit UNKNOWN, not no change."""
    if rows is False:
        rows = inventory()
    try:
        if rows is None:
            raise ValueError('unavailable inventory')
        return choose_previous(rows, current)
    except (ValueError, TypeError):
        return None, 'Previous-release comparison unavailable. This does not mean nothing changed.'


def _vkey(version):
    return tuple(int(x) for x in version.split('.'))


def publish_guard(current, rows, fallback):
    """W15 (17 Oct 2026, L059): never publish an app version below the newest published release
    of the same app. Android refuses a lower versionCode over an installed build, and the shelf
    would show it as the newest (De-Vanced Facebook 580 with 3 patches went out four times over
    Hushfacebook 582 with 82, 11 to 16 Oct). A fallback build is never published blind: no
    readable inventory, no fallback release. Returns the refusal reason, or None."""
    if rows is None:
        return 'release inventory unreadable, so a fallback build is not published blind' if fallback else None
    prefix = current['tag'].split('-v' + current['version'] + '-b', 1)[0]
    best = None
    for row in rows:
        if not isinstance(row, dict) or row.get('draft') or row.get('prerelease'):
            continue
        match = re.fullmatch(re.escape(prefix) + r'-v([0-9]+(?:[.][0-9]+)*)-b[0-9]+', str(row.get('tag_name', '')))
        if match and (best is None or _vkey(match[1]) > _vkey(best)):
            best = match[1]
    if best is not None and _vkey(current['version']) < _vkey(best):
        return ('app %s is older than the published %s; a phone cannot update to it and the shelf would show it as newest'
                % (current['version'], best))
    return None


def _names(values):
    return ', '.join(sorted(values)) if values else 'none'


def changes(current, previous):
    """Return only the release facts a person needs to install this build."""
    old_version = previous.get('version', 'unknown') if previous else 'unknown'
    old_bundle = previous.get('bundle', 'unknown') if previous else 'unknown'
    old_provider = previous.get('provider', 'unknown') if previous else 'unknown'
    old_patches = set(previous.get('patches', [])) if previous and not previous.get('legacy') else set()
    new_patches = set(current['patches'])
    lines = [
        'App version: %s -> %s.' % (old_version, current['version']),
        'Bundle version (provider): %s (%s) -> %s (%s).' %
        (old_bundle, old_provider, current['bundle'], current['provider']),
        'Patches added: %s.' % _names(new_patches - old_patches),
        'Patches removed: %s.' % _names(old_patches - new_patches),
    ]
    if previous and previous.get('legacy'):
        lines[2] = 'Patches added: not recorded for the previous release.'
        lines[3] = 'Patches removed: not recorded for the previous release.'
    elif not previous:
        lines[2] = 'Patches added: ' + _names(new_patches) + '.'
        lines[3] = 'Patches removed: none.'
    return lines


def provider_changelog(current):
    """Build short provider notes from the existing release metadata."""
    lines = []
    if current.get('fallback'):
        lines.append(current['fallback'])
    if current.get('dropped'):
        lines.append('Provider no longer offers: ' + ', '.join(current['dropped']))
    return lines

def text(value):
    value = html.escape(str(value), quote=False)
    return re.sub(r'([\\`*_\[\]|])', r'\\\1', value)


def works_on(current):
    """Device requirements: verified Android minimum and CPU, plus MicroG from src/targets.json (W2)."""
    names = {21: '5.0', 22: '5.1', 23: '6', 24: '7.0', 25: '7.1', 26: '8', 27: '8.1', 28: '9', 29: '10',
             30: '11', 31: '12', 32: '12L', 33: '13', 34: '14', 35: '15', 36: '16'}
    api = current['min_sdk']
    cpu = 'ARM64 phones' if current['arch'] == 'arm64-v8a' else 'any phone CPU (no native code)'
    rows = ['- Android %s or newer (minimum API %d), %s.' % (names.get(api, 'API %d' % api), api, cpu)]
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'targets.json')
        with open(path, encoding='utf-8') as f:
            match = [t for t in json.load(f) if isinstance(t, dict) and t.get('id') == current['target']]
        microg = bool(match and match[0].get('needs_microg'))
    except (OSError, ValueError):
        microg = None
    if microg:
        rows.append('- Install [Morphe MicroG RE](https://github.com/MorpheApp/MicroG-RE/releases) first: Google sign-in in this app goes through it.')
    elif microg is None:
        rows.append('- MicroG requirement unknown: src/targets.json was unreadable when these notes were written.')
    return rows

ABOUT = 'About these builds: what CI checks, its limits and install help'
ABOUT_ANCHOR = 'about-these-builds'


def render(current, previous=None, reason=''):
    checked(current)
    download = WEB + '/releases/download/' + current['tag'] + '/' + current['apk']
    lines = ['## Changes', *('- ' + text(x) for x in changes(current, previous))]
    provider_lines = provider_changelog(current)
    if provider_lines:
        lines += ['', '## Provider changelog', *('- ' + text(x) for x in provider_lines)]
    lines += ['', '## Install', '- [Download and install the APK](' + download + ').']
    lines += ['', '[pf-release-v1]: # "' + base64.b64encode(json.dumps(current, sort_keys=True, separators=(',', ':')).encode()).decode() + '"']
    body = '\n'.join(lines) + '\n'
    if len(body.encode()) > 120000:
        raise ValueError('release notes exceed safe size')
    return body
