import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cache_prune', ROOT / 'src/etc/cache_prune.py')
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def row(cache_id, key, created, accessed):
    return {'id': cache_id, 'key': key, 'created_at': created, 'last_accessed_at': accessed}


class FakeGh:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        endpoint = command[2] if command[1] == 'api' and len(command) > 2 and command[2] != '--method' else ''
        if command[1:3] == ['api', '--method']:
            return subprocess.CompletedProcess(command, 0, '', '')
        page = 2 if 'page=2' in endpoint else 1
        return subprocess.CompletedProcess(command, 0, json.dumps({'actions_caches': self.pages[page - 1]}), '')


class CachePrune(unittest.TestCase):
    def test_prefix_removes_only_rightmost_version_or_hash_segment(self):
        self.assertEqual(cp.cache_prefix('morphe-jar-a1b2c3d4'), 'morphe-jar')
        self.assertEqual(cp.cache_prefix('tool-v2.4.1'), 'tool')
        self.assertEqual(cp.cache_prefix('tool-v2.4.1-deadbeef'), 'tool-v2.4.1')
        self.assertEqual(cp.cache_prefix('pf-action-smoke-12345-2'), 'pf-action-smoke-12345-2')
        self.assertEqual(cp.cache_prefix('cache-without-suffix'), 'cache-without-suffix')

    def test_stale_non_newest_is_deleted_and_newest_or_fresh_is_kept(self):
        old = '2026-10-20T12:00:00Z'
        older = '2026-10-21T12:00:00Z'
        fresh = '2026-10-30T11:00:00Z'
        rows = [
            row(10, 'morphe-jar-aaaaaaa', old, old),
            row(11, 'morphe-jar-bbbbbbb', older, old),
            row(12, 'morphe-jar-ccccccc', fresh, old),
            row(13, 'other-v1.0', old, old),
        ]
        fake = FakeGh([rows])
        summary = tempfile.NamedTemporaryFile(delete=False)
        summary.close()
        before = os.environ.get('GITHUB_STEP_SUMMARY')
        os.environ['GITHUB_STEP_SUMMARY'] = summary.name
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cp.main(['--repo', 'o/r', '--now', NOW.isoformat()], run=fake), 0)
            self.assertIn('delete cache id=10', output.getvalue())
            self.assertIn('delete cache id=11', output.getvalue())
            self.assertNotIn('id=12', output.getvalue())
            self.assertNotIn('id=13', output.getvalue())
            self.assertEqual([c[-1] for c in fake.calls if c[1:3] == ['api', '--method']],
                             ['repos/o/r/actions/caches/10', 'repos/o/r/actions/caches/11'])
            self.assertIn('Deleted: 2', Path(summary.name).read_text())
        finally:
            if before is None:
                os.environ.pop('GITHUB_STEP_SUMMARY', None)
            else:
                os.environ['GITHUB_STEP_SUMMARY'] = before
            os.unlink(summary.name)

    def test_dry_run_paginates_and_does_not_delete(self):
        old = '2026-10-20T12:00:00Z'
        page1 = [row(1000 + i, 'bulk-v%d.0' % i, old, old) for i in range(100)]
        page2 = [row(21, 'cache-v2.0', '2026-10-22T12:00:00Z', old),
                 row(20, 'cache-v1.0', old, old)]
        fake = FakeGh([page1, page2])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cp.main(['--repo', 'o/r', '--dry-run', '--now', NOW.isoformat()], run=fake), 0)
        self.assertIn('would delete cache id=20', output.getvalue())
        self.assertNotIn('--method', ' '.join(' '.join(c) for c in fake.calls))
        self.assertEqual(len([c for c in fake.calls if c[1] == 'api']), 2)

    def test_missing_timestamps_are_safe(self):
        rows = [row(30, 'bad-v1.0', '', '2026-10-01T00:00:00Z'),
                row(31, 'bad-v2.0', '2026-10-20T00:00:00Z', '')]
        self.assertEqual(cp.candidates(rows, NOW), [])


if __name__ == '__main__':
    unittest.main()
