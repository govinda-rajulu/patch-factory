#!/usr/bin/env python3
"""Onboarding gate: every new app, provider or patch name needs a written record.

Compares two checkouts of this repository (base and head) without git and without
network. Run from the BASE checkout so a pull request cannot rewrite its own gate:

    python3 base/src/etc/onboard_check.py --base base --head head --manifest out.json

What counts as onboarding (packet W1, 8 Oct 2026):
- a target id that is new, or a target that goes from disabled to enabled;
- a candidate or extra bundle whose source (owner/repo, or GitLab project id) is new
  for that target;
- a patch name added to any include-patches file a head target uses.

Each one needs docs/review/onboarding/<target id>.md at head that names it verbatim:
the provider as owner/repo (or gitlab:<project id>), each added patch name exactly as
the include file has it. A record containing TODO fails. An added name that matches a
CONFIRM rule also needs the line "Owner approved: <name>" (CONFIRM means a human
decides). An added name that matches a BANNED rule always fails.

Removals and unrelated edits are listed, never blocked. The manifest is data for the
agent review (src/council/onboard_review.py); it decides nothing by itself.
Standard library only.
"""
import argparse
import json
import sys
from pathlib import Path

RECORDS = Path('docs/review/onboarding')
WATCHED = ('src/targets.json', 'src/patches/', 'src/options/')


def load_targets(root):
    path = Path(root) / 'src' / 'targets.json'
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('src/targets.json must be an array')
    return data


def rules(root, kind):
    path = Path(root) / 'src' / 'patches' / kind
    if not path.is_file():
        return []
    rows = [line.strip().lower() for line in path.read_text(encoding='utf-8').splitlines()]
    return [r for r in rows if r and not r.startswith('#')]


def names(root, patch_dir, side):
    """Patch names in one selection file; '#' lines are comments, '|' starts options."""
    path = Path(root) / 'src' / 'patches' / patch_dir / (side + '-patches')
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        out.append(line.split('|', 1)[0].strip())
    return out


def source_key(bundle):
    if (bundle.get('host') or 'github') == 'gitlab':
        return 'gitlab:' + str(bundle.get('project_id'))
    return '%s/%s' % (bundle.get('owner'), bundle.get('repo'))


def bundles(target):
    rows = []
    for b in target.get('candidates') or []:
        rows.append(('candidate', b))
    for b in target.get('extra_bundles') or []:
        rows.append(('extra', b))
    return rows


def manifest(base, head):
    """Everything onboarding-relevant that changed from base to head, as plain data."""
    old = {t.get('id'): t for t in load_targets(base)}
    new = {t.get('id'): t for t in load_targets(head)}
    out = {'new_targets': [], 'enabled_targets': [], 'removed_targets': sorted(set(old) - set(new)),
           'new_providers': [], 'patch_changes': [], 'records': {}, 'problems': []}
    for tid, t in new.items():
        before = old.get(tid)
        if before is None:
            out['new_targets'].append({'id': tid, 'package': t.get('package'), 'label': t.get('label'),
                                       'enabled': bool(t.get('enabled')),
                                       'sources': [source_key(b) for _, b in bundles(t)]})
        elif t.get('enabled') and not before.get('enabled'):
            out['enabled_targets'].append(tid)
        seen = {source_key(b) for _, b in bundles(before or {})}
        for kind, b in bundles(t):
            key = source_key(b)
            if key not in seen:
                out['new_providers'].append({'target': tid, 'kind': kind, 'name': b.get('name'),
                                             'source': key, 'channel': b.get('channel'),
                                             'patch_dir': b.get('patch_dir')})
        for _, b in bundles(t):
            pd = b.get('patch_dir')
            if not pd:
                continue
            row = {'target': tid, 'patch_dir': pd}
            for side in ('include', 'exclude'):
                a = names(base, pd, side)
                z = names(head, pd, side)
                row['added_' + side] = [n for n in z if n not in a]
                row['removed_' + side] = [n for n in a if n not in z]
            if any(row[k] for k in ('added_include', 'removed_include', 'added_exclude', 'removed_exclude')):
                out['patch_changes'].append(row)
    return out


def needs(m):
    """(target id, list of required verbatim mentions) for every onboarding item."""
    req = {}
    for t in m['new_targets']:
        req.setdefault(t['id'], [])
    for tid in m['enabled_targets']:
        req.setdefault(tid, [])
    for p in m['new_providers']:
        req.setdefault(p['target'], []).append(p['source'])
    for c in m['patch_changes']:
        if c['added_include']:
            req.setdefault(c['target'], []).extend(c['added_include'])
    return req


def check(base, head):
    m = manifest(base, head)
    banned, confirm = rules(head, 'BANNED'), rules(head, 'CONFIRM')
    problems = []
    for tid, mentions in sorted(needs(m).items()):
        path = Path(head) / RECORDS / (str(tid) + '.md')
        rel = str(RECORDS / (str(tid) + '.md'))
        if not path.is_file() or path.is_symlink():
            problems.append('%s: onboarding record %s is missing' % (tid, rel))
            continue
        text = path.read_text(encoding='utf-8')
        m['records'][tid] = text[:20000]
        if 'TODO' in text:
            problems.append('%s: %s still contains TODO' % (tid, rel))
        for item in dict.fromkeys(mentions):
            if item not in text:
                problems.append('%s: %s does not name %r' % (tid, rel, item))
    for c in m['patch_changes']:
        for n in c['added_include']:
            low = n.lower()
            hit = [r for r in banned if r in low]
            if hit:
                problems.append('%s: added patch %r matches BANNED %r' % (c['target'], n, hit[0]))
            hit = [r for r in confirm if r in low]
            if hit:
                path = Path(head) / RECORDS / (str(c['target']) + '.md')
                text = path.read_text(encoding='utf-8') if path.is_file() else ''
                if ('Owner approved: ' + n) not in text:
                    problems.append('%s: added patch %r matches CONFIRM %r; the record needs '
                                    '"Owner approved: %s"' % (c['target'], n, hit[0], n))
    m['problems'] = problems
    m['rules'] = {'BANNED': banned, 'CONFIRM': confirm}
    m['onboarding'] = bool(needs(m))
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('--base', required=True)
    ap.add_argument('--head', required=True)
    ap.add_argument('--manifest')
    a = ap.parse_args(argv)
    m = check(a.base, a.head)
    if a.manifest:
        Path(a.manifest).write_text(json.dumps(m, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print('ONBOARDING %s: %d new target(s), %d enabled, %d new provider(s), %d selection change(s)' % (
        'YES' if m['onboarding'] else 'NO', len(m['new_targets']), len(m['enabled_targets']),
        len(m['new_providers']), len(m['patch_changes'])))
    for p in m['problems']:
        print('::error::onboarding: ' + p)
    if m['problems']:
        print('ONBOARD_CHECK FAIL (%d problem(s)); template: docs/review/onboarding/README.md' % len(m['problems']))
        return 1
    print('ONBOARD_CHECK OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
