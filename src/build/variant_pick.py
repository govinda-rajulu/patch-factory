#!/usr/bin/env python3
"""Pick one APKMirror variant row that fits the phone (packet W16k, owner 25 Oct 2026).

stdin: the release page's variant rows, one row of HTML per line (get_apk in utils.sh splits them).
Every row is judged on all three at once, never one filter after another:
  chip     arm64-v8a first, then a row that also carries arm64-v8a, then universal/noarch;
           a row with only 32-bit or x86 code never fits;
  Android  the row's minimum Android must be at or under --ceiling (a row with no readable
           minimum ranks after every row that names one; the SDK gate after download decides);
  screen   --dpi when asked, else nodpi / 120-640dpi first.
The wanted type (--type BUNDLE or APK) ranks first, the other type is a fallback. A row carrying
--pin (exact version_code) wins among fitting rows. Before W16k the picker kept a non-fitting row
when nothing fitted (Truecaller 26.41.5, run 40191947359, Android 12L+ build); now nothing fits
means exit 4 and the caller tries the other store, then a lower version.
stdout: "TYPE<TAB>href" of the chosen row. stderr: one line per row with its verdict.
Exit 0 chosen, 3 no rows at all, 4 rows but none fits.
"""
import argparse
import re
import sys

SDK = [('4.4', 19), ('5.0', 21), ('5.1', 22), ('6', 23), ('7.0', 24), ('7.1', 25), ('8.0', 26), ('8.1', 27),
       ('9', 28), ('10', 29), ('11', 30), ('12L', 32), ('12.1', 32), ('12', 31), ('13', 33), ('14', 34),
       ('15', 35), ('16', 36), ('17', 37)]


def android_sdk(text):
    m = re.search(r'Android\s+([0-9]+(?:\.[0-9]+)?L?)\s*\+', text)
    if not m:
        return None
    v = m.group(1)
    for prefix, api in SDK:
        if v == prefix or v.startswith(prefix + '.') or (prefix.endswith('L') and v.startswith(prefix)):
            return api
    for prefix, api in SDK:  # '7' alone, '8' alone
        if v.split('.')[0] == prefix:
            return api
    return None


def plain(row):
    return ' '.join(re.sub(r'<[^>]+>', ' ', row).split())


def kind(row):
    m = re.search(r'apkm-badge[^>]*>\s*(BUNDLE|APK)\s*<', row, re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r'\b(BUNDLE|APK)\b', plain(row))
    return m.group(1).upper() if m else ''


def chip(text, want):
    t = text.lower()
    want = (want or 'arm64-v8a').lower()
    if re.search(r'\b(universal|noarch)\b', t):
        return 2
    archs = set(re.findall(r'arm64-v8a|armeabi-v7a|armeabi|x86_64|x86', t))
    if want in archs:
        return 0 if archs == {want} else 1
    return None  # no arm64 code: never fits this phone


def screen(text, dpi):
    t = text.lower()
    if dpi and dpi.lower() in t:
        return 0
    for rank, d in enumerate(('nodpi', '120-640dpi', '120-480dpi', '480-640dpi', '480dpi'), 1):
        if d in t:
            return rank
    return 9


def judge(rows, want_type, arch, dpi, ceiling, minver, pin):
    out = []
    for i, row in enumerate(rows):
        href = re.search(r'accent_color[^>]*href="([^"]+)"', row)
        if not href:
            continue
        text = plain(row)
        k = kind(row)
        c = chip(text, arch)
        sdk = android_sdk(text)
        why = []
        if c is None:
            why.append('no arm64 code')
        if ceiling and sdk is not None and sdk > ceiling:
            why.append('needs Android API %d, phone %d' % (sdk, ceiling))
        if minver and minver.lower() not in text.lower():
            why.append('not %s' % minver)
        pinned = bool(pin) and re.search(r'\b%s\b' % re.escape(pin), row) is not None
        score = (0 if pinned else 1, 0 if k == want_type else 1, 0 if sdk is not None else 1,
                 c if c is not None else 9, screen(text, dpi), i)
        out.append(dict(href=href.group(1), type=k or want_type, sdk=sdk, chip=c, why=why, score=score, text=text[:90]))
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--type', default='APK')
    p.add_argument('--arch', default='')
    p.add_argument('--dpi', default='')
    p.add_argument('--ceiling', default='')
    p.add_argument('--minver', default='')
    p.add_argument('--pin', default='')
    a = p.parse_args(argv)
    rows = [l for l in sys.stdin.read().split('\n') if 'table-row' in l or 'accent_color' in l]
    ceiling = int(a.ceiling) if a.ceiling.isdigit() else None
    judged = judge(rows, a.type.upper(), a.arch, a.dpi, ceiling, a.minver, a.pin)
    if not judged:
        print('VARIANT_PICK no variant rows on the page', file=sys.stderr)
        return 3
    fit = sorted((r for r in judged if not r['why']), key=lambda r: r['score'])
    for r in judged:
        print('VARIANT_PICK %s %s: %s' % ('fits' if not r['why'] else 'skip', r['text'],
              '; '.join(r['why']) or 'Android API %s, %s' % (r['sdk'] or '?', ['arm64', 'arm64+', 'universal'][r['chip']])),
              file=sys.stderr)
    if not fit:
        print('VARIANT_PICK none of %d builds fits this phone (API %s, arm64)' % (len(judged), ceiling or '?'), file=sys.stderr)
        return 4
    best = fit[0]
    print('VARIANT_PICK chose %s' % best['text'], file=sys.stderr)
    if a.arch and best['chip'] == 2:
        print('VARIANT_PICK arch fallback: %s -> universal' % a.arch, file=sys.stderr)
    print('%s\t%s' % (best['type'], best['href']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
