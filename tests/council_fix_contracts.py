"""W14: council seats are trained by docs/council/AGENT-SPEC.md and may propose one-line fixes.
A fix applies only when its quoted line occurs once and the result parses; nothing is pushed."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('council_fix', ROOT / 'src/council/council.py')
council = importlib.util.module_from_spec(spec)
spec.loader.exec_module(council)


def group(file, quote, replacement, seats=('gpt',), severity='medium'):
    return {'file': file, 'line': 1, 'quote': quote, 'replacement': replacement, 'issue': 'x', 'fix': 'y',
            'rule': '', 'severity': severity, 'seats': list(seats)}


class Training(unittest.TestCase):
    def test_spec_state_and_checkpoint_reach_review_and_audit(self):
        ctx = council.trained('BASE')
        self.assertTrue(ctx.startswith('BASE\n\nAGENT SPEC (trusted):\nYou are one seat of the patch-factory council.'))
        self.assertIn('STATE, newest entry (trusted):\n## ', ctx)
        self.assertIn('OPEN-WORK, current checkpoint (trusted):\n## Current checkpoint', ctx)
        src = (ROOT / 'src/council/council.py').read_text()
        self.assertEqual(src.count("context = trained("), 2)
        for word in ('never push, merge', 'exactly once', 'Caveman', 'L054', 'L052', 'replacement'):
            self.assertIn(word, council.agent_spec())

    def test_trained_audit_fits_the_smallest_audit_seat(self):
        spec_ = json.loads(council.read('src/council/shards.json'))
        seats = json.loads(council.read('src/council/seats.json'))['seats']
        budget = min(s['max_input_chars'] for s in seats if 'audit' in s.get('jobs', council.JOBS))
        inst, worst = council.prompt('AUDIT.md'), 0
        for s in spec_['shards']:
            files = council.shard_files(spec_, s['id'])
            parts, _ = council.audit_parts(files)
            ctx = council.trained('\n\n'.join(['REPOSITORY RULES (trusted):\n' + council.agents_limits(),
                                               'OWNER (trusted):\n' + council.read('docs/council/OWNER.md'),
                                               'LESSONS (trusted):\n' + '\n\n'.join(council.lessons(council.tags_for(files)))]))
            for p in parts:
                block, _ = council.envelope('files', ''.join(council.file_block(r, b) for r, b in p), council.AUDIT_PART_CHARS)
                user = '\n\n'.join([inst, ctx, 'Shard %s, part 10 of 10. Files: %s' % (s['id'], json.dumps([r for r, _ in p])), block])
                worst = max(worst, len(council.base_system('0' * 16)) + len(user))
        self.assertLess(worst, budget)

    def test_replacement_is_optional_single_line(self):
        f = {'severity': 'low', 'file': 'a.py', 'line': 1, 'quote': 'x = 1', 'issue': 'i', 'fix': 'f', 'rule': ''}
        self.assertEqual(council.check_review({'summary': 's', 'verdict': 'looks_ok', 'findings': [dict(f)]})['findings'][0]['replacement'], '')
        council.check_review({'summary': 's', 'verdict': 'looks_ok', 'findings': [dict(f, replacement='x = 2')]})
        for bad in ('a\nb', 'x' * 401, 3):
            with self.assertRaises(ValueError):
                council.check_review({'summary': 's', 'verdict': 'looks_ok', 'findings': [dict(f, replacement=bad)]})


class FixLane(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old = council.ROOT
        council.ROOT = self.tmp
        (self.tmp / 'a.py').write_text('def f():\n    return 1\n\nx = 2\nx = 2\n')
        (self.tmp / 'b.json').write_text('{"a": 1}\n')
        (self.tmp / 'c.sh').write_text('#!/bin/bash\nset -uo pipefail\necho hi\n')
        (self.tmp / 'd.yml').write_text('a: 1\n')

    def tearDown(self):
        council.ROOT = self.old
        shutil.rmtree(self.tmp)

    def test_each_rule(self):
        fixes, patch = council.propose_fixes([
            group('a.py', 'return 1', 'return 2', seats=('gpt', 'gemini')),   # applies, indentation kept
            group('a.py', 'x = 2', 'x = 3'),                                   # twice in the file
            group('b.json', '{"a": 1}', '{"a": 1,}'),                          # would not parse
            group('c.sh', 'set -uo pipefail', 'set -uo pipefail || true'),     # weakens a check
            group('c.sh', 'echo hi', 'echo hello'),                            # applies; shell checked by the step
            group('d.yml', 'a: 1', 'a: 2'),                                    # no checker for yml
            group('../x.py', 'a', 'b'), group('a.py', 'return 1', ''),         # outside the repo; no replacement
        ])
        status = [f['status'] for f in fixes]
        self.assertEqual(status, ['applies', 'words only: quoted line found 2 times', 'words only: edited file does not parse',
                                  'refused: weakens a check', 'applies; syntax checked in the run step',
                                  'words only: no syntax check for this file type', 'file not found'])
        self.assertIn('-    return 1\n+    return 2', patch)
        self.assertIn('+echo hello', patch)
        self.assertNotIn('x = 3', patch)
        self.assertEqual((self.tmp / 'a.py').read_text(), 'def f():\n    return 1\n\nx = 2\nx = 2\n')  # nothing written
        r = subprocess.run(['git', 'apply', '--check', '-'], input=patch, text=True, cwd=self.tmp, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = '\n'.join(council.fix_section(fixes))
        self.assertIn('#### Proposed fixes (2 of 7 apply; syntax checked, not tested, never pushed)', text)
        self.assertIn('council-fixes', text)

    def test_check_step_applies_to_a_scratch_copy_only(self):
        _, patch = council.propose_fixes([group('c.sh', 'echo hi', 'echo hello'), group('a.py', 'return 1', 'return 2')])
        subprocess.run(['git', 'init', '-q'], cwd=self.tmp, check=True)
        (self.tmp / 'council-out').mkdir()
        (self.tmp / 'council-out/fixes.patch').write_text(patch)
        r = subprocess.run(['bash', str(ROOT / 'src/council/check_fixes.sh'), 'council-out/fixes.patch'], cwd=self.tmp,
                           capture_output=True, text=True, env={'PATH': '/usr/bin:/bin:/usr/local/bin'})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('PATCH applies', r.stdout)
        self.assertIn('SYNTAX OK c.sh', r.stdout)
        self.assertIn('SYNTAX OK a.py (checked by the council step)', r.stdout)
        self.assertEqual((self.tmp / 'c.sh').read_text(), '#!/bin/bash\nset -uo pipefail\necho hi\n')
        self.assertTrue((self.tmp / 'council-out/CHECKS.txt').is_file())
        broken = patch.replace('+echo hello', '+if then')
        (self.tmp / 'council-out/fixes.patch').write_text(broken)
        r = subprocess.run(['bash', str(ROOT / 'src/council/check_fixes.sh')], cwd=self.tmp, capture_output=True, text=True)
        self.assertIn('SYNTAX FAIL c.sh', r.stdout)
        self.assertEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
