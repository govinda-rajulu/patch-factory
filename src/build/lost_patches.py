#!/usr/bin/env python3
"""Drop a chosen patch the picked bundle and app version no longer offer (packet W13).

Owner decision, 10 Oct 2026: when the build's bundle lacks a chosen patch, build without it
and name it, instead of failing the whole build (piko 3.10.0-dev.14 made two Instagram
patches always-on and took their names off its list; every Instagram build then failed).

  lost_patches.py prune ID WINNER VERSION   before the inputs are captured: reads each
      bundle's listing (the same list-patches call coverage.py uses) and removes, in this
      runner's checkout only, every include name the bundle does not offer, or offers only
      for other app versions. Writes ./.dropped (bundle TAB name TAB reason).
  lost_patches.py accept ID FILE            after patching: FILE holds requested names the
      patcher did not apply. Accepts them as dropped, or refuses.
Refuses (exit 4, so build_attempts.py can try the next provider) when the target sets
"strict_patches": true, or when more than max(3, a quarter) of the chosen names would go.
An unreadable listing changes nothing (exit 0): the applied-patch gate still decides.
BANNED and CONFIRM are untouched: this only ever removes names.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coverage  # noqa: E402

LEDGER = Path('.dropped')


def target(root, ident):
    rows = [t for t in json.loads((root / 'src/targets.json').read_text(encoding='utf-8')) if t.get('id') == ident]
    if len(rows) != 1:
        raise ValueError('target %s not configured' % ident)
    return rows[0]


def bundles(root, t, winner):
    """(bundle name, mpp path, patch_dir) in load order, from the files build.sh staged."""
    dirs = {c['name']: c['patch_dir'] for c in t['candidates'] if c['name'] == winner}
    dirs.update({b['name']: b.get('patch_dir') for b in t.get('extra_bundles', [])})
    files = sorted(list(root.glob('*.mpp')) + list((root / 'extra').glob('*.mpp')), key=lambda p: p.name)
    out = []
    for p in files:
        name = p.stem.split('-', 1)[1]
        if dirs.get(name):
            out.append((name, p, dirs[name]))
    return out


def lines(path):
    return [l for l in path.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')]


def limit(total):
    return max(3, total // 4)


def read_ledger(root):
    p = root / LEDGER
    return [l.split('\t') for l in p.read_text(encoding='utf-8').splitlines() if l] if p.is_file() else []


def write_ledger(root, rows):
    (root / LEDGER).write_text(''.join('\t'.join(r) + '\n' for r in rows), encoding='utf-8')


def total_requested(root, t, winner):
    return sum(len(lines(root / 'src/patches' / d / 'include-patches')) for _, _, d in bundles(root, t, winner))


def prune(root, ident, winner, version, listing=coverage.listing_text):
    t = target(root, ident)
    jars = list(root.glob('morphe-desktop-*.jar'))
    plan, total, unread = [], 0, 0
    for name, mpp, d in bundles(root, t, winner):
        inc = root / 'src/patches' / d / 'include-patches'
        want = lines(inc)
        total += len(want)
        try:
            if len(jars) != 1:
                raise coverage.Unavailable('need exactly one patcher jar')
            offered = coverage.parse(listing(str(jars[0]), str(mpp), t['package']), t['package'])
        except (coverage.Unavailable, ValueError, OSError) as e:
            print('::notice::PATCH_CHECK_UNAVAILABLE %s: %s; nothing dropped from this bundle'
                  % (name, str(e) if isinstance(e, coverage.Unavailable) else type(e).__name__))
            unread += 1
            continue
        for line in want:
            n = line.split('|', 1)[0]
            v = offered.get(n)
            if v is None:
                plan.append((name, inc, line, n, 'the bundle no longer offers it'))
            elif version and v['versions'] is not None and version not in v['versions']:
                plan.append((name, inc, line, n, 'not offered for app ' + version))
    if not plan and unread:
        return 0
    if not plan:
        print('PATCHES_ALL_OFFERED: every chosen patch is offered for app %s' % (version or 'any'))
        return 0
    for name, _, _, n, why in plan:
        print('::notice::PATCH_DROPPED %s: %s (%s)' % (name, n, why))
    if t.get('strict_patches') is True:
        print('::error::%s sets strict_patches, so a lost patch fails the build' % ident)
        return 4
    if len(plan) > limit(total):
        print('::error::%d of %d chosen patches are gone, more than %d; refusing (the next provider is tried)'
              % (len(plan), total, limit(total)))
        return 4
    for inc in {p[1] for p in plan}:
        gone = {p[2] for p in plan if p[1] == inc}
        raw = inc.read_bytes().decode('utf-8').split('\n')
        inc.write_bytes('\n'.join(l for l in raw if l not in gone).encode('utf-8'))
    write_ledger(root, read_ledger(root) + [[p[0], p[3], p[4]] for p in plan])
    print('PATCHES_DROPPED=%d of %d' % (len(plan), total))
    return 0


def accept(root, ident, missing_file):
    t = target(root, ident)
    missing = [l.strip() for l in Path(missing_file).read_text(encoding='utf-8').splitlines() if l.strip()]
    if not missing:
        return 0
    before = read_ledger(root)
    total = len([l for l in (root / '.requested').read_text(encoding='utf-8').splitlines() if l]) + len(before)
    for n in missing:
        print('::notice::PATCH_DROPPED %s: requested but not applied by the patcher' % n)
    if t.get('strict_patches') is True:
        print('::error::%s sets strict_patches, so a lost patch fails the build' % ident)
        return 4
    if len(before) + len(missing) > limit(total):
        print('::error::%d of %d chosen patches lost, more than %d; refusing' % (len(before) + len(missing), total, limit(total)))
        return 4
    write_ledger(root, before + [['-', n, 'requested but not applied'] for n in missing])
    return 0


def main(argv):
    root = Path(os.environ.get('PF_ROOT', '.'))
    try:
        if argv[:1] == ['prune'] and len(argv) == 4:
            return prune(root, argv[1], argv[2], argv[3])
        if argv[:1] == ['accept'] and len(argv) == 3:
            return accept(root, argv[1], argv[2])
    except (ValueError, KeyError, OSError) as e:
        print('::error::lost_patches: %s' % e)
        return 1
    print('usage: lost_patches.py prune ID WINNER VERSION | accept ID FILE', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
