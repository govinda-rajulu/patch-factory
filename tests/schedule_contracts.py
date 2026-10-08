"""Schedule contracts: quiet minutes, IST labels, poll-only checks and one writer at a time.

GitHub documents that scheduled runs are delayed at busy times such as the start of
every hour; this repo observed 4-6.5 hour delays on :00/:30 schedules in September 2026.
Quiet minutes reduce, but cannot remove, that queueing. So the daily build (2. Check
new patch) also polls three more times a day. Its first cron is the full daily run;
the others are poll-only: they skip the full shadow observation unless the legacy
poll found something to build, then resolve only the targets Build will consume, and a
concurrency queue stops any overlap.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows'
LINE = re.compile(r'^\s+- cron: "([0-9]{1,2}) ([0-9]{1,2}) ([^"]+)"\s+# ([0-9]{2}):([0-9]{2}) IST\b')
SCHEDULED = {'ci.yml', 'watch.yml', 'agent-watch.yml', 'community-watch.yml', 'keepalive.yml', 'council.yml', 'tooling-watch.yml'}
CRONS_PER_WORKFLOW = {'ci.yml': 4, 'council.yml': 2}  # every other scheduled workflow has exactly one
MAIN_WRITERS = ('keepalive.yml', 'community-watch.yml')
RESOLVE_IF = ("    if: needs.plan.outputs.resolution_matrix != '' && (github.event_name != 'schedule'"
              " || github.event.schedule == '%s' || needs.plan.outputs.count != '0')\n")
RESOLVE_MATRIX = ("      matrix: ${{ fromJSON((github.event_name == 'schedule' && github.event.schedule != '%s')"
                  " && needs.plan.outputs.matrix || needs.plan.outputs.resolution_matrix) }}\n")
REPORT_IF = ("    if: always() && !cancelled() && needs.plan.result == 'success'"
             " && needs.resolve.result != 'skipped'\n")
BUILD_IF = ("    if: always() && !cancelled() && needs.plan.result == 'success'"
            " && needs.plan.outputs.count != '0'\n")
QUEUE = 'concurrency:\n  # A poll must never overlap a running build'
QUEUE_TAIL = '\n  group: daily-poll\n  cancel-in-progress: false\n\njobs:\n'

def cron_lines():
    found = {}
    for path in sorted(WF.glob('*.yml')):
        for line in path.read_text().splitlines():
            if 'cron:' in line:
                found.setdefault(path.name, []).append(line)
    return found

def ist(minute, hour):
    return divmod((hour * 60 + minute + 330) % 1440, 60)

def cron_of(line):
    m = LINE.match(line)
    return '%s %s %s' % (m[1], m[2], m[3])

def job(text, name):
    """The body of one top-level job in a workflow's text."""
    body = text.split('\n  %s:\n' % name, 1)[1]
    return re.split(r'\n  [A-Za-z_][A-Za-z0-9_-]*:\n', body, maxsplit=1)[0]

def poll_problems(text):
    """Why the daily workflow's poll-only wiring is unsafe; [] when it is not."""
    lines = [l for l in text.splitlines() if 'cron:' in l]
    if len(lines) != CRONS_PER_WORKFLOW['ci.yml'] or not all(LINE.match(l) for l in lines):
        return ['cron lines']
    out = []
    primary = cron_of(lines[0])
    if not primary.endswith(' * * *'):
        out.append('first cron is not daily')
    if (RESOLVE_IF % primary) not in job(text, 'resolve'):
        out.append('resolve is not tied to the first cron')
    resolve = job(text, 'resolve')
    if (RESOLVE_MATRIX % primary) not in resolve or resolve.count('matrix: ') != 1:
        out.append('poll-only resolve is not narrowed to the build matrix')
    if REPORT_IF not in job(text, 'dependency_report'):
        out.append('report runs without observations')
    build = job(text, 'build')
    if BUILD_IF not in build or 'needs: [plan, resolve]' not in build:
        out.append('build gate changed')
    if 'github.event.schedule' in build or 'github.event.schedule' in job(text, 'plan'):
        out.append('poll-only schedule changes Plan or Build')
    if text.count(QUEUE) != 1 or text.count(QUEUE_TAIL) != 1 or text.count('group:') != 1:
        out.append('no single queue')
    return out

class Schedules(unittest.TestCase):
    def test_every_schedule_is_labelled_in_ist_and_off_peak(self):
        found = cron_lines()
        self.assertEqual(set(found), SCHEDULED)
        seen = set()
        for name, lines in sorted(found.items()):
            with self.subTest(workflow=name):
                self.assertEqual(len(lines), CRONS_PER_WORKFLOW.get(name, 1))
                for line in lines:
                    m = LINE.match(line)
                    self.assertIsNotNone(m, line)
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

    def test_daily_polls_are_spread_across_the_day(self):
        lines = cron_lines()['ci.yml']
        times = []
        for line in lines:
            m = LINE.match(line)
            self.assertEqual(m[3], '* * *', line)
            times.append(int(m[2]) * 60 + int(m[1]))
        self.assertEqual(len(set(times)), len(times))
        ordered = sorted(times)
        gaps = [b - a for a, b in zip(ordered, ordered[1:])] + [ordered[0] + 1440 - ordered[-1]]
        self.assertGreaterEqual(min(gaps), 4 * 60, gaps)
        self.assertIn('poll-only', lines[1] + lines[2] + lines[3])

    def test_poll_only_runs_skip_full_observation_and_queue(self):
        text = (WF / 'ci.yml').read_text()
        self.assertEqual(poll_problems(text), [])

    def test_poll_checks_catch_unsafe_mutants(self):
        text = (WF / 'ci.yml').read_text()
        primary = cron_of(cron_lines()['ci.yml'][0])
        mutants = {
            'resolve on every poll': text.replace(" || github.event.schedule == '%s'" % primary, ''),
            'resolve tied to a poll-only cron': text.replace("github.event.schedule == '%s'" % primary,
                                                             "github.event.schedule == '23 6 * * *'"),
            'resolve skipped when building': text.replace(" || needs.plan.outputs.count != '0')", ')'),
            'report without observations': text.replace(" && needs.resolve.result != 'skipped'", ''),
            'overlapping runs': text.replace('  group: daily-poll\n', ''),
            'cancelling queue': text.replace('group: daily-poll\n  cancel-in-progress: false',
                                             'group: daily-poll\n  cancel-in-progress: true'),
            'build gated on schedule': text.replace(BUILD_IF, BUILD_IF.rstrip('\n') +
                                                    " && github.event.schedule == '%s'\n" % primary),
            'poll resolves every target': text.replace(RESOLVE_MATRIX % primary,
                                                       '      matrix: ${{ fromJSON(needs.plan.outputs.resolution_matrix) }}\n'),
            'full run narrowed too': text.replace("github.event.schedule != '%s')" % primary,
                                                  "github.event.schedule != '23 6 * * *')"),
            'narrowed on manual runs': text.replace("(github.event_name == 'schedule' && ", "(true && "),
            'fifth cron': text.replace('  workflow_dispatch:\n', '    - cron: "23 9 * * *"  # 14:53 IST\n  workflow_dispatch:\n', 1),
        }
        for label, mutant in mutants.items():
            with self.subTest(mutant=label):
                self.assertNotEqual(mutant, text)
                self.assertNotEqual(poll_problems(mutant), [])

    def test_main_writers_share_one_queue(self):
        block = 'concurrency:\n  # Shared with '
        for name in MAIN_WRITERS:
            with self.subTest(workflow=name):
                text = (WF / name).read_text()
                self.assertIn(block, text)
                self.assertIn('\n  group: main-writer\n  cancel-in-progress: false\n', text)
                self.assertEqual(text.count('group:'), 1)

    def test_readme_states_every_poll_in_ist(self):
        lines = cron_lines()['ci.yml']
        m = LINE.match(lines[0])
        want = '(`%s` UTC = %02d:%02d IST;' % ((cron_of(lines[0]),) + ist(int(m[1]), int(m[2])))
        later = ['%02d:%02d' % ist(int(LINE.match(l)[1]), int(LINE.match(l)[2])) for l in lines[1:]]
        want += ' plus poll-only checks at %s and %s IST' % (', '.join(later[:-1]), later[-1])
        self.assertIn(want, (ROOT / 'README.md').read_text())

if __name__ == '__main__':
    unittest.main()
