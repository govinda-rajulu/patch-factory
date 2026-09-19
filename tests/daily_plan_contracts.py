import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('daily_plan_contract',
                                            ROOT / 'src/etc/daily_plan.py')
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)

class DailyPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pf-plan-contract-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'src/etc').mkdir(parents=True)
        shutil.copyfile(ROOT / 'src/etc/daily_plan.py',
                        self.root / 'src/etc/daily_plan.py')
        self.config = self.root / 'src/targets.json'
        self.config.write_text(json.dumps([
            {'id': 'youtube', 'enabled': True, 'poll': True}]))
        self.output = self.root / 'output'
        self.output.write_bytes(b'preserved=yes\n')
        self.env = dict(os.environ, GITHUB_OUTPUT=str(self.output))
        for k in ('GITHUB_TOKEN', 'GH_TOKEN', 'KEYSTORE_PASS', 'KEYSTORE_B64'):
            self.env.pop(k, None)
        self.poll("printf 'new_patch=0\\n' >> \"$GITHUB_OUTPUT\"\n")

    def poll(self, body):
        (self.root / 'src/etc/poll.sh').write_text(body)

    def cli(self, extra=(), env=None):
        return subprocess.run([sys.executable, 'src/etc/daily_plan.py', *extra],
                              cwd=self.root, env=self.env if env is None else env,
                              capture_output=True, text=True, timeout=15)

    def refused(self):
        before = self.output.read_bytes()
        result = self.cli()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.output.read_bytes(), before)
        return result

    def test_zero_and_one_are_exact_results(self):
        for value in (0, 1):
            with self.subTest(value=value):
                self.output.write_text('preserved=yes\n')
                self.poll("printf 'new_patch=" + str(value) + "\\n' >> \"$GITHUB_OUTPUT\"\n")
                result = self.cli()
                self.assertEqual(result.returncode, 0, result.stderr)
                lines = self.output.read_text().splitlines()
                self.assertEqual(lines[:2], ['preserved=yes', 'count=' + str(value)])
                self.assertEqual(json.loads(lines[2][7:]), {'target': ['youtube'] if value else []})

    def test_missing_invalid_and_duplicate_evidence_refuse(self):
        for data in ('', 'new_patch=maybe\n', 'new_patch=0\nnew_patch=1\n',
                     'new_patch=1\nnew_patch=1\n', 'new_patch=0\n\n',
                     'poll_state=unknown\n', 'new_patch=0\npoll_state=unknown\n',
                     'new_patch=1\nextra=2\n', 'new_patch =1\n',
                     'new_patch= 1\n', 'new_patch=01\n', 'new_patch<<EOF\n1\nEOF\n'):
            with self.subTest(data=data):
                self.poll("printf '%s' " + shlex.quote(data) + " >> \"$GITHUB_OUTPUT\"\n")
                self.refused()

    def test_crlf_and_no_final_newline_supported(self):
        for data in (b'new_patch=0\r\n', b'new_patch=1'):
            self.assertEqual(plan.poll_result(data), data.startswith(b'new_patch=1'))
        for data in (b'new_patch=1\r', b'new_patch=1\v', b'new_patch=1\x85',
                     b'new_patch=1\xe2\x80\xa8', b'new_patch=1\x00'):
            with self.subTest(data=data), self.assertRaises(plan.PlanError):
                plan.poll_result(data)

    def test_failed_process_never_uses_its_valid_output(self):
        self.poll("printf 'new_patch=1\\n' >> \"$GITHUB_OUTPUT\"\nexit 2\n")
        self.refused()

    def test_invalid_config_rejected_before_poll(self):
        self.poll("touch CALLED\nprintf 'new_patch=0\\n' >> \"$GITHUB_OUTPUT\"\n")
        cases = ['[]', '{}', '[null]', '[7]', '[NaN]', '[{"id":"x","id":"y","enabled":true}]']
        for data in [
            [{'id': 'a', 'enabled': True, 'poll': True}] * 2,
            [{'id': 'a', 'poll': True}],
            [{'id': 'a', 'enabled': 'true', 'poll': True}],
            [{'id': 'a', 'enabled': 1, 'poll': True}],
            [{'id': 'a', 'enabled': True, 'poll': 'false'}],
            [{'id': 'a', 'enabled': True, 'poll': None}],
            [{'id': '../bad', 'enabled': True, 'poll': True}],
            [{'id': 'a\n::error::bad', 'enabled': True, 'poll': True}],
        ]:
            cases.append(json.dumps(data))
        cases += ['{bad', '[' * 2000]
        for data in cases:
            with self.subTest(data=data[:80]):
                self.config.write_text(data)
                self.refused()
                self.assertFalse((self.root / 'CALLED').exists())

    def test_disabled_and_not_opted_in_are_not_called(self):
        self.config.write_text(json.dumps([
            {'id': 'disabled', 'enabled': False, 'poll': True},
            {'id': 'off', 'enabled': True, 'poll': False},
            {'id': 'absent', 'enabled': True},
            {'id': 'selected', 'enabled': True, 'poll': True},
        ]))
        self.poll("printf '%s\\n' \"$1\" >> CALLED\nprintf 'new_patch=1\\n' >> \"$GITHUB_OUTPUT\"\n")
        self.assertEqual(self.cli().returncode, 0)
        self.assertEqual((self.root / 'CALLED').read_text(), 'selected\n')
        self.assertIn('matrix={"target":["selected"]}', self.output.read_text())

    def test_zero_eligible_targets_is_valid_not_empty_config(self):
        self.config.write_text('[{"id":"off","enabled":false,"poll":true}]')
        self.poll('touch CALLED\nexit 2\n')
        self.assertEqual(self.cli().returncode, 0)
        self.assertFalse((self.root / 'CALLED').exists())
        self.assertIn('count=0\nmatrix={"target":[]}', self.output.read_text())

    def test_one_failed_target_prevents_partial_matrix_and_continues_diagnostics(self):
        self.config.write_text(json.dumps([{'id': i, 'enabled': True, 'poll': True}
                                           for i in ('first', 'bad', 'last')]))
        self.poll("echo \"$1\" >> CALLED\n"
                  "[ \"$1\" != bad ] || exit 2\n"
                  "printf 'new_patch=1\\n' >> \"$GITHUB_OUTPUT\"\n")
        self.refused()
        self.assertEqual((self.root / 'CALLED').read_text().splitlines(), ['first', 'bad', 'last'])

    def test_all_fourteen_keep_config_order_and_unique_temp_paths(self):
        data = json.loads((ROOT / 'src/targets.json').read_text())
        self.config.write_text(json.dumps(data))
        self.poll("printf '%s %s\\n' \"$1\" \"$GITHUB_OUTPUT\" >> CALLED\n"
                  "printf 'new_patch=1\\n' >> \"$GITHUB_OUTPUT\"\n")
        self.assertEqual(self.cli().returncode, 0)
        expected = [t['id'] for t in data if t['enabled'] and t.get('poll', False)]
        rows = [r.split() for r in (self.root / 'CALLED').read_text().splitlines()]
        self.assertEqual([r[0] for r in rows], expected)
        self.assertEqual(len(set(r[1] for r in rows)), len(expected))
        self.assertTrue(all(not Path(r[1]).exists() for r in rows))
        self.assertEqual(json.loads(self.output.read_text().splitlines()[2][7:]), {'target': expected})

    def test_config_drift_during_poll_refused(self):
        self.poll("printf '\\n' >> src/targets.json\nprintf 'new_patch=1\\n' >> \"$GITHUB_OUTPUT\"\n")
        self.refused()

    def test_missing_output_destination_and_argument_refuse(self):
        env = {k:v for k,v in self.env.items() if k != 'GITHUB_OUTPUT'}
        self.assertNotEqual(self.cli(env=env).returncode, 0)
        self.assertNotEqual(self.cli(extra=['extra']).returncode, 0)
        self.assertEqual(self.output.read_bytes(), b'preserved=yes\n')

    def test_output_symlink_refused_without_touching_target(self):
        self.output.unlink()
        target = self.root / 'real-output'
        target.write_bytes(b'keep\n')
        self.output.symlink_to(target)
        self.refused()
        self.assertEqual(target.read_bytes(), b'keep\n')

    def test_reused_plan_output_and_nonnewline_refused(self):
        for old in (b'count=0\n', b'matrix={}\n', b'matrix<<EOF\n{}\nEOF\n',
                    b'preserved-without-newline'):
            self.output.write_bytes(old)
            self.refused()

    def test_poll_output_symlink_missing_invalid_utf8_and_oversized_refused(self):
        bodies = [
            'rm "$GITHUB_OUTPUT"\n',
            'rm "$GITHUB_OUTPUT"\nln -s "$PWD/output" "$GITHUB_OUTPUT"\n',
            "printf '\\377' > \"$GITHUB_OUTPUT\"\n",
            "head -c 65537 /dev/zero > \"$GITHUB_OUTPUT\"\n",
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.poll(body)
                self.refused()

    def test_timeout_and_spawn_failure_refuse_with_clean_scratch(self):
        paths = []
        for error in (subprocess.TimeoutExpired('poll', 0.01), OSError('fixture')):
            def fail(args, **kwargs):
                paths.append(Path(kwargs['env']['GITHUB_OUTPUT']))
                raise error
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(plan.PlanError):
                    plan.collect(self.root, ['youtube'], self.env, timeout=0.01, runner=fail)
        self.assertTrue(all(not p.exists() for p in paths))

    def test_real_subprocess_timeout_refuses(self):
        self.poll('exec sleep 2\n')
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(plan.PlanError):
                plan.collect(self.root, ['youtube'], self.env, timeout=0.05)
        self.assertEqual(self.output.read_bytes(), b'preserved=yes\n')

    def test_no_raw_poll_record_or_environment_in_wrapper_errors(self):
        self.poll("printf 'new_patch=PRIVATE_SENTINEL\\n' >> \"$GITHUB_OUTPUT\"\n")
        self.env['PRIVATE_SECRET'] = 'PRIVATE_SENTINEL'
        proc = self.refused()
        self.assertNotIn('PRIVATE_SENTINEL', proc.stdout + proc.stderr)

    def test_workflow_calls_real_helper_and_gates_build(self):
        text = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assertIn('run: python3 src/etc/daily_plan.py', text)
        self.assertNotIn('NEW:-0', text)
        self.assertIn('    needs: plan\n', text)
        self.assertIn("if: always() && !cancelled() && needs.plan.result == 'success' && needs.plan.outputs.count != '0'", text)
        self.assertIn("needs: [plan, resolve]", text)
        self.assertIn('max-parallel: 6', text)
        self.assertIn('secrets: inherit', text)
        # The workflow entrypoint itself is exercised, not only a helper import.
        line = next(x.strip().removeprefix('run: ') for x in text.splitlines()
                    if 'run: python3 src/etc/daily_plan.py' in x)
        proc = subprocess.run(['bash', '-c', line], cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_config_symlink_and_oversize_refuse_before_poll(self):
        old = self.config.read_bytes()
        self.config.unlink()
        source = self.root / 'other';source.write_bytes(old)
        self.config.symlink_to(source)
        self.refused()
        self.config.unlink()
        self.config.write_bytes(b' ' * (plan.MAX_CONFIG + 1))
        self.refused()

    def test_result_nonregular_file_refused(self):
        fifo = self.root / 'fifo';os.mkfifo(fifo)
        with self.assertRaises(plan.PlanError):
            plan.regular_bytes(fifo, plan.MAX_OUTPUT)

    def test_success_does_not_change_target_configuration(self):
        before = self.config.read_bytes()
        self.assertEqual(self.cli().returncode, 0)
        self.assertEqual(self.config.read_bytes(), before)
