"""run_log.py: key lines come from what a step printed, never from its echoed script (W9, L042)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('run_log', ROOT / 'src/etc/run_log.py')
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)

T = '2026-10-09T13:20:01.1234567Z '
JOB, STEP = 'Patch linkedin', 'Patch apk'
# Shaped like `gh run view --log`: job, step, timestamp, then the runner's text.
LOG = '\n'.join(JOB + '\t' + STEP + '\t' + T + x for x in [
    '##[group]Run bash src/build/build.sh linkedin',
    'bash src/build/build.sh linkedin',
    'echo "::notice::VERSION_STEP_DOWN step=$N from=$OLD to=$NEW"',
    'shell: /usr/bin/bash -e {0}',
    'env:',
    '  VERSION_STEP_DOWN_MAX: 3',
    '##[endgroup]',
    'resolve: picked 4.1.1258',
    'minSdkVersion=32 ceiling=29',
    '##[notice]VERSION_STEP_DOWN step=1 from=4.1.1258 to=4.1.1255.1 source=provider',
    'minSdkVersion=29',
    '##[group]Run echo done',
    'echo "minSdkVersion fake"',
    '##[endgroup]',
]) + '\n'


class RunLog(unittest.TestCase):
    def test_echoed_script_lines_are_not_key_lines(self):
        got = rl.key_lines(LOG, ['VERSION_STEP_DOWN', 'minSdkVersion'])
        self.assertEqual(got, ['Patch apk | minSdkVersion=32 ceiling=29',
                               'Patch apk | ##[notice]VERSION_STEP_DOWN step=1 from=4.1.1258 to=4.1.1255.1 source=provider',
                               'Patch apk | minSdkVersion=29'])
        self.assertFalse(any('echo' in g or '$N' in g or 'MAX' in g for g in got))

    def test_a_plain_grep_would_have_kept_the_noise(self):
        # Negative control: the W8 way (substring match on every line) picks up 3 script lines.
        plain = [l for l in LOG.splitlines() if 'VERSION_STEP_DOWN' in l or 'minSdkVersion' in l]
        self.assertEqual(len(plain), 6)
        self.assertEqual(len(rl.key_lines(LOG, ['VERSION_STEP_DOWN', 'minSdkVersion'])), 3)

    def test_raw_job_log_without_job_and_step_columns(self):
        raw = '\n'.join(T + x for x in ['##[group]Run x', 'grep MARK', '##[endgroup]', 'MARK found']) + '\n'
        self.assertEqual(rl.key_lines(raw, ['MARK']), ['MARK found'])

    def test_limit_and_cli_exit_codes(self):
        many = ''.join(JOB + '\t' + STEP + '\t' + T + 'hit %d\n' % n for n in range(9))
        self.assertEqual(len(rl.key_lines(many, ['hit'], limit=4)), 4)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'run.log'
            p.write_text(LOG, encoding='utf-8')
            self.assertEqual(rl.main([str(p), 'minSdkVersion']), 0)
            self.assertEqual(rl.main([str(p), 'NOT_IN_THE_LOG']), 1)
            self.assertEqual(rl.main([str(p), 'shell: /usr/bin/bash']), 1)


if __name__ == '__main__':
    unittest.main()
