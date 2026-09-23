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
    return checked(dict(schema=1, target=report['target'], label=target.get('label', report['target']),
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


def previous_release(current):
    """Optional GET-only history read. Errors become explicit UNKNOWN, not no change."""
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
                return choose_previous(rows, current)
        raise ValueError('incomplete inventory')
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return None, 'Previous-release comparison unavailable. This does not mean nothing changed.'


def changes(current, previous):
    if not previous:
        return ['Change comparison unavailable; the verified current build is listed below.']
    result = [('App version unchanged at ' + current['version'] + '; this is another build.')
              if current['version'] == previous['version'] else
              'App version: ' + previous['version'] + ' -> ' + current['version'] + '.']
    if previous.get('legacy'):
        return result + ['Patch changes were not recorded in a comparable format in the previous release.']
    for key, label in [('provider', 'Patch providers'), ('bundle', 'Primary patch bundle'),
                       ('min_sdk', 'Minimum Android API'), ('package', 'Android package'),
                       ('signer', 'Signing certificate')]:
        if current[key] != previous[key]:
            result.append(label + ' changed: ' + str(previous[key]) + ' -> ' + str(current[key]) + '.')
    old, new = set(previous['patches']), set(current['patches'])
    for label, values in [('Applied patch names added', new-old), ('Applied patch names removed', old-new)]:
        if values:
            result.append(label + ': ' + ', '.join(sorted(values)) + '.')
    if old == new:
        result.append('Applied patch names unchanged; this does not prove unchanged patch code or defaults.')
    if current['source'] != previous['source']:
        result.append('Repository source changed; see the exact source comparison below.')
    if current['sha256'] != previous['sha256']:
        result.append('APK bytes differ from the previous release.')
    return result


def text(value):
    value = html.escape(str(value), quote=False)
    return re.sub(r'([\\`*_\[\]|])', r'\\\1', value)


def render(current, previous=None, reason='Previous-release comparison not requested in this nonpublishing check.'):
    checked(current)
    guide = WEB + '/blob/' + current['source'] + '/docs/guide.md'
    lines = ['## What changed', *('- ' + text(x) for x in changes(current, previous)), '',
             text(reason), '', '## Release summary', '',
             '| Detail | Value |', '| --- | --- |']
    values = [('App', current['label']), ('App version', current['version']),
              ('Android package', current['package']), ('Minimum Android API', current['min_sdk']),
              ('Native code', current['arch']), ('Size', format(current['bytes']/1048576, '.1f') + ' MB'),
              ('Patch providers', current['provider']), ('Primary bundle', current['bundle']),
              ('Applied patch names', len(current['patches']))]
    lines += ['| ' + name + ' | ' + text(value) + ' |' for name, value in values]
    lines += ['', '## Applied patches (' + str(len(current['patches'])) + ')',
              '<details>', '<summary>All applied patch names</summary>', '',
              *('- ' + text(name) for name in current['patches']),
              '', '</details>', '', '## Checks and limitations',
              '- CI checked APK identity, declared minimum Android API, native payloads, applied patch names and its configured signing certificate.',
              '- Not phone-tested by this pipeline; not proof of original-publisher authenticity or installed-app compatibility.',
              '- Same-version patch-only update delivery in Obtainium remains limited. New build does not necessarily mean a new app version.',
              '', '## Download evidence', 'File: `' + current['apk'] + '`',
              'SHA-256: `' + current['sha256'] + '`',
              'CI signing certificate SHA-256: `' + current['signer'] + '`',
              '[Build source](' + WEB + '/tree/' + current['source'] + ')']
    suffix = '-b' + current['tag'].split('-b')[-1]
    ident = parse(suffix)
    if not ident['legacy']:
        lines.append('[Exact build run](' + WEB + '/actions/runs/' + str(ident['run_id']) + '/attempts/' + str(ident['attempt']) + ')')
    if previous:
        lines.append('[Previous app release](' + WEB + '/releases/tag/' + previous['tag'] + ')')
        if not previous.get('legacy') and previous['source'] != current['source']:
            lines.append('[Source comparison](' + WEB + '/compare/' + previous['source'] + '...' + current['source'] + ')')
    lines += ['', '## Help and stable information',
              '[Install, updates, source types and status meanings](' + guide + ')',
              'No automatic uninstall, import migration or device-protection bypass is required or recommended.',
              '', '[pf-release-v1]: # "' + base64.b64encode(json.dumps(current, sort_keys=True, separators=(',', ':')).encode()).decode() + '"']
    body = '\n'.join(lines) + '\n'
    if len(body.encode()) > 120000:
        raise ValueError('release notes exceed safe size')
    return body
