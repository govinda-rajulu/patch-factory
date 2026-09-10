#!/usr/bin/env python3
"""Record exact patcher inputs and verify the final APK. No private key export."""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

from verify_output import verify as verify_structure

SCHEMA = 1
ANDROID = '{http://schemas.android.com/apk/res/android}'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(args, cwd, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=120)
    # Do not include stderr or argv in errors: keytool can mention credentials.
    require(result.returncode == 0, pathlib.Path(args[0]).name + ' failed (exit ' + str(result.returncode) + ')')
    return result.stdout


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def record(root, relative):
    p = root / relative
    require(p.is_file() and not p.is_symlink(), 'missing or symlinked input: ' + relative)
    require(p.resolve().is_relative_to(root.resolve()), 'input outside checkout')
    return {'path': relative, 'bytes': p.stat().st_size, 'sha256': sha(p)}


def atomic_json(path, data):
    temp = path.with_name(path.name + '.cand')
    temp.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
    os.replace(temp, path)


def sdk_tools(name, env):
    sdk = pathlib.Path(env.get('ANDROID_HOME') or env.get('ANDROID_SDK_ROOT') or '/usr/local/lib/android/sdk')
    if name == 'aapt2' or name == 'apksigner':
        found = list(sdk.glob('build-tools/*/' + name))
    else:
        found = list(sdk.glob('cmdline-tools/*/bin/' + name)) + list(sdk.glob('tools/bin/' + name))
    def key(p):
        return tuple(int(x) for x in re.findall(r'\d+', str(p.parent)))
    found.sort(key=key, reverse=True)
    located = shutil.which(name, path=env.get('PATH'))
    if located:
        found.append(pathlib.Path(located))
    result = []
    for p in found:
        if p.is_file() and os.access(p, os.X_OK) and str(p) not in result:
            result.append(str(p))
    return result


def cert_from_keystore(root, env):
    require(bool(env.get('KEYSTORE_PASS')) and bool(env.get('KEYSTORE_ALIAS')), 'signing credentials absent')
    keytool = shutil.which('keytool', path=env.get('PATH'))
    require(keytool is not None, 'keytool unavailable')
    cert = command([keytool, '-exportcert', '-keystore', str((root / 'src/ks.keystore').resolve()),
                    '-alias', env['KEYSTORE_ALIAS'], '-storepass:env', 'KEYSTORE_PASS'], root, env)
    require(len(cert) > 100 and cert[:1] == b'0', 'keytool did not export a DER certificate')
    return hashlib.sha256(cert).hexdigest()


def capture_signer(root, env):
    path = root / '.signer-before-build.json'
    require(not path.exists(), 'signer capture already exists; use a fresh checkout')
    fingerprint = cert_from_keystore(root, env)
    atomic_json(path, {'schema': SCHEMA, 'certificate_sha256': fingerprint,
                       'trust': 'current CI keystore; historical device continuity not established'})
    print('SIGNER CAPTURED: public certificate fingerprint only; no key/password written')


def target(root, ident):
    matches = [x for x in json.loads((root / 'src/targets.json').read_text()) if x['id'] == ident and x.get('enabled')]
    require(len(matches) == 1, 'unknown or ambiguous enabled target')
    return matches[0]


def expected_package(root, t):
    # The committed, generated import is already the installation identity contract.
    apps = json.loads((root / 'docs/obtainium-govind.json').read_text())['apps']
    matches = [a for a in apps if a['name'] == t['label']]
    require(len(matches) == 1, 'ambiguous/missing expected output package in committed imports')
    package = matches[0]['id']
    require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+', package), 'invalid expected output package')
    return package


def capture_inputs(root, ident, winner, env):
    t = target(root, ident)
    candidates = [x for x in t['candidates'] if x['name'] == winner]
    require(len(candidates) == 1, 'winner not in target')
    signer = json.loads((root / '.signer-before-build.json').read_text())
    require(re.fullmatch('[0-9a-f]{64}', signer['certificate_sha256']), 'invalid captured signer')
    files = command(['git', 'ls-files', '-z'], root).decode().split('\0')
    files = sorted(x for x in files if x)
    require(files and 'src/targets.json' in files, 'no tracked source inventory')
    require(not any(x.endswith(('.keystore', '.ks', '.p12', '.jks', '.b64')) for x in files), 'signing material must not be tracked')
    source = command(['git', 'rev-parse', 'HEAD'], root).decode().strip()
    require(re.fullmatch('[0-9a-f]{40}', source), 'unreadable git source commit')
    repo_files = [record(root, x) for x in files]
    jars = list(root.glob('morphe-desktop-*.jar'))
    require(len(jars) == 1, 'expected exactly one patcher jar')
    bundle_paths = list(root.glob('*.mpp')) + list((root / 'extra').glob('*.mpp'))
    selected = [candidates[0]] + t.get('extra_bundles', [])
    require(len(bundle_paths) == len(selected), 'bundle inventory mismatch')
    bundle_records = [record(root, str(p.relative_to(root))) for p in sorted(bundle_paths)]
    tools = [record(root, str(jars[0].relative_to(root))), record(root, 'APKEditor.jar'), record(root, 'pup')]
    patcher_input = record(root, 'download/' + t['apk_name'] + '.apk')
    requested = record(root, '.requested')
    config_fingerprint = hashlib.sha256(json.dumps(repo_files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    data = {'schema': SCHEMA, 'target': ident, 'winner': winner, 'source_commit': source,
            'expected_package': expected_package(root, t), 'sdk_ceiling': t['min_sdk_ceiling'],
            'expected_certificate_sha256': signer['certificate_sha256'], 'repository_files': repo_files,
            'repository_bytes_fingerprint': config_fingerprint, 'tools': tools, 'bundles': bundle_records,
            'patcher_input_apk': patcher_input, 'requested_ledger': requested,
            'limitations': ['Patcher input may be a merged/repacked store download; original publisher signature is not verified.',
                            'Runtime/OS/container transitive dependencies are not fully pinned or attested.',
                            'This is evidence collected in the same runner, not isolation against a malicious patcher.']}
    atomic_json(root / '.build-inputs.json', data)
    print('INPUTS RECORDED: commit, tracked bytes, patcher/tool/bundle hashes and exact patcher-input APK')


def parse_badging(text):
    pkg = re.search(r"^package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']*)'", text, re.M)
    sdk = re.search(r"^sdkVersion:'([0-9]+)'", text, re.M)
    require(pkg is not None and sdk is not None, 'incomplete aapt2 metadata')
    return {'package': pkg[1], 'version_code': pkg[2], 'version_name': pkg[3], 'min_sdk': int(sdk[1])}


def parse_manifest(text):
    top = ET.fromstring(text)
    sdk = top.find('uses-sdk')
    require(top.tag == 'manifest' and sdk is not None, 'incomplete manifest XML')
    result = {'package': top.attrib['package'], 'version_code': top.attrib[ANDROID + 'versionCode'],
              'version_name': top.attrib[ANDROID + 'versionName'], 'min_sdk': int(sdk.attrib[ANDROID + 'minSdkVersion'])}
    require(result['version_code'].isdigit(), 'non-numeric version code')
    return result


def metadata(root, apk, env):
    for tool in sdk_tools('aapt2', env):
        try:
            result = parse_badging(command([tool, 'dump', 'badging', str(apk)], root).decode())
            result['reader'] = tool
            return result
        except (ValueError, UnicodeError, subprocess.TimeoutExpired):
            continue
    for tool in sdk_tools('apkanalyzer', env):
        try:
            result = parse_manifest(command([tool, 'manifest', 'print', str(apk)], root).decode())
            result['reader'] = tool
            return result
        except (ValueError, KeyError, UnicodeError, ET.ParseError, subprocess.TimeoutExpired):
            continue
    raise ValueError('final APK metadata unreadable; no valid Android reader result')


def native_architecture(apk):
    with zipfile.ZipFile(apk) as z:
        natives = [n for n in z.namelist() if n.startswith('lib/') and not n.endswith('/')]
        for name in natives:
            bits = name.split('/')
            require(len(bits) >= 3 and bits[1] == 'arm64-v8a', 'non-arm64 native member: ' + name)
            if name.endswith('.so'):
                with z.open(name) as f:
                    h = f.read(20)
                require(len(h) == 20 and h[:4] == b'\x7fELF' and h[4] == 2 and h[5] == 1
                        and int.from_bytes(h[18:20], 'little') == 183, 'native library is not ELF64 AArch64: ' + name)
        return {'classification': 'arm64-v8a' if natives else 'no-native-libraries', 'native_file_count': len(natives)}


def parse_signers(text):
    matches = re.findall(r'^Signer #([0-9]+) certificate SHA-256 digest:\s*([0-9a-fA-F:]+)\s*$', text, re.M)
    require(len(matches) == 1 and matches[0][0] == '1', 'expected exactly one APK signer certificate')
    fingerprint = matches[0][1].replace(':', '').lower()
    require(re.fullmatch('[0-9a-f]{64}', fingerprint), 'invalid signer fingerprint')
    return fingerprint


def apk_signer(root, apk, env):
    tools = sdk_tools('apksigner', env)
    require(tools, 'apksigner unavailable; final signature is unverified')
    # A verification failure must not be silently retried with an older verifier.
    text = command([tools[0], 'verify', '--print-certs', '--verbose', str(apk)], root).decode()
    return {'certificate_sha256': parse_signers(text), 'verifier': tools[0], 'cryptographic_verification': 'passed'}


def validate_identity(meta, architecture, signer, captured, version):
    require(meta['package'] == captured['expected_package'], 'finished APK package differs from committed installation identity')
    require(meta['version_name'] == version, 'finished APK version differs from release metadata')
    require(0 < meta['min_sdk'] <= int(captured['sdk_ceiling']), 'finished APK exceeds SDK ceiling')
    require(architecture['classification'] in ('arm64-v8a', 'no-native-libraries'), 'wrong output architecture')
    require(signer['certificate_sha256'] == captured['expected_certificate_sha256'], 'finished APK signer differs from the pre-build CI certificate')


def verify_records(root, records):
    for item in records:
        require(record(root, item['path']) == item, 'input changed during patching: ' + item['path'])


def verify_final(root, ident, env):
    verify_structure(root)
    captured = json.loads((root / '.build-inputs.json').read_text())
    require(captured['schema'] == SCHEMA and captured['target'] == ident, 'input capture target/schema mismatch')
    require(command(['git', 'rev-parse', 'HEAD'], root).decode().strip() == captured['source_commit'], 'source commit changed during build')
    verify_records(root, captured['repository_files'] + captured['tools'] + captured['bundles']
                   + [captured['patcher_input_apk'], captured['requested_ledger']])
    require(cert_from_keystore(root, env) == captured['expected_certificate_sha256'], 'CI keystore certificate changed during build')
    t = target(root, ident)
    require(expected_package(root, t) == captured['expected_package'] and t['min_sdk_ceiling'] == captured['sdk_ceiling'], 'identity contract changed')
    apk = next((root / 'release').glob('*.apk')).resolve()
    meta = metadata(root, apk, env)
    arch = native_architecture(apk)
    signer = apk_signer(root, apk, env)
    version = (root / 'release/.version').read_text().strip()
    validate_identity(meta, arch, signer, captured, version)
    applied = [x.removeprefix('- ').strip() for x in (root / 'release/.applied').read_text().splitlines() if x.strip()]
    require(applied, 'no applied-patch evidence')
    report = {'schema': SCHEMA, 'status': 'verified', 'target': ident, 'inputs': captured,
              'output': record(root, str(apk.relative_to(root.resolve()))), 'manifest': meta,
              'architecture': arch, 'signature': signer, 'applied_patch_names': applied,
              'historical_signer_continuity': 'not checked against an installed app or retained trusted release',
              'device_test': 'not performed', 'attestation': 'same-run evidence, not a signed independent attestation'}
    dest = root / 'build-evidence' / (ident + '.json')
    dest.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(dest, report)
    print('IDENTITY VERIFIED: ' + json.dumps({'target': ident, 'package': meta['package'], 'min_sdk': meta['min_sdk'],
                                           'architecture': arch['classification'], 'signer_sha256': signer['certificate_sha256'],
                                           'apk_sha256': report['output']['sha256']}, sort_keys=True))
    return report


if __name__ == '__main__':
    try:
        root = pathlib.Path('.').resolve()
        mode = sys.argv[1]
        if mode == 'capture-signer':
            capture_signer(root, os.environ)
        elif mode == 'capture-inputs':
            capture_inputs(root, sys.argv[2], sys.argv[3], os.environ)
        elif mode == 'verify':
            verify_final(root, sys.argv[2], os.environ)
        else:
            raise ValueError('unknown identity mode')
    except (ValueError, OSError, KeyError, IndexError, StopIteration, subprocess.TimeoutExpired, zipfile.BadZipFile) as e:
        print('::error::artifact identity: ' + str(e), file=sys.stderr)
        sys.exit(1)
