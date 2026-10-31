"""W15g signing-split contracts: real ZIPs and local stand-ins, never the network or SDK."""
import base64
import contextlib
import io
import hashlib
import json
import re
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'build'))
import artifact_identity as ai  # noqa: E402
import build_attempts  # noqa: E402
import sign_apk  # noqa: E402

IDENT = 'demo'
RUN_ENV = {'GITHUB_RUN_ID': '123456', 'GITHUB_RUN_ATTEMPT': '2'}
CERTIFICATE = b'0' + bytes(range(1, 160))
PIN = hashlib.sha256(CERTIFICATE).hexdigest()
OTHER_CERTIFICATE = b'0' + bytes(range(2, 161))
APK_NAME = 'demo-v1.2-arm64-v8a.apk'
META = {'package': 'com.example.app', 'version_code': '42', 'version_name': '1.2'}


def executable(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    path.chmod(0o755)
    return path


def write_zip(path, rows, page_align_so=True):
    """Write a stored ZIP with controllable local-data alignment and entry order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in rows:
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_STORED
            desired = 16384 if name.endswith('.so') and page_align_so else 4
            current_data_offset = archive.fp.tell() + 30 + len(name.encode('utf-8'))
            if name.endswith('.so') and not page_align_so:
                # Deliberately retain 4-byte alignment while losing 16-KiB page alignment.
                pad = (4 - current_data_offset) % 16384
                if pad < 4:
                    pad += 16384
            else:
                pad = (-current_data_offset) % desired
                if 0 < pad < 4:
                    pad += desired
            if pad:
                info.extra = struct.pack('<HH', 0xCAFE, pad - 4) + b'\0' * (pad - 4)
            archive.writestr(info, data)


def add_signatures(path):
    with zipfile.ZipFile(path, 'a', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('META-INF/MANIFEST.MF', b'Manifest-Version: 1.0\n')
        archive.writestr('META-INF/CERT.SF', b'Signature-Version: 1.0\n')
        archive.writestr('META-INF/CERT.RSA', b'fake certificate block')


class Harness:
    def __init__(self, root):
        self.root = Path(root)
        self.bin = self.root / 'fake-bin'
        self.sdk = self.root / 'android-home'
        self.tools = self.sdk / 'build-tools' / '35.0.0'
        self.log = self.root / 'tool-calls.jsonl'
        self.root.joinpath('src/build').mkdir(parents=True, exist_ok=True)
        self.root.joinpath('src/targets.json').write_text(targets_text(), encoding='utf-8')
        self.root.joinpath('src/build/ci-signer.json').write_text(
            json.dumps({'certificate_sha256': PIN}), encoding='utf-8')
        self.bin.mkdir(parents=True, exist_ok=True)
        self.tools.mkdir(parents=True, exist_ok=True)
        self._install_tools()

    def _install_tools(self):
        logger = """
import json, os, sys
with open(os.environ['FAKE_TOOL_LOG'], 'a', encoding='utf-8') as out:
    out.write(json.dumps({'tool': TOOL, 'argv': sys.argv[1:], 'env': {
        k: os.environ.get(k) for k in ('KEYSTORE_PASS','KEYSTORE_ALIAS','FAKE_SCHEMES',
            'FAKE_CERT','FAKE_SIGNERS','FAKE_ZIPALIGN_EXIT','FAKE_SIGN_FAIL')
    }}, sort_keys=True) + '\\n')
"""
        apksigner = "#!/usr/bin/env python3\nTOOL='apksigner'\n" + logger + r'''
import shutil, zipfile
if sys.argv[1] == 'sign':
    if os.environ.get('FAKE_SIGN_FAIL') == '1':
        sys.exit(9)
    args = sys.argv[2:]
    out = args[args.index('--out') + 1]
    source = args[-1]
    shutil.copyfile(source, out)
    # Like apksig (W15g smokes 31 Oct): directory entries and stamp-cert-sha256 are not written.
    with zipfile.ZipFile(source) as old:
        dropped = [i.filename for i in old.infolist() if i.filename.endswith('/') or i.filename == 'stamp-cert-sha256']
    if dropped:
        temp = out + '.drop'
        with zipfile.ZipFile(out) as old, zipfile.ZipFile(temp, 'w') as new:
            for item in old.infolist():
                if item.filename not in dropped:
                    new.writestr(item, old.read(item.filename))
        os.replace(temp, out)
    if os.environ.get('FAKE_SIGN_MODE') == 'bad':
        temp = out + '.rewrite'
        with zipfile.ZipFile(out) as old, zipfile.ZipFile(temp, 'w') as new:
            for item in old.infolist():
                data = old.read(item.filename)
                if item.filename == 'classes.dex':
                    data += b' tampered'
                new.writestr(item.filename, data, compress_type=item.compress_type)
        os.replace(temp, out)
    with zipfile.ZipFile(out, 'a', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF', b'Manifest-Version: 1.0\n')
        z.writestr('META-INF/CERT.SF', b'Signature-Version: 1.0\n')
        z.writestr('META-INF/CERT.RSA', b'fake certificate block')
    sys.exit(0)
if sys.argv[1] == 'verify':
    count = int(os.environ.get('FAKE_SIGNERS', '1'))
    print('Number of signers: %d' % count)
    cert = os.environ.get('FAKE_CERT', 'a' * 64)
    for n in range(1, count + 1):
        fingerprint = cert if n == 1 else 'b' * 64
        print('Signer #%d certificate SHA-256 digest: %s' % (n, fingerprint))
    schemes = dict(pair.split('=', 1) for pair in os.environ.get(
        'FAKE_SCHEMES', 'v1=false,v2=true,v3=false,v3.1=false,v4=false').split(','))
    for scheme in ('v1', 'v2', 'v3', 'v3.1', 'v4'):
        version = 'v' + scheme[1:] if scheme.startswith('v3.') else scheme
        print('Verified using %s scheme (APK Signature Scheme %s): %s' %
              (version, version, schemes.get(scheme, 'false')))
    sys.exit(0)
sys.exit(7)
'''
        executable(self.tools / 'apksigner', apksigner)
        zipalign = "#!/usr/bin/env python3\nTOOL='zipalign'\n" + logger + r'''
import sys
sys.exit(int(os.environ.get('FAKE_ZIPALIGN_EXIT', '0')))
'''
        executable(self.tools / 'zipalign', zipalign)
        aapt2 = "#!/usr/bin/env python3\nTOOL='aapt2'\n" + logger + r'''
print("package: name='com.example.app' versionCode='42' versionName='1.2'")
print("sdkVersion:'%s'" % os.environ.get('FAKE_MIN_SDK', '24'))
print("targetSdkVersion:'35'")
'''
        executable(self.tools / 'aapt2', aapt2)
        keytool = "#!/usr/bin/env python3\nimport base64\nTOOL='keytool'\n" + logger + r'''
sys.stdout.buffer.write(base64.b64decode(os.environ['FAKE_CERT_B64']))
'''
        executable(self.bin / 'keytool', keytool)

    def env(self, **extra):
        e = dict(os.environ)
        e.update(RUN_ENV)
        e.update({'ANDROID_HOME': str(self.sdk), 'PATH': str(self.bin) + os.pathsep + os.environ.get('PATH', ''),
                  'FAKE_TOOL_LOG': str(self.log), 'FAKE_CERT_B64': base64.b64encode(CERTIFICATE).decode(),
                  'FAKE_MIN_SDK': '24', 'FAKE_CERT': PIN,
                  'FAKE_ZIPALIGN_EXIT': '0', 'FAKE_SIGN_FAIL': '0'})
        e.update(extra)
        return e

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def init_git(self):
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)
        subprocess.run(['git', 'add', 'src/targets.json', 'src/build/ci-signer.json'], cwd=self.root, check=True)
        subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=test@example.invalid',
                        'commit', '-qm', 'fixture'], cwd=self.root, check=True)
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def create_release(self, min_sdk=24, source_commit=None):
        apk = self.root / 'release' / APK_NAME
        write_zip(apk, payload_rows(), page_align_so=True)
        for name, value in (('.version', '1.2'), ('.tagprefix', 'demo'), ('.tagsuffix', ''),
                            ('.provider', 'fixture'), ('.patchver', '1'), ('.applied', '- Safe patch\n')):
            (apk.parent / name).write_text(value, encoding='utf-8')
        record = ai.record(self.root, 'release/' + APK_NAME)
        if not (self.root / '.git').exists():
            self.init_git()
        head = source_commit or subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.root, check=True,
                                               capture_output=True, text=True).stdout.strip()
        report = {
            'schema': ai.SCHEMA, 'status': 'unsigned', 'signing_split': True, 'target': IDENT,
            'inputs': {'source_commit': head, 'target': IDENT, 'expected_certificate_sha256': PIN,
                       'winner': 'winner'},
            'output': record, 'manifest': {'package': META['package'], 'version_code': META['version_code'],
                                           'version_name': META['version_name'], 'min_sdk': min_sdk,
                         'reader': str(self.tools / 'aapt2')},
            'unsigned': {'binding': {'run_id': RUN_ENV['GITHUB_RUN_ID'],
                                    'run_attempt': RUN_ENV['GITHUB_RUN_ATTEMPT']},
                        'signature_files_present': []},
        }
        evidence = self.root / 'build-evidence' / (IDENT + '.json')
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(report), encoding='utf-8')
        return report, apk

    def create_verify_pair(self, min_sdk=24, signed_rows=None, signed_order=None, unsigned_rows=None):
        unsigned = self.root / 'signing' / APK_NAME
        release = self.root / 'release' / APK_NAME
        write_zip(unsigned, payload_rows() if unsigned_rows is None else unsigned_rows, page_align_so=True)
        records = payload_rows() if signed_rows is None else signed_rows
        if signed_order is not None:
            by_name = dict(records)
            records = [(name, by_name[name]) for name in signed_order]
        write_zip(release, records, page_align_so=True)
        add_signatures(release)
        report = {
            'schema': ai.SCHEMA, 'status': 'unsigned', 'signing_split': True, 'target': IDENT,
            'inputs': {'expected_certificate_sha256': PIN},
            'output': ai.record(self.root, 'signing/' + APK_NAME),
            'manifest': {'package': META['package'], 'version_code': META['version_code'],
                         'version_name': META['version_name'], 'min_sdk': min_sdk,
                         'reader': str(self.tools / 'aapt2')},
            'unsigned': {'binding': {'run_id': RUN_ENV['GITHUB_RUN_ID'],
                                    'run_attempt': RUN_ENV['GITHUB_RUN_ATTEMPT']},
                        'signature_files_present': []},
        }
        # The handoff's output describes the unsigned APK in release/ before sign() moved it.
        # The unsigned handoff digest is the still-unsigned file in signing/.
        report['output'] = {'path': 'release/' + APK_NAME,
                            'bytes': unsigned.stat().st_size, 'sha256': ai.sha(unsigned)}
        report_path = self.root / 'build-evidence' / (IDENT + '.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report), encoding='utf-8')
        return unsigned, release, report


def quiet_call(function, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def verify_with_env(root, env):
    # zipalign_check inherits process env; match the workflow, whose caller supplies os.environ.
    with patch.dict(os.environ, env, clear=True):
        return quiet_call(sign_apk.verify, root, IDENT, env)


def targets_text():
    rows = [{'id': IDENT, 'candidates': [
        {'name': 'primary', 'fallback': False},
        {'name': 'winner', 'fallback': True, 'overrides': {'min_sdk_ceiling': 24}},
    ]}]
    return json.dumps(rows, indent=2, ensure_ascii=False) + '\n'


def payload_rows():
    return [('classes.dex', b'dex payload'), ('lib/arm64-v8a/libdemo.so', b'native payload'),
            ('resources.arsc', b'resources payload')]


class SchemeContracts(unittest.TestCase):
    def test_minimum_sdk_selects_exact_schemes(self):
        self.assertEqual(sign_apk.expected_schemes(24),
                         {'v1': False, 'v2': True, 'v3': False, 'v3.1': False, 'v3.2': False, 'v4': False})
        self.assertEqual(sign_apk.expected_schemes(23),
                         {'v1': True, 'v2': True, 'v3': True, 'v3.1': False, 'v3.2': False, 'v4': False})

    def test_scheme_flags_are_exact_and_never_enable_v4(self):
        self.assertEqual(sign_apk.scheme_flags(sign_apk.expected_schemes(24)),
                         ['--v1-signing-enabled', 'false', '--v2-signing-enabled', 'true',
                          '--v3-signing-enabled', 'false', '--v4-signing-enabled', 'false'])
        self.assertEqual(sign_apk.scheme_flags(sign_apk.expected_schemes(23)),
                         ['--v1-signing-enabled', 'true', '--v2-signing-enabled', 'true',
                          '--v3-signing-enabled', 'true', '--v4-signing-enabled', 'false'])


class SignContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.h = Harness(self.temp.name)
        self.root = self.h.root
        self.h.init_git()
        self.report, self.apk = self.h.create_release()
        self.report['inputs']['source_commit'] = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()
        (self.root / 'build-evidence' / (IDENT + '.json')).write_text(json.dumps(self.report))
        self.key = self.root / 'src/ks.keystore'
        self.key.write_bytes(b'fake keystore bytes')
        self.env = self.h.env(KEYSTORE_PASS='do-not-leak-this-password', KEYSTORE_ALIAS='test-alias')

    def tearDown(self):
        self.temp.cleanup()

    def test_sign_uses_separate_input_and_out_and_password_env_refs(self):
        quiet_call(sign_apk.sign, self.root, IDENT, self.env)
        self.assertFalse(self.key.exists())
        calls = [c for c in self.h.calls() if c['tool'] == 'apksigner' and c['argv'][0] == 'sign']
        self.assertEqual(len(calls), 1)
        call = calls[0]
        argv = call['argv']
        self.assertEqual(argv[argv.index('--ks-pass') + 1], 'env:KEYSTORE_PASS')
        self.assertEqual(argv[argv.index('--key-pass') + 1], 'env:KEYSTORE_PASS')
        self.assertNotIn('do-not-leak-this-password', argv)
        self.assertEqual(call['env']['KEYSTORE_PASS'], 'do-not-leak-this-password')
        self.assertEqual(argv[argv.index('--out') + 1], str(self.apk))
        self.assertEqual(argv[-1], str(self.root / 'signing' / APK_NAME))
        self.assertNotEqual(argv[-1], argv[argv.index('--out') + 1])
        self.assertEqual(argv[argv.index('--alignment-preserved') + 1], 'true')
        self.assertEqual(argv[argv.index('--v4-signing-enabled') + 1], 'false')
        self.assertEqual(argv[argv.index('--v1-signing-enabled') + 1], 'false')
        self.assertEqual(argv[argv.index('--v2-signing-enabled') + 1], 'true')
        self.assertEqual(argv[argv.index('--v3-signing-enabled') + 1], 'false')

    def test_sign_uses_legacy_scheme_flags_below_sdk_24(self):
        self.report['manifest']['min_sdk'] = 23
        (self.root / 'build-evidence' / (IDENT + '.json')).write_text(json.dumps(self.report))
        quiet_call(sign_apk.sign, self.root, IDENT, self.env)
        argv = next(c['argv'] for c in self.h.calls() if c['tool'] == 'apksigner' and c['argv'][0] == 'sign')
        for flag in ('--v1-signing-enabled', '--v2-signing-enabled', '--v3-signing-enabled'):
            self.assertEqual(argv[argv.index(flag) + 1], 'true')
        self.assertEqual(argv[argv.index('--v4-signing-enabled') + 1], 'false')

    def test_sign_deletes_keystore_when_apksigner_fails(self):
        env = self.h.env(KEYSTORE_PASS='pw', KEYSTORE_ALIAS='test-alias', FAKE_SIGN_FAIL='1')
        with self.assertRaisesRegex(ValueError, 'apksigner sign failed'):
            quiet_call(sign_apk.sign, self.root, IDENT, env)
        self.assertFalse(self.key.exists())

    def test_fake_bad_sign_mode_tampers_payload_and_verify_detects_it(self):
        env = self.h.env(KEYSTORE_PASS='pw', KEYSTORE_ALIAS='test-alias', FAKE_SIGN_MODE='bad')
        quiet_call(sign_apk.sign, self.root, IDENT, env)
        with self.assertRaisesRegex(ValueError, 'changed entry bytes'):
            verify_with_env(self.root, self.h.env())

    def test_sign_stops_before_apksigner_when_keystore_pin_differs(self):
        env = self.h.env(KEYSTORE_PASS='pw', KEYSTORE_ALIAS='test-alias',
                         FAKE_CERT_B64=base64.b64encode(OTHER_CERTIFICATE).decode())
        with self.assertRaisesRegex(ValueError, 'differs from.*pin'):
            quiet_call(sign_apk.sign, self.root, IDENT, env)
        self.assertFalse(self.key.exists())
        self.assertFalse(any(c['tool'] == 'apksigner' and c['argv'][0] == 'sign' for c in self.h.calls()))


class HandoffContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.h = Harness(self.temp.name)
        self.root = self.h.root
        self.head = self.h.init_git()
        self.report, self.apk = self.h.create_release(source_commit=self.head)

    def tearDown(self):
        self.temp.cleanup()

    def call_handoff(self, env=None):
        return quiet_call(sign_apk.handoff, self.root, IDENT, env or self.h.env())

    def test_handoff_accepts_same_run_commit_and_apk(self):
        report, apk = self.call_handoff()
        self.assertEqual(report['output']['sha256'], ai.sha(apk))

    def test_handoff_refuses_another_run_id(self):
        env = self.h.env(GITHUB_RUN_ID='123457')
        with self.assertRaisesRegex(ValueError, 'another workflow run'):
            self.call_handoff(env)

    def test_handoff_refuses_another_attempt(self):
        env = self.h.env(GITHUB_RUN_ATTEMPT='3')
        with self.assertRaisesRegex(ValueError, 'another workflow run'):
            self.call_handoff(env)

    def test_handoff_refuses_another_commit(self):
        self.report['inputs']['source_commit'] = 'f' * 40
        (self.root / 'build-evidence' / (IDENT + '.json')).write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, 'another source commit'):
            self.call_handoff()

    def test_handoff_refuses_changed_apk_bytes(self):
        self.apk.write_bytes(self.apk.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'unsigned APK differs'):
            self.call_handoff()

    def test_handoff_requires_version_metadata(self):
        (self.root / 'release/.version').unlink()
        with self.assertRaisesRegex(ValueError, 'missing or symlinked input'):
            self.call_handoff()


class PlaceContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.h = Harness(self.temp.name)
        self.root = self.h.root

    def tearDown(self):
        self.temp.cleanup()

    def stage(self, add_targets=None):
        stage = self.root / 'handoff'
        (stage / 'release').mkdir(parents=True, exist_ok=True)
        write_zip(stage / 'release' / APK_NAME, payload_rows())
        (stage / 'build-evidence').mkdir(parents=True, exist_ok=True)
        (stage / 'build-evidence' / (IDENT + '.json')).write_text(json.dumps(
            {'inputs': {'winner': 'winner'}}), encoding='utf-8')
        if add_targets is not None:
            (stage / 'src').mkdir(parents=True, exist_ok=True)
            (stage / 'src/targets.json').write_text(add_targets, encoding='utf-8')
        return stage

    def test_place_refuses_unexpected_file(self):
        stage = self.stage()
        (stage / 'unexpected.bin').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'unexpected file'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')

    def test_place_refuses_symlink(self):
        stage = self.stage()
        (stage / 'release' / 'linked.apk').symlink_to(stage / 'release' / APK_NAME)
        with self.assertRaisesRegex(ValueError, 'unexpected file'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')

    def test_place_refuses_existing_release_folder(self):
        self.stage()
        (self.root / 'release').mkdir()
        with self.assertRaisesRegex(ValueError, 'release already exists'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')

    def test_place_refuses_unrecognized_carried_targets_view(self):
        self.stage('[]\n')
        with self.assertRaisesRegex(ValueError, 'neither the checkout nor the winning candidate view'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')

    def test_place_accepts_exact_winner_view(self):
        original = (self.root / 'src/targets.json').read_text()
        view = build_attempts.view_text(original, IDENT, 'winner')
        stage = self.stage(view)
        quiet_call(sign_apk.place, self.root, IDENT, 'handoff')
        self.assertEqual((self.root / 'src/targets.json').read_text(), view)
        self.assertFalse(stage.exists())
        self.assertTrue((self.root / 'release' / APK_NAME).is_file())


class VerifyContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.h = Harness(self.temp.name)
        self.root = self.h.root

    def tearDown(self):
        self.temp.cleanup()

    def pair(self, **extra):
        unsigned, signed, report = self.h.create_verify_pair()
        env = self.h.env(**extra)
        return unsigned, signed, report, env

    def refuses(self, **extra):
        _, _, _, env = self.pair(**extra)
        with self.assertRaises(ValueError):
            verify_with_env(self.root, env)

    def test_verify_refuses_keystore_environment(self):
        self.refuses(KEYSTORE_PASS='must-not-be-present')

    def test_verify_refuses_keystore_file(self):
        self.pair()
        (self.root / 'src/ks.keystore').write_bytes(b'still here')
        with self.assertRaisesRegex(ValueError, 'keystore still present'):
            verify_with_env(self.root, self.h.env())

    def test_verify_refuses_second_signer(self):
        self.refuses(FAKE_SIGNERS='2')

    def test_verify_refuses_wrong_certificate(self):
        self.refuses(FAKE_CERT='c' * 64)

    def test_verify_refuses_v1_when_sdk_24_requires_v2_only(self):
        self.refuses(FAKE_SCHEMES='v1=true,v2=true,v3=false,v3.1=false,v4=false')

    def test_verify_refuses_v4(self):
        self.refuses(FAKE_SCHEMES='v1=false,v2=true,v3=false,v3.1=false,v4=true')

    def test_verify_refuses_changed_non_signature_entry(self):
        rows = payload_rows()
        rows[0] = (rows[0][0], b'tampered dex')
        self.h.create_verify_pair(signed_rows=rows)
        with self.assertRaisesRegex(ValueError, 'changed entry bytes'):
            verify_with_env(self.root, self.h.env())

    def test_verify_refuses_added_non_signature_entry(self):
        rows = payload_rows() + [('assets/added.bin', b'added')]
        self.h.create_verify_pair(signed_rows=rows)
        with self.assertRaisesRegex(ValueError, 'added or removed a non-signature entry'):
            verify_with_env(self.root, self.h.env())

    def test_verify_accepts_directory_and_source_stamp_entries_the_signer_drops(self):
        # W15g live smokes 31 Oct: apksigner 37 left out stamp-cert-sha256 (12 apps) and
        # directory entries (mxplayer lib/, instagram assets/); 13 of 17 stopped on this.
        unsigned = [('lib/', b''), ('lib/arm64-v8a/', b'')] + payload_rows() + [('stamp-cert-sha256', b'stamp digest')]
        self.h.create_verify_pair(unsigned_rows=unsigned)
        report = verify_with_env(self.root, self.h.env())
        self.assertEqual(report['signing']['dropped_by_signer'], ['lib/', 'lib/arm64-v8a/', 'stamp-cert-sha256'])
        self.assertEqual(report['signing']['entries_compared'], 3)

    def test_verify_refuses_source_stamp_written_by_signing(self):
        self.h.create_verify_pair(signed_rows=payload_rows() + [('stamp-cert-sha256', b'new stamp')])
        with self.assertRaisesRegex(ValueError, 'directory or source-stamp entry: stamp-cert-sha256'):
            verify_with_env(self.root, self.h.env())

    def test_verify_refuses_directory_written_by_signing(self):
        self.h.create_verify_pair(signed_rows=[('assets/', b'')] + payload_rows())
        with self.assertRaisesRegex(ValueError, 'directory or source-stamp entry: assets/'):
            verify_with_env(self.root, self.h.env())

    def test_verify_names_a_removed_payload_entry(self):
        self.h.create_verify_pair(signed_rows=payload_rows()[1:])
        with self.assertRaisesRegex(ValueError, r'removed: classes[.]dex; added: none'):
            verify_with_env(self.root, self.h.env())

    def test_only_the_root_source_stamp_file_may_disappear(self):
        unsigned = payload_rows() + [('assets/stamp-cert-sha256', b'app data'), ('res/raw/timestamp.proto', b'proto')]
        self.h.create_verify_pair(unsigned_rows=unsigned, signed_rows=payload_rows() + [('res/raw/timestamp.proto', b'proto')])
        with self.assertRaisesRegex(ValueError, 'removed: assets/stamp-cert-sha256'):
            verify_with_env(self.root, self.h.env())

    def test_verify_refuses_reordered_non_signature_entries(self):
        names = [name for name, _ in reversed(payload_rows())]
        self.h.create_verify_pair(signed_order=names)
        with self.assertRaisesRegex(ValueError, 'reordered entries'):
            verify_with_env(self.root, self.h.env())

    def test_verify_refuses_lost_16k_native_alignment(self):
        unsigned = self.root / 'signing' / APK_NAME
        release = self.root / 'release' / APK_NAME
        write_zip(unsigned, payload_rows(), page_align_so=True)
        write_zip(release, payload_rows(), page_align_so=False)
        add_signatures(release)
        report = {'schema': ai.SCHEMA, 'status': 'unsigned', 'signing_split': True, 'target': IDENT,
                  'inputs': {'expected_certificate_sha256': PIN},
                  'output': {'path': 'release/' + APK_NAME, 'bytes': unsigned.stat().st_size,
                             'sha256': ai.sha(unsigned)},
                  'manifest': {'package': META['package'], 'version_code': META['version_code'],
                               'version_name': META['version_name'], 'min_sdk': 24},
                  'unsigned': {'binding': {'run_id': RUN_ENV['GITHUB_RUN_ID'],
                                          'run_attempt': RUN_ENV['GITHUB_RUN_ATTEMPT']},
                              'signature_files_present': []}}
        evidence = self.root / 'build-evidence' / (IDENT + '.json')
        evidence.parent.mkdir(parents=True)
        evidence.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'lost 16 KiB native library alignment'):
            verify_with_env(self.root, self.h.env())

    def test_verify_refuses_zipalign_failure(self):
        self.refuses(FAKE_ZIPALIGN_EXIT='1')

    def test_verify_accepts_signed_apk_and_writes_release_contract_fields(self):
        _, _, _, env = self.pair()
        report = verify_with_env(self.root, env)
        self.assertEqual(report['status'], 'verified')
        self.assertTrue(report['signing_split'])
        self.assertEqual(report['signature']['certificate_sha256'], PIN)
        self.assertEqual(report['signature']['cryptographic_verification'], 'passed')
        self.assertEqual(report['signing']['binding'], {'run_id': RUN_ENV['GITHUB_RUN_ID'],
                                                        'run_attempt': RUN_ENV['GITHUB_RUN_ATTEMPT']})
        self.assertEqual(report['signing']['pin'], PIN)
        self.assertGreater(report['signing']['entries_compared'], 0)
        self.assertTrue(report['signing']['schemes']['v2'])
        self.assertFalse(report['signing']['schemes']['v4'])
        self.assertNotEqual(report['unsigned_output']['sha256'], report['output']['sha256'])
        saved = json.loads((self.root / 'build-evidence' / (IDENT + '.json')).read_text())
        self.assertEqual(saved, report)


class WorkflowContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / '.github/workflows/manual-patch.yml'
        try:
            import yaml  # Actions runners ship PyYAML
            cls.workflow = yaml.safe_load(path.read_text())
            return
        except ImportError:
            pass
        # Assistant sandbox without PyYAML: a bundled js-yaml, else skip (workflow_yaml_contracts style).
        env = dict(os.environ)
        env['NODE_PATH'] = '/opt/sd-artifact/node_modules' + os.pathsep + env.get('NODE_PATH', '')
        script = ("const fs=require('fs'), y=require('js-yaml'); "
                  "process.stdout.write(JSON.stringify(y.load(fs.readFileSync(process.argv[1],'utf8'))));")
        try:
            result = subprocess.run(['node', '-e', script, str(path)], cwd=ROOT, env=env,
                                    capture_output=True, text=True, check=True, timeout=10)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            raise unittest.SkipTest('no YAML parser available')
        cls.workflow = json.loads(result.stdout)

    def test_patch_has_read_only_permissions_and_no_signing_secret(self):
        patch = self.workflow['jobs']['patch']
        self.assertEqual(patch.get('permissions'), {'contents': 'read'})
        # The only secret in the patch job is the VirusTotal lookup key, in the
        # nonpublishing scan step alone (W16y-b); never a signing secret.
        holders = [(step.get('name'), re.findall(r'secrets[.]([A-Z_]+)', json.dumps(step)))
                   for step in patch['steps'] if 'secrets.' in json.dumps(step)]
        self.assertEqual(holders, [('Run provider safety scan', ['VT_API_KEY'])])
        scan = next(step for step in patch['steps'] if step.get('name') == 'Run provider safety scan')
        self.assertIn('!inputs.publish', scan.get('if', ''))
        self.assertNotIn('KEYSTORE', json.dumps(patch))

    def test_keystore_secrets_are_only_in_sign_decode_and_sign_steps(self):
        references = []
        for job_name, job in self.workflow['jobs'].items():
            for step in job.get('steps', []):
                if 'secrets.KEYSTORE_' in json.dumps(step):
                    references.append((job_name, step.get('name')))
        self.assertEqual(references, [('sign', 'Decode keystore'), ('sign', 'Sign APK')])

    def test_publish_is_write_only_job_without_keystore_secret(self):
        publish = self.workflow['jobs']['publish']
        self.assertEqual(publish['permissions']['contents'], 'write')
        self.assertNotIn('secrets.KEYSTORE', json.dumps(publish))

    def test_handoff_artifacts_are_run_scoped_and_keep_hidden_files(self):
        expected = {'patch-output-', 'signed-output-'}
        found = set()
        for job in self.workflow['jobs'].values():
            for step in job.get('steps', []):
                if 'actions/upload-artifact@' not in step.get('uses', ''):
                    continue
                name = step.get('with', {}).get('name', '')
                if name.startswith(tuple(expected)):
                    found.add(name.split('${{', 1)[0])
                    self.assertIn('${{ github.run_id }}', name)
                    self.assertIn('${{ github.run_attempt }}', name)
                    self.assertIs(step['with'].get('include-hidden-files'), True)
        self.assertEqual(found, expected)

    def test_interjob_downloads_fail_on_digest_mismatch(self):
        downloads = []
        for job_name, job in self.workflow['jobs'].items():
            for step in job.get('steps', []):
                if 'actions/download-artifact@' in step.get('uses', ''):
                    downloads.append((job_name, step.get('name'), step.get('with', {}).get('digest-mismatch')))
        self.assertTrue(downloads)
        self.assertTrue(all(setting == 'error' for _, _, setting in downloads), downloads)

    def test_keystore_cleanup_and_publish_gate(self):
        sign = self.workflow['jobs']['sign']
        remove = next(step for step in sign['steps'] if step.get('name') == 'Remove keystore')
        self.assertEqual(remove.get('if'), 'always()')
        publish = self.workflow['jobs']['publish']
        gate = publish.get('if', '')
        self.assertIn('inputs.publish', gate)
        self.assertIn("github.ref == 'refs/heads/main'", gate)




class SchemeStrictness(unittest.TestCase):
    def test_unknown_or_v32_true_scheme_lines_refused(self):
        base = ('Verified using v1 scheme (JAR signing): false\n'
                'Verified using v2 scheme (APK Signature Scheme v2): true\n'
                'Verified using v3 scheme (APK Signature Scheme v3): false\n')
        self.assertEqual(sign_apk.parse_schemes(base + 'Verified using v3.2 scheme (APK Signature Scheme v3.2): false\n'),
                         sign_apk.expected_schemes(24))
        self.assertNotEqual(sign_apk.parse_schemes(base + 'Verified using v3.2 scheme (APK Signature Scheme v3.2): true\n'),
                            sign_apk.expected_schemes(24))
        with self.assertRaises(ValueError):
            sign_apk.parse_schemes(base + 'Verified using v5 scheme (APK Signature Scheme v5): false\n')

    def test_signature_file_names_case_insensitive(self):
        import artifact_identity as ai
        for name in ('META-INF/CERT.RSA', 'META-INF/other.rsa', 'META-INF/x.Sf', 'META-INF/SIG-old', 'META-INF/MANIFEST.MF'):
            self.assertTrue(ai.SIGNATURE_FILE.fullmatch(name), name)
        for name in ('META-INF/services/x', 'META-INF/a/b.RSA', 'lib/arm64-v8a/x.so'):
            self.assertFalse(ai.SIGNATURE_FILE.fullmatch(name), name)


class PatcherProbe(unittest.TestCase):
    """W15g: --unsigned support comes from help text or the jar's PatchCommand class."""
    def setUp(self):
        sys.path.insert(0, str(ROOT / 'src/build'))
        import patcher_probe
        self.probe = patcher_probe
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def jar(self, body):
        path = Path(self.tmp.name) / 'morphe-desktop-1.20.0-all.jar'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('app/morphe/desktop/command/PatchCommand.class', body)
        return str(path)

    def test_help_or_class_evidence(self):
        self.assertEqual(self.probe.supports(self.jar(b'x'), 'Usage: patch [-f] [--unsigned] ...'), 'help')
        self.assertEqual(self.probe.supports(self.jar(b'..\x01\x00\x0a--unsigned\x01\x00\x20Disable signing'), "Unknown option: '--help'"), 'class')
        self.assertIsNone(self.probe.supports(self.jar(b'\x01\x00\x0b--unsignedx'), 'Unknown option: --unsigned-not'))
        self.assertIsNone(self.probe.supports(str(Path(self.tmp.name) / 'missing.jar'), ''))

    def test_build_sh_uses_the_probe_before_patching(self):
        text = (ROOT / 'src/build/build.sh').read_text()
        self.assertLess(text.index('patcher_probe.py'), text.index('python3 src/build/patch_target.py'))
        self.assertIn('UNSIGNED_UNSUPPORTED', text)



if __name__ == '__main__':
    unittest.main()
