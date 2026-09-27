"""Review desk contracts: docs/review stays indexed and the index has no dead links.

Sustain step from the 27 September 2026 5S audit. Adding a record to docs/review
without listing it in docs/review/README.md, or leaving a link to a moved file,
fails Validate.
"""
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESK = ROOT / 'docs' / 'review'
INDEX = DESK / 'README.md'
LINK = re.compile(r'\]\(([^)\s]+)\)')
SCHEME = re.compile(r'^[a-z][a-z0-9+.-]*:')


def local_targets(text):
    """Relative link targets in the index; web links and pure anchors are ignored."""
    found = []
    for target in LINK.findall(text):
        if SCHEME.match(target) or target.startswith('#'):
            continue
        found.append(target.split('#', 1)[0])
    return found


def entries(folder):
    """Direct children of the desk; folders carry a trailing slash."""
    return sorted(p.name + ('/' if p.is_dir() else '') for p in folder.iterdir()
                  if p.name != 'README.md' and not p.name.startswith('.'))


def problems(folder, text):
    targets = local_targets(text)
    listed = set(targets)
    missing = [e for e in entries(folder) if e not in listed]
    dead = []
    for target in targets:
        path = folder / target
        if not path.exists() or (target.endswith('/') and not path.is_dir()):
            dead.append(target)
    return missing, dead


class ReviewDesk(unittest.TestCase):
    def test_every_record_is_indexed_and_every_link_resolves(self):
        self.assertTrue(INDEX.is_file(), 'docs/review/README.md is missing')
        missing, dead = problems(DESK, INDEX.read_text(encoding='utf-8'))
        self.assertEqual(missing, [], 'unlisted in docs/review/README.md')
        self.assertEqual(dead, [], 'dead links in docs/review/README.md')

    def test_coverage_is_not_vacuous(self):
        self.assertGreaterEqual(len(entries(DESK)), 20)
        self.assertGreaterEqual(len(local_targets(INDEX.read_text(encoding='utf-8'))), 20)

    def test_unlisted_record_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'LISTED.md').write_text('x\n')
            (folder / 'NEW-2026-01-01.md').write_text('x\n')
            (folder / 'data').mkdir()
            missing, dead = problems(folder, '[a](LISTED.md)\n')
            self.assertEqual(missing, ['NEW-2026-01-01.md', 'data/'])
            self.assertEqual(dead, [])

    def test_dead_link_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'LISTED.md').write_text('x\n')
            (folder / 'plain').write_text('x\n')
            missing, dead = problems(folder, '[a](LISTED.md) [b](GONE.md) [c](plain/)\n')
            self.assertEqual(dead, ['GONE.md', 'plain/'])
            self.assertEqual(missing, ['plain'])

    def test_web_links_and_anchors_are_not_files(self):
        text = '[w](https://example.com/x.md) [m](mailto:a@b.c) [h](#top) [f](A.md#part)\n'
        self.assertEqual(local_targets(text), ['A.md'])


if __name__ == '__main__':
    unittest.main()
