"""Micro-audit contracts, 27 September 2026 (docs/review/AUDIT-MICRO-2026-09-27.md).

Each test pins one fixed defect and carries a negative control built from a mutant of
the real file, so the check is proven able to fail:
  H1 no package install at build time (check_sdk.sh)
  M1 signing secrets only in the steps whose code reads the keystore (manual-patch.yml)
  M1 steps without secrets never reach keystore code (Python import closure)
  L1 keystore decode takes the secret from env, not from script text
  L2 keepalive only exits quietly when nothing is staged
  L3 Nightly watch runs one at a time
  L4 Explore fails on a failed listing and fences provider names in the issue body
"""
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows'
SIGNING = ('KEYSTORE_PASS', 'KEYSTORE_ALIAS')
KEYSTORE_STEPS = {'Patch apk', 'Verify finished APK identity'}
INSTALLERS = ('pip install', 'pip3 install', '-m pip', 'easy_install', 'uv pip', 'pipx ')
SCRIPT = re.compile(r'\b(src/(?:build|etc)/[A-Za-z0-9_./-]+\.(?:py|sh))\b')
IMPORT = re.compile(r'^[ \t]*(?:from[ \t]+([A-Za-z_]\w*)[ \t]+import\b|import[ \t]+([A-Za-z_][\w \t,]*))', re.M)


def job_env(text):
    """The patch job's own env block (4-space key, 6-space entries)."""
    start = text.index('\n    env:\n') + len('\n    env:\n')
    end = text.index('\n    steps:\n', start)
    return text[start:end]


def steps(text):
    """Split a single-job workflow into steps: name, env text, run text, uses."""
    body = text[text.index('\n    steps:\n') + len('\n    steps:\n'):]
    chunks = re.split(r'(?m)^      - ', body)[1:]
    out = []
    for chunk in chunks:
        lines = ('  ' + chunk).splitlines()
        first = lines[0].strip()
        name = first[len('name: '):] if first.startswith('name: ') else ''
        env, run, uses, mode = [], [], '', None
        for line in lines[1:]:
            if re.match(r'^        [A-Za-z-]+:', line):
                key = line.strip().split(':', 1)[0]
                mode = key
                rest = line.split(':', 1)[1].strip()
                if key == 'run' and rest not in ('|', '>'):
                    run.append(rest)
                if key == 'uses':
                    uses = rest
                continue
            if mode == 'env':
                env.append(line)
            elif mode == 'run':
                run.append(line)
        out.append({'name': name, 'env': '\n'.join(env), 'run': '\n'.join(run), 'uses': uses})
    return out


def signing_problems(text):
    found = []
    if any(s in job_env(text) for s in SIGNING + ('KEYSTORE_B64',)):
        found.append('signing secret in job-wide env')
    rows = steps(text)
    names = [r['name'] for r in rows]
    for secret in SIGNING:
        holders = {r['name'] for r in rows if secret + ':' in r['env']}
        if holders != KEYSTORE_STEPS:
            found.append(secret + ' held by ' + ', '.join(sorted(holders)))
    b64 = {r['name'] for r in rows if 'KEYSTORE_B64' in r['env']}
    if b64 != {'Decode keystore'}:
        found.append('KEYSTORE_B64 held by ' + ', '.join(sorted(b64)))
    for r in rows:
        if '${{ secrets.' in r['run']:
            found.append('secret expanded into script text: ' + r['name'])
        if r['uses'] and 'KEYSTORE' in r['env']:
            found.append('signing secret handed to action: ' + r['name'])
    if 'Decode keystore' in names and 'Patch apk' in names and \
            names.index('Decode keystore') > names.index('Patch apk'):
        found.append('keystore decoded after use')
    return found


# Live reads only: the process environment, or a shell variable. A plain `env[...]`
# parameter read counts too, except in patch_target.py, whose command() takes env
# from its caller; callers are checked instead (execution_inputs passes dummies).
SECRET_READ = re.compile(r"""(?:os\.environ|getenv)\s*(?:\.get\(|\[|\()\s*['"]KEYSTORE_(?:PASS|ALIAS)"""
                         r"""|\$\{?KEYSTORE_(?:PASS|ALIAS)\b""")
PARAM_READ = re.compile(r"""\benv(?:\.get\(|\[)\s*['"]KEYSTORE_(?:PASS|ALIAS)""")
READER_USE = re.compile(r'from[ \t]+artifact_identity[ \t]+import[^\n]*\b(?:cert_from_keystore|capture_signer|verify_final)\b'
                        r'|artifact_identity\.(?:cert_from_keystore|capture_signer|verify_final)\b'
                        r'|artifact_identity\.py["\']?\s*,?\s*["\']?(?:verify|capture-signer)\b')
COMMAND_USE = re.compile(r'patch_target\.command\(|from[ \t]+patch_target[ \t]+import[^\n]*\bcommand\b')
DUMMY = '"KEYSTORE_PASS": "OMITTED"'


def local_module(root, importer, name):
    for folder in (importer.parent, root / 'src' / 'build', root / 'src' / 'etc'):
        p = folder / (name + '.py')
        if p.is_file():
            return p
    return None


def closure(root, entry):
    """The entry plus every repo Python module it imports, transitively.

    Path strings inside Python (hash inventories, subprocess argv) are not followed;
    shell entries are checked as written. docs/review/AUDIT-MICRO-2026-09-27.md
    records this limit.
    """
    seen, todo = [], [root / entry]
    while todo:
        p = todo.pop()
        if p in seen or not p.is_file():
            continue
        seen.append(p)
        if p.suffix != '.py':
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        for a, b in IMPORT.findall(text):
            for name in ([a] if a else [x.strip() for x in b.split(',')]):
                name = name.split()[0] if name.split() else ''
                m = local_module(root, p, name) if name else None
                if m:
                    todo.append(m)
    return seen


def reaches_keystore(root, entry):
    """Why an entry would need signing secrets, or '' when it cannot."""
    for p in closure(root, entry):
        rel = str(p.relative_to(root))
        if p.name == 'artifact_identity.py':
            continue  # defines the readers; only its callers matter
        text = p.read_text(encoding='utf-8', errors='replace')
        if SECRET_READ.search(text) or (p.name != 'patch_target.py' and PARAM_READ.search(text)):
            return rel + ' reads a signing secret'
        if READER_USE.search(text):
            return rel + ' calls a keystore reader'
        if COMMAND_USE.search(text) and DUMMY not in text:
            return rel + ' builds the signing command without dummy credentials'
    return ''


def unsigned_entries(root, text):
    """Script entry points of every manual-patch step that holds no signing secret."""
    found = []
    for r in steps(text):
        if r['name'] in KEYSTORE_STEPS:
            continue
        found += SCRIPT.findall(r['run'])
        if r['uses'].startswith('./'):
            action = (root / r['uses'] / 'action.yml').read_text(encoding='utf-8')
            if 'artifact_identity.py verify' in action or 'capture-signer' in action:
                found.append(r['uses'] + ' runs a keystore mode')
            found += SCRIPT.findall(action)
    return sorted(set(found))


def install_problems(text):
    return [i for i in INSTALLERS if i in text]


def keepalive_problems(text):
    found = []
    if re.search(r'git commit[^\n]*\|\|', text):
        found.append('commit failure masked')
    if 'git diff --cached --quiet && exit 0' not in text:
        found.append('no staged-change guard')
    return found


def watch_problems(text):
    want = 'concurrency:\n  # Schedule and manual runs both rewrite standing issue #27; queue, never overlap.\n' \
           '  group: nightly-watch\n  cancel-in-progress: false\n'
    return [] if want in text and text.count('group:') == 1 else ['Nightly watch can overlap']


def explore_problems(text):
    found = []
    rows = {r['name']: r for r in steps(text)}
    if not rows['List patches']['run'].lstrip().startswith('set -o pipefail'):
        found.append('listing pipeline hides java failures')
    if 'java -jar "${{ steps.patcher.outputs.jar }}"' not in rows['List patches']['run']:
        found.append('listing no longer runs the verified patcher output')  # provider_watch_contracts pins this
    for r in rows.values():
        if '${{ inputs.' in r['run'] or '${{ github.event' in r['run']:
            found.append('dispatch input expanded into script text: ' + r['name'])
    issue = rows['Open issue']['run']
    if issue.count("echo '```text'") != 1 or issue.count("echo '```'") != 1 or "tr '`'" not in issue:
        found.append('provider names not fenced in issue body')
    return found


class Audit(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding='utf-8')

    def test_h1_sdk_gate_never_installs_packages(self):
        for rel in ('src/build/check_sdk.sh', 'src/build/build.sh'):
            self.assertEqual(install_problems(self.read(rel)), [], rel)
        self.assertIn('optional reader skipped (no runtime install)', self.read('src/build/check_sdk.sh'))

    def test_h1_control_old_install_clause_is_detected(self):
        text = self.read('src/build/check_sdk.sh').replace(
            "import pyaxmlparser' 2>/dev/null; then",
            "import pyaxmlparser' 2>/dev/null || pip install -q pyaxmlparser 2>/dev/null; then", 1)
        self.assertEqual(install_problems(text), ['pip install'])

    def test_m1_signing_secrets_are_step_scoped(self):
        self.assertEqual(signing_problems(self.read('.github/workflows/manual-patch.yml')), [])

    def test_m1_controls_job_wide_or_missing_secrets_are_detected(self):
        text = self.read('.github/workflows/manual-patch.yml')
        wide = text.replace('      COE: ${{ vars.COE }}\n',
                            '      KEYSTORE_PASS: ${{ secrets.KEYSTORE_PASS }}\n      COE: ${{ vars.COE }}\n', 1)
        self.assertIn('signing secret in job-wide env', signing_problems(wide))
        verify = text.index('      - name: Verify finished APK identity\n')
        lost = text[:verify] + text[verify:].replace(
            '          KEYSTORE_PASS: ${{ secrets.KEYSTORE_PASS }}\n', '', 1)
        self.assertTrue(any(p.startswith('KEYSTORE_PASS held by') for p in signing_problems(lost)))
        inline = text.replace('printf \'%s\' "$KEYSTORE_B64"', 'echo "${{ secrets.KEYSTORE_B64 }}"', 1)
        self.assertIn('secret expanded into script text: Decode keystore', signing_problems(inline))

    def test_m1_steps_without_secrets_never_reach_keystore_code(self):
        text = self.read('.github/workflows/manual-patch.yml')
        entries = unsigned_entries(ROOT, text)
        self.assertIn('src/build/release_contract.py', entries)  # coverage is not vacuous
        self.assertIn('src/build/shadow_inputs.py', entries)
        for entry in entries:
            with self.subTest(entry=entry):
                self.assertFalse(entry.endswith('keystore mode'), entry)
                self.assertEqual(reaches_keystore(ROOT, entry), '')
        for signed in ('src/build/build.sh', 'src/build/artifact_identity.py'):
            self.assertTrue((ROOT / signed).is_file())

    def test_m1_control_closure_finds_direct_and_imported_readers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = root / 'src/build'
            b.mkdir(parents=True)
            (b / 'artifact_identity.py').write_text('def cert_from_keystore(r, e):\n    return e["KEYSTORE_PASS"]\n')
            (b / 'patch_target.py').write_text("def command(r, i, w, env):\n    return ['--keystore-password=' + env['KEYSTORE_PASS']]\n")
            (b / 'observe.py').write_text('import patch_target\n'
                                           'def public(r):\n    clean = {"KEYSTORE_PASS": "OMITTED", "KEYSTORE_ALIAS": "OMITTED"}\n'
                                           '    return patch_target.command(r, 1, 2, clean)\n')
            (b / 'clean.py').write_text('from artifact_identity import record\nimport observe\n'
                                         'SHARED = ("src/build/build.sh",)\nNAMES = ("KEYSTORE_PASS",)\n')
            (b / 'live.py').write_text('import os\nimport patch_target\npatch_target.command(1, 2, 3, os.environ)\n')
            (b / 'helper.py').write_text('import artifact_identity\nartifact_identity.cert_from_keystore(1, {})\n')
            (b / 'indirect.py').write_text('def f():\n    import helper\n')
            (b / 'env.py').write_text('import os\nP = os.environ.get("KEYSTORE_ALIAS")\n')
            (b / 'param.py').write_text('def f(env):\n    return env.get("KEYSTORE_PASS")\n')
            (b / 'uses_env.py').write_text('from env import P\n')
            (b / 'reads.sh').write_text('echo "$KEYSTORE_ALIAS"\n')
            self.assertEqual(reaches_keystore(root, 'src/build/clean.py'), '')
            self.assertEqual(reaches_keystore(root, 'src/build/indirect.py'), 'src/build/helper.py calls a keystore reader')
            self.assertEqual(reaches_keystore(root, 'src/build/uses_env.py'), 'src/build/env.py reads a signing secret')
            self.assertEqual(reaches_keystore(root, 'src/build/param.py'), 'src/build/param.py reads a signing secret')
            self.assertEqual(reaches_keystore(root, 'src/build/live.py'),
                             'src/build/live.py builds the signing command without dummy credentials')
            self.assertEqual(reaches_keystore(root, 'src/build/reads.sh'), 'src/build/reads.sh reads a signing secret')

    def test_l2_keepalive_quiet_exit_only_when_nothing_staged(self):
        self.assertEqual(keepalive_problems(self.read('.github/workflows/keepalive.yml')), [])

    def test_l2_control_masked_commit_is_detected(self):
        text = self.read('.github/workflows/keepalive.yml').replace(
            'git commit -m "chore: keepalive"\n', 'git commit -m "chore: keepalive" || exit 0\n', 1)
        self.assertIn('commit failure masked', keepalive_problems(text))

    def test_l3_nightly_watch_queues(self):
        self.assertEqual(watch_problems(self.read('.github/workflows/watch.yml')), [])
        text = self.read('.github/workflows/watch.yml')
        self.assertNotEqual(watch_problems(text.replace('cancel-in-progress: false', 'cancel-in-progress: true')), [])

    def test_l4_explore_listing_and_issue_body(self):
        self.assertEqual(explore_problems(self.read('.github/workflows/explore.yml')), [])

    def test_l4_controls_unfenced_or_unguarded_explore_is_detected(self):
        text = self.read('.github/workflows/explore.yml')
        self.assertIn('listing pipeline hides java failures',
                      explore_problems(text.replace('          set -o pipefail\n', '', 1)))
        self.assertIn('dispatch input expanded into script text: List patches',
                      explore_problems(text.replace('--filter-package-name "$PKG"', '--filter-package-name "${{ inputs.package }}"', 1)))
        self.assertIn('provider names not fenced in issue body',
                      explore_problems(text.replace("            echo '```text'\n", '', 1)))


if __name__ == '__main__':
    unittest.main()
