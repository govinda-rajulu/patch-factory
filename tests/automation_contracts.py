"""Every automation is wired end to end (W14, owner ask 11 Oct 2026: "check automations once if
all connected properly and displays exact"). A workflow that is missing from one of these lists
fails silently: no status refresh, no failure issue, an empty purpose or the wrong page section."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows'
sys.path.insert(0, str(ROOT / 'src/etc'))
import status  # noqa: E402


def flows():
    out = {}
    for p in sorted(WF.glob('*.yml')):
        text = p.read_text(encoding='utf-8')
        name = re.search(r'(?m)^name:\s*["\']?(.+?)["\']?\s*$', text)[1]
        on = text.split('\non:', 1)[1].split('\npermissions:', 1)[0].split('\njobs:', 1)[0].split('\nconcurrency:', 1)[0]
        events = set(re.findall(r'(?m)^  ([a-z_]+):', on))
        out[p.name] = dict(name=name, events=events, text=text)
    return out


def listed(text):
    return re.findall(r'"([^"]+)"', re.search(r'(?m)^\s*workflows:\s*\[(.*)\]\s*$', text)[1])


class Automations(unittest.TestCase):
    def setUp(self):
        self.f = flows()
        self.names = {v['name']: k for k, v in self.f.items()}

    def test_every_workflow_has_a_purpose_line_on_the_page(self):
        self.assertEqual(sorted(set(self.f) - set(status.PURPOSE)), [])
        self.assertEqual(sorted(set(status.PURPOSE) - set(self.f)), [])

    def test_status_page_refreshes_after_every_workflow(self):
        own = self.f['status.yml']
        wanted = {v['name'] for k, v in self.f.items() if k not in ('status.yml', 'notify-failure.yml')}
        self.assertEqual(sorted(wanted - set(listed(own['text']))), [])

    def test_failure_issues_cover_every_scheduled_or_dispatched_flow_they_can_read(self):
        text = self.f['notify-failure.yml']['text']
        names = listed(text)
        permitted = dict(re.findall(r'\["\.github/workflows/([a-z-]+\.yml)", "([^"]+)"\]', text))
        self.assertEqual(sorted(permitted.values()), sorted(names))
        for file, name in permitted.items():
            self.assertEqual(self.f[file]['name'], name)
            # notify-failure refuses pull_request and workflow_run events; such a flow would turn it red.
            self.assertFalse(self.f[file]['events'] & {'pull_request', 'workflow_run'}, file)
        should = {v['name'] for k, v in self.f.items()
                  if v['events'] & {'schedule', 'workflow_dispatch'} and not v['events'] & {'pull_request', 'workflow_run'}}
        self.assertEqual(sorted(should - set(names)), [])

    def test_portal_sections_name_real_workflows(self):
        js = (ROOT / 'docs/portal.js').read_text(encoding='utf-8')
        for const in ('BUILD_FLOWS', 'WATCH_FLOWS'):
            names = re.findall(r"'([^']+)'", re.search(r'const %s=\[(.*?)\];' % const, js)[1])
            self.assertEqual([n for n in names if n not in self.names], [], const)
        watch = re.findall(r"\['([a-z-]+\.yml)','([^']+)'", re.search(r'const WATCH=\[(.*?)\];\n', js)[1])
        for file, name in watch:
            self.assertEqual(self.f[file]['name'], name)
        for file in ('agent-watch.yml', 'watch.yml', 'community-watch.yml', 'tooling-watch.yml', 'selection-watch.yml'):
            self.assertIn(self.f[file]['name'], js, file)

    def test_every_schedule_is_in_the_generated_schedule_table(self):
        table = (ROOT / 'docs/SCHEDULES.md').read_text(encoding='utf-8')
        for file, v in self.f.items():
            if 'schedule' in v['events']:
                self.assertIn('`%s`' % file, table)


class ActionPins(unittest.TestCase):
    def test_no_test_hardcodes_an_action_commit(self):
        """W15: Dependabot moves action pins weekly; a test holding one exact sha failed every
        bump (Validate #404 on PR #185). Tests match the shape ([0-9a-f]{40}), never the value."""
        bad = []
        for f in sorted((ROOT / 'tests').glob('*.py')) + sorted((ROOT / 'tests').glob('*.cjs')):
            for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
                if re.search(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}', line):
                    bad.append('%s:%d' % (f.name, n))
        self.assertEqual(bad, [])

    def test_dependabot_asks_for_no_missing_label(self):
        self.assertNotIn('labels:', (ROOT / '.github/dependabot.yml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
