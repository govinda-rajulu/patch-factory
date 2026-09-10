#!/usr/bin/env python3
"""Apply explicit decisions to both sides, checking current policy before any write."""
import csv
import json
import os
import pathlib
import sys
import tempfile


def lines(p):
    return [x.strip() for x in p.read_text().splitlines() if x.strip() and not x.startswith('#')]


def apply_decisions(root, decisions):
    targets = json.loads((root / 'src/targets.json').read_text())
    modes = {}
    for t in targets:
        if not t.get('enabled'):
            continue
        for b in t['candidates'] + t.get('extra_bundles', []):
            d = b['patch_dir']
            mode = bool(t.get('exclusive'))
            if d in modes and modes[d] != mode:
                raise ValueError('shared directory has incompatible modes: ' + d)
            modes[d] = mode
    banned = [x.lower() for x in lines(root / 'src/patches/BANNED')]
    if not banned:
        raise ValueError('empty BANNED policy')
    exceptions = {tuple(x.split('|')[:2]) for x in lines(root / 'src/patches/EXCEPTIONS')}
    quarantined = {tuple(x.split('|')[:2]) for x in lines(root / 'src/patches/QUARANTINE')}
    grouped = {}
    for d, name, decision, default_on in decisions:
        if d not in modes:
            raise ValueError('stale or unknown bundle directory: ' + d)
        if decision not in ('IN', 'OUT', '?') or not name or any(c in name for c in '\r\n\t|'):
            raise ValueError('invalid decision row')
        key = (d, name)
        value = (decision, default_on)
        if key in grouped and grouped[key] != value:
            raise ValueError('conflicting decisions: ' + str(key))
        grouped[key] = value
    state = {}
    for (d, name), (decision, default_on) in grouped.items():
        if decision == '?':
            continue
        if d not in state:
            folder = root / 'src/patches' / d
            state[d] = [lines(folder / 'include-patches'), lines(folder / 'exclude-patches')]
        inc, exc = state[d]
        if decision == 'IN':
            if ((any(b in name.lower() for b in banned) and (d, name) not in exceptions)
                    or (d, name) in quarantined):
                raise ValueError('policy rejects IN: ' + d + ' / ' + name)
            exc[:] = [s for s in exc if s != name]
            if (modes[d] or not default_on) and name not in inc:
                inc.append(name)
        else:
            inc[:] = [s for s in inc if s != name]
            if name not in exc:
                exc.append(name)
    plan = []
    for d, (inc, exc) in state.items():
        if modes[d] and not inc:
            raise ValueError('would empty exclusive bundle: ' + d)
        if set(inc) & set(exc):
            raise ValueError('include/exclude overlap: ' + d)
        for name in inc:
            if ((any(b in name.lower() for b in banned) and (d, name) not in exceptions)
                    or (d, name) in quarantined):
                raise ValueError('final include violates policy: ' + d + ' / ' + name)
        for side, names in [('include', inc), ('exclude', exc)]:
            p = root / 'src/patches' / d / (side + '-patches')
            new = ('\n'.join(names) + '\n').encode() if names else b''
            old = p.read_bytes()
            if new != old:
                plan.append((p, old, new))
    # Validate cross-bundle identities using the entire proposed final state.
    for t in targets:
        if not t.get('enabled'):
            continue
        for candidate in t['candidates']:
            requested = []
            for b in [candidate] + t.get('extra_bundles', []):
                d = b['patch_dir']
                requested += state[d][0] if d in state else lines(root / 'src/patches' / d / 'include-patches')
            if len(requested) != len(set(requested)):
                raise ValueError('duplicate requested name across bundles: ' + t['id'])
    staged = []
    try:
        for p, old, new in plan:
            fd, name = tempfile.mkstemp(prefix='.selection-', dir=p.parent)
            with os.fdopen(fd, 'wb') as f:
                f.write(new)
            os.chmod(name, p.stat().st_mode & 0o777)
            staged.append((p, pathlib.Path(name), old))
        written = []
        try:
            for p, temp, old in staged:
                os.replace(temp, p)
                written.append((p, old))
        except OSError:
            for p, old in written:
                p.write_bytes(old)
            raise
    finally:
        for _, temp, _ in staged:
            temp.unlink(missing_ok=True)
    for p, old, new in plan:
        print(str(p) + ': ' + str(len(old)) + ' -> ' + str(len(new)) + ' bytes')
    print('selection files changed:', len(plan))
    return len(plan)


def main(kind):
    root = pathlib.Path('.')
    decisions = []
    if kind == 'chooser':
        files = sorted(pathlib.Path('/tmp/pf/choose').glob('*.txt'))
        if not files:
            raise ValueError('no chooser files')
        for f in files:
            for row in csv.reader(f.open(), delimiter='\t'):
                if len(row) < 2 or row[0].startswith('#'):
                    continue
                sign = row[0].strip()
                if sign not in ('+', '-', ''):
                    raise ValueError('invalid chooser decision')
                decisions.append((f.stem, row[1].strip(), {'+': 'IN', '-': 'OUT', '': '?'}[sign], False))
    else:
        p = root / 'docs/review' / ('PATCHES.tsv' if kind == 'full' else 'UNREVIEWED.tsv')
        with p.open(newline='') as f:
            for row in csv.reader(f, delimiter='\t'):
                if not row or row[0].startswith('#') or row[0] == 'DECISION':
                    continue
                if kind == 'full':
                    if len(row) < 8:
                        raise ValueError('malformed full sheet')
                    decisions.append((row[3], row[4], row[0].strip().upper(), row[5] == 'ON'))
                else:
                    if len(row) < 4:
                        raise ValueError('malformed unreviewed sheet')
                    decision = {'INCLUDE': 'IN', 'EXCLUDE': 'OUT', '?': '?'}.get(row[0].strip().upper())
                    if decision is None:
                        raise ValueError('invalid unreviewed decision')
                    decisions.append((row[2], row[3], decision, False))
    apply_decisions(root, decisions)


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except (ValueError, KeyError, OSError, IndexError) as e:
        print('ABORT: ' + str(e), file=sys.stderr)
        sys.exit(1)
