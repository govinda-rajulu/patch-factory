"""Longest build first (W15c, 21 Oct 2026): order only, never the set of apps."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import run_order  # noqa: E402


class RunOrder(unittest.TestCase):
    def test_committed_minutes_name_only_configured_apps(self):
        table = run_order.minutes(ROOT)
        ids = {t['id'] for t in json.loads((ROOT / 'src/targets.json').read_text(encoding='utf-8'))}
        self.assertTrue(table)
        self.assertEqual(set(table) - ids, set())

    def test_longest_first_unknown_first_ties_keep_request(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'src/etc').mkdir(parents=True)
            (Path(d) / run_order.FILE).write_text(json.dumps({'minutes': {'a': 1, 'b': 5, 'c': 5}}))
            self.assertEqual(run_order.order(d, ['a', 'c', 'x', 'b']), ['x', 'c', 'b', 'a'])
            self.assertEqual(run_order.order(d, []), [])

    def test_no_file_keeps_request_and_bad_values_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(run_order.order(d, ['b', 'a']), ['b', 'a'])
            (Path(d) / 'src/etc').mkdir(parents=True)
            for bad in ({'minutes': {'a': 0}}, {'minutes': {'a': 'x'}}, {'minutes': []}, [], {'minutes': {'a': float('inf')}}):
                with self.subTest(bad=str(bad)):
                    (Path(d) / run_order.FILE).write_text(json.dumps(bad))
                    with self.assertRaises(ValueError):
                        run_order.order(d, ['a'])


if __name__ == '__main__':
    unittest.main()
