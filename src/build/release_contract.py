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
from artifact_identity import SCHEMA, command, expected_package, pinned_certificate, record, require, run_binding, target
from build_identity import parse as parse_build_suffix, verify_run
import input_recipe
import release_notes


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
    input_recipe.verify(root, ident, captured['winner'], captured['local_input_recipe'])
    # W15g: only an APK the Sign job signed and checked against the unsigned patch output.
    require(d.get('signing_split') is True and isinstance(d.get('signing'), dict) and isinstance(d.get('unsigned_output'), dict),
            'legacy or unsigned identity report; only a Sign job report can be released')
    signing = d['signing']
    require(signing.get('binding') == run_binding(os.environ) == d['unsigned']['binding'],
            'signing evidence is from another workflow run or attempt')
    require(type(signing.get('entries_compared')) is int and signing['entries_compared'] > 0
            and isinstance(signing.get('schemes'), dict) and signing['schemes'].get('v2') is True
            and signing['schemes'].get('v4') is False, 'incomplete signing evidence')
    unsigned = d['unsigned_output']
    require(re.fullmatch('[0-9a-f]{64}', unsigned.get('sha256', '')) and unsigned['sha256'] != d['output']['sha256'],
            'unsigned/signed hand-off evidence missing')
    sig = d['signature']
    cert = sig['certificate_sha256']
    require(re.fullmatch('[0-9a-f]{64}', cert) and sig['cryptographic_verification'] == 'passed'
            and cert == captured['expected_certificate_sha256'] == signing.get('pin') == pinned_certificate(root),
            'release signer evidence mismatch')
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
    optional = {}
    for key in ('dropped', 'fallback', 'fallback-provider'):
        if (root / 'release' / ('.' + key)).exists():
            optional[key] = read_text(root, 'release/.' + key)
    dropped = [line.removeprefix('- ').strip() for line in optional.get('dropped', '').splitlines() if line.strip()]
    for name in dropped:
        one_line(name, 'dropped patch')
    fields = {'version': version, 'prefix': prefix, 'suffix': suffix, 'tag': prefix+'-v'+version+suffix,
              'apkname': apk.name, 'apkpath': relative, 'sha256': output['sha256'],
              'sizemb': format(output['bytes']/1048576, '.1f'), 'provider': provider,
              'patchver': patchver, 'aplist': '\n'.join('- '+name for name in applied)}
    if dropped:
        fields['dropped'] = '\n'.join(dropped)
    if optional.get('fallback-provider'):
        fields['fallback'] = one_line(optional['fallback-provider'], 'fallback provider')
    elif optional.get('fallback'):
        # Older controller markers carried prose only; retain it as a provider-safe legacy value.
        fields['fallback'] = one_line(provider, 'fallback provider')
    if re.fullmatch(r'20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]Z', os.environ.get('PF_BUILT_AT', '')):
        fields['built'] = os.environ['PF_BUILT_AT']  # W16k: set once per job (manual-patch.yml)
    summary = release_notes.snapshot(fields, d, t)
    fields['summary'] = json.dumps(summary, sort_keys=True)
    fields['notes'] = release_notes.render(summary)
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
        summary = json.loads(fields['summary'])
        rows = release_notes.inventory()
        release_contract_root = pathlib.Path.cwd()
        refusal = release_notes.publish_guard(summary, rows, bool(fields.get('fallback')),
                                              target(release_contract_root, sys.argv[1]),
                                              release_contract_root)
        coverage = summary.get('_coverage')
        if coverage:
            summary['coverage'] = coverage['pct']
            fields['summary'] = json.dumps({k: v for k, v in summary.items() if not k.startswith('_')}, sort_keys=True)
        if refusal:
            summary_line = 'RELEASE_SUMMARY %s: %s' % (summary['target'], refusal)
            print(summary_line)
            step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
            if step_summary:
                with open(step_summary, 'a', encoding='utf-8') as out:
                    out.write(summary_line + '\n')
            raise ValueError('PUBLISH_REFUSED ' + summary['target'] + ': ' + refusal + '. Nothing was published.')
        if coverage:
            summary_line = ('RELEASE_SUMMARY %s: fallback coverage %s%% (%d of %d patches), publication allowed.' %
                            (summary['target'], coverage['pct'], coverage['patches'], coverage['primary']))
            print(summary_line)
            step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
            if step_summary:
                with open(step_summary, 'a', encoding='utf-8') as out:
                    out.write(summary_line + '\n')
        previous, reason = release_notes.previous_release(summary, rows)
        fields['notes'] = release_notes.render(summary, previous, reason)
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
