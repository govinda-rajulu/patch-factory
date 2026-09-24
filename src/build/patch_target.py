#!/usr/bin/env python3
"""Build the same per-bundle patch argv without eval or shell parsing."""
import json
import os
import pathlib
import subprocess
import sys


def command(root, target_id, winner, env):
    targets = json.loads((root / 'src/targets.json').read_text())
    t = next(x for x in targets if x['id'] == target_id and x.get('enabled'))
    c = next(x for x in t['candidates'] if x['name'] == winner)
    jars = list(root.glob('morphe-desktop-*.jar'))
    if len(jars) != 1 or not jars[0].stat().st_size:
        raise ValueError('need exactly one nonempty patcher jar')
    bundles = {c['name']: c}
    bundles.update({b['name']: b for b in t.get('extra_bundles', [])})
    files = sorted(list(root.glob('*.mpp')) + list((root / 'extra').glob('*.mpp')), key=lambda p: p.name)
    expected = {'09-' + winner + '.mpp'} | {('%02d-' % (i + 1)) + b['name'] + '.mpp' for i, b in enumerate(t.get('extra_bundles', []))}
    if len(files) != len(expected) or {p.name for p in files} != expected:
        raise ValueError('bundle files do not match selected target')
    cmd = ['java', '-jar', str(jars[0]), 'patch']
    ledger = []
    for i, p in enumerate(files):
        name = p.stem.split('-', 1)[1]
        cmd += ['-p', str(p)]
        if i == 0 and t.get('exclusive'):
            cmd += ['--exclusive']
        d = root / 'src/patches' / bundles[name]['patch_dir']
        for line in (d / 'exclude-patches').read_text().splitlines():
            if line:
                cmd += ['-d', line]
        for line in (d / 'include-patches').read_text().splitlines():
            if line:
                patch = line.split('|', 1)[0]
                cmd += ['-e', patch]
                ledger.append(name + '\t' + patch)
    expected_ledger = (root / '.requested').read_text().splitlines()
    if ledger != expected_ledger:
        raise ValueError('argv request ledger differs from selections.sh')
    if env.get('COE'):
        cmd += ['--continue-on-error']
    cmd += ['--options-file', str(root / 'src/options' / (c['options'] + '.json')),
            '--striplibs', 'arm64-v8a', '--keystore=' + str(root / 'src/ks.keystore'),
            '--keystore-password=' + env['KEYSTORE_PASS'],
            '--keystore-entry-alias=' + env['KEYSTORE_ALIAS'],
            '--keystore-entry-password=' + env['KEYSTORE_PASS'], '--force',
            '--out=' + str(root / 'release' / (t['apk_name'] + '-arm64-v8a.apk')),
            str(root / 'download' / (t['apk_name'] + '.apk'))]
    return cmd


if __name__ == '__main__':
    try:
        args = command(pathlib.Path('.'), sys.argv[1], sys.argv[2], os.environ)
        if os.environ.get('PF_SOURCE_READY') == 'true':
            # Mandatory byte check at the actual subprocess boundary.
            import artifact_identity
            import source_inputs
            root = pathlib.Path('.').resolve()
            target = artifact_identity.target(root, sys.argv[1])
            source_inputs.consumed(root, sys.argv[1], {
                'target': sys.argv[1],
                'patcher_input_apk': artifact_identity.record(
                    root, 'download/' + target['apk_name'] + '.apk')}, os.environ)
        if os.environ.get('PF_EXECUTION_OBSERVATION') == 'true':
            import execution_inputs
            execution_inputs.capture(pathlib.Path('.'), sys.argv[1], sys.argv[2], os.environ)
        # Never print argv: it carries signing passwords.
        sys.exit(subprocess.run(args, check=False).returncode)
    except (ValueError, KeyError, OSError, StopIteration, IndexError) as e:
        print('::error::cannot construct patch command: ' + str(e), file=sys.stderr)
        sys.exit(1)
