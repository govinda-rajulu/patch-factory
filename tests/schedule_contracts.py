"""Schedule contracts: quiet minutes, IST labels and one main writer at a time.

GitHub documents that scheduled runs are delayed at busy times such as the start of
every hour; this repo observed 4-6.5 hour delays on :00/:30 schedules in September 2026.
Quiet minutes reduce, but cannot remove, that queueing.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows'
LINE = re.compile(r'^    - cron: "([0-9]{1,2}) ([0-9]{1,2}) ([^"]+)"  # ([0-9]{2}):([0-9]{2}) IST\b')
SCHEDULED = {'ci.yml', 'watch.yml', 'agent-watch.yml', 'community-watch.yml', 'keepalive.yml'}
MAIN_WRITERS = ('keepalive.yml', 'community-watch.yml')


def cron_lines():
    found = {}
    for path in sorted(WF.glob('*.yml')):
        for line in path.read_text().splitlines():
            if 'cron:' in line:
                found.setdefault(path.name, []).append(line)
    return found


def ist(minute, hour):
    return divmod((hour * 60 + minute + 330) % 1440, 60)


class Schedules(unittest.TestCase):
    def test_every_schedule_is_labelled_in_ist_and_off_peak(self):
        found = cron_lines()
        self.assertEqual(set(found), SCHEDULED)
        seen = set()
        for name, lines in sorted(found.items()):
            with self.subTest(workflow=name):
                self.assertEqual(len(lines), 1)
                m = LINE.match(lines[0])
                self.assertIsNotNone(m, lines[0])
                minute, hour = int(m[1]), int(m[2])
                self.assertTrue(0 <= minute <= 59 and 0 <= hour <= 23)
                self.assertNotIn(minute, (0, 15, 30, 45))
                self.assertEqual((int(m[4]), int(m[5])), ist(minute, hour))
                self.assertNotIn((minute, hour), seen)
                seen.add((minute, hour))

    def test_label_check_rejects_a_wrong_ist_comment(self):
        bad = '    - cron: "23 12 * * *"  # 18:00 IST daily'
        m = LINE.match(bad)
        self.assertNotEqual((int(m[4]), int(m[5])), ist(int(m[1]), int(m[2])))
        self.assertIsNone(LINE.match("    - cron: '23 12 * * *'"))

    def test_main_writers_share_one_queue(self):
        block = 'concurrency:\n  # Shared with '
        for name in MAIN_WRITERS:
            with self.subTest(workflow=name):
                text = (WF / name).read_text()
                self.assertIn(block, text)
                self.assertIn('\n  group: main-writer\n  cancel-in-progress: false\n', text)
                self.assertEqual(text.count('group:'), 1)

    def test_readme_states_the_daily_build_in_ist(self):
        m = LINE.match(cron_lines()['ci.yml'][0])
        cron = '%s %s %s' % (m[1], m[2], m[3])
        want = '(`%s` UTC = %02d:%02d IST;' % ((cron,) + ist(int(m[1]), int(m[2])))
        self.assertIn(want, (ROOT / 'README.md').read_text())


if __name__ == '__main__':
    unittest.main()
