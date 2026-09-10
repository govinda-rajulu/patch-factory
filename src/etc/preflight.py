#!/usr/bin/env python3
"""Read-only checks shared by local tests, PR validation and every build."""
import json
import pathlib
import re
import subprocess
import sys


def check(root=pathlib.Path('.'), target_id=None):
    targets = json.loads((root / 'src/targets.json').read_text())
    if not isinstance(targets, list) or not targets:
        raise ValueError('targets must be a nonempty array')
    ids = [t['id'] for t in targets]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate target IDs')
    if target_id is not None and not any(t['id'] == target_id and t.get('enabled') for t in targets):
        raise ValueError('unknown or disabled target: ' + target_id)
    prefixes = []
    for t in targets:
        if not t.get('enabled'):
            continue
        for field in ('id', 'apk_name', 'tag_prefix'):
            if not re.fullmatch(r'[a-z0-9-]+', t.get(field, '')):
                raise ValueError('unsafe or missing target field: ' + field)
        prefixes.append(t['tag_prefix'])
        if not t.get('label') or not t.get('candidates'):
            raise ValueError('enabled target needs label and candidates: ' + t['id'])
        bundles = t['candidates'] + t.get('extra_bundles', [])
        names = [b['name'] for b in bundles]
        if len(set(names)) != len(names):
            raise ValueError('duplicate bundle names: ' + t['id'])
        for b in bundles:
            for field in ('name', 'patch_dir'):
                if not re.fullmatch(r'[a-zA-Z0-9_-]+', b.get(field, '')):
                    raise ValueError('unsafe or missing bundle ' + field)
            d = root / 'src/patches' / b['patch_dir']
            inc = (d / 'include-patches').read_text().splitlines()
            exc = (d / 'exclude-patches').read_text().splitlines()
            inc = [s.split('|', 1)[0] for s in inc if s]
            exc = [s for s in exc if s]
            if any(s != s.strip() for s in inc + exc):
                raise ValueError('whitespace in patch name: ' + str(d))
            if len(inc) != len(set(inc)) or len(exc) != len(set(exc)):
                raise ValueError('duplicate patch entries: ' + str(d))
            if set(inc) & set(exc):
                raise ValueError('include/exclude overlap: ' + str(d))
            if t.get('exclusive') and not inc:
                raise ValueError('exclusive bundle has no include list: ' + str(d))
            if b in t['candidates']:
                op = b.get('options', '')
                if not re.fullmatch(r'[a-zA-Z0-9_-]+', op):
                    raise ValueError('unsafe options name')
                if not isinstance(json.loads((root / 'src/options' / (op + '.json')).read_text()), list):
                    raise ValueError('options must be arrays')
        for candidate in t['candidates']:
            selected = [candidate] + t.get('extra_bundles', [])
            requested = [s.split('|', 1)[0] for b in selected for s in
                         (root / 'src/patches' / b['patch_dir'] / 'include-patches').read_text().splitlines() if s]
            if len(requested) != len(set(requested)):
                raise ValueError('cross-bundle requested name collision: ' + t['id'])
    if len(prefixes) != len(set(prefixes)):
        raise ValueError('duplicate enabled release prefixes')
    for script in ('bancheck.sh', 'quarantine.sh'):
        subprocess.run(['bash', 'src/etc/' + script], cwd=root, check=True)
    print('PREFLIGHT OK: selections, paths, options and policy checked')


if __name__ == '__main__':
    try:
        check(target_id=sys.argv[1] if len(sys.argv) > 1 else None)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as e:
        print('::error::preflight: ' + str(e), file=sys.stderr)
        sys.exit(1)
