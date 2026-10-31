"""Adversarial W15g signing-split scenarios not covered by the baseline contracts.

These tests model the patch job as an artifact writer.  They never invoke a network,
real Android SDK, or GitHub; the SDK executables are the local stand-ins from the
existing signing-split harness.
"""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signing_split_contracts import (APK_NAME, CERTIFICATE, Harness, IDENT, META, PIN,
                                     payload_rows, quiet_call, write_zip)

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'src' / 'build'))
import artifact_identity as ai  # noqa: E402
import build_identity  # noqa: E402
import release_contract  # noqa: E402
import sign_apk  # noqa: E402


class ArtifactBoundaryScenarios(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.h = Harness(self.temp.name)
        self.root = self.h.root

    def tearDown(self):
        self.temp.cleanup()

    def stage(self, apk_name=APK_NAME):
        stage = self.root / 'handoff'
        (stage / 'release').mkdir(parents=True)
        write_zip(stage / 'release' / apk_name, payload_rows())
        (stage / 'build-evidence').mkdir()
        (stage / 'build-evidence' / (IDENT + '.json')).write_text(
            json.dumps({'inputs': {'winner': 'winner'}}), encoding='utf-8')
        return stage

    def test_path_traversal_and_symlinked_metadata_refused(self):
        stage = self.stage()
        (stage / 'release' / '.provider').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'unexpected file'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')

    def test_control_character_apk_name_refused_before_signing(self):
        self.stage('demo-\n-v1.2-arm64-v8a.apk')
        with self.assertRaisesRegex(ValueError, 'unexpected file'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')

    def test_targets_view_cannot_escape_checkout(self):
        stage = self.stage()
        (stage / 'src').mkdir()
        # A carried view must be exactly the committed checkout or the selected,
        # recomputed candidate view; arbitrary traversal-like JSON is not accepted.
        (stage / 'src' / 'targets.json').write_text(
            '{"../../outside": "not a target"}\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'neither the checkout nor the winning candidate view'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')
        self.assertFalse((self.root / 'outside').exists())

    def test_oversized_handoff_refused_before_hashing_or_tools(self):
        stage = self.stage()
        # Sparse files make this a real size-boundary test without consuming the
        # worker's disk. The file is one byte above the implementation limit.
        apk = stage / 'release' / APK_NAME
        apk.write_bytes(b'')
        with open(apk, 'r+b') as stream:
            stream.truncate(sign_apk.HANDOFF_MAX_BYTES + 1)
        with self.assertRaisesRegex(ValueError, 'too large'):
            quiet_call(sign_apk.place, self.root, IDENT, 'handoff')

    def test_malformed_report_types_are_refused_without_secret_text(self):
        self.h.init_git()
        report, apk = self.h.create_release(source_commit=subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=self.root, check=True,
            capture_output=True, text=True).stdout.strip())
        report['inputs'] = []
        (self.root / 'build-evidence' / (IDENT + '.json')).write_text(json.dumps(report))
        env = self.h.env(KEYSTORE_PASS='super-secret', KEYSTORE_ALIAS='private-alias')
        with self.assertRaises((ValueError, TypeError, KeyError)) as caught:
            quiet_call(sign_apk.handoff, self.root, IDENT, env)
        self.assertNotIn('super-secret', str(caught.exception))
        self.assertNotIn('private-alias', str(caught.exception))

    def test_sign_failure_cleans_keystore_and_does_not_print_credentials(self):
        self.h.init_git()
        self.h.create_release()
        env = self.h.env(KEYSTORE_PASS='super-secret', KEYSTORE_ALIAS='private-alias', FAKE_SIGN_FAIL='1')
        self.root.joinpath('src/ks.keystore').write_bytes(CERTIFICATE)
        output = io.StringIO()
        with self.assertRaisesRegex(ValueError, 'apksigner sign failed'):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                sign_apk.sign(self.root, IDENT, env)
        self.assertFalse((self.root / 'src/ks.keystore').exists())
        self.assertNotIn('super-secret', output.getvalue())
        self.assertNotIn('private-alias', output.getvalue())

    def test_verify_refuses_any_secret_environment_and_foreign_signer(self):
        self.h.create_verify_pair()
        env = self.h.env(KEYSTORE_PASS='secret', FAKE_CERT='f' * 64)
        with self.assertRaises(ValueError):
            with patch.dict(os.environ, env, clear=True):
                sign_apk.verify(self.root, IDENT, env)


class PublicationBindingScenarios(unittest.TestCase):
    """Exercise release_contract's final tag binding with a tiny isolated report."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'release').mkdir()
        (self.root / 'build-evidence').mkdir()
        (self.root / 'src/build').mkdir(parents=True)
        (self.root / 'src/build/ci-signer.json').write_text(json.dumps({'certificate_sha256': PIN}))
        apk = self.root / 'release/fixture-v4.2.1-arm64-v8a.apk'
        apk.write_bytes(b'x' * 1000001)
        self.target = {'tag_prefix': 'fixture', 'min_sdk_ceiling': 29}
        self.env = {'GITHUB_RUN_ID': '12345', 'GITHUB_RUN_ATTEMPT': '2'}
        self.report = {
            'schema': 1, 'status': 'verified', 'signing_split': True, 'target': 'fixture',
            'inputs': {'source_commit': 'a' * 40, 'target': 'fixture', 'winner': 'fixture',
                       'local_input_recipe': {'fixture_only': True}, 'expected_package': 'org.fixture',
                       'expected_certificate_sha256': PIN},
            'manifest': {'package': 'org.fixture', 'min_sdk': 29, 'version_name': '4.2.1'},
            'unsigned': {'binding': {'run_id': '12345', 'run_attempt': '2'}},
            'unsigned_output': {'sha256': 'c' * 64, 'bytes': 1000001},
            'signing': {'binding': {'run_id': '12345', 'run_attempt': '2'}, 'entries_compared': 1,
                        'schemes': {'v1': False, 'v2': True, 'v3': False, 'v3.1': False, 'v4': False},
                        'pin': PIN},
            'signature': {'certificate_sha256': PIN, 'cryptographic_verification': 'passed'},
            'architecture': {'classification': 'arm64-v8a'}, 'applied_patch_names': ['Safe patch']}
        self.report['output'] = ai.record(self.root, str(apk.relative_to(self.root)))
        (self.root / 'build-evidence/fixture.json').write_text(json.dumps(self.report))
        for name, value in {'.version': '4.2.1', '.tagprefix': 'fixture', '.tagsuffix': '',
                            '.provider': 'provider', '.patchver': '1', '.applied': '- Safe patch'}.items():
            (self.root / 'release' / name).write_text(value)
        self.patches = [
            patch.object(release_contract, 'target', return_value=self.target),
            patch.object(release_contract, 'expected_package', return_value='org.fixture'),
            patch.object(release_contract, 'command', return_value=('a' * 40).encode()),
            patch.object(release_contract.input_recipe, 'verify', return_value=None),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def tearDown(self):
        self.temp.cleanup()

    def test_suffix_date_is_bound_to_build_timestamp_at_publish(self):
        # Same run/attempt but a fabricated future date: run_binding alone is
        # insufficient to prevent a patch-controlled wrong release tag.
        suffix = '-b20991231' + self.env['GITHUB_RUN_ID'].zfill(20) + self.env['GITHUB_RUN_ATTEMPT'].zfill(6)
        (self.root / 'release/.tagsuffix').write_text(suffix)
        with patch.dict(os.environ, {**self.env, 'PF_BUILT_AT': '2025-01-01T00:00Z'}, clear=True):
            fields = release_contract.verify(self.root, 'fixture')
            self.assertEqual(build_identity.verify_run(fields['suffix'], os.environ)['run_id'], 12345)
            self.assertNotEqual(fields['suffix'][2:10], os.environ['PF_BUILT_AT'][:10].replace('-', ''))
            with patch.object(release_contract, 'verify', return_value=fields), \
                 patch.object(release_contract, 'sys') as fake_sys:
                fake_sys.argv = ['release_contract.py', 'fixture', '--github-output']
                with self.assertRaisesRegex(ValueError, 'tag date'):
                    release_contract.main()

    def test_publish_output_uses_literal_metadata_not_shell_or_expression_evaluation(self):
        # GitHub output's random multiline delimiter is data-safe; expression-looking
        # provider text remains literal and cannot become a secret reference.
        (self.root / 'release/.provider').write_text('${{ secrets.KEYSTORE_PASS }}')
        suffix = build_identity.create(self.env)
        (self.root / 'release/.tagsuffix').write_text(suffix)
        with patch.dict(os.environ, self.env, clear=True):
            fields = release_contract.verify(self.root, 'fixture')
        text = release_contract.output_text(fields)
        self.assertIn('${{ secrets.KEYSTORE_PASS }}', text)
        self.assertNotIn('KEYSTORE_PASS=', text)


if __name__ == '__main__':
    unittest.main()
