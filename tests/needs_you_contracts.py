import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import needs_you as n  # noqa: E402
import community_model as model  # noqa: E402


class Renderer(unittest.TestCase):
    def test_empty_day_is_one_plain_line(self):
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name in n.ISSUES:
                p = Path(d) / (name + '.md'); p.write_text('# report: OK\n'); paths[name] = p
            body = n.render(paths)
        self.assertIn('**Needs you:** nothing needs you today.', body)
        self.assertNotIn('## Decide', body)

    def test_groups_decide_install_fix_and_keeps_reports(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            files = {
                'selection': '# Selection watch: NEEDS YOU\n\n## Needs you\n\n- add or skip Name\n',
                'tooling': '# Tooling watch\n\nnew update available\n',
                'nightly': '## Nightly Watch: UNKNOWN\n',
                'provider': '# Provider watch: OK\n',
                'community': '## Provider ranker\n**Needs you:** choose whether to switch.\n- **app**: better provider\n',
            }
            for name, text in files.items(): (p / (name + '.md')).write_text(text)
            body = n.render({name: p / (name + '.md') for name in n.ISSUES})
        self.assertLess(body.index('## Decide'), body.index('## Install'))
        self.assertLess(body.index('## Install'), body.index('## Fix'))
        self.assertIn('## FYI', body)
        self.assertIn('add or skip Name', body)
        self.assertNotIn('What this watch does not check', body)

    def test_each_watch_source_reaches_its_owner_group(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            files = {
                "selection": "## Needs you\n\n- decide whether to add or skip a patch\n",
                "tooling": "# Tooling watch\n\nupdate available\n",
                "nightly": "## Nightly Watch: UNKNOWN\n",
                "provider": "# Provider watch: FAILED\nprovider could not be read\n",
                "community": "## Provider ranker\n**Needs you:** choose whether to switch.\n- **app**: better provider\n",
            }
            for name, text in files.items(): (p / (name + ".md")).write_text(text)
            body = n.render({name: p / (name + ".md") for name in n.ISSUES})
        self.assertIn("## Decide", body)
        self.assertIn("## Install", body)
        self.assertIn("## Fix", body)
        self.assertIn("## FYI", body)
        self.assertIn("decide whether to add", body)
        self.assertIn("install any update", body)
        self.assertIn("Nightly reported", body)
        self.assertIn("Provider reported", body)

    def test_changed_issue_edits_then_comments_and_unchanged_is_quiet(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if args[1:3] == ['issue', 'list']:
                return SimpleNamespace(returncode=0, stdout=json.dumps([{'number': 9, 'title': 'Needs you', 'body': 'old', 'user': {'type': 'Bot'}}]), stderr='')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        self.assertEqual(n.deliver('new\n', run=run), 'EDITED')
        self.assertEqual([x[1:3] for x in calls], [['issue', 'list'], ['issue', 'edit'], ['issue', 'comment']])
        calls.clear()
        def same(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout=json.dumps([{'number': 9, 'title': 'Needs you', 'body': 'new\n', 'user': {'type': 'Bot'}}]), stderr='')
        self.assertEqual(n.deliver('new\n', run=same), 'UNCHANGED')
        self.assertEqual(len(calls), 1)


class Ranker(unittest.TestCase):
    def test_official_first_and_better_flag_only_for_a_real_alternative(self):
        index = {"bundles": [
            {"source":"github", "repo":"community/patches", "patches":[{"name":"a", "compatiblePackagesKey":0}, {"name":"b", "compatiblePackagesKey":0}, {"name":"c", "compatiblePackagesKey":0}], "targetApps":["com.x"]},
            {"source":"github", "repo":"MorpheApp/morphe-patches", "patches":[{"name":"official", "compatiblePackagesKey":1}], "targetApps":["com.x"]},
        ], "compatibilities": [
            [{"packageName":"com.x", "targets":[{"version":"1"}]}],
            [{"packageName":"com.x", "targets":[{"version":"2"}]}],
        ]}
        target = [{"id":"x", "enabled":True, "package":"com.x", "current_version":"2", "candidates":[{"owner":"community", "repo":"patches"}]}]
        row = model.rank_providers(index, target)[0]
        self.assertEqual(row["providers"][0]["repo"], "MorpheApp/morphe-patches")
        self.assertTrue(row["better_exists"])
        self.assertTrue(row["better"][0]["supports_current"])

    def test_configured_official_provider_does_not_flag_a_weaker_other(self):
        index = {"bundles": [
            {"source":"github", "repo":"MorpheApp/morphe-patches", "patches":[{"name":"official", "compatiblePackagesKey":0}], "targetApps":["com.x"]},
            {"source":"github", "repo":"community/patches", "patches":[{"name":"a", "compatiblePackagesKey":0}], "targetApps":["com.x"]},
        ], "compatibilities": [[{"packageName":"com.x", "targets":[{"version":"2"}]}]]}
        target = [{"id":"x", "enabled":True, "package":"com.x", "current_version":"2", "candidates":[{"owner":"MorpheApp", "repo":"morphe-patches"}]}]
        self.assertFalse(model.rank_providers(index, target)[0]["better_exists"])


if __name__ == '__main__':
    unittest.main()
