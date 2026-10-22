"""Signing pin contracts (packet W15h, 22 Oct 2026). One home for the CI certificate:
src/build/ci-signer.json. The build stops when the keystore differs, and every patched-app
entry in docs/obtainium.json pins it (Obtainium 1.6.16+ allowedSigningCertHashes)."""
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

PIN = json.loads((ROOT / 'src/build/ci-signer.json').read_text())['certificate_sha256']


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


class BuildStops(unittest.TestCase):
    def capture(self, pinned, actual):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            (r / 'src/build').mkdir(parents=True)
            pin = r / 'src/build/ci-signer.json'
            pin.write_text(json.dumps({'certificate_sha256': pinned}))
            with patch.object(identity, 'cert_from_keystore', return_value=actual), contextlib.redirect_stdout(io.StringIO()):
                identity.capture_signer(r, {}, pin=pin)
            return json.loads((r / '.signer-before-build.json').read_text())['certificate_sha256']

    def test_matching_keystore_captures(self):
        self.assertEqual(self.capture(PIN, PIN), PIN)

    def test_other_keystore_stops_before_patching(self):
        with self.assertRaisesRegex(ValueError, 'Obtainium pin'):
            self.capture(PIN, 'b' * 64)

    def test_capture_reads_the_pin_before_the_build(self):
        s = (ROOT / 'src/build/build.sh').read_text()
        self.assertLess(s.index('capture-signer'), s.index('python3 src/build/patch_target.py'))
        self.assertIn("capture_signer(root, os.environ, pin=root / 'src/build/ci-signer.json')",
                      (ROOT / 'src/build/artifact_identity.py').read_text())
        self.assertIn('python3 src/build/artifact_identity.py capture-signer || exit 1', s)

    def test_missing_pin_file_stops(self):
        with tempfile.TemporaryDirectory() as d, patch.object(identity, 'cert_from_keystore', return_value=PIN):
            with self.assertRaises(OSError):
                identity.capture_signer(Path(d), {}, pin=Path(d) / 'src/build/ci-signer.json')


if __name__ == '__main__':
    unittest.main()
