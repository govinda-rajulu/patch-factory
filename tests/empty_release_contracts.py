"""Empty release-list contracts (packet W15h, 22 Oct 2026): an empty first page from GitHub is
asked again before it counts, and the error names a transient API answer, not missing releases."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'build'))
import github_bundle as bundle  # noqa: E402

REL = {'tag_name': 'v1', 'published_at': '2026-10-22T00:00:00Z', 'prerelease': False, 'draft': False, 'assets': []}


class EmptyFirstPage(unittest.TestCase):
    def test_empty_then_rows_recovers(self):
        waits = []
        with patch.object(bundle, 'api_page', side_effect=[[], [REL]]) as m:
            self.assertEqual(bundle.first_page('o', 'r', {}, sleep=waits.append), [REL])
        self.assertEqual(m.call_count, 2)
        self.assertEqual(waits, [10])

    def test_three_empty_answers_stop_with_a_plain_reason(self):
        with patch.object(bundle, 'api_page', side_effect=[[], [], []]):
            with self.assertRaisesRegex(ValueError, 'empty release list .* three times; transient'):
                bundle.first_page('o', 'r', {}, sleep=lambda s: None)

    def test_choose_release_uses_the_retry(self):
        with patch.object(bundle, 'first_page', return_value=[REL]) as f, patch.object(bundle, 'api_page') as a:
            self.assertEqual(bundle.choose_release('o', 'r', 'latest', {})['tag_name'], 'v1')
        f.assert_called_once()
        a.assert_not_called()

    def test_poll_asks_three_times(self):
        s = (ROOT / 'src/etc/poll.sh').read_text()
        self.assertIn('for wait in ${PF_POLL_WAITS:-0 10 30}; do', s)
        self.assertIn('if type == "array" then', s)


if __name__ == '__main__':
    unittest.main()
