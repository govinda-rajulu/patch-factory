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
import release_contract
import input_recipe


class Identity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pf-identity-')
        self.r = pathlib.Path(self.temp.name).resolve()
        shutil.copytree(ROOT / 'src', self.r / 'src')
        shutil.copytree(ROOT / 'docs', self.r / 'docs')
        shutil.copytree(ROOT / '.github', self.r / '.github')
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


class DexContainerTests(unittest.TestCase):
    """Synthetic structural fixtures, NOT the Facebook DEX from the CI log."""
    @staticmethod
    def seal(blob):
        import struct
        import zlib
        blob = bytearray(blob)
        blob[12:32] = hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I', blob, 8, zlib.adler32(blob[12:]))
        return bytes(blob)

    def fixture(self):
        import struct
        # Empty standard DEX: 112-byte header + 28-byte two-entry map.
        blob = bytearray(140)
        blob[:8] = b'dex\n038\0'
        struct.pack_into('<20I', blob, 32, 140, 112, 0x12345678, 0, 0, 112,
                         *([0]*12), 28, 112)
        struct.pack_into('<IHHIIHHII', blob, 112, 2, 0, 0, 1, 0, 0x1000, 0, 1, 112)
        return self.seal(blob)

    def changed(self, offset, value, fmt='<I'):
        import struct
        blob = bytearray(self.fixture())
        struct.pack_into(fmt, blob, offset, value)
        return self.seal(blob)

    def test_synthetic_container_checks(self):
        got = native_payloads.inspect_dex(self.fixture())
        self.assertEqual(got['version'], '038')
        self.assertTrue(got['adler32_verified'])
        self.assertTrue(got['sha1_verified'])
        self.assertFalse(got['bytecode_semantics_verified'])

    def test_documented_standard_versions(self):
        for version in (b'035', b'037', b'038', b'039', b'040'):
            blob = bytearray(self.fixture());blob[4:7] = version
            self.assertEqual(native_payloads.inspect_dex(self.seal(blob))['version'], version.decode())

    def test_observed_ci_header_alone_cannot_pass(self):
        # These 20 bytes, and only these, came from run 34457350435.
        with self.assertRaisesRegex(ValueError, 'size'):
            native_payloads.inspect_dex(bytes.fromhex('6465780a3033380041c672064730b32e77cbaa0a'))

    def test_checksum_bad(self):
        blob = bytearray(self.fixture());blob[8] ^= 1
        with self.assertRaisesRegex(ValueError, 'Adler'):
            native_payloads.inspect_dex(blob)

    def test_sha1_bad_even_with_correct_adler(self):
        import struct
        import zlib
        blob = bytearray(self.fixture());blob[12] ^= 1
        struct.pack_into('<I', blob, 8, zlib.adler32(blob[12:]))
        with self.assertRaisesRegex(ValueError, 'SHA-1'):
            native_payloads.inspect_dex(blob)

    def test_file_size_bad(self):
        with self.assertRaisesRegex(ValueError, 'size'):
            native_payloads.inspect_dex(self.changed(32, 144))

    def test_header_size_bad(self):
        with self.assertRaisesRegex(ValueError, 'size'):
            native_payloads.inspect_dex(self.changed(36, 120))

    def test_reverse_endian_rejected(self):
        with self.assertRaisesRegex(ValueError, 'endian'):
            native_payloads.inspect_dex(self.changed(40, 0x78563412))

    def test_future_container_rejected(self):
        blob = bytearray(self.fixture());blob[4:7] = b'041'
        with self.assertRaisesRegex(ValueError, 'version'):
            native_payloads.inspect_dex(self.seal(blob))

    def test_unknown_version_rejected(self):
        blob = bytearray(self.fixture());blob[4:7] = b'036'
        with self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.seal(blob))

    def test_trailing_bytes_rejected(self):
        with self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.fixture()+b'extra')

    def test_data_bounds_bad(self):
        with self.assertRaisesRegex(ValueError, 'data bounds'):
            native_payloads.inspect_dex(self.changed(104, 24))

    def test_linked_data_rejected(self):
        with self.assertRaisesRegex(ValueError, 'linked'):
            native_payloads.inspect_dex(self.changed(44, 4))

    def test_map_missing_rejected(self):
        with self.assertRaisesRegex(ValueError, 'map offset'):
            native_payloads.inspect_dex(self.changed(52, 0))

    def test_map_count_oversized(self):
        with self.assertRaisesRegex(ValueError, 'map length'):
            native_payloads.inspect_dex(self.changed(112, 100000))

    def test_map_reserved_nonzero(self):
        with self.assertRaisesRegex(ValueError, 'map type'):
            native_payloads.inspect_dex(self.changed(118, 1, '<H'))

    def test_map_unknown_kind(self):
        with self.assertRaisesRegex(ValueError, 'map type'):
            native_payloads.inspect_dex(self.changed(128, 0xffff, '<H'))

    def test_map_duplicate_kind(self):
        with self.assertRaisesRegex(ValueError, 'map type'):
            native_payloads.inspect_dex(self.changed(128, 0, '<H'))

    def test_map_self_offset_bad(self):
        with self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.changed(136, 116))

    def test_map_zero_count_bad(self):
        with self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.changed(132, 0))

    def test_header_map_mismatch(self):
        with self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.changed(120, 2))

    def test_header_pair_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'count/offset'):
            native_payloads.inspect_dex(self.changed(56, 1))

    def test_size_limit(self):
        with patch.object(native_payloads, 'MAX_MEMBER_BYTES', 120), self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.fixture())

    def archive(self, payload, name='lib/arm64-v8a/anything.so', elf=True):
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w') as z:
            z.writestr(name, payload)
            if elf:
                header = bytearray(20);header[:6] = b'\x7fELF\x02\x01';header[18:20] = (183).to_bytes(2, 'little')
                z.writestr('lib/arm64-v8a/real.so', header)
        result.seek(0)
        return result

    def test_full_native_path_reports_bytecode_not_elf(self):
        got = native_payloads.verify_native_payloads(self.archive(self.fixture()), self.archive(self.fixture()))
        item = got['packaged_data'][0]
        self.assertEqual(item['format'], 'dex-container-checked')
        self.assertTrue(item['executable_bytecode'])
        self.assertFalse(item['executable_elf'])
        self.assertEqual(item['input_sha256'], item['output_sha256'])
        self.assertEqual(got['direct_arm64_elf_count'], 1)

    def test_same_valid_dex_different_input_refused(self):
        blob = bytearray(self.fixture());blob[4:7] = b'039';other = self.seal(blob)
        with self.assertRaisesRegex(ValueError, 'bytes changed'):
            native_payloads.verify_native_payloads(self.archive(self.fixture()), self.archive(other))

    def test_dex_needs_input(self):
        with self.assertRaises(ValueError):
            native_payloads.verify_native_payloads(self.archive(self.fixture()))

    def test_dex_is_not_native_abi_proof(self):
        with self.assertRaisesRegex(ValueError, 'no direct arm64 ELF'):
            native_payloads.verify_native_payloads(self.archive(self.fixture(), elf=False),
                                                   self.archive(self.fixture(), elf=False))

    def test_real_filename_does_not_bypass_gate(self):
        name = 'lib/arm64-v8a/libhelium_child.dex.so'
        with self.assertRaises(ValueError):
            native_payloads.verify_native_payloads(self.archive(b'dex\n038\0broken', name),
                                                   self.archive(b'dex\n038\0broken', name))

    def nonempty(self):
        import struct
        blob = bytearray(172)
        blob[:8] = b'dex\n038\0'
        struct.pack_into('<20I', blob, 32, 172, 112, 0x12345678, 0, 0, 120,
                         1, 112, *([0]*10), 56, 116)
        struct.pack_into('<I', blob, 112, 116)
        # One empty string at 116, two padding bytes, then the map.
        struct.pack_into('<I', blob, 120, 4)
        for i, (kind, count, offset) in enumerate(((0,1,0),(1,1,112),(0x2002,1,116),(0x1000,1,120))):
            struct.pack_into('<HHII', blob, 124+i*12, kind, 0, count, offset)
        return self.seal(blob)

    def mutated_nonempty(self, offset, value, fmt='<I'):
        import struct
        blob = bytearray(self.nonempty());struct.pack_into(fmt, blob, offset, value)
        return self.seal(blob)

    def test_nonempty_table_and_map(self):
        self.assertEqual(native_payloads.inspect_dex(self.nonempty())['map_entries'], 4)

    def test_fixed_table_overrun(self):
        with self.assertRaisesRegex(ValueError, 'fixed section'):
            native_payloads.inspect_dex(self.mutated_nonempty(56, 2))

    def test_fixed_table_in_header(self):
        with self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.mutated_nonempty(60, 108))

    def test_map_unsorted(self):
        with self.assertRaisesRegex(ValueError, 'unsorted'):
            native_payloads.inspect_dex(self.mutated_nonempty(156, 112))

    def test_map_fixed_count_disagrees(self):
        with self.assertRaisesRegex(ValueError, 'section mismatch'):
            native_payloads.inspect_dex(self.mutated_nonempty(136, 2, '<H'))

    def test_map_data_count_overlaps_next_section(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            native_payloads.inspect_dex(self.mutated_nonempty(152, 5))

    def test_data_map_out_of_range(self):
        with self.assertRaises(ValueError):
            native_payloads.inspect_dex(self.mutated_nonempty(156, 9999))


class ReleaseContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / 'release').mkdir()
        (self.root / 'build-evidence').mkdir()
        self.name = 'release/fixture-v4.2.1-arm64-v8a.apk'
        (self.root / self.name).write_bytes(b'x' * 1000001)
        self.target = {'tag_prefix': 'fixture', 'min_sdk_ceiling': 29}
        self.report = {'schema': 1, 'status': 'verified', 'target': 'fixture',
                       'inputs': {'source_commit': 'a'*40, 'target': 'fixture', 'winner': 'fixture',
                                  'local_input_recipe': {'fixture_only': True},
                                  'expected_package': 'org.fixture', 'expected_certificate_sha256': 'b'*64},
                       'manifest': {'package': 'org.fixture', 'min_sdk': 29, 'version_name': '4.2.1'},
                       'signature': {'certificate_sha256': 'b'*64, 'cryptographic_verification': 'passed'},
                       'architecture': {'classification': 'arm64-v8a'},
                       'output': identity.record(self.root, self.name),
                       'applied_patch_names': ['Remove ads', 'PEOF']}
        for name, value in {'.version': '4.2.1', '.tagprefix': 'fixture', '.tagsuffix': '-b20260910',
                            '.provider': 'provider + extra', '.patchver': 'v1.0', '.applied': '- Remove ads\n- PEOF'}.items():
            (self.root / 'release' / name).write_text(value+'\n')
        self.save()
        self.addCleanup(patch.stopall)
        patch.object(release_contract, 'target', return_value=self.target).start()
        patch.object(release_contract, 'expected_package', return_value='org.fixture').start()
        patch.object(release_contract, 'command', return_value=('a'*40).encode()).start()
        # Legacy narrow handoff tests isolate metadata. InputRecipeFlow below exercises
        # the real capture/final/release recipe chain without mocking this new gate.
        patch.object(input_recipe, 'verify', return_value=None).start()

    def save(self):
        (self.root / 'build-evidence/fixture.json').write_text(json.dumps(self.report))

    def verify(self):
        return release_contract.verify(self.root, 'fixture')

    def test_valid_handoff(self):
        fields = self.verify()
        self.assertEqual(fields['tag'], 'fixture-v4.2.1-b20260910')
        self.assertEqual(fields['apkpath'], self.name)
        self.assertEqual(fields['sha256'], self.report['output']['sha256'])

    def test_apk_changed_after_identity(self):
        (self.root / self.name).write_bytes(b'y'*1000001)
        with self.assertRaisesRegex(ValueError, 'verified bytes'):self.verify()

    def test_extra_apk_refused(self):
        (self.root / 'release/stale.apk').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'exactly one'):self.verify()

    def test_missing_apk_refused(self):
        (self.root / self.name).unlink()
        with self.assertRaises(ValueError):self.verify()

    def test_symlink_apk_refused(self):
        p = self.root / self.name
        p.rename(self.root / 'outside');p.symlink_to(self.root / 'outside')
        with self.assertRaisesRegex(ValueError, 'symlink'):self.verify()

    def test_missing_report_refused(self):
        (self.root / 'build-evidence/fixture.json').unlink()
        with self.assertRaises(ValueError):self.verify()

    def test_old_commit_refused(self):
        self.report['inputs']['source_commit'] = 'c'*40;self.save()
        with self.assertRaisesRegex(ValueError, 'different source'):self.verify()

    def test_wrong_target_refused(self):
        self.report['target'] = 'other';self.save()
        with self.assertRaises(ValueError):self.verify()

    def test_unverified_report_refused(self):
        self.report['status'] = 'pending';self.save()
        with self.assertRaises(ValueError):self.verify()

    def test_changed_version_refused(self):
        (self.root / 'release/.version').write_text('4.2.2')
        with self.assertRaisesRegex(ValueError, 'version mismatch'):self.verify()

    def test_changed_prefix_refused(self):
        (self.root / 'release/.tagprefix').write_text('different')
        with self.assertRaisesRegex(ValueError, 'prefix mismatch'):self.verify()

    def test_invalid_suffix_refused(self):
        (self.root / 'release/.tagsuffix').write_text('-b20260231')
        with self.assertRaises(ValueError):self.verify()

    def test_changed_applied_list_refused(self):
        (self.root / 'release/.applied').write_text('- Another patch')
        with self.assertRaisesRegex(ValueError, 'applied-patch'):self.verify()

    def test_wrong_signer_refused(self):
        self.report['signature']['certificate_sha256'] = 'c'*64;self.save()
        with self.assertRaisesRegex(ValueError, 'signer'):self.verify()

    def test_wrong_package_refused(self):
        self.report['manifest']['package'] = 'org.other';self.save()
        with self.assertRaisesRegex(ValueError, 'package'):self.verify()

    def test_too_new_sdk_refused(self):
        self.report['manifest']['min_sdk'] = 30;self.save()
        with self.assertRaisesRegex(ValueError, 'SDK'):self.verify()

    def test_provider_output_injection_refused(self):
        (self.root / 'release/.provider').write_text('provider\napkpath=other.apk')
        with self.assertRaisesRegex(ValueError, 'single-line'):self.verify()

    def test_metadata_symlink_refused(self):
        p = self.root / 'release/.tagprefix';p.unlink()
        (self.root / 'prefix').write_text('fixture');p.symlink_to(self.root / 'prefix')
        with self.assertRaises(ValueError):self.verify()

    def test_output_delimiter_not_patch_name(self):
        fields = self.verify();text = release_contract.output_text(fields)
        lines = text.splitlines();found = [line for line in lines if line.startswith('aplist<<')]
        self.assertEqual(len(found), 1)
        delimiter = found[0].split('<<')[1]
        self.assertNotIn(delimiter, fields['aplist'].splitlines())
        self.assertIn('- PEOF', text)
        self.assertEqual(lines.count(delimiter), 1)

    def test_workflow_exercises_release_helper_in_smoke(self):
        s = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        self.assertLess(s.index('Verify finished APK identity'), s.index('Verify release handoff'))
        self.assertLess(s.index('Verify release handoff'), s.index('Releasing APK files'))
        self.assertIn('run: python3 src/build/release_contract.py "$TARGET"', s)

    def test_action_consumes_one_verified_path(self):
        s = (ROOT / '.github/actions/release/action.yml').read_text()
        self.assertIn('artifacts: ${{ steps.meta.outputs.apkpath }}', s)
        self.assertIn('python3 src/build/release_contract.py "$TARGET" --github-output', s)
        self.assertNotIn('head -1', s)
        self.assertNotIn('aplist<<PEOF', s)

    def test_workflow_build_id_handoff(self):
        from build_identity import create
        env={'GITHUB_RUN_ID':'12345','GITHUB_RUN_ATTEMPT':'2'}
        suffix=create(env)
        (self.root / 'release/.tagsuffix').write_text(suffix)
        with patch.dict(os.environ,env):
            self.assertTrue(self.verify()['tag'].endswith(suffix))

    def test_handoff_rejects_other_workflow_identity(self):
        from build_identity import create
        (self.root / 'release/.tagsuffix').write_text(create({'GITHUB_RUN_ID':'12345','GITHUB_RUN_ATTEMPT':'2'}))
        with patch.dict(os.environ,{'GITHUB_RUN_ID':'12346','GITHUB_RUN_ATTEMPT':'2'}):
            with self.assertRaisesRegex(ValueError,'another workflow'):
                self.verify()


def load_tests(loader, tests, pattern):
    # Keep the existing CI entrypoint; no workflow edit required for these contracts.
    import input_recipe_contracts
    tests.addTests(loader.loadTestsFromTestCase(input_recipe_contracts.InputRecipeTests))
    tests.addTests(loader.loadTestsFromTestCase(input_recipe_contracts.InputRecipeFlow))
    return tests


if __name__=='__main__':unittest.main()
