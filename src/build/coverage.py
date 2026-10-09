#!/usr/bin/env python3
"""Coverage-first app version choice (packet W12, owner design 10 Oct 2026).

resolve.sh used to take the newest app version a provider lists. Now, per candidate:
  1. the version where the most of OUR chosen patches apply wins
     (exclusive targets: the include list; others: the provider's defaults minus excludes,
     plus includes);
  2. the newest version breaks a tie;
  3. max_app_version stays a hard ceiling, and a target that pins an exact version_code
     keeps that version (coverage is reported, never changes it).
A chosen patch the listing does not tie to versions (universal, any version, or absent)
counts at every version, so it never moves the choice. Patches lost at the chosen version
are named. Any doubt about the listing prints COVERAGE_UNAVAILABLE and exits 3; resolve.sh
then keeps the newest version exactly as before, and the applied-patch gate still decides.

Usage: coverage.py JAR MPP PACKAGE TARGET_ID CANDIDATE MAXVER < "VERSION COUNT" lines
       coverage.py --listing FILE PACKAGE TARGET_ID CANDIDATE MAXVER < lines   (tests)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = re.compile(r'[0-9]+(?:[.][0-9]+)+')
LIMIT = 16 * 1024 * 1024


class Unavailable(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Unavailable(why)


def vkey(v):
    return tuple(int(x) for x in v.split('.'))


def parse(text, package):
    """{name: {'enabled': bool, 'versions': set or None}}; None means any version."""
    out, cur, pkg, collecting = {}, None, None, False
    names = enabled = 0
    for raw in text.splitlines():
        line = raw[6:] if raw.startswith('INFO: ') else raw
        if line.startswith('Name: '):
            names += 1
            name = line[6:].strip()
            need(name and name not in out, 'duplicate or empty patch name')
            cur = out[name] = {'enabled': None, 'versions': None, 'packages': False}
            pkg, collecting = None, False
            continue
        if cur is None:
            continue
        if line.startswith('Enabled: '):
            enabled += 1
            cur['enabled'] = line[9:].strip() == 'true'
            collecting = False
        elif line.startswith('\tPackage name: '):
            pkg = line[15:].strip()
            cur['packages'] = True
            collecting = False
        elif line == '\tCompatible versions:':
            collecting = pkg == package
            if collecting:
                cur['versions'] = set()
        elif collecting and line.startswith('\t\t') and VERSION.fullmatch(line.strip()):
            cur['versions'].add(line.strip())
        else:
            collecting = False
    need(names > 0, 'no patch names in the listing')
    need(names == enabled, 'listing parse mismatch: %d names, %d enabled lines' % (names, enabled))
    for v in out.values():
        if v['versions'] is not None and not v['versions']:
            v['versions'] = None
    return out


def lines(path):
    if not path.is_file():
        return []
    return [l.strip() for l in path.read_text(encoding='utf-8').splitlines() if l.strip() and not l.lstrip().startswith('#')]


def chosen(root, target, candidate, listing):
    c = [x for x in target.get('candidates') or [] if x.get('name') == candidate]
    need(len(c) == 1, 'candidate %s not configured' % candidate)
    d = root / 'src/patches' / c[0]['patch_dir']
    inc, exc = lines(d / 'include-patches'), set(lines(d / 'exclude-patches'))
    if target.get('exclusive'):
        want = [n for n in inc if n not in exc]
    else:
        want = sorted({n for n, v in listing.items() if v['enabled']} - exc | (set(inc) - exc))
    need(want, 'no chosen patches')
    need(any(n in listing for n in want), 'none of the chosen patches is in the listing')
    return want


def choose(listing, want, versions, maxver, fixed):
    vs = sorted({v for v in versions if VERSION.fullmatch(v)}, key=vkey, reverse=True)
    if maxver:
        vs = [v for v in vs if vkey(v) <= vkey(maxver)]
    need(vs, 'no version at or under the ceiling')

    def cover(v):
        return [n for n in want if n not in listing or listing[n]['versions'] is None or v in listing[n]['versions']]

    newest = vs[0]
    if fixed:
        pick = newest
    else:
        pick = max(vs, key=lambda v: (len(cover(v)), vkey(v)))
    got = cover(pick)
    lost = [n for n in want if n not in got]
    return dict(pick=pick, covered=len(got), total=len(want), lost=lost, newest=newest,
                newest_covered=len(cover(newest)), fixed=fixed)


def listing_text(jar, mpp, package):
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'JAVA_HOME', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR')}
    with tempfile.TemporaryFile() as out:
        r = subprocess.run(['java', '-jar', jar, 'list-patches', '--patches=' + mpp, '-x', '--with-packages',
                            '--with-versions', '-f', package], stdout=out, stderr=subprocess.DEVNULL, env=env, timeout=300)
        out.seek(0)
        data = out.read(LIMIT + 1)
    need(r.returncode == 0, 'list-patches exit %d' % r.returncode)
    need(0 < len(data) <= LIMIT, 'empty or oversized listing')
    return data.decode('utf-8', 'replace')


def main(argv):
    root = Path(os.environ.get('PF_ROOT', '.'))
    try:
        if argv[:1] == ['--listing']:
            text = Path(argv[1]).read_text(encoding='utf-8')
            package, tid, cand, maxver = argv[2:6]
        else:
            jar, mpp, package, tid, cand, maxver = argv[:6]
            text = listing_text(jar, mpp, package)
        maxver = '' if maxver in ('', 'null') else maxver
        targets = json.loads((root / 'src/targets.json').read_text(encoding='utf-8'))
        t = [x for x in targets if x.get('id') == tid]
        need(len(t) == 1, 'target %s not configured' % tid)
        listing = parse(text, package)
        want = chosen(root, t[0], cand, listing)
        versions = [l.split()[0] for l in sys.stdin.read().splitlines() if l.split()]
        r = choose(listing, want, versions, maxver, bool(t[0].get('version_code')))
    except (Unavailable, ValueError, OSError, subprocess.SubprocessError) as e:
        print('COVERAGE_UNAVAILABLE %s' % (str(e) if isinstance(e, Unavailable) else type(e).__name__))
        return 3
    print('COVERAGE_PICK=%s' % r['pick'])
    print('COVERAGE_COVERED=%d' % r['covered'])
    print('COVERAGE_TOTAL=%d' % r['total'])
    note = ' (exact version_code pin: version kept)' if r['fixed'] else ''
    print('COVERAGE %s: app %s covers %d of %d chosen patches; newest %s covers %d%s'
          % (cand, r['pick'], r['covered'], r['total'], r['newest'], r['newest_covered'], note))
    for n in r['lost'][:20]:
        print('COVERAGE_LOST %s: %s' % (cand, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
