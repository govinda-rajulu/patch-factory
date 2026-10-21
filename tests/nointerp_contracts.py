"""src/etc/nointerp.sh (W15d, AUDIT 4): a dispatch input interpolated into a shell command is an
injection, in a run: block AND in a one-line run:. Passing it through env: is the safe form."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'block': ('      - run: |\n          echo ${{ inputs.x }}\n', 1),
    'one line': ('      - run: echo ${{ inputs.x }}\n', 1),
    'one line, event inputs': ('      - name: n\n        run: echo ${{ github.event.inputs.x }}\n', 1),
    'env is safe': ('      - env:\n          X: ${{ inputs.x }}\n        run: echo "$X"\n', 0),
    'if is not shell': ("      - if: inputs.x == 'true'\n        run: echo ok\n", 0),
}


class NoInterp(unittest.TestCase):
    def check(self, step):
        with tempfile.TemporaryDirectory() as d:
            wf = Path(d) / '.github/workflows'
            wf.mkdir(parents=True)
            (wf / 'x.yml').write_text('on: workflow_dispatch\njobs:\n  a:\n    steps:\n' + step, encoding='utf-8')
            return subprocess.run(['bash', str(ROOT / 'src/etc/nointerp.sh')], cwd=d, capture_output=True, text=True, timeout=60).returncode

    def test_cases(self):
        for label, (step, want) in CASES.items():
            with self.subTest(case=label):
                self.assertEqual(self.check(step), want)

    def test_repository_is_clean(self):
        r = subprocess.run(['bash', 'src/etc/nointerp.sh'], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == '__main__':
    unittest.main()
