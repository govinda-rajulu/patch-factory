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
import re
from pathlib import Path

RECORDS = Path('docs/review/onboarding')
WATCHED = ('src/targets.json', 'src/patches/', 'src/options/')
ID_RX = re.compile(r'^[a-z0-9][a-z0-9-]{0,40}$')


def load_targets(root):
    path = Path(root) / 'src' / 'targets.json'
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('src/targets.json must be an array')
    for target in data:
        if (not isinstance(target, dict) or not isinstance(target.get('id'), str)
                or not ID_RX.fullmatch(target['id'])):
            raise ValueError('invalid target id')
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


def paid_ok(root):
    p = Path(root) / 'src/patches/ADOPT.json'
    try:
        apps = json.loads(p.read_text(encoding='utf-8')).get('paid_ok_targets', []) if p.is_file() else []
    except ValueError:
        apps = []
    return {a for a in apps if isinstance(a, str)}


def owner_takes(root):
    """'target: name' for every owner take in src/patches/DECISIONS.json (bounded)."""
    p = Path(root) / 'src/patches/DECISIONS.json'
    try:
        rows = json.loads(p.read_text(encoding='utf-8')).get('names', []) if p.is_file() else []
    except (ValueError, AttributeError):
        rows = []
    out = ['%s: %s' % (r['target'], r['name']) for r in rows if isinstance(r, dict) and r.get('call') == 'take'
           and isinstance(r.get('target'), str) and isinstance(r.get('name'), str)]
    return sorted(set(out))[:400]


def owner_policy(base, head=None):
    """W15b (owner, 20 Oct 2026): apps where a paid unlock is the owner's decision, not a block.
    Read from the BASE commit, so a pull request cannot add its own app to the list.
    W16k (owner, 25 Oct 2026: PR #247 got five false blocks from the old base list): when the
    repository owner wrote the pull request (head is given only then), the owner's own head
    ADOPT.json and DECISIONS.json takes count too. A bot or anyone else gets the base only."""
    apps, takes = paid_ok(base), owner_takes(base)
    source = 'src/patches/ADOPT.json and DECISIONS.json on the base commit'
    if head is not None:
        apps |= paid_ok(head)
        takes = sorted(set(takes) | set(owner_takes(head)))[:400]
        source += ', plus the head commit: the repository owner wrote this pull request'
    # W16j (owner, 25 Oct 2026): the list now holds account apps too (Truecaller, Telegram, Amazon Music);
    # the owner accepted their risk. The key name stays for the prompt and its tests.
    return {'paid_unlock_ok_offline_apps': sorted(apps), 'owner_takes': takes, 'source': source}


def same_build_duplicates(head, targets, changes):
    """W16k: rule 4 means ONE build. A build is one candidate plus every extra bundle; another
    candidate is a separate (fallback) build, and an exclude is not a use. Only names this
    change adds to an include list are judged."""
    added = {(c['target'], n) for c in changes for n in c['added_include']}
    out = []
    for t in targets:
        tid, extras = t.get('id'), t.get('extra_bundles') or []
        for cand in t.get('candidates') or []:
            # W16w: a candidate whose overrides set extra_bundles builds with those extras only
            # (an empty list builds it alone), as the build does; rule 4 judges that build.
            ov = cand.get('overrides') if isinstance(cand.get('overrides'), dict) else {}
            build = [cand] + (list(ov.get('extra_bundles') or []) if 'extra_bundles' in ov else extras)
            seen = {}
            for b in build:
                for n in names(head, b.get('patch_dir') or '', 'include') if b.get('patch_dir') else []:
                    seen.setdefault(n, []).append(b.get('name'))
            for n, owners in seen.items():
                if len(owners) > 1 and (tid, n) in added:
                    out.append({'target': tid, 'name': n, 'bundles': owners})
    uniq = {(r['target'], r['name']): r for r in out}
    return [uniq[k] for k in sorted(uniq)]


def manifest(base, head, owner_pr=False):
    """Everything onboarding-relevant that changed from base to head, as plain data."""
    old = {t.get('id'): t for t in load_targets(base)}
    new = {t.get('id'): t for t in load_targets(head)}
    out = {'new_targets': [], 'enabled_targets': [], 'removed_targets': sorted(set(old) - set(new)),
           'new_providers': [], 'patch_changes': [], 'records': {}, 'problems': [],
           'owner_policy': owner_policy(base, head if owner_pr else None)}
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
    out['same_build_duplicates'] = same_build_duplicates(head, list(new.values()), out['patch_changes'])
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


def check(base, head, owner_pr=False):
    m = manifest(base, head, owner_pr)
    banned, confirm = rules(head, 'BANNED'), rules(head, 'CONFIRM')
    problems = []
    for tid, mentions in sorted(needs(m).items()):
        root = Path(head).resolve()
        records_root = (root / RECORDS).resolve()
        path = root / RECORDS / (str(tid) + '.md')
        resolved = path.resolve()
        rel = str(RECORDS / (str(tid) + '.md'))
        if root not in records_root.parents or records_root not in resolved.parents:
            problems.append('%s: onboarding record path escapes %s' % (tid, RECORDS))
            continue
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
    ap.add_argument('--owner-pr', action='store_true',
                    help='the repository owner wrote the pull request: head policy counts too (W16k)')
    a = ap.parse_args(argv)
    m = check(a.base, a.head, a.owner_pr)
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
