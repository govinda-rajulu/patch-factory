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


def fetch_script():
    start = TEXT.index('      - name: Fetch bundle')
    body = TEXT[start:TEXT.index('      - name: List patches', start)]
    lines = body.split('\n')
    i = lines.index('        run: |')
    return '\n'.join(l[10:] for l in lines[i + 1:] if l.strip())


class FetchChannel(unittest.TestCase):
    """W16h: the first fetch status is shown and the issue names the channel that served it."""
    def run_fetch(self, first_ok):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'src/build').mkdir(parents=True)
            # Fake fetcher: the asked channel fails unless first_ok; the other one serves 20000 bytes.
            (root / 'src/build/fetch_bundle.sh').write_text(
                'if [ "$3" = "prerelease" ] && [ "%s" != "1" ]; then exit 4; fi\nhead -c 20000 /dev/zero > "$4"\n'
                % ('1' if first_ok else '0'))
            out = root / 'out'
            r = subprocess.run(['bash', '-e', '-c', fetch_script()], cwd=root, capture_output=True, text=True,
                               env={**os.environ, 'HOST': 'github', 'IDENT': 'a/b', 'PKG': 'x.y',
                                    'CHAN': 'prerelease', 'GITHUB_OUTPUT': str(out)})
            return r, out.read_text() if out.exists() else ''

    def test_fallback_reports_status_and_used_channel(self):
        r, out = self.run_fetch(False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('no bundle on prerelease (fetch status 4); trying latest', r.stdout)
        self.assertEqual(out.strip(), 'channel=latest')

    def test_first_channel_used_when_it_serves(self):
        r, out = self.run_fetch(True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('trying', r.stdout)
        self.assertEqual(out.strip(), 'channel=prerelease')

    def test_issue_names_the_used_channel(self):
        issue = TEXT[TEXT.index('      - name: Open issue'):]
        self.assertIn('CHAN: ${{ steps.fetch.outputs.channel }}', issue)
        self.assertNotIn('|| true', fetch_script())


if __name__ == '__main__':
    unittest.main()
