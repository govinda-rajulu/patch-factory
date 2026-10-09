"""docs/SCHEDULES.md is generated from the workflow files and stays current (packet W7)."""
import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pf_schedules', ROOT / 'src/etc/schedules.py')
sch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sch)


class Schedules(unittest.TestCase):
    def test_table_is_current_and_checked_by_validate(self):
        x = subprocess.run([sys.executable, 'src/etc/schedules.py', '--check'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(x.returncode, 0, x.stdout)
        self.assertIn('run: python3 src/etc/schedules.py --check', (ROOT / '.github/workflows/validate.yml').read_text())

    def test_every_cron_has_one_row_with_its_ist_time(self):
        crons = []
        for wf in (ROOT / '.github/workflows').glob('*.yml'):
            crons += re.findall(r'cron: "([0-9]+) ([0-9]+) [^"]+"\s+# ([0-9]{2}:[0-9]{2}) IST', wf.read_text())
        table = (ROOT / 'docs/SCHEDULES.md').read_text()
        rows = [l for l in table.splitlines() if re.match(r'^\| [0-9]{2}:[0-9]{2} \|', l)]
        self.assertEqual(len(rows), len(crons))
        for minute, hour, ist in crons:
            total = (int(hour) * 60 + int(minute) + 330) % 1440
            self.assertEqual('%02d:%02d' % (total // 60, total % 60), ist)
            self.assertTrue(any(r.startswith('| %s |' % ist) for r in rows), ist)

    def test_stale_table_fails_the_check(self):
        text = sch.render()
        self.assertIn('| 17:53 | daily | 2. Check new patch (`ci.yml`) | Full daily check', text)
        self.assertEqual(text.count('Quick poll'), 3)
        original = sch.OUT.read_bytes()
        try:
            sch.OUT.write_bytes(original.replace(b'17:53', b'17:54'))
            self.assertEqual(sch.main(['--check']), 1)
        finally:
            sch.OUT.write_bytes(original)

    def test_guide_links_the_table(self):
        self.assertIn('[SCHEDULES.md](SCHEDULES.md)', (ROOT / 'docs/guide.md').read_text())


if __name__ == '__main__':
    unittest.main()
