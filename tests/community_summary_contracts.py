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


if __name__ == '__main__':
    unittest.main()
