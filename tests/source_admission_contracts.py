"""Reviewed exact-version source admissions (26 Sep 2026) and the parser rules they need.

Observed SDK37 output is stored as fixtures; this is not Android certification or a device test.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import artifact_identity as identity
import original_apk
import source_fallback as fb
import source_fallback_contracts as fixtures

FIX = ROOT / 'tests/fixtures'
REVIEWED = {
    'reddit': ('apkmirror', '2026.38.0', '2638001', 68282446,
               '3ab0a58a4ce8425d3e9bd40574f3952d1c1eda6f3394a4cd07ee1c2dde79995c',
               '970b91143813b4c9d5f3634f672c9fcaa5621b4efaaedafd6c235cbbb869736f', 'bundle', ['arm64-v8a'], 29),
    'telegram': ('apkpure', '12.10.1', '70382', 125179933,
                 'f88359ba39e1b3c44d6f86f3e2a435109c456715a8996d8388fccbbbbc7362f8',
                 '49c1522548ebacd46ce322b6fd47f6092bb745d0f88082145caf35e14dcc38e1', 'apk',
                 ['arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64'], 23),
    'facebook': ('apkpure', '490.0.0.63.82', '457215604', 63922261,
                 '6f0b901f03af5c511d92338b1179a8411542e06cf4e6b9e151b90be4f3e29371',
                 'e3f9e1e0cf99d0e56a055ba65e241b3399f7cea524326b0cdd6ec1327ed0fdc1', 'apk', ['arm64-v8a'], 28),
    'truecaller-combo': ('apkpure', '26.10.6', '2610006', 110330489,
                         'b453dc1d4517f6c7bb8a049b7f155cc52ec452d8d8558076058bbd0e22f3f6e5',
                         '7712b5f255f2c85b8b164519116ac4381bb9a3582dcdd2b73ac06ee7464913ae', 'bundle',
                         ['arm64-v8a'], 26),
}
FACEBOOK_CERT = REVIEWED['facebook'][5]


def truecaller_badging():
    parts, cur = {}, None
    for line in (FIX / 'aapt2-37-truecaller-26.10.6-splits.txt').read_text().splitlines():
        if line.startswith('== '):
            cur = line[3:]
            parts[cur] = []
        else:
            parts[cur].append(line)
    return {k: '\n'.join(v) + '\n' for k, v in parts.items()}


class ReviewedAdmissions(unittest.TestCase):
    def test_every_admission_is_one_reviewed_exact_artifact(self):
        doc = fb.policy(ROOT)
        admitted = {k: v['admissions'] for k, v in doc['targets'].items() if v['admissions']}
        self.assertTrue(set(admitted) <= set(REVIEWED))
        for ident, rows in admitted.items():
            with self.subTest(target=ident):
                self.assertEqual(len(rows), 1)
                a = rows[0]
                src, ver, code, size, sha, cert, kind, abis, sdk = REVIEWED[ident]
                self.assertEqual((a['source'], a['version_name'], a['version_code']), (src, ver, code))
                self.assertEqual(a['container'], {'bytes': size, 'sha256': sha})
                self.assertEqual(a['certificate_sha256'], cert)
                self.assertEqual((a['variant']['kind'], a['variant']['abis'], a['variant']['min_sdk']),
                                 (kind, abis, sdk))
                self.assertTrue((ROOT / a['evidence']).is_file())

    def test_photos_rotation_stays_blocked(self):
        doc = fb.policy(ROOT)
        self.assertEqual(doc['targets']['photos']['admissions'], [])
        self.assertIn('rotat', doc['targets']['photos']['blocked_reason'])

    def test_other_versions_never_admitted(self):
        doc = fb.policy(ROOT)
        for ident, row in doc['targets'].items():
            for version in ('1.0', '999.0'):
                with self.subTest(target=ident, version=version), \
                        patch.object(fb, 'run_checked', side_effect=AssertionError('network')):
                    self.assertNotIn(version, [a['version_name'] for a in row['admissions']])
                    with self.assertRaises(ValueError):
                        fb.admission(ROOT, ident, version)


class SignerLabels(unittest.TestCase):
    def facebook(self):
        return (FIX / 'apksigner-37-facebook-v2-only.txt').read_text()

    def test_observed_v2_only_signer_parses_to_the_one_certificate(self):
        self.assertEqual(identity.parse_signers(self.facebook()), FACEBOOK_CERT)

    def test_v2_label_ambiguity_still_refused(self):
        text = self.facebook()
        line = 'V2 Signer: certificate SHA-256 digest: ' + FACEBOOK_CERT
        for bad in (text + line + '\n',
                    text + 'V3.0 Signer: certificate SHA-256 digest: ' + 'a' * 64 + '\n',
                    text + 'Signer #1 certificate SHA-256 digest: ' + FACEBOOK_CERT + '\n',
                    text.replace('Number of signers: 1', 'Number of signers: 2'),
                    text.replace('Number of signers: 1\n', ''),
                    text.replace(FACEBOOK_CERT, 'abcdef')):
            with self.subTest(bad=bad[-90:]), self.assertRaises(ValueError):
                identity.parse_signers(bad)

    def test_observed_v31_rotation_is_still_unrecognized(self):
        with self.assertRaisesRegex(ValueError, 'unrecognized certificate identity'):
            identity.parse_signers((FIX / 'apksigner-37-photos-v31-rotation.txt').read_text())


class ConfigSplitSdk(unittest.TestCase):
    def test_observed_truecaller_splits(self):
        parts = truecaller_badging()
        got = {k: original_apk.parse(v) for k, v in parts.items()}
        self.assertEqual(got['split-0.apk']['min_sdk'], 26)
        self.assertIsNone(got['split-0.apk']['split'])
        self.assertEqual(got['split-3.apk'], {'package': 'com.truecaller', 'version_code': '2610006',
                                             'version_name': '26.10.6', 'min_sdk': 26,
                                             'split': 'insights_category_model'})
        for name, split in (('split-1.apk', 'config.arm64_v8a'), ('split-2.apk', 'config.xhdpi'),
                            ('split-4.apk', 'insights_category_model.config.arm64_v8a')):
            self.assertEqual(got[name], {'package': 'com.truecaller', 'version_code': '2610006',
                                         'version_name': '', 'min_sdk': None, 'split': split})

    def test_missing_sdk_refused_outside_config_splits(self):
        parts = truecaller_badging()
        base = parts['split-0.apk'].replace("minSdkVersion:'26'\n", '')
        feature = parts['split-3.apk'].replace("minSdkVersion:'26'\n", '')
        for bad in (base, feature,
                    parts['split-1.apk'].replace("split='config.arm64_v8a'", "split='configx.arm64_v8a'"),
                    parts['split-1.apk'].replace("split='config.arm64_v8a'", "split='a.b.config.arm64_v8a'"),
                    parts['split-1.apk'].replace("split='config.arm64_v8a'", "split='config'"),
                    parts['split-1.apk'] + "minSdkVersion:'Q'\n"):
            with self.subTest(bad=bad[:120]), self.assertRaises(ValueError):
                original_apk.parse(bad)

    def fixture(self):
        f = fixtures.FallbackContracts()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.make_bundle()
        return f

    def test_consumer_accepts_config_split_without_sdk_only_with_reviewed_base(self):
        for mode in ('good', 'named-feature', 'base-missing', 'base-differs'):
            f = self.fixture()

            def meta(root, path, env, **kwargs):
                m = dict(f.meta)
                if path.name == 'split-1.apk':
                    m.update(split='config.arm64_v8a' if mode != 'named-feature' else 'feature_x',
                             version_name='', min_sdk=None)
                elif mode == 'base-missing':
                    m['min_sdk'] = None
                elif mode == 'base-differs':
                    m['min_sdk'] = 28
                return m
            with self.subTest(mode=mode):
                if mode == 'good':
                    self.assertEqual(len(f.inspect(metadata=meta)['splits']), 2)
                else:
                    with self.assertRaises(ValueError):
                        f.inspect(metadata=meta)


class BrowserWait(unittest.TestCase):
    def test_loopback_browser_wait_is_sixty_seconds(self):
        text = (ROOT / 'src/build/utils.sh').read_text()
        self.assertEqual(text.count('maxTimeout:60000'), 1)
        self.assertEqual(text.count('maxTimeout:15000'), 0)


if __name__ == '__main__':
    unittest.main()
