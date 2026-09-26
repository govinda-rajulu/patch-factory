"""Observed SDK37 Reddit output and simulated failures, not Android certification."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import artifact_identity as identity
import original_apk
import source_fallback as fb
import source_variant as variant
import source_pilot
import source_fallback_contracts as fixtures

EVIDENCE = ROOT / source_pilot.EVIDENCE


class OriginalVariantContracts(unittest.TestCase):
    def setUp(self):
        self.e = json.loads(EVIDENCE.read_text())

    def test_all_27_observed_original_outputs_parse_without_invented_fields(self):
        self.assertEqual(len(self.e['original_parts']), 27)
        for part in self.e['original_parts']:
            with self.subTest(part=part['part']):
                self.assertEqual(original_apk.parse('\n'.join(part['metadata_output'])), part['manifest'])
                self.assertEqual(identity.parse_signers('\n'.join(part['signer_output'])),
                                 self.e['certificate_sha256'])
                self.assertEqual(part['verifier_exit'], 0)
        self.assertEqual(sum(p['manifest']['split'] is None for p in self.e['original_parts']), 1)
        self.assertEqual(sum(p['manifest']['version_name'] == '' for p in self.e['original_parts']), 26)

    def test_source_stamp_never_supplies_or_replaces_the_app_certificate(self):
        text = '\n'.join(self.e['original_parts'][0]['signer_output'])
        stamp = self.e['original_parts'][0]['source_stamp_certificate_sha256']
        cert = self.e['certificate_sha256']
        self.assertNotEqual(cert, stamp)
        self.assertEqual(identity.parse_signers(text.replace(stamp, 'a' * 64)), cert)
        for bad in (text.replace('Number of signers: 1', 'Number of signers: 2'),
                    text + '\nSigner #2 certificate SHA-256 digest: ' + cert,
                    text + '\nUnknown signer: certificate SHA-256 digest: ' + cert,
                    text + '\nSource Stamp Signer: certificate SHA-256 digest: ' + stamp,
                    text.replace(stamp, 'aa'),
                    '\n'.join(s for s in text.splitlines() if not s.startswith('V3.0 Signer:'))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                identity.parse_signers(bad)

    def test_original_metadata_missing_ambiguous_malformed_refused(self):
        base = '\n'.join(self.e['original_parts'][0]['metadata_output'])
        for bad in (base + '\n' + base, base.replace("versionName='2026.38.0'", "versionName=''"),
                    base.replace("versionCode='2638001'", "versionCode='abc'"),
                    base.replace("minSdkVersion:'29'", ""), base + "\nsdkVersion:'32'",
                    base.replace("minSdkVersion:'29'", "minSdkVersion:'Q'"),
                    base.replace(" versionCode=", " name='wrong.pkg' versionCode="),
                    base.replace("versionName='2026.38.0'", "versionName='' split=''")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                original_apk.parse(bad)

    def test_variant_url_exact_release_host_and_native_constraints(self):
        v = self.e['variant']
        args = (self.e['source'], self.e['mapping'], self.e['version_name'], 29)
        self.assertEqual(variant.validate(v, *args), v)
        for changes in ({'min_sdk': 32}, {'min_sdk': True}, {'abis': ['x86']},
                        {'abis': ['arm64-v8a', 'arm64-v8a']}, {'kind': 'latest'},
                        {'apkmirror_url': v['apkmirror_url'] + '?token=secret'},
                        {'apkmirror_url': v['apkmirror_url'].replace('redditinc', 'someone')},
                        {'apkmirror_url': v['apkmirror_url'].replace('2026-38-0-release', '2026-39-0-release')},
                        {'apkmirror_url': v['apkmirror_url'].replace('https:', 'http:')}):
            bad = dict(v, **changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                variant.validate(bad, *args)

    def test_variant_cli_requires_bound_file_and_refuses_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'selector.json'
            d = {'source': 'apkmirror', 'package': self.e['package'], 'version': self.e['version_name'],
                 'mapping': self.e['mapping'], 'ceiling': 29, 'variant': self.e['variant']}
            p.write_text(json.dumps(d))
            args = [sys.executable, str(ROOT / 'src/build/source_variant.py'),
                    'apkmirror_url', str(p), 'apkmirror', self.e['package'], self.e['version_name']]
            good = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(good.stdout.strip(), self.e['variant']['apkmirror_url'])
            p.write_text('{"source":"apkmirror",' + json.dumps(d)[1:])
            bad = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertNotIn('https:', bad.stdout + bad.stderr)

    def fixture(self):
        f = fixtures.FallbackContracts()
        f.setUp()
        self.addCleanup(f.doCleanups)
        return f

    def test_split_empty_version_only_with_unique_base_and_matching_code(self):
        for mode in ('good', 'two-base', 'no-base', 'wrong-name', 'wrong-code', 'sdk32'):
            f = self.fixture()
            f.make_bundle()
            def meta(root, path, env, **kwargs):
                m = f.metadata(root, path, env, **kwargs)
                if mode == 'two-base': m['split'] = None
                if mode == 'no-base': m['split'] = 'config.arm64_v8a'
                if path.name == 'split-1.apk':
                    if mode == 'wrong-name': m['version_name'] = '999'
                    if mode == 'wrong-code': m['version_code'] = '999'
                    if mode == 'sdk32': m['min_sdk'] = 32
                return m
            with self.subTest(mode=mode):
                if mode == 'good': self.assertEqual(len(f.inspect(metadata=meta)['splits']), 2)
                else:
                    with self.assertRaises(ValueError): f.inspect(metadata=meta)

    def test_duplicate_named_splits_refused_even_with_one_base(self):
        import zipfile
        f = self.fixture()
        f.make_bundle()
        with zipfile.ZipFile(f.raw, 'a') as z:
            z.writestr('duplicate-name.apk', fixtures.apk_bytes('arm64-v8a'))
        f.a['container'] = fb.file_record(f.raw)
        def meta(root, path, env, **kwargs):
            m = dict(f.meta)
            if path.name != 'split-0.apk': m.update(split='config.arm64_v8a', version_name='')
            return m
        with self.assertRaisesRegex(ValueError, 'duplicate original split'):
            f.inspect(metadata=meta)

    def test_reviewed_abi_and_sdk_inventory_exact_not_merely_compatible(self):
        f = self.fixture()
        f.make_bundle()
        f.a['variant']['abis'] = ['arm64-v8a', 'x86_64']
        with self.assertRaisesRegex(ValueError, 'ABI inventory'): f.inspect()
        f.a['variant']['abis'] = ['arm64-v8a']
        f.a['variant']['min_sdk'] = 28
        # Prior extracted bytes are preserved, so use a new scratch for the next refusal.
        (f.root / 'scratch').rename(f.root / 'old-scratch')
        with self.assertRaisesRegex(ValueError, 'SDK differs'): f.inspect()

    def test_policy_admits_only_reviewed_exact_versions(self):
        doc = fb.policy(ROOT)
        self.assertEqual(len(doc['targets']), 14)
        reviewed = {'reddit', 'telegram', 'facebook', 'truecaller-combo'}
        self.assertTrue(all(row['admissions'] == [] for ident, row in doc['targets'].items()
                            if ident not in reviewed))
        self.assertTrue(all(len(row['admissions']) <= 1 for row in doc['targets'].values()))
        # The PR85 originals record itself stays a historical, non-activating observation.
        self.assertFalse(self.e['qualification']['activation'])

    def test_production_recipe_covers_new_metadata_and_variant_readers(self):
        import input_recipe
        paths = [row['path'] for row in input_recipe.create(ROOT, 'reddit', 'adobo', {})['components']]
        self.assertIn('src/build/original_apk.py', paths)
        self.assertIn('src/build/source_variant.py', paths)

    def test_pilot_rejects_wrong_original_before_new_scratch_or_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / 'wrong.apkm'
            raw.write_bytes(b'wrong bytes')
            scratch = Path(temp) / 'scratch'
            with patch.object(fb, 'inspect_original', side_effect=AssertionError('tool called')):
                with self.assertRaisesRegex(ValueError, 'raw bytes differ'):
                    source_pilot.inspect(ROOT, raw, scratch, {})
            self.assertFalse(scratch.exists())

    def test_pilot_positive_calls_actual_original_checks_without_admission(self):
        f = self.fixture()
        f.make_bundle()
        import zipfile,hashlib
        with zipfile.ZipFile(f.raw) as z:
            parts=[{'bytes':len(z.read(n)), 'sha256':hashlib.sha256(z.read(n)).hexdigest()}
                   for n in z.namelist()]
        e={'status':'ORIGINALS_REVIEWED_NOT_ACTIVATED','qualification':{'activation':False},
           'target':'reddit','package':f.t['package'],'original_parts':parts,
           **{k:v for k,v in f.a.items() if k!='evidence'}}
        (f.root/source_pilot.EVIDENCE).write_text(json.dumps(e))
        before=(f.root/fb.POLICY).read_bytes()
        with patch.object(fb,'apk_metadata',side_effect=f.metadata), \
             patch.object(fb,'apk_certificate',side_effect=f.certificate):
            result=source_pilot.inspect(f.root,f.raw,f.root/'pilot-scratch',f.env)
        self.assertEqual(result['status'],'CANDIDATE_ORIGINAL_CONSUMER_PASSED')
        self.assertEqual(result['original']['splits'],parts)
        self.assertEqual(f.events.count('certificate'),2)
        self.assertEqual((f.root/fb.POLICY).read_bytes(),before)
        self.assertFalse((f.root/fb.RECEIPT).exists())
        self.assertFalse(result['patch'] or result['sign'] or result['publish'] or result['activation'])


if __name__ == '__main__':
    unittest.main()
