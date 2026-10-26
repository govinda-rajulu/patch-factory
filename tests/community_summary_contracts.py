"""Community summaries count one source/repository identity once."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OneProviderPerRepository(unittest.TestCase):
    def fixture(self, root):
        (root / 'src/community').mkdir(parents=True)
        (root / 'src').mkdir(exist_ok=True)
        (root / 'src/targets.json').write_text(json.dumps([
            {'id': 'app', 'enabled': True, 'package': 'com.example.app',
             'candidates': [{'owner': 'wired', 'repo': 'mine'}]}
        ]))
        bundle = lambda repo, patch: {'source': 'github', 'repo': repo, 'name': repo,
                                      'patches': [{'name': patch, 'compatiblePackagesKey': 0}]}
        index = {'compatibilities': [{'packageName': 'com.example.app'}],
                 'bundles': [bundle('Owner/Repo', 'One'), bundle('owner/repo', 'Two')]}
        (root / 'src/community/bundles.json').write_text(json.dumps(index))
        return index

    def run_script(self, script, *args, cwd=None):
        return subprocess.run(['python3', str(ROOT / 'src/etc' / script), *args], cwd=cwd,
                              text=True, capture_output=True, check=True).stdout

    def test_discover_reports_duplicate_repository_as_one_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = self.fixture(root)
            path = root / 'index.json'
            path.write_text(json.dumps(index))
            out = self.run_script('community_discover.py', str(path), cwd=root)
            self.assertIn('index knows 1 provider(s)', out)
            self.assertIn('total unwired providers covering your apps: 1', out)

    def test_all_reports_duplicate_repository_as_one_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            out = self.run_script('community_all.py', cwd=root)
            self.assertIn('(1 provider(s) in the index)', out)
            self.assertIn('unwired provider/app pairs: 1', out)


    def test_equivalent_compatibility_rows_count_one_patch(self):
        # W16o round 3: the live index doubles a repository with the same patch under a
        # second, equivalent compatibility row; the summaries count it once, like the model.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            row = {'packageName': 'com.example.app'}
            patch = lambda key: {'name': 'Same', 'compatiblePackagesKey': key}
            index = {'compatibilities': [row, dict(row)],
                     'bundles': [{'source': 'github', 'repo': 'owner/repo', 'name': 'r', 'patches': [patch(0)]},
                                 {'source': 'github', 'repo': 'Owner/Repo', 'name': 'r', 'patches': [patch(1)]}]}
            (root / 'src/community/bundles.json').write_text(json.dumps(index))
            path = root / 'index.json'
            path.write_text(json.dumps(index))
            out = self.run_script('community_discover.py', str(path), cwd=root)
            self.assertIn('1 patches for this app', out)
            out = self.run_script('community_all.py', cwd=root)
            self.assertRegex(out, r'owner/repo.*\b1 patches|Owner/Repo.*\b1 patches')

if __name__ == '__main__':
    unittest.main()
