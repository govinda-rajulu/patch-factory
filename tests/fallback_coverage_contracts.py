"""Owner decision 30 Oct 2026: fallback releases need a 50% patch-coverage floor."""
import base64
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/build'))
sys.path.insert(0, str(ROOT / 'src/etc'))
import release_notes as notes  # noqa: E402
import status  # noqa: E402


def doc(target='fixture', tag='fixture-v4.2.1-b2026103000000000000100000000000001', patches=None, **extra):
    value = {'schema': 1, 'target': target, 'version': '4.2.1', 'source': 'a' * 40,
             'sha256': 'b' * 64, 'signer': 'c' * 64, 'package': 'org.fixture',
             'tag': tag, 'provider': 'primary', 'bundle': '1.0', 'apk': 'fixture-v4.2.1-arm64-v8a.apk',
             'label': 'Fixture', 'arch': 'arm64-v8a', 'patches': patches or ['A', 'B', 'C', 'D'],
             'min_sdk': 29, 'bytes': 1000001}
    value.update(extra)
    return value


def row(value, published='2026-10-29T00:00:00Z'):
    encoded = base64.b64encode(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).decode()
    return {'id': hash(value['tag']) & 0xffff, 'tag_name': value['tag'], 'draft': False,
            'prerelease': False, 'published_at': published,
            'body': '[pf-release-v1]: # "' + encoded + '"'}


class Coverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        inc = self.root / 'src/patches/primary'
        inc.mkdir(parents=True)
        inc.joinpath('include-patches').write_text('A\nB\nC\nD\n')
        self.target = {'id': 'fixture', 'candidates': [{'name': 'primary', 'patch_dir': 'primary'},
                                                        {'name': 'backup', 'fallback': True, 'patch_dir': 'backup'}]}
        self.current = doc(patches=['A'], fallback='backup', provider='backup')
        self.addCleanup(self.tmp.cleanup)

    def test_below_floor_is_named_and_refused(self):
        out = io.StringIO()
        with redirect_stdout(out):
            why = notes.publish_guard(self.current, [row(doc())], True, self.target, self.root)
        self.assertIn('below', why)
        self.assertIn('FALLBACK_BELOW_FLOOR target=fixture provider=backup patches=1 primary=4 pct=25', out.getvalue())
        with redirect_stdout(out := io.StringIO()):
            why = notes.publish_guard(self.current, [row(doc())], True, self.target, self.root)
        self.assertIn('test-only and was not published', why)
        self.assertIn('patches=1 primary=4 pct=25', out.getvalue())

    def test_above_floor_gets_banner_metadata_and_missing_primary_names(self):
        current = dict(self.current, patches=['A', 'B', 'C'], provider='backup')
        with redirect_stdout(io.StringIO()):
            self.assertIsNone(notes.publish_guard(current, [row(doc())], True, self.target, self.root))
        current['coverage'] = current['_coverage']['pct']
        body = notes.render(current)
        self.assertTrue(body.startswith('FALLBACK BUILD: backup, 3 of 4 patches (75%). Read before use.'))
        self.assertIn('- D', body)
        decoded = notes.decode(body, current['tag'], 'fixture')
        self.assertEqual((decoded['fallback'], decoded['coverage']), ('backup', 75))

    def test_no_primary_uses_configured_include_count_and_says_basis(self):
        current = dict(self.current, patches=['A', 'B', 'C'], provider='backup')
        with redirect_stdout(out := io.StringIO()):
            self.assertIsNone(notes.publish_guard(current, [], True, self.target, self.root))
        self.assertIn('primary=4', out.getvalue())
        self.assertIn('basis=configured', out.getvalue())
        self.assertIn('No primary release on the shelf', notes.render(current))

    def test_old_metadata_without_fallback_or_coverage_still_parses(self):
        old = doc()
        self.assertNotIn('fallback', notes.checked(old))
        self.assertNotIn('coverage', notes.checked(old))

    def test_unreadable_inventory_remains_blind_refusal(self):
        self.assertIn('not published blind', notes.publish_guard(self.current, None, True, self.target, self.root))


class StatusFallback(unittest.TestCase):
    def test_status_tags_fallback_release(self):
        value = doc(patches=['A', 'B'], fallback='backup', coverage=50)
        release = row(value)

        class Reader:
            problems = []
            def get(self, path, label):
                return [release]

        latest, complete = status.releases(Reader(), {'fixture': 'fixture'})
        self.assertTrue(complete)
        self.assertEqual(latest['fixture']['fallback'], 'backup')
        self.assertEqual(latest['fixture']['coverage'], 50)
        app = {'id': 'fixture', 'label': 'Fixture', 'release': latest['fixture']}
        self.assertTrue(bool(app['release'].get('fallback')))
        # The build() app shape contains the user-facing tag; assert the source contract too.
        source = (ROOT / 'src/etc/status.py').read_text()
        self.assertIn("'tags': ['on fallback'] if on_fallback else []", source)


if __name__ == '__main__':
    unittest.main()
