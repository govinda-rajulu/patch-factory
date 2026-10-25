"""W16k (owner, 25 Oct 2026): run 40194762238 failed collect with no reason in its log.
A failed collect now names the stage and our own stop code, in the log and in status.json."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/etc'))
import community_watch as cw  # noqa: E402


class Reason(unittest.TestCase):
    def run_with(self, reader):
        out = Path(tempfile.mkdtemp()) / 'o'
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            status = cw.collect(ROOT, out, {'run_id': '1', 'attempt': '1'}, reader)
        return status, err.getvalue()

    def test_stage_and_code_are_named(self):
        base = (ROOT / cw.BASELINE).read_bytes()

        def reader(url):
            if url == cw.INDEX_URL:
                return base
            raise ValueError('FEED_SIZE')
        status, log = self.run_with(reader)
        self.assertEqual((status['state'], status['stage'], status['code']), ('FAILED', 'fetch news', 'FEED_SIZE'))
        self.assertIn('::error::Community Watch collect failed at fetch news: ValueError FEED_SIZE', log)

    def test_untrusted_message_is_not_echoed(self):
        def reader(url):
            raise ValueError('<script>feed text</script>')
        status, log = self.run_with(reader)
        self.assertEqual((status['stage'], status['code']), ('fetch index', ''))
        self.assertNotIn('script', log)


if __name__ == '__main__':
    unittest.main()
