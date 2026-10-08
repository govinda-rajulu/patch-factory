"""CHANGELOG generator: squash merges and merge commits both keep their pull request number."""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('changelog', ROOT / 'src/etc/changelog.py')
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)


class Changelog(unittest.TestCase):
    def test_squash_subject_keeps_number(self):
        self.assertEqual(cl.parse('abc1234', '2026-10-07', 'handover 7 Oct (#157)'),
                         ('2026-10-07', 'abc1234', 'handover 7 Oct', 157))

    def test_merge_commit_uses_title_and_number(self):
        row = cl.parse('5e648da', '2026-10-08', 'Merge pull request #158 from govinda-rajulu/packet/w2',
                       '\npacket W2: two-step app changes\n')
        self.assertEqual(row, ('2026-10-08', '5e648da', 'packet W2: two-step app changes', 158))

    def test_bot_commit_stays_direct(self):
        self.assertEqual(cl.parse('0a0a0a0', '2026-10-08', 'keepalive')[3], None)
        self.assertIn('direct `0a0a0a0`', cl.render([cl.parse('0a0a0a0', '2026-10-08', 'keepalive')]))

    def test_real_merge_commit_history(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*a):
                subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', *a],
                               cwd=d, check=True, capture_output=True)
            git('init', '-q', '-b', 'main')
            Path(d, 'a').write_text('1')
            git('add', 'a'); git('commit', '-q', '-m', 'first change (#1)')
            git('switch', '-q', '-c', 'feature')
            Path(d, 'b').write_text('2')
            git('add', 'b'); git('commit', '-q', '-m', 'inner commit not listed')
            git('switch', '-q', 'main')
            git('merge', '-q', '--no-ff', 'feature', '-m', 'Merge pull request #2 from o/feature', '-m', 'second change title')
            old = os.getcwd()
            os.chdir(d)
            try:
                rows = cl.history('main')
            finally:
                os.chdir(old)
        self.assertEqual([(r[2], r[3]) for r in rows], [('second change title', 2), ('first change', 1)])


if __name__ == '__main__':
    unittest.main()
