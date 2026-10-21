"""S2 publisher pins (packet W13): observe when unpinned, refuse a mismatch; unreadable fails when pinned (W15b)."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
import publisher_cert as pc  # noqa: E402


class Publisher(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r = Path(self.t.name)
        (self.r / 'src/build').mkdir(parents=True)
        (self.r / 'download').mkdir()
        (self.r / 'src/targets.json').write_text(json.dumps([dict(id='x', enabled=True, package='com.x', apk_name='x')]))
        with zipfile.ZipFile(self.r / 'download/x.apkm', 'w') as z:
            z.writestr('base.apk', b'base')
            z.writestr('split_config.arm64_v8a.apk', b'split')
        self.seen = []

    def signer(self, cert):
        def fn(root, apk, env):
            self.seen.append(Path(apk).read_bytes())
            return {'certificate_sha256': cert}
        return fn

    def pins(self, value):
        (self.r / 'src/build/PUBLISHERS.json').write_text(json.dumps(value))

    def test_unpinned_observes_the_base_apk(self):
        self.assertEqual(pc.check(self.r, 'x', {}, self.signer('a' * 64)), 0)
        self.assertEqual(self.seen, [b'base'])

    def test_pinned_match_passes_and_mismatch_fails(self):
        self.pins({'com.x': ['a' * 64]})
        self.assertEqual(pc.check(self.r, 'x', {}, self.signer('a' * 64)), 0)
        self.assertEqual(pc.check(self.r, 'x', {}, self.signer('b' * 64)), 1)

    def test_committed_pins_are_well_formed(self):
        # W14: seeded from the PUBLISHER_CERT lines CI read on 10 Oct 2026 (SESSION-2026-10-11)
        import re
        pins = json.loads((ROOT / 'src/build/PUBLISHERS.json').read_text(encoding='utf-8'))
        packages = {t['package'] for t in json.loads((ROOT / 'src/targets.json').read_text(encoding='utf-8'))}
        self.assertGreaterEqual(len(pins), 16)
        for pkg, certs in pins.items():
            self.assertIn(pkg, packages)
            self.assertTrue(certs and all(re.fullmatch('[0-9a-f]{64}', c) for c in certs), pkg)

    def test_unreadable_fails_when_pinned_and_passes_when_not(self):
        # W15b (owner, 20 Oct 2026): a pinned package with an unreadable original stops.
        def bad(root, apk, env):
            raise ValueError('apksigner failed (exit 1)')
        self.assertEqual(pc.check(self.r, 'x', {}, bad), 0)
        self.pins({'com.x': ['a' * 64]})
        self.assertEqual(pc.check(self.r, 'x', {}, bad), 1)

    def test_plain_apk_is_read_directly(self):
        (self.r / 'download/x.apkm').unlink()
        (self.r / 'download/x.apk').write_bytes(b'plain')
        self.assertEqual(pc.check(self.r, 'x', {}, self.signer('a' * 64)), 0)
        self.assertEqual(self.seen, [b'plain'])


class Prepared(unittest.TestCase):
    # W15c (20 Oct 2026): a prepared split app arrives merged; prepare checked its original.
    setUp_base = Publisher.setUp
    signer = Publisher.signer
    pins = Publisher.pins

    def setUp(self):
        self.setUp_base()
        (self.r / 'download/x.apkm').unlink()
        (self.r / 'download/x.apk').write_bytes(b'merged')
        self.pins({'com.x': ['a' * 64]})

    def kind(self, apk_type):
        (self.r / 'src/targets.json').write_text(json.dumps([dict(id='x', enabled=True, package='com.x', apk_name='x', apk_type=apk_type)]))

    def test_prepared_bundle_is_not_read_again(self):
        self.kind('bundle')
        self.assertEqual(pc.check(self.r, 'x', {'PF_SOURCE_READY': 'true'}, self.signer('b' * 64)), 0)
        self.assertEqual(self.seen, [])

    def test_prepared_plain_apk_is_still_checked(self):
        self.kind('apk')
        self.assertEqual(pc.check(self.r, 'x', {'PF_SOURCE_READY': 'true'}, self.signer('b' * 64)), 1)
        self.assertEqual(self.seen, [b'merged'])

    def test_unprepared_bundle_without_its_box_is_still_checked(self):
        self.kind('bundle')
        self.assertEqual(pc.check(self.r, 'x', {}, self.signer('b' * 64)), 1)
        self.assertEqual(pc.check(self.r, 'x', {'PF_SOURCE_READY': 'false'}, self.signer('b' * 64)), 1)

    def test_prepared_bundle_with_its_box_reads_the_box(self):
        self.kind('bundle')
        with zipfile.ZipFile(self.r / 'download/x.apkm', 'w') as z:
            z.writestr('base.apk', b'base')
        self.assertEqual(pc.check(self.r, 'x', {'PF_SOURCE_READY': 'true'}, self.signer('b' * 64)), 1)
        self.assertEqual(self.seen, [b'base'])


if __name__ == '__main__':
    unittest.main()
