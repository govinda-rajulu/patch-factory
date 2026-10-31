"""W17a Sustain checks: doc links, page-weight budget, advisory prose lint (knowledge/style/)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import doclinks  # noqa: E402
import page_weight  # noqa: E402
import prose_lint  # noqa: E402


class DocLinks(unittest.TestCase):
    def repo(self, files):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        r = Path(t.name)
        for name, text in files.items():
            (r / name).parent.mkdir(parents=True, exist_ok=True)
            (r / name).write_text(text)
        subprocess.run(['git', 'init', '-q'], cwd=r, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=r, check=True)
        return r

    def test_broken_link_fails_and_good_ones_pass(self):
        r = self.repo({'a.md': '[ok](b/c.md#x) [web](https://x.invalid/y) [top](#h) `[code](nope.md)`\n'
                               '```\n[fenced](nope.md)\n```\n[bad](missing.md)\n', 'b/c.md': '[up](../a.md)\n'})
        self.assertEqual(doclinks.broken(str(r)), [('a.md', 'missing.md')])
        self.assertEqual(doclinks.main([], str(r)), 1)

    def test_link_outside_the_repo_is_broken(self):
        r = self.repo({'a.md': '[out](../../etc/passwd)\n'})
        self.assertEqual(len(doclinks.broken(str(r))), 1)

    def test_absolute_link_is_broken(self):
        r = self.repo({'a.md': '[abs](/etc/passwd)\n'})
        self.assertEqual(len(doclinks.broken(str(r))), 1)

    def test_repository_links_resolve(self):
        self.assertEqual(doclinks.broken(str(ROOT)), [])


class PageWeight(unittest.TestCase):
    def test_under_budget_and_counts_only_the_latin_font(self):
        parts = page_weight.first_load(str(ROOT))
        self.assertLessEqual(sum(parts.values()), page_weight.BUDGET)
        self.assertIn('docs/assets/manrope-v4.504-latin.woff2', parts)
        self.assertNotIn('docs/assets/manrope-v4.504.woff2', parts)
        self.assertIn('docs/portal.js', parts)
        self.assertIn('docs/assets/microg.png', parts)

    def test_font_outside_docs_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            (r / 'docs/assets').mkdir(parents=True)
            (r / 'docs/index.html').write_text('@font-face{src:url("/etc/passwd");unicode-range:U+0000-00FF}')
            (r / 'docs/portal.js').write_text('')
            with self.assertRaises(ValueError):
                page_weight.first_load(str(r))

    def test_budget_is_a_deliberate_number(self):
        self.assertEqual(page_weight.BUDGET, 350_000)


class ProseLint(unittest.TestCase):
    def test_finds_tells_and_skips_code(self):
        text = 'One \u2014 two.\nThis is crucial.\n`a \u2014 b` https://x.invalid/\u2014\n```\nleverage\n```\n|---|---|\n'
        kinds = [f[2] for f in prose_lint.findings('x.md', text)]
        self.assertEqual(kinds, ['dash', 'stock'])

    def test_never_fails(self):
        self.assertEqual(prose_lint.main([str(ROOT / 'AGENTS.md')]), 0)


if __name__ == '__main__':
    unittest.main()
