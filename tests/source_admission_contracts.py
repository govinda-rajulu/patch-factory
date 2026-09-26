"""Reviewed exact-version source admissions (26 Sep 2026) and the parser rules they need.

Photos 7.92.0.977185651 is admitted with an exact v3.0 -> v3.1 key-rotation pair pin.

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
    'photos': ('apkpure', '7.92.0.977185651', '52372370', 230966267,
               '20047c44376edaac9380d01632eabd6db1087ecaca0252aad80cc5b8b3b42624',
               '3d7a1223019aa39d9ea0e3436ab7c0896bfb4fb679f4de5fe7c23f326c8f994a', 'apk',
               ['arm64-v8a', 'armeabi-v7a', 'x86', 'x86_64'], 24),
}
FACEBOOK_CERT = REVIEWED['facebook'][5]
PHOTOS_OLD = REVIEWED['photos'][5]
PHOTOS_NEW = '5aad2bee6db95d17e05a08d7d1e64c10a1511879154483916b6ae6c7fd9cb0c6'
PHOTOS_ROTATION = [{'min_sdk': 24, 'max_sdk': 32, 'certificate_sha256': PHOTOS_OLD},
                   {'min_sdk': 33, 'max_sdk': 2147483647, 'certificate_sha256': PHOTOS_NEW}]


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
                self.assertEqual(a.get('signer_rotation'), PHOTOS_ROTATION if ident == 'photos' else None)

    def test_photos_admission_pins_the_exact_rotation_pair(self):
        doc = fb.policy(ROOT)
        rows = doc['targets']['photos']['admissions']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['signer_rotation'], PHOTOS_ROTATION)
        self.assertEqual(rows[0]['mapping'], {
            'download_url': 'https://apkpure.com/google-photos/com.google.android.apps.photos/download'})
        ev = json.loads((ROOT / rows[0]['evidence']).read_text())
        self.assertEqual(ev['signer_rotation'], PHOTOS_ROTATION)
        self.assertIn('rotation', doc['targets']['photos']['blocked_reason'])

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


class RotationSigner(unittest.TestCase):
    def photos(self):
        return (FIX / 'apksigner-37-photos-v31-rotation.txt').read_text()

    def test_observed_photos_rotation_parses_to_the_exact_pair(self):
        self.assertEqual(identity.parse_original_signers(self.photos()), (PHOTOS_OLD, PHOTOS_ROTATION))

    def test_single_signer_originals_are_unchanged(self):
        text = (FIX / 'apksigner-37-facebook-v2-only.txt').read_text()
        self.assertEqual(identity.parse_original_signers(text), (FACEBOOK_CERT, None))
        with self.assertRaises(ValueError):
            identity.parse_original_signers(text.replace('Number of signers: 1', 'Number of signers: 2'))

    def test_every_other_rotation_shape_refuses(self):
        text = self.photos()
        old_line = next(l for l in text.splitlines() if l.startswith('V3.0 Signer:') and 'certificate SHA-256' in l)
        new_line = next(l for l in text.splitlines() if l.startswith('V3.1 Signer:') and 'certificate SHA-256' in l)
        bad = {
            'gap': text.replace('maxSdkVersion=32)', 'maxSdkVersion=31)'),
            'overlap': text.replace('(minSdkVersion=33,', '(minSdkVersion=32,'),
            'capped': text.replace('maxSdkVersion=2147483647)', 'maxSdkVersion=34)'),
            'same-cert': text.replace(PHOTOS_NEW, PHOTOS_OLD),
            'no-v30': text.replace(old_line + '\n', ''),
            'no-v31-cert': text.replace(new_line + '\n', ''),
            'extra-v31': text + new_line.replace('33', '40') + '\n',
            'extra-v30': text + old_line + '\n',
            'unlabelled-v30': text + 'V3.0 Signer: certificate SHA-256 digest: ' + 'a' * 64 + '\n',
            'legacy': text + 'Signer #1 certificate SHA-256 digest: ' + PHOTOS_OLD + '\n',
            'v32': text + 'V3.2 Signer: (minSdkVersion=35, maxSdkVersion=2147483647) certificate SHA-256 digest: ' + 'b' * 64 + '\n',
            'two-signers': text.replace('Number of signers: 1', 'Number of signers: 2'),
            'no-count': text.replace('Number of signers: 1\n', ''),
            'v31-unverified': text.replace('(APK Signature Scheme v3.1): true', '(APK Signature Scheme v3.1): false'),
            'v3-unverified': text.replace('(APK Signature Scheme v3): true', '(APK Signature Scheme v3): false'),
            'bad-hex': text.replace(PHOTOS_NEW, 'abcdef'),
            'two-stamps': text + 'Source Stamp Signer: certificate SHA-256 digest: ' + 'c' * 64 + '\n',
        }
        for name, t in bad.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                identity.parse_original_signers(t)

    def test_finished_apks_still_refuse_rotation(self):
        with self.assertRaises(ValueError):
            identity.parse_signers(self.photos())


class RotationPolicy(unittest.TestCase):
    def fixture(self, rotation=PHOTOS_ROTATION, evidence_rotation=PHOTOS_ROTATION):
        f = fixtures.FallbackContracts()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.a['certificate_sha256'] = PHOTOS_OLD
        if rotation is not None and rotation != 'NULL':
            f.a['signer_rotation'] = rotation
        f.authorize_fixture()
        path = f.root / f.a['evidence']
        ev = json.loads(path.read_text())
        ev.pop('signer_rotation', None)
        if evidence_rotation is not None:
            ev['signer_rotation'] = evidence_rotation
        path.write_text(json.dumps(ev))
        return f

    def test_reviewed_pair_validates_and_binds_evidence(self):
        f = self.fixture()
        a = fb.admission(f.root, f.ident, f.a['version_name'])[1]
        self.assertEqual(a['signer_rotation'], PHOTOS_ROTATION)
        for ev_rot in (None, list(reversed(PHOTOS_ROTATION))):
            with self.subTest(evidence=ev_rot), self.assertRaises(ValueError):
                fb.policy(self.fixture(evidence_rotation=ev_rot).root)

    def test_malformed_pairs_refused(self):
        def swap(i, **kw):
            r = [dict(x) for x in PHOTOS_ROTATION]
            r[i].update(kw)
            return r
        for name, rot in {
                'one': PHOTOS_ROTATION[:1], 'three': PHOTOS_ROTATION + PHOTOS_ROTATION[1:],
                'reversed': list(reversed(PHOTOS_ROTATION)), 'null': 'NULL', 'empty': [],
                'gap': swap(0, max_sdk=31), 'capped': swap(1, max_sdk=34),
                'wrong-start': swap(0, certificate_sha256='2' * 64),
                'same': swap(1, certificate_sha256=PHOTOS_OLD),
                'string-sdk': swap(0, min_sdk='24'), 'bool-sdk': swap(1, min_sdk=True),
                'extra-key': swap(0, scheme='v3.0'), 'short-hex': swap(1, certificate_sha256='ab')}.items():
            rot = None if rot == 'NULL' else rot
            f = self.fixture(rotation='NULL', evidence_rotation=None)
            path = f.root / fb.POLICY
            doc = json.loads(path.read_text())
            doc['targets'][f.ident]['admissions'][0]['signer_rotation'] = rot
            path.write_text(json.dumps(doc))
            ev = f.root / f.a['evidence']
            data = json.loads(ev.read_text())
            data['signer_rotation'] = rot
            ev.write_text(json.dumps(data))
            with self.subTest(case=name), self.assertRaises(ValueError):
                fb.policy(f.root)

    def inspect(self, f, reader):
        scratch = f.root / 'scratch'
        scratch.mkdir(exist_ok=True)
        with patch.object(fb, 'apk_metadata', side_effect=f.metadata), \
                patch.object(fb, 'apk_certificate', side_effect=AssertionError('single-key reader used')), \
                patch.object(fb, 'apk_signing_identity', side_effect=reader):
            return fb.inspect_original(f.root, f.raw, f.t, f.a, f.env, scratch)

    def test_consumer_requires_the_exact_pair(self):
        f = self.fixture()
        self.assertEqual(self.inspect(f, lambda *a: (PHOTOS_OLD, PHOTOS_ROTATION))['certificate_sha256'], PHOTOS_OLD)
        for name, got in {'single': (PHOTOS_OLD, None), 'new-only': (PHOTOS_NEW, None),
                          'other-pair': (PHOTOS_OLD, [PHOTOS_ROTATION[0], dict(PHOTOS_ROTATION[1], certificate_sha256='9' * 64)]),
                          'ranges': (PHOTOS_OLD, [dict(PHOTOS_ROTATION[0], max_sdk=31), dict(PHOTOS_ROTATION[1], min_sdk=32)])}.items():
            g = self.fixture()
            with self.subTest(case=name), self.assertRaisesRegex(ValueError, 'rotation differs'):
                self.inspect(g, lambda *a, got=got: got)

    def test_single_key_admissions_never_use_the_rotation_reader(self):
        f = fixtures.FallbackContracts()
        f.setUp()
        self.addCleanup(f.doCleanups)
        with patch.object(fb, 'apk_signing_identity', side_effect=AssertionError('rotation reader used')):
            self.assertEqual(f.inspect()['certificate_sha256'], fixtures.CERT)
        with patch.object(fb, 'apk_signing_identity', side_effect=AssertionError('rotation reader used')), \
                self.assertRaisesRegex(ValueError, 'signer differs'):
            f.inspect(certificate=lambda *a: PHOTOS_NEW)


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
