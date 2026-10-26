"""W16i (owner, 25 Oct 2026): chained workflows wait for a burst to settle and run once;
removed names stay out; an old bundle that works is information, not a warning."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows'
sys.path.insert(0, str(ROOT / 'src/etc'))
import selection_watch as sw  # noqa: E402

MAIN_ONLY = ("github.event.workflow_run.conclusion == 'success' && github.event.workflow_run.head_branch == 'main' "
             "&& github.event.workflow_run.head_repository.full_name == github.repository")


def job(text, name):
    m = re.search(r'^  %s:\n(.*?)(?=^  [a-z][a-z-]*:\n|\Z)' % re.escape(name), text, re.S | re.M)
    assert m, name
    return m.group(1)


class Settle(unittest.TestCase):
    def test_status_waits_and_the_newest_run_wins(self):
        # W16k: no cancel-in-progress (Notify runs inside and must never be cancelled); after the
        # wait an older run sees a newer one and stops quietly, so no run ends "cancelled".
        text = (WF / 'status.yml').read_text()
        head = text[:text.index('\njobs:')]
        self.assertNotIn('cancel-in-progress', head)
        self.assertIn('    branches: [main]\n', head)
        self.assertIn("- name: Let related runs settle\n        if: github.event_name == 'workflow_run'\n        run: sleep 180", text)
        self.assertLess(text.index('Let related runs settle'), text.index('- name: Newest run publishes'))
        self.assertLess(text.index('- name: Newest run publishes'), text.index('Checkout main (the reader that runs)'))
        gate = "if: steps.newest.outputs.newer == '0' || github.event_name != 'workflow_run'"
        self.assertEqual(text.count(gate), 3)
        self.assertIn('|| newer=0', text)  # an API hiccup publishes rather than hiding the page

    def test_qualify_settles_only_on_main_successes(self):
        text = (WF / 'qualify-baselines.yml').read_text()
        self.assertIn('    branches: [main]\n', text[:text.index('\njobs:')])  # W16k
        settle, qualify = job(text, 'settle'), job(text, 'qualify')
        self.assertIn('if: ' + MAIN_ONLY, settle)
        self.assertIn('group: qualify-settle\n      cancel-in-progress: true', settle)
        self.assertIn('sleep 180', settle)
        self.assertIn('needs: settle', qualify)
        self.assertIn("if: needs.settle.result == 'success'", qualify)
        self.assertIn('group: qualify\n      cancel-in-progress: false', qualify)

    def test_rule_merge_runs_on_schedule_and_request_only(self):
        # W16k: bot-started runs never woke it (L069); owner smokes started 30 passes a day for nothing.
        text = (WF / 'rule-merge.yml').read_text()
        head = text[:text.index('\njobs:')]
        self.assertNotIn('workflow_run', head)
        self.assertNotIn('\nconcurrency:', head)
        self.assertEqual(head.count('- cron:'), 2)
        merge = job(text, 'merge')
        self.assertNotIn('needs:', merge)
        self.assertIn('group: rule-merge\n      cancel-in-progress: false', merge)
        self.assertIn('PF_RULE_MERGE_PATIENCE', merge)

    def test_failure_notices_are_never_merged(self):
        # One notify run per finished run: merging them could hide app A's failure behind app B's success.
        text = (WF / 'notify-failure.yml').read_text()
        self.assertIn('group: notify-${{ github.event.workflow_run.workflow_id }}\n      cancel-in-progress: false', text)
        self.assertNotIn('sleep', text)


class Quiet(unittest.TestCase):
    def test_old_bundle_is_a_log_line_not_a_warning(self):
        text = (ROOT / 'src/build/resolve.sh').read_text()
        line = [l for l in text.splitlines() if '"$AGE" -gt "$MAXAGE"' in l]
        self.assertEqual(len(line), 1)
        self.assertNotIn('::warning::', line[0])
        self.assertIn('information only, the applied-count gate decides', line[0])


class RemovedStaysOut(unittest.TestCase):
    def test_pr_243_names_are_decided(self):
        # W16j: newuser7171 left the repo (never built on 12.10.4) and is a dropped provider.
        self.assertFalse((ROOT / 'src/patches/telegram-newuser7171').exists())
        self.assertIn('newuser7171/telegram-morphe-patches-', (ROOT / 'src/patches/DECISIONS.json').read_text())
        for folder, name in (('truecaller-heval99', 'Restore classic call log'),
                             ('truecaller-heval99', 'Use SMS for verification codes')):
            exc = sw.lines(ROOT / 'src/patches' / folder / 'exclude-patches')
            inc = [l.split('|', 1)[0] for l in sw.lines(ROOT / 'src/patches' / folder / 'include-patches')]
            self.assertIn(name, exc, folder)
            self.assertNotIn(name, inc, folder)

    def test_excluded_names_never_wait_or_adopt(self):
        import json
        rows = sw.provider_watch.inventory(json.loads((ROOT / 'src/targets.json').read_text()))
        rows = [r for r in rows if (r['target'], r['name']) in (('telegram', 'newuser7171'), ('truecaller-combo', 'heval99'))]
        observed = {r['target'] + '/' + r['name']: sw.lines(ROOT / 'docs/review/providers' / r['baseline']) for r in rows}
        plan = sw.plan_names(ROOT, rows, observed, {})
        names = {w['name'] for w in plan['waiting'] + plan['backlog']}
        for n in ('Bypass channel restrictions', 'Restore classic call log', 'Use SMS for verification codes'):
            self.assertNotIn(n, names)


if __name__ == '__main__':
    unittest.main()
