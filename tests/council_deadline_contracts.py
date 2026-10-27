"""W16p deadline contracts, 26 Oct 2026.

These tests use a fake transport and a tiny monotonic budget. The HTTP cap assertion is
intentionally behavioural: deleting the cap in http() makes it fail with 90 seconds.
"""
import importlib.util
import http.server
import json
import threading
import time
import unittest
import urllib.error
from email.message import Message
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('council_deadline', ROOT / 'src/council/council.py')
council = importlib.util.module_from_spec(spec)
spec.loader.exec_module(council)

ENV = {'NVIDIA_API_KEY': 'nvapi-FAKE-0001', 'PF_RETRY_SLEEP': '0', 'PF_PACE_SCALE': '0'}
SEAT = {'id': 'slow', 'provider': 'nvidia', 'models': ['m1', 'm2'], 'max_input_chars': 100000}


class SlowOpener:
    def __init__(self):
        self.timeouts = []

    def open(self, request, timeout):
        self.timeouts.append(timeout)
        time.sleep(timeout)
        raise TimeoutError('fake slow provider')


class TrickleHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '20')
        self.end_headers()
        for _ in range(20):
            try:
                self.wfile.write(b'x')
                self.wfile.flush()
                time.sleep(0.2)
            except (BrokenPipeError, ConnectionResetError):
                break

    def log_message(self, *_args):
        pass


class FakeResponse:
    def __init__(self, status=200, body=b'ok'):
        self.status = status
        self.body = body
        self.fp = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size=-1):
        out, self.body = self.body, b''
        return out


class RecordingOpener:
    def __init__(self):
        self.timeouts = []

    def open(self, request, timeout):
        self.timeouts.append(timeout)
        return FakeResponse(201, b'{}')


class DeadlineContracts(unittest.TestCase):
    def setUp(self):
        council._RUN_DEADLINE = None
        council._RUN_START = None
        council._model_cache.clear()
        council._pace_last.clear()

    def test_slow_provider_stops_before_budget_and_late_seat_abstains(self):
        env = dict(ENV, PF_COUNCIL_SECONDS='0.08', PF_DEADLINE_GUARD_SECONDS='0.01')
        opener = SlowOpener()
        original = council._OPENER
        council._OPENER = opener
        try:
            started = time.monotonic()
            row = council.run_seat(SEAT, 'system', 'user', env, council.check_review, 'canary')
            elapsed = time.monotonic() - started
            late = council.run_seat(dict(SEAT, id='late'), 'system', 'user', env,
                                    council.check_review, 'canary')
        finally:
            council._OPENER = original
        self.assertLess(elapsed, 0.15)
        self.assertEqual(row['status'], 'ABSTAIN_DEADLINE')
        self.assertEqual(late['status'], 'ABSTAIN_DEADLINE')
        self.assertTrue(opener.timeouts)
        self.assertLessEqual(max(opener.timeouts), 0.08)

    def test_trickling_body_stops_at_absolute_deadline(self):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), TrickleHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old_loopback = council._ALLOW_INSECURE_LOOPBACK
        council._ALLOW_INSECURE_LOOPBACK = True
        env = dict(ENV, PF_COUNCIL_SECONDS='1', PF_DEADLINE_GUARD_SECONDS='0')
        council.install_deadline(env)
        started = time.monotonic()
        try:
            result = council.http('GET', 'http://127.0.0.1:%d/' % server.server_port, {}, timeout=90)
        finally:
            council._ALLOW_INSECURE_LOOPBACK = old_loopback
            server.shutdown()
            server.server_close()
        elapsed = time.monotonic() - started
        self.assertEqual(result, (0, 'TimeoutError'))
        self.assertLess(elapsed, 1.5)

    def test_pacing_lock_wait_uses_remaining_timeout(self):
        env = dict(ENV, PF_COUNCIL_SECONDS='0.08', PF_DEADLINE_GUARD_SECONDS='0')
        council.install_deadline(env)
        provider = 'nvidia'
        lock = council._pace_lock.setdefault(provider, threading.Lock())
        lock.acquire()
        try:
            with self.assertRaises(council.DeadlineExceeded):
                council.paced(provider, env)
        finally:
            lock.release()

    def test_github_posting_uses_reserved_window_after_provider_deadline(self):
        env = {'GITHUB_TOKEN': 'ghs-FAKE-TOKEN-0001', 'PF_COUNCIL_SECONDS': '0.01'}
        council.install_deadline(env)
        time.sleep(0.03)
        opener = RecordingOpener()
        original = council._OPENER
        council._OPENER = opener
        try:
            result = council.gh(env, 'POST', 'repos/govinda-rajulu/patch-factory/issues/1/comments', {'body': 'ok'})
        finally:
            council._OPENER = original
        self.assertEqual(result, '{}')
        # W16p round 2: the GitHub window is bounded (deadline plus GITHUB_GRACE_SECONDS).
        self.assertEqual(len(opener.timeouts), 1)
        self.assertTrue(59.0 < opener.timeouts[0] <= 60.0, opener.timeouts)

    def test_redirect_recalculates_timeout_for_second_hop(self):
        env = dict(ENV, PF_COUNCIL_SECONDS='0.25', PF_DEADLINE_GUARD_SECONDS='0')
        council.install_deadline(env)
        first = 'https://api.github.com/repos/govinda-rajulu/patch-factory/issues/1'
        second = 'https://api.github.com/repos/govinda-rajulu/patch-factory/issues/2'
        opener = RecordingOpener()
        original_open = opener.open
        calls = [0]

        def open_redirect(request, timeout):
            calls[0] += 1
            opener.timeouts.append(timeout)
            if calls[0] == 1:
                time.sleep(0.15)
                headers = Message()
                headers['Location'] = second
                raise urllib.error.HTTPError(request.full_url, 302, 'redirect', headers, BytesIO())
            return FakeResponse(200, b'{}')

        opener.open = open_redirect
        original = council._OPENER
        council._OPENER = opener
        try:
            result = council.http('GET', first, {}, timeout=90)
        finally:
            council._OPENER = original
        self.assertEqual(result, (200, '{}'))
        self.assertEqual(len(opener.timeouts), 2)
        self.assertLess(opener.timeouts[1], 0.15)

    def test_reserve_blocks_provider_transport_start(self):
        env = dict(ENV, PF_COUNCIL_SECONDS='0.05', PF_DEADLINE_GUARD_SECONDS='0.04')
        council.install_deadline(env)
        time.sleep(0.02)
        opener = SlowOpener()
        original = council._OPENER
        council._OPENER = opener
        try:
            result = council.http('GET', 'https://integrate.api.nvidia.com/v1/models', {}, timeout=90)
        finally:
            council._OPENER = original
        self.assertEqual(result, (0, 'deadline exceeded'))
        self.assertEqual(opener.timeouts, [])

    def test_http_timeout_is_capped_by_remaining_budget(self):
        env = dict(ENV, PF_COUNCIL_SECONDS='0.05', PF_DEADLINE_GUARD_SECONDS='0')
        council.install_deadline(env)
        opener = SlowOpener()
        original = council._OPENER
        council._OPENER = opener
        try:
            status, text = council.http('GET', 'https://integrate.api.nvidia.com/v1/models', {}, timeout=90)
        finally:
            council._OPENER = original
        self.assertEqual((status, text), (0, 'TimeoutError'))
        self.assertLessEqual(opener.timeouts[0], 0.05)
        self.assertLess(opener.timeouts[0], 90)

    def test_audit_render_keeps_unreached_parts_as_carry_over(self):
        body = council.render_audit('selection', [], [('a', 'x'), ('b', 'y')], [], [2],
                                    'a' * 64, 'b' * 64)
        self.assertIn('Not reviewed (time or part limit): part(s) 2.', body)

    def test_workflows_set_budget_and_unbuffered_output(self):
        council_workflow = (ROOT / '.github/workflows/council.yml').read_text()
        onboard_workflow = (ROOT / '.github/workflows/onboard-review.yml').read_text()
        self.assertIn("PF_COUNCIL_SECONDS: '2700'", council_workflow)
        self.assertIn("PF_DEADLINE_GUARD_SECONDS: '120'", council_workflow)
        self.assertIn("PYTHONUNBUFFERED: '1'", council_workflow)
        self.assertIn("PF_COUNCIL_SECONDS: '1020'", onboard_workflow)
        self.assertIn("PF_DEADLINE_GUARD_SECONDS: '120'", onboard_workflow)
        self.assertIn("PYTHONUNBUFFERED: '1'", onboard_workflow)


if __name__ == '__main__':
    unittest.main()


class GithubWindowIsPerThread(unittest.TestCase):
    """W16p round 2, 27 Oct 2026: a GitHub call in one thread must not lift the provider deadline
    for the other lanes, and no GitHub call may outlive the deadline plus its grace."""

    def setUp(self):
        self.saved = (council._RUN_DEADLINE, council._RUN_START, council._RUN_GUARD)

    def tearDown(self):
        council._RUN_DEADLINE, council._RUN_START, council._RUN_GUARD = self.saved
        council._TL.github_until = None

    def test_provider_lane_keeps_its_deadline_while_github_posts(self):
        council._RUN_DEADLINE = time.monotonic() + 1.0
        council._RUN_GUARD = 0.0
        inside, seen = threading.Event(), {}
        release = threading.Event()

        def fake_http(method, url, headers, body=None, timeout=60):
            inside.set()
            release.wait(2)
            return 200, '{}'
        old = council.http
        council.http = fake_http
        try:
            t = threading.Thread(target=council.github_http, args=('GET', 'https://api.github.com/x', {}))
            t.start()
            inside.wait(2)
            seen['provider'] = council.bounded_timeout(90)
            release.set()
            t.join(3)
        finally:
            council.http = old
        self.assertLessEqual(seen['provider'], 1.0)

    def test_github_window_ends_after_the_grace(self):
        council._RUN_DEADLINE = time.monotonic() - council.GITHUB_GRACE_SECONDS - 1
        council._RUN_GUARD = 0.0
        status, text = council.github_http('GET', 'https://api.github.com/repos/o/r/issues/1', {})
        self.assertEqual((status, text), (0, 'deadline exceeded'))

    def test_github_window_outlasts_the_provider_deadline(self):
        council._RUN_DEADLINE = time.monotonic() - 1
        council._RUN_GUARD = 0.0
        council._TL.github_until = council._RUN_DEADLINE + council.GITHUB_GRACE_SECONDS
        self.assertGreater(council.bounded_timeout(60), 30)
        council._TL.github_until = None
        self.assertEqual(council.bounded_timeout(60), 0.0)
