#!/usr/bin/env python3
"""Bind release metadata and the exact artifact to same-run identity evidence.

No network, private-key reads, publishing or pruning. This is a handoff check,
not isolation from a malicious process with access to the whole runner.
"""
import datetime
import json
import os
import pathlib
import re
import sys
import uuid
from artifact_identity import SCHEMA, command, expected_package, record, require, target
from build_identity import parse as parse_build_suffix, verify_run


def read_text(root, relative):
    record(root, relative)  # refuse missing, symlinked or outside-checkout paths
    text = (root / relative).read_text()
    require(len(text) <= 100000, 'release metadata too large: ' + relative)
    return text.strip()


def one_line(value, label):
    require(bool(value) and not any(ord(c) < 32 or ord(c) == 127 for c in value),
            'invalid single-line release metadata: ' + label)
    return value


def verify(root, ident):
    root = pathlib.Path(root).resolve()
    t = target(root, ident)
    report_path = 'build-evidence/' + ident + '.json'
    record(root, report_path)
    d = json.loads((root / report_path).read_text())
    require(d['schema'] == SCHEMA and d['status'] == 'verified' and d['target'] == ident,
            'unverified or wrong-target identity report')
    captured = d['inputs']
    head = command(['git', 'rev-parse', 'HEAD'], root).decode().strip()
    require(captured['source_commit'] == head and captured['target'] == ident,
            'release evidence is from a different source commit/target')
    sig = d['signature']
    cert = sig['certificate_sha256']
    require(re.fullmatch('[0-9a-f]{64}', cert) and sig['cryptographic_verification'] == 'passed'
            and cert == captured['expected_certificate_sha256'], 'release signer evidence mismatch')
    require(d['manifest']['package'] == captured['expected_package'] == expected_package(root, t),
            'release package evidence mismatch')
    require(0 < d['manifest']['min_sdk'] <= t['min_sdk_ceiling'], 'release SDK evidence mismatch')
    require(d['architecture']['classification'] in ('arm64-v8a', 'no-native-libraries'),
            'release architecture evidence mismatch')
    apks = list((root / 'release').glob('*.apk'))
    require(len(apks) == 1, 'release needs exactly one APK')
    apk = apks[0]
    require(apk.name.endswith('-arm64-v8a.apk'), 'unexpected release APK suffix')
    relative = 'release/' + apk.name
    output = record(root, relative)
    require(output == d['output'] and output['bytes'] > 1000000,
            'release APK no longer matches verified bytes/path')
    version = one_line(read_text(root, 'release/.version'), 'version')
    require(re.fullmatch(r'[0-9]+(?:[.][0-9]+)*', version)
            and version == d['manifest']['version_name'], 'release version mismatch')
    require(apk.name.endswith('-v' + version + '-arm64-v8a.apk'), 'APK filename/version mismatch')
    prefix = one_line(read_text(root, 'release/.tagprefix'), 'prefix')
    require(prefix == t['tag_prefix'] and re.fullmatch('[a-z0-9-]+', prefix), 'release target prefix mismatch')
    suffix = one_line(read_text(root, 'release/.tagsuffix'), 'suffix')
    build_id = parse_build_suffix(suffix)
    if not build_id['legacy']:
        verify_run(suffix, os.environ)
    provider = one_line(read_text(root, 'release/.provider'), 'provider')
    patchver = one_line(read_text(root, 'release/.patchver'), 'patchver')
    applied = [line.removeprefix('- ').strip() for line in read_text(root, 'release/.applied').splitlines() if line.strip()]
    require(applied and applied == d['applied_patch_names'], 'applied-patch metadata differs from verified report')
    for name in applied:
        one_line(name, 'applied patch')
    fields = {'version': version, 'prefix': prefix, 'suffix': suffix, 'tag': prefix+'-v'+version+suffix,
              'apkname': apk.name, 'apkpath': relative, 'sha256': output['sha256'],
              'sizemb': format(output['bytes']/1048576, '.1f'), 'provider': provider,
              'patchver': patchver, 'aplist': '\n'.join('- '+name for name in applied)}
    return fields


def output_text(fields):
    chunks = []
    for key, value in fields.items():
        # Unique delimiters also handle a patch literally named PEOF safely.
        delimiter = 'PF_' + uuid.uuid4().hex
        while delimiter in value.splitlines():
            delimiter = 'PF_' + uuid.uuid4().hex
        chunks.append(key+'<<'+delimiter+'\n'+value+'\n'+delimiter+'\n')
    return ''.join(chunks)


def main():
    fields = verify(pathlib.Path.cwd(), sys.argv[1])
    if '--github-output' in sys.argv[2:]:
        verify_run(fields['suffix'], os.environ)
        dest = pathlib.Path(os.environ['GITHUB_OUTPUT'])
        with dest.open('a') as out:
            out.write(output_text(fields))
    print('RELEASE_CONTRACT_VERIFIED ' + json.dumps(fields, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, IndexError, TypeError) as error:
        print('::error::release contract: ' + str(error), file=sys.stderr)
        sys.exit(1)
