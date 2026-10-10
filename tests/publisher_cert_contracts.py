"""S2 publisher pins (packet W13): observe when unpinned, refuse a mismatch, pass unreadable."""
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

    def test_unreadable_passes(self):
        self.pins({'com.x': ['a' * 64]})
        def bad(root, apk, env):
            raise ValueError('apksigner unavailable')
        self.assertEqual(pc.check(self.r, 'x', {}, bad), 0)

    def test_plain_apk_is_read_directly(self):
        (self.r / 'download/x.apkm').unlink()
        (self.r / 'download/x.apk').write_bytes(b'plain')
        self.assertEqual(pc.check(self.r, 'x', {}, self.signer('a' * 64)), 0)
        self.assertEqual(self.seen, [b'plain'])


if __name__ == '__main__':
    unittest.main()
