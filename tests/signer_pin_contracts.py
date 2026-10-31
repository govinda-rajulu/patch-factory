"""Signing pin contracts: Sign alone checks the decoded keystore against the committed pin."""
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'build'))
import artifact_identity as identity  # noqa: E402
import sign_apk  # noqa: E402

PIN = json.loads((ROOT / 'src/build/ci-signer.json').read_text())['certificate_sha256']


def job_block(text, name):
    matches = list(re.finditer(r'(?m)^  (patch|sign|publish):\s*$', text))
    for i, match in enumerate(matches):
        if match[1] == name:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return text[match.start():end]
    raise AssertionError('missing workflow job: ' + name)


class OneHome(unittest.TestCase):
    def test_pin_is_a_sha256(self):
        self.assertRegex(PIN, '^[0-9a-f]{64}$')

    def test_recovery_and_observed_apksigner_agree(self):
        self.assertIn('`' + PIN + '`', (ROOT / 'RECOVERY.md').read_text())
        self.assertEqual(identity.parse_signers((ROOT / 'tests/fixtures/apksigner-37-keymapper.txt').read_text()), PIN)

    def test_page_constant_matches(self):
        self.assertIn("const CI_CERT='%s';" % PIN, (ROOT / 'docs/portal.js').read_text())

    def test_every_patched_entry_pins_it(self):
        apps = json.loads((ROOT / 'docs/obtainium.json').read_text())['apps']
        self.assertTrue(apps)
        for app in apps:
            self.assertEqual(json.loads(app['additionalSettings'])['allowedSigningCertHashes'], PIN, app['name'])

    def test_companions_are_not_pinned_to_our_key(self):
        # MicroG RE and Obtainium are signed by their own authors; our key there would block them.
        for name in ('obtainium-microg.json', 'obtainium-self.json'):
            for app in json.loads((ROOT / 'docs' / name).read_text())['apps']:
                self.assertNotIn('allowedSigningCertHashes', json.loads(app['additionalSettings']))

    def test_no_other_copy_of_the_value_in_code(self):
        homes = set()
        for p in list((ROOT / 'src').rglob('*.py')) + list((ROOT / 'src').rglob('*.sh')) + list((ROOT / '.github').rglob('*.yml')):
            if PIN in p.read_text(errors='replace'):
                homes.add(str(p.relative_to(ROOT)))
        self.assertEqual(homes, set())


class SignJobPin(unittest.TestCase):
    def pinned_root(self, root, pin=PIN):
        path = root / 'src/build/ci-signer.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'certificate_sha256': pin}))
        return path

    def test_sign_job_keystore_certificate_must_match_committed_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.pinned_root(root)
            with patch.object(identity, 'cert_from_keystore', return_value=PIN), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(identity.check_keystore_pin(root, {'KEYSTORE_PASS': 'fixture', 'KEYSTORE_ALIAS': 'fixture'}), PIN)
            with patch.object(identity, 'cert_from_keystore', return_value='b' * 64):
                with self.assertRaisesRegex(ValueError, 'Obtainium pin'):
                    identity.check_keystore_pin(root, {'KEYSTORE_PASS': 'fixture', 'KEYSTORE_ALIAS': 'fixture'})

    def test_sign_checks_pin_before_invoking_apksigner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'src').mkdir()
            (root / 'src/ks.keystore').write_bytes(b'fixture')
            (root / 'release').mkdir()
            apk = root / 'release/fixture.apk'
            apk.write_bytes(b'unsigned fixture')
            report = {'manifest': {'min_sdk': 29}}
            events = []

            def run(args, **kwargs):
                events.append(('apksigner', args[1]))
                output = Path(args[args.index('--out') + 1])
                output.write_bytes(b'signed fixture')
                return type('Result', (), {'returncode': 0})()

            def pin_check(*args):
                events.append(('pin-check', None))
                return PIN

            env = {'KEYSTORE_PASS': 'fixture', 'KEYSTORE_ALIAS': 'fixture'}
            with patch.object(sign_apk, 'handoff', return_value=(report, apk)), \
                 patch.object(identity, 'check_keystore_pin', side_effect=pin_check), \
                 patch.object(identity, 'sdk_tools', return_value=['/fixture/apksigner']), \
                 patch.object(sign_apk.subprocess, 'run', side_effect=run), \
                 contextlib.redirect_stdout(io.StringIO()):
                sign_apk.sign(root, 'fixture', env)
            self.assertEqual(events, [('pin-check', None), ('apksigner', 'sign')])
            self.assertFalse((root / 'src/ks.keystore').exists())

    def test_workflow_signs_only_in_sign_job_and_patch_publish_are_key_free(self):
        workflow = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        patch_job, sign_job, publish_job = (job_block(workflow, name) for name in ('patch', 'sign', 'publish'))
        self.assertNotIn('KEYSTORE', patch_job)
        self.assertNotIn('ks.keystore', patch_job)
        self.assertNotIn('KEYSTORE', publish_job)
        self.assertNotIn('ks.keystore', publish_job)
        self.assertIn('KEYSTORE_B64: ${{ secrets.KEYSTORE_B64 }}', sign_job)
        self.assertIn('KEYSTORE_PASS: ${{ secrets.KEYSTORE_PASS }}', sign_job)
        self.assertIn('KEYSTORE_ALIAS: ${{ secrets.KEYSTORE_ALIAS }}', sign_job)
        self.assertLess(sign_job.index('Decode keystore'), sign_job.index('Sign APK'))

    def test_old_prepatch_signer_capture_is_gone(self):
        build = (ROOT / 'src/build/build.sh').read_text()
        workflow = (ROOT / '.github/workflows/manual-patch.yml').read_text()
        self.assertNotIn('capture-signer', build)
        self.assertNotIn('.signer-before-build.json', build)
        patch_job = job_block(workflow, 'patch')
        self.assertNotIn('Decode keystore', patch_job)
        self.assertIn('Verify unsigned APK identity', patch_job)
        source = (ROOT / 'src/build/sign_apk.py').read_text()
        self.assertIn('ai.check_keystore_pin(root, env)', source)
        self.assertLess(source.index('ai.check_keystore_pin(root, env)'), source.index('subprocess.run(args, cwd=root, env=env'))
        pin_check = (ROOT / 'src/build/artifact_identity.py').read_text()
        self.assertIn('fingerprint == pinned_certificate(root)', pin_check)

    def test_missing_pin_file_stops(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(identity, 'cert_from_keystore', return_value=PIN):
            with self.assertRaises(OSError):
                identity.check_keystore_pin(Path(tmp), {'KEYSTORE_PASS': 'fixture', 'KEYSTORE_ALIAS': 'fixture'})


if __name__ == '__main__':
    unittest.main()
