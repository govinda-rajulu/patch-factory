"""Status page data must name real workflows: a misspelt workflow_run name never fires and never errors."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows'


def workflow_names():
    names = {}
    for p in sorted(WF.glob('*.yml')):
        m = re.search(r'(?m)^name:\s*["\']?(.+?)["\']?\s*$', p.read_text(encoding='utf-8'))
        if m:
            names[m[1]] = p.name
    return names


class StatusWorkflows(unittest.TestCase):
    def test_every_listed_workflow_exists(self):
        text = (WF / 'status.yml').read_text(encoding='utf-8')
        m = re.search(r'(?m)^\s*workflows:\s*\[(.*)\]\s*$', text)
        self.assertIsNotNone(m, 'status.yml has no one-line workflows: [...] list')
        listed = re.findall(r'"([^"]+)"', m[1])
        self.assertTrue(listed)
        known = workflow_names()
        self.assertEqual([n for n in listed if n not in known], [])

    def test_status_does_not_trigger_itself(self):
        text = (WF / 'status.yml').read_text(encoding='utf-8')
        own = re.search(r'(?m)^name:\s*["\']?(.+?)["\']?\s*$', text)[1]
        self.assertNotIn('"%s"' % own, re.search(r'(?m)^\s*workflows:\s*\[(.*)\]', text)[1])


if __name__ == '__main__':
    unittest.main()
