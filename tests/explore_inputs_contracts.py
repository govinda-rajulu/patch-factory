"""4. Explore patches refuses malformed inputs before any download (packet W7, desk lead)."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / '.github/workflows/explore.yml').read_text()


def step_script():
    start = TEXT.index('      - name: Refuse a malformed provider or package')
    body = TEXT[start:TEXT.index('      - name: Set up Java', start)]
    lines = body.split('\n')
    i = lines.index('        run: |')
    return '\n'.join(l[10:] for l in lines[i + 1:] if l.strip())


class Explore(unittest.TestCase):
    def check(self, host, ident, pkg):
        return subprocess.run(['bash', '-c', step_script()], capture_output=True, text=True,
                              env={**os.environ, 'HOST': host, 'IDENT': ident, 'PKG': pkg}).returncode

    def test_real_shapes_pass(self):
        for host, ident, pkg in (('github', 'heyymichii/michii-patches', 'com.linkedin.android'),
                                 ('github', 'RookieEnough/De-Vanced', 'com.amazon.mp3'),
                                 ('gitlab', '82031658', 'com.truecaller')):
            self.assertEqual(self.check(host, ident, pkg), 0, (host, ident, pkg))

    def test_malformed_inputs_stop(self):
        for host, ident, pkg in (('github', 'a/b', 'com.x;rm -rf ~'), ('github', 'a/b', 'nodots'),
                                 ('github', 'a/b', '$(id).x'), ('github', 'a b/c', 'com.x'),
                                 ('github', 'owner', 'com.x'), ('gitlab', 'owner/repo', 'com.x'),
                                 ('github', 'a/b', 'com.' + 'x' * 130), ('github', 'a/b\nc', 'com.x')):
            self.assertNotEqual(self.check(host, ident, pkg), 0, (host, ident, pkg))

    def test_check_runs_before_downloads_and_uses_env(self):
        self.assertLess(TEXT.index('Refuse a malformed provider or package'), TEXT.index('Download morphe-desktop'))
        self.assertNotIn('${{ inputs.package }}"', step_script())


if __name__ == '__main__':
    unittest.main()
