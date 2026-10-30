#!/usr/bin/env python3
"""Read-only weekly check that configured store pins remain listed.

Only store listing/release HTML is read.  No APK, bundle, final download URL, cookie,
or credential is fetched or printed.  The checker is deliberately small and pure enough
for offline tests: ``check_target`` accepts a fetch function returning HTML.
"""
import argparse
import html as html_lib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
HOSTS = {'www.apkmirror.com', 'apkmirror.com', 'apkpure.com', 'www.apkpure.com'}
MARKERS = {'OK': 'PIN_STORE_OK', 'MISSING': 'PIN_STORE_MISSING', 'UNKNOWN': 'PIN_STORE_UNKNOWN'}

VERSION_RX = re.compile(r'(?<![0-9])\d+(?:\.\d+){1,5}(?![0-9])')
TAG_RX = re.compile(r'\b(?:version(?:Name|_name)?|release|app-version)[^\n]{0,100}?([0-9]+(?:\.[0-9]+){1,5})', re.I)


def _safe_url(url):
    parsed = urllib.parse.urlparse(url or '')
    if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password:
        raise ValueError('unsupported listing host')
    return url


def _visible(body):
    """W16y-b review: drop scripts, styles and comments so a number inside page code is
    never read as a listed release."""
    body = body if isinstance(body, str) else ''
    body = re.sub(r'(?is)<!--.*?-->', ' ', body)
    return re.sub(r'(?is)<(script|style|noscript)\b[^>]*>.*?</\1\s*>', ' ', body)


def _text(body):
    body = html_lib.unescape(_visible(body))
    return re.sub(r'<[^>]+>', ' ', body)


def listing_facts(body):
    """Return conservative facts from listing HTML; binary links are intentionally ignored."""
    raw = _visible(body)
    text = _text(raw)
    versions = set(VERSION_RX.findall(text))
    versions.update(TAG_RX.findall(text))
    # Store pages expose version codes in variant rows/attributes.  Keep only numeric tokens
    # next to an explicit code label, avoiding arbitrary IDs and URLs.
    codes = set(re.findall(r'(?i)(?:version[ _-]?code|versionCode|code)[^0-9]{0,40}(\d{5,15})', raw))
    return {'text': text, 'versions': versions, 'codes': codes}


def target_url(target, apps):
    package = target.get('package')
    source = target.get('source') or 'apkmirror'
    data = (apps.get(source) or {}).get(package) if isinstance(apps, dict) else None
    if not isinstance(data, dict):
        raise ValueError('store mapping missing')
    # Build mappings use list_url/download_url; neither points at final binary content.
    url = data.get('list_url') if source == 'apkmirror' else data.get('download_url')
    return _safe_url(url)


def check_target(target, apps, fetch):
    """Check one configured target, returning a bounded record for output/tests."""
    result = {'target': target.get('id', ''), 'store': target.get('source') or 'apkmirror'}
    try:
        url = target_url(target, apps)
        body = fetch(url)
        if not isinstance(body, str) or not body or len(body.encode('utf-8', 'ignore')) > MAX_BYTES:
            raise ValueError('listing unreadable')
        facts = listing_facts(body)
        if not facts['versions'] and not facts['codes']:
            raise ValueError('listing parser found no release facts')
        wanted_code = str(target.get('version_code')) if target.get('version_code') is not None else None
        wanted_version = str(target.get('max_app_version')) if target.get('max_app_version') else None
        if wanted_code and wanted_code not in facts['codes'] and not re.search(r'(?<!\d)' + re.escape(wanted_code) + r'(?!\d)', facts['text']):
            result.update(status='MISSING', reason='version_code_not_listed')
        elif wanted_version and wanted_version not in facts['versions'] and not re.search(r'(?<!\d)' + re.escape(wanted_version) + r'(?!\d)', facts['text']):
            result.update(status='MISSING', reason='max_version_not_listed')
        else:
            result.update(status='OK')
            if wanted_version:
                result['version'] = wanted_version
            if wanted_code:
                result['code'] = wanted_code
    except Exception:
        # Transport, parser and malformed stub responses are all unknown: never infer OK.
        result.update(status='UNKNOWN', reason='listing_unreadable')
    return result


def http_fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'patch-factory-pin-check/1', 'Accept': 'text/html'})
    with urllib.request.urlopen(request, timeout=25) as response:
        # W16y-b review: a redirect off the store, or anything that is not a web page
        # (an APK, a bundle), is refused before any body is read.
        _safe_url(response.geturl())
        kind = (response.headers.get('Content-Type') or '').split(';')[0].strip().lower()
        if kind not in ('text/html', 'application/xhtml+xml'):
            raise ValueError('not a listing page')
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('listing too large')
    return data.decode('utf-8', 'replace')


def line(result):
    fields = [MARKERS[result['status']], 'target=' + str(result['target']), 'store=' + str(result['store'])]
    if result.get('version'):
        fields.append('version=' + result['version'])
    if result.get('code'):
        fields.append('code=' + result['code'])
    if result.get('reason'):
        fields.append('reason=' + result['reason'])
    return ' '.join(fields)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--targets', default='src/targets.json')
    parser.add_argument('--apps', default='src/build/helper/apps.json')
    parser.add_argument('--json-out')
    parser.add_argument('--strict', action='store_true', help='exit 1 on MISSING or UNKNOWN (not used yet)')
    args = parser.parse_args(argv)
    targets = json.loads(Path(args.targets).read_text(encoding='utf-8'))
    apps = json.loads(Path(args.apps).read_text(encoding='utf-8'))
    # W16y-b review: only exact build pins (version_code). A max_app_version is a ceiling the
    # resolver may step under, not a pin the patches rely on.
    selected = [t for t in targets if t.get('enabled') and t.get('version_code') is not None]
    results = [check_target(t, apps, http_fetch) for t in selected]
    # Exactly one bounded machine-readable line per selected target.
    for result in results:
        print(line(result))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    # W16y-b (wrong call 115): plain HTTPS reads were tested only against stubs, while the build
    # reaches APKMirror through its browser helper. Until a live run proves these reads, this is
    # a report-only probe: it prints its lines and keeps evidence, and never fails.
    if args.strict:
        return 1 if any(r['status'] in ('MISSING', 'UNKNOWN') for r in results) else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
