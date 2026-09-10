import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import artifact_identity as identity
import native_payloads


class Identity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pf-identity-')
        self.r = pathlib.Path(self.temp.name).resolve()
        shutil.copytree(ROOT / 'src', self.r / 'src')
        shutil.copytree(ROOT / 'docs', self.r / 'docs')
        (self.r / 'release').mkdir()
        (self.r / 'download').mkdir()
        (self.r / 'extra').mkdir()
        self.env = {**os.environ, 'ANDROID_HOME': str(self.r / 'sdk'), 'KEYSTORE_PASS': 'fixture password', 'KEYSTORE_ALIAS': 'fixture'}
        self.cert = b'0' + b'certificate-fixture' * 20
        self.fingerprint = hashlib.sha256(self.cert).hexdigest()
        self.meta = {'package': 'io.github.sds100.keymapper', 'version_code': '42', 'version_name': '4.2.1', 'min_sdk': 29, 'reader': 'fixture'}

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, b):
        p = self.r / name;p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b if isinstance(b, bytes) else b.encode())
        return p

    def tool(self, name, text):
        p = self.put('sdk/build-tools/35.0.0/' + name, '#!/bin/bash\n' + text + '\n')
        p.chmod(0o755)
        return str(p)

    def apk(self, entries=None):
        p = self.r / 'release/key-mapper-v4.2.1-arm64-v8a.apk'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('AndroidManifest.xml', b'fixture')
            z.writestr('classes.dex', b'd' * 1000100)
            for name, value in (entries or {}).items():z.writestr(name, value)
        return p

    def elf(self, machine=183, kind=2):
        h = bytearray(64);h[:4] = b'\x7fELF';h[4] = kind;h[5] = 1;h[18:20] = machine.to_bytes(2, 'little');return bytes(h)

    def capture_fixture(self):
        for name in ('morphe-desktop-fixture.jar', 'APKEditor.jar', 'pup', '09-lain.mpp', 'download/key-mapper.apk', 'src/ks.keystore'):
            self.put(name, 'fixture')
        self.put('.requested', 'lain\tUnlock Premium\n')
        for args in (['git','init','-q'], ['git','config','user.name','Fixture'], ['git','config','user.email','fixture@example.invalid'],
                     ['git','add','src/targets.json','src/build/artifact_identity.py','docs/obtainium-govind.json'], ['git','commit','-qm','fixture']):
            subprocess.run(args, cwd=self.r, check=True, capture_output=True)
        with patch.object(identity, 'cert_from_keystore', return_value=self.fingerprint), contextlib.redirect_stdout(io.StringIO()):
            identity.capture_signer(self.r, self.env)
            identity.capture_inputs(self.r, 'keymapper', 'lain', self.env)
        self.put('release/.version', '4.2.1\n');self.put('release/.applied', '- Unlock Premium\n')
        self.apk()
        return json.loads((self.r / '.build-inputs.json').read_text())

    def verify_fixture(self):
        with patch.object(identity, 'cert_from_keystore', return_value=self.fingerprint), \
             patch.object(identity, 'metadata', return_value=self.meta), \
             patch.object(identity, 'apk_signer', return_value={'certificate_sha256':self.fingerprint, 'verifier':'fixture','cryptographic_verification':'passed'}), \
             contextlib.redirect_stdout(io.StringIO()):
            return identity.verify_final(self.r, 'keymapper', self.env)

    def test_complete_fixture_capture_and_verify(self):
        captured = self.capture_fixture();report = self.verify_fixture()
        self.assertEqual(report['status'], 'verified')
        self.assertEqual(report['signature']['certificate_sha256'], self.fingerprint)
        self.assertEqual(report['architecture']['classification'], 'no-native-libraries')
        self.assertTrue((self.r / 'build-evidence/keymapper.json').exists())
        self.assertNotIn('fixture password', json.dumps(report))
        self.assertNotIn('src/ks.keystore', [x['path'] for x in captured['repository_files']])

    def test_same_runner_limit_is_explicit(self):
        self.capture_fixture();report = self.verify_fixture()
        self.assertIn('not a signed independent', report['attestation'])
        self.assertIn('not checked', report['historical_signer_continuity'])

    def test_changed_input_rejected(self):
        self.capture_fixture();self.put('download/key-mapper.apk','changed')
        with self.assertRaisesRegex(ValueError, 'input changed'):self.verify_fixture()

    def test_changed_tracked_source_rejected(self):
        self.capture_fixture();self.put('src/targets.json','[]')
        with self.assertRaisesRegex(ValueError, 'input changed'):self.verify_fixture()

    def test_changed_bundle_rejected(self):
        self.capture_fixture();self.put('09-lain.mpp','changed')
        with self.assertRaisesRegex(ValueError, 'input changed'):self.verify_fixture()

    def test_changed_patcher_rejected(self):
        self.capture_fixture();self.put('morphe-desktop-fixture.jar','changed')
        with self.assertRaisesRegex(ValueError, 'input changed'):self.verify_fixture()

    def test_changed_request_ledger_rejected(self):
        self.capture_fixture();self.put('.requested','changed')
        with self.assertRaisesRegex(ValueError, 'input changed'):self.verify_fixture()

    def test_wrong_target_capture_rejected(self):
        self.capture_fixture();p=self.r/'.build-inputs.json';d=json.loads(p.read_text());d['target']='photos';p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, 'target/schema'):self.verify_fixture()

    def test_signer_capture_reuse_rejected(self):
        self.put('.signer-before-build.json','{}')
        with self.assertRaises(ValueError):identity.capture_signer(self.r,self.env)

    def test_two_signers_rejected(self):
        with self.assertRaises(ValueError):identity.parse_signers('Signer #1 certificate SHA-256 digest: '+self.fingerprint+'\nSigner #2 certificate SHA-256 digest: '+self.fingerprint)

    def test_valid_signer_parser(self):
        self.assertEqual(identity.parse_signers('Verifies\nSigner #1 certificate SHA-256 digest: '+self.fingerprint+'\nSigner #1 public key SHA-256 digest: '+'b'*64+'\n'),self.fingerprint)

    def test_colon_separated_fingerprint(self):
        text=':'.join(self.fingerprint[i:i+2].upper() for i in range(0,64,2))
        self.assertEqual(identity.parse_signers('Signer #1 certificate SHA-256 digest: '+text),self.fingerprint)

    def test_missing_signer_rejected(self):
        with self.assertRaises(ValueError):identity.parse_signers('Verifies')

    def test_public_key_digest_not_certificate(self):
        with self.assertRaises(ValueError):identity.parse_signers('Signer #1 public key SHA-256 digest: '+self.fingerprint)

    def test_invalid_signer_digest_rejected(self):
        with self.assertRaises(ValueError):identity.parse_signers('Signer #1 certificate SHA-256 digest: abcdef')

    def test_signature_verification_failure_not_fallback(self):
        self.tool('apksigner', 'exit 1')
        with self.assertRaisesRegex(ValueError,'apksigner failed'):identity.apk_signer(self.r,self.apk(),self.env)

    def test_signature_success_fixture(self):
        self.tool('apksigner', "echo 'Signer #1 certificate SHA-256 digest: "+self.fingerprint+"'")
        self.assertEqual(identity.apk_signer(self.r,self.apk(),self.env)['certificate_sha256'],self.fingerprint)

    def test_no_verifier_rejected(self):
        with patch.object(identity, 'sdk_tools', return_value=[]):
            with self.assertRaises(ValueError):identity.apk_signer(self.r,self.apk(),self.env)

    def test_native_arm64(self):
        self.assertEqual(identity.native_architecture(self.apk({'lib/arm64-v8a/libtest.so':self.elf()}))['classification'],'arm64-v8a')

    def test_native_wrong_directory(self):
        with self.assertRaises(ValueError):identity.native_architecture(self.apk({'lib/x86/libtest.so':self.elf(3)}))

    def test_native_wrong_elf_machine(self):
        with self.assertRaises(ValueError):identity.native_architecture(self.apk({'lib/arm64-v8a/libtest.so':self.elf(62)}))

    def test_native_wrong_elf_class(self):
        with self.assertRaises(ValueError):identity.native_architecture(self.apk({'lib/arm64-v8a/libtest.so':self.elf(183,1)}))

    def test_native_invalid_elf(self):
        with self.assertRaises(ValueError):identity.native_architecture(self.apk({'lib/arm64-v8a/libtest.so':b'bad'}))

    def test_no_native_is_explicit(self):
        self.assertEqual(identity.native_architecture(self.apk())['classification'],'no-native-libraries')

    def test_parse_badging(self):
        text="package: name='com.fixture' versionCode='42' versionName='1.2' platformBuildVersionName=''\nsdkVersion:'29'\n"
        self.assertEqual(identity.parse_badging(text)['min_sdk'],29)

    def test_badging_missing_sdk_rejected(self):
        with self.assertRaises(ValueError):identity.parse_badging("package: name='com.fixture' versionCode='1' versionName='1'")

    def test_parse_xml(self):
        text='<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.fixture" android:versionCode="42" android:versionName="1.2"><uses-sdk android:minSdkVersion="29"/></manifest>'
        self.assertEqual(identity.parse_manifest(text)['package'],'com.fixture')

    def test_output_package_mapping_matches_current_imports(self):
        targets=json.loads((self.r/'src/targets.json').read_text())
        for t in targets:
            expected={'youtube':'app.morphe.android.youtube','photos':'app.morphe.android.apps.photos'}.get(t['id'],t['package'])
            self.assertEqual(identity.expected_package(self.r,t),expected)

    def test_ambiguous_output_package_rejected(self):
        p=self.r/'docs/obtainium-govind.json';d=json.loads(p.read_text());d['apps'] += copy.deepcopy(d['apps']);p.write_text(json.dumps(d))
        with self.assertRaises(ValueError):identity.expected_package(self.r,identity.target(self.r,'youtube'))

    def identity_args(self):
        return [dict(self.meta),{'classification':'arm64-v8a'}, {'certificate_sha256':self.fingerprint},
                {'expected_package':self.meta['package'],'expected_certificate_sha256':self.fingerprint,'sdk_ceiling':29}, '4.2.1']

    def test_identity_correct(self):identity.validate_identity(*self.identity_args())

    def test_identity_wrong_package(self):
        args=self.identity_args();args[0]['package']='com.wrong'
        with self.assertRaises(ValueError):identity.validate_identity(*args)

    def test_identity_wrong_signer(self):
        args=self.identity_args();args[2]['certificate_sha256']='a'*64
        with self.assertRaises(ValueError):identity.validate_identity(*args)

    def test_identity_wrong_version(self):
        args=self.identity_args();args[0]['version_name']='99'
        with self.assertRaises(ValueError):identity.validate_identity(*args)

    def test_identity_excessive_sdk(self):
        args=self.identity_args();args[0]['min_sdk']=30
        with self.assertRaises(ValueError):identity.validate_identity(*args)

    def test_identity_wrong_arch(self):
        args=self.identity_args();args[1]['classification']='x86'
        with self.assertRaises(ValueError):identity.validate_identity(*args)

    def test_raw_keystore_certificate_hash(self):
        with patch.object(identity.shutil,'which',return_value='/fixture/keytool'), patch.object(identity,'command',return_value=self.cert) as mocked:
            self.assertEqual(identity.cert_from_keystore(self.r,self.env),self.fingerprint)
            argv=mocked.call_args[0][0]
            self.assertIn('-storepass:env',argv);self.assertNotIn(self.env['KEYSTORE_PASS'],argv)

    def test_invalid_der_rejected(self):
        with patch.object(identity.shutil,'which',return_value='/fixture/keytool'), patch.object(identity,'command',return_value=b'error'):
            with self.assertRaises(ValueError):identity.cert_from_keystore(self.r,self.env)

    def test_symlink_input_rejected(self):
        p=self.put('source','fixture');(self.r/'alias').symlink_to(p)
        with self.assertRaises(ValueError):identity.record(self.r,'alias')

    def test_workflow_verifies_before_release(self):
        s=(ROOT/'.github/workflows/manual-patch.yml').read_text()
        self.assertLess(s.index('Verify finished APK identity'),s.index('Releasing APK files'))
        self.assertLess(s.index('Save build evidence (JSON only)'),s.index('Releasing APK files'))
        self.assertIn('path: build-evidence/*.json',s)
        self.assertIn('if-no-files-found: error',s)

    def test_capture_precedes_patcher(self):
        s=(ROOT/'src/build/build.sh').read_text()
        self.assertLess(s.index('capture-signer'),s.index('source ./src/build/utils.sh'))
        self.assertLess(s.index('capture-inputs'),s.index('python3 src/build/patch_target.py'))

    def observed_output(self):
        # User-provided stdout from SDK 37.0.0, run 34453111340. DN masking
        # retained as supplied; the certificate digest and labels are verbatim.
        return (ROOT / 'tests/fixtures/apksigner-37-keymapper.txt').read_text()

    def test_observed_sdk37_format(self):
        self.assertEqual(identity.parse_signers(self.observed_output()),
                         '08480f6649a2be33ff3cccacce07454761d5fb9abe65f1e2caeeb782e382d050')

    def test_scheme_count_two_rejected(self):
        with self.assertRaises(ValueError):
            identity.parse_signers(self.observed_output().replace('Number of signers: 1', 'Number of signers: 2'))

    def test_scheme_missing_count_rejected(self):
        with self.assertRaises(ValueError):
            identity.parse_signers(self.observed_output().replace('Number of signers: 1\n', ''))

    def test_scheme_duplicate_certificate_rejected(self):
        with self.assertRaises(ValueError):
            identity.parse_signers(self.observed_output() + 'V3.0 Signer: certificate SHA-256 digest: ' + 'a' * 64 + '\n')

    def test_mixed_certificate_labels_rejected(self):
        with self.assertRaises(ValueError):
            identity.parse_signers(self.observed_output() + 'Signer #1 certificate SHA-256 digest: ' + 'a' * 64 + '\n')

    def test_unknown_scheme_identity_rejected(self):
        with self.assertRaises(ValueError):
            identity.parse_signers(self.observed_output() + 'V9.0 Signer: certificate SHA-256 digest: ' + 'a' * 64 + '\n')

    def test_legacy_declared_count_two_rejected(self):
        with self.assertRaises(ValueError):
            identity.parse_signers('Number of signers: 2\nSigner #1 certificate SHA-256 digest: ' + self.fingerprint)

    def test_nonelf_still_rejected_with_header_evidence(self):
        apk = self.apk({'lib/arm64-v8a/fixture.zip.so': b'PK\x03\x04fixture'})
        source = self.r / 'source.apk'
        shutil.copy(apk, source)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(ValueError):
            identity.native_architecture(apk, source)
        output = json.loads(buf.getvalue().split('NATIVE_MEMBER_DIAGNOSTIC ', 1)[1].splitlines()[0])
        self.assertEqual(output['input_header_hex'], output['output_header_hex'])
        self.assertTrue(output['output_header_hex'].startswith('504b0304'))
        self.assertEqual(output['policy'], 'still rejected; classification needs evidence')

    def zip_bytes(self, entries):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as z:
            for name, data in entries:
                z.writestr(name, data)
        return out.getvalue()

    def preserved_payload(self, payload, name='lib/arm64-v8a/data.so'):
        apk = self.apk({'lib/arm64-v8a/libreal.so': self.elf(), name: payload})
        source = self.r / 'source.apk'
        shutil.copy(apk, source)
        return apk, source

    def test_observed_three_byte_text_preserved(self):
        apk, source = self.preserved_payload(bytes.fromhex('312e30'), 'lib/arm64-v8a/libAIVSecureRenderer.so')
        result = identity.native_architecture(apk, source)
        evidence = result['packaged_data'][0]
        self.assertEqual(evidence['format'], 'literal-text-1.0')
        self.assertEqual(evidence['input_sha256'], evidence['output_sha256'])
        self.assertEqual(result['direct_arm64_elf_count'], 1)

    def test_valid_zip_preserved_and_inspected(self):
        payload = self.zip_bytes([('assets/data.txt', b'resource'), ('binary', self.elf())])
        apk, source = self.preserved_payload(payload, 'lib/arm64-v8a/libassets.zip.so')
        result = identity.native_architecture(apk, source)
        evidence = result['packaged_data'][0]
        self.assertEqual(evidence['format'], 'validated-zip')
        self.assertEqual(evidence['archive_inspection']['visible_arm64_elf_members'], 1)
        self.assertEqual(evidence['archive_inspection']['other_data_members'], 1)

    def test_matching_header_size_not_enough(self):
        original = self.zip_bytes([('data.txt', b'AAAA')])
        changed = self.zip_bytes([('data.txt', b'BBBB')])
        apk, source = self.preserved_payload(original)
        self.apk({'lib/arm64-v8a/libreal.so': self.elf(), 'lib/arm64-v8a/data.so': changed})
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            identity.native_architecture(apk, source)

    def test_text_changed_from_input_rejected(self):
        apk, source = self.preserved_payload(b'1.0')
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('lib/arm64-v8a/data.so', b'2.0')
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            identity.native_architecture(apk, source)

    def test_known_filename_not_a_pass(self):
        apk, source = self.preserved_payload(b'unknown', 'lib/arm64-v8a/libAIVSecureRenderer.so')
        with self.assertRaisesRegex(ValueError, 'unclassified'):
            identity.native_architecture(apk, source)

    def test_preserved_data_without_input_rejected(self):
        apk, _ = self.preserved_payload(b'1.0')
        with self.assertRaises(ValueError):
            identity.native_architecture(apk)

    def test_data_only_is_not_arm64_proof(self):
        apk = self.apk({'lib/arm64-v8a/data.so': b'1.0'})
        source = self.r / 'source.apk';shutil.copy(apk, source)
        with self.assertRaisesRegex(ValueError, 'no direct arm64 ELF'):
            identity.native_architecture(apk, source)

    def test_x86_elf_inside_preserved_zip_rejected(self):
        apk, source = self.preserved_payload(self.zip_bytes([('hidden.bin', self.elf(62))]))
        with self.assertRaisesRegex(ValueError, 'not ELF64 AArch64'):
            identity.native_architecture(apk, source)

    def test_x86_elf_wrong_suffix_rejected(self):
        apk = self.apk({'lib/arm64-v8a/not-a-so.dat': self.elf(62)})
        with self.assertRaises(ValueError):
            identity.native_architecture(apk)

    def test_nested_zip_inspected(self):
        payload = self.zip_bytes([('inner.zip', self.zip_bytes([('real', self.elf())]))])
        apk, source = self.preserved_payload(payload)
        result = identity.native_architecture(apk, source)
        self.assertEqual(result['packaged_data'][0]['archive_inspection']['nested_zip_archives'], 1)

    def test_nested_x86_zip_rejected(self):
        payload = self.zip_bytes([('inner.zip', self.zip_bytes([('wrong', self.elf(3))]))])
        apk, source = self.preserved_payload(payload)
        with self.assertRaises(ValueError):
            identity.native_architecture(apk, source)

    def test_zip_crc_failure_rejected(self):
        payload = self.zip_bytes([('data', b'UNIQUE-CONTENT')]).replace(b'UNIQUE-CONTENT', b'BROKEN-CONTENT')
        apk, source = self.preserved_payload(payload)
        with self.assertRaises(ValueError):
            identity.native_architecture(apk, source)

    def test_zip_duplicate_entries_rejected(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            payload = self.zip_bytes([('same', b'a'), ('same', b'b')])
        apk, source = self.preserved_payload(payload)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            identity.native_architecture(apk, source)

    def test_zip_traversal_rejected(self):
        apk, source = self.preserved_payload(self.zip_bytes([('../outside', b'a')]))
        with self.assertRaisesRegex(ValueError, 'traversal'):
            identity.native_architecture(apk, source)

    def test_zip_expansion_limit_rejected(self):
        apk, source = self.preserved_payload(self.zip_bytes([('large', b'x' * 100)]))
        with patch.object(native_payloads, 'MAX_EXPANDED_BYTES', 50), self.assertRaisesRegex(ValueError, 'expansion'):
            identity.native_architecture(apk, source)

    def test_nested_zip_depth_limit_rejected(self):
        payload = self.zip_bytes([('inner', self.zip_bytes([('data', b'a')]))])
        apk, source = self.preserved_payload(payload)
        with patch.object(native_payloads, 'MAX_DEPTH', 0), self.assertRaisesRegex(ValueError, 'nesting'):
            identity.native_architecture(apk, source)

    def test_packaged_zip_report_does_not_claim_opaque_abi(self):
        apk, source = self.preserved_payload(self.zip_bytes([('compressed.bin', b'\xfd7zXZ\x00opaque')]))
        result = identity.native_architecture(apk, source)
        self.assertIn('not ABI-certified', result['scope'])
        self.assertEqual(result['packaged_data'][0]['archive_inspection']['other_data_members'], 1)

    def test_observed_release_text_preserved(self):
        apk, source = self.preserved_payload(b'release=452', 'lib/arm64-v8a/libInit.so')
        result = identity.native_architecture(apk, source)
        self.assertEqual(result['packaged_data'][0]['format'], 'literal-text-release-452')

    def test_other_release_text_still_rejected(self):
        apk, source = self.preserved_payload(b'release=453', 'lib/arm64-v8a/libInit.so')
        with self.assertRaises(ValueError):
            identity.native_architecture(apk, source)

    def test_all_unknown_data_members_are_reported(self):
        apk = self.apk({'lib/arm64-v8a/libreal.so': self.elf(),
                        'lib/arm64-v8a/first.so': b'unknown1', 'lib/arm64-v8a/second.so': b'unknown2'})
        source = self.r / 'source.apk';shutil.copy(apk, source)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), self.assertRaises(ValueError):
            identity.native_architecture(apk, source)
        summary = json.loads(buffer.getvalue().split('NATIVE_SCAN_SUMMARY ', 1)[1])
        self.assertEqual(len(summary['unclassified']), 2)


if __name__=='__main__':unittest.main()
