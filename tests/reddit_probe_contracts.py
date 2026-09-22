import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/build"))
import reddit_page_probe as probe


class RedditProbe(unittest.TestCase):
    def raw(self, **kwargs):
        sol = {"response": '<a id="download_link" href="https://host/x?sig=FAKE_SECRET">2026.38.0</a>',
               "url": probe.REQUESTS[0][1], "status": 200,
               "cookies": [{"name": "secret", "value": "FAKE_SECRET"}], "userAgent": "FAKE_SECRET"}
        sol.update(kwargs)
        return json.dumps({"status": "ok", "solution": sol}).encode()

    def test_two_fixed_pages_only(self):
        calls = []
        report = probe.collect(lambda url: calls.append(url) or self.raw())
        self.assertEqual(calls, [u for _, u in probe.REQUESTS])
        self.assertEqual(len(report["observations"]), 2)
        self.assertTrue(all(r["state"] == "OBSERVED" for r in report["observations"]))
        self.assertNotIn("FAKE_SECRET", json.dumps(report))

    def test_no_arbitrary_url(self):
        with self.assertRaises(ValueError):
            probe.request_page("https://other.invalid")

    def test_redirect_not_used_as_new_request(self):
        calls = []
        report = probe.collect(lambda url: calls.append(url) or self.raw(url="https://other.invalid/?sig=FAKE_SECRET"))
        self.assertEqual(len(calls), 2)
        self.assertFalse(report["observations"][0]["same_apkpure_host"])
        self.assertNotIn("other.invalid", json.dumps(report))

    def test_challenge_and_missing_link_are_observations_not_recovery(self):
        r = probe.collect(lambda _: self.raw(response="Just a moment"))
        row = r["observations"][0]
        self.assertTrue(row["diagnostic"]["response_shape"]["challenge_marker_present"])
        self.assertEqual(row["diagnostic"]["response_shape"]["apkpure_download_ids"], 0)
        self.assertIn("not the historical response", row["limits"])

    def test_bad_input_unknown_and_no_raw_leak(self):
        for raw in (b"FAKE_SECRET", b"[]", b'{"solution":[]}', b"x"*(probe.MAX+1), None):
            with self.subTest(raw_type=type(raw).__name__):
                report = probe.collect(lambda _: raw)
                self.assertTrue(all(x["state"] == "UNKNOWN" for x in report["observations"]))
                self.assertNotIn("FAKE_SECRET", json.dumps(report))

    def test_missing_body_unknown(self):
        report = probe.collect(lambda _: self.raw(response=None))
        self.assertEqual(report["observations"][0]["state"], "UNKNOWN")

    def test_exception_redacted_and_second_page_attempted(self):
        calls = []
        def bad(url):
            calls.append(url)
            raise OSError("FAKE_SECRET")
        report = probe.collect(bad)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("FAKE_SECRET", json.dumps(report))

    def test_credentials_refuse_before_requests(self):
        for key in ("GH_TOKEN", "GITHUB_TOKEN", "KEYSTORE_PASS", "KEYSTORE_ALIAS", "KEYSTORE_B64"):
            with patch.dict(os.environ, {key: "FAKE_SECRET"}, clear=True), patch.object(sys, "argv", ["probe"]), patch.object(probe, "collect") as collect:
                with self.assertRaises(ValueError):
                    probe.main()
                collect.assert_not_called()

    def test_extra_arguments_refused(self):
        with patch.object(sys, "argv", ["probe", "arbitrary"]), patch.object(probe, "collect") as collect:
            with self.assertRaises(ValueError):
                probe.main()
            collect.assert_not_called()

    def test_output_no_overwrite(self):
        old = Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            try:
                os.chdir(d)
                report = probe.collect(lambda _: self.raw())
                env={"GITHUB_REPOSITORY":"govinda-rajulu/patch-factory","GITHUB_SHA":"a"*40,"GITHUB_RUN_ID":"123","GITHUB_RUN_ATTEMPT":"1"}
                with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["probe"]), patch.object(probe, "collect", return_value=report), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(probe.main(), 0)
                    before = Path("page-probe/report.json").read_bytes()
                    with self.assertRaises(FileExistsError):
                        probe.main()
                    self.assertEqual(Path("page-probe/report.json").read_bytes(), before)
            finally:
                os.chdir(old)

    def test_missing_workflow_identity_refuses_before_request(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["probe"]), patch.object(probe, "collect") as collect:
            with self.assertRaises(ValueError):
                probe.main()
            collect.assert_not_called()

    def test_local_transport_is_bounded_no_proxy_and_no_redirect(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.geturl.return_value = "http://127.0.0.1:8191/v1"
        response.read.return_value = self.raw()
        client = unittest.mock.Mock()
        client.open.return_value = response
        with patch.object(probe.urllib.request, "build_opener", return_value=client) as build:
            self.assertEqual(probe.request_page(probe.BASE), self.raw())
        request = client.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8191/v1")
        self.assertEqual(client.open.call_args.kwargs["timeout"], 35)
        self.assertEqual(json.loads(request.data), {"cmd": "request.get", "url": probe.BASE, "maxTimeout": 15000})
        response.read.assert_called_once_with(probe.MAX+1)
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsNone(build.call_args.args[1].redirect_request())

    def test_workflow_has_no_build_secrets_or_publish(self):
        text = (ROOT / ".github/workflows/reddit-page-probe.yml").read_text()
        for forbidden in ("secrets.", "secrets: inherit", "contents: write", "actions: write", "build.sh", "ks.keystore", "release/action", "schedule:"):
            self.assertNotIn(forbidden, text)
        for required in ("contents: read", "persist-credentials: false", "127.0.0.1:8191:8191", "test \"$ready\" = 1", "retention-days: 7", "timeout-minutes: 6"):
            self.assertIn(required, text)
        self.assertIn("139dfee1c6f89249c8d665d1333a42e8ec74ec0a86bc6bb1c8461e10d3a66a47", text)

    def test_failure_stages_are_distinct_and_secret_free(self):
        cases = (
            (None, "response", "invalid-input"),
            (b"x" * (probe.MAX + 1), "response", "oversized-response"),
            (b"FAKE_SECRET", "decode", "invalid-json"),
            (b"\xff", "decode", "invalid-json"),
            (b"[]", "resolver", "invalid-envelope"),
            (b'{"status":"FAKE_SECRET"}', "resolver", "invalid-envelope"),
            (b'{"status":"error","message":"FAKE_SECRET"}', "resolver", "resolver-error"),
            (b'{"status":"ok","solution":[]}', "resolver", "missing-solution"),
            (self.raw(response=None), "html", "missing-html"),
            (self.raw(url="https://[FAKE_SECRET"), "html", "invalid-final-url"),
            (self.raw(url={"secret": "FAKE_SECRET"}), "html", "invalid-final-url"),
            (self.raw(response="\ud800"), "html", "invalid-html"),
        )
        for raw, stage, reason in cases:
            with self.subTest(reason=reason):
                report = probe.collect(lambda _: raw)
                self.assertEqual(len(report["observations"]), 2)
                for row in report["observations"]:
                    self.assertEqual(row["state"], "UNKNOWN")
                    self.assertEqual((row["stage"], row["reason"]), (stage, reason))
                    self.assertEqual(row["raw_details"], "WITHHELD")
                self.assertNotIn("FAKE_SECRET", json.dumps(report))

    def test_transport_types_are_categorical_not_exception_text(self):
        cases = (
            (TimeoutError("FAKE_SECRET"), "timeout"),
            (ConnectionRefusedError("FAKE_SECRET"), "connection"),
            (probe.urllib.error.URLError(TimeoutError("FAKE_SECRET")), "timeout"),
            (probe.urllib.error.URLError(ConnectionRefusedError("FAKE_SECRET")), "connection"),
            (probe.urllib.error.URLError("FAKE_SECRET"), "transport-error"),
            (OSError("FAKE_SECRET"), "transport-error"),
            (ValueError("FAKE_SECRET"), "unclassified"),
        )
        for error, expected in cases:
            with self.subTest(expected=expected):
                calls = []
                def fetch(url):
                    calls.append(url)
                    raise error
                report = probe.collect(fetch)
                self.assertEqual(calls, [url for _, url in probe.REQUESTS])
                self.assertTrue(all(r["reason"] == expected for r in report["observations"]))
                self.assertNotIn("FAKE_SECRET", json.dumps(report))

    def test_http_error_status_numeric_only_no_body_read(self):
        stream = unittest.mock.Mock()
        error = probe.urllib.error.HTTPError(
            "https://host/?sig=FAKE_SECRET", 503, "FAKE_SECRET",
            {"Set-Cookie": "FAKE_SECRET"}, stream)
        row = probe.failure("failed-version", error)
        self.assertEqual(row["local_http_status"], 503)
        self.assertEqual(row["reason"], "local-http")
        stream.read.assert_not_called()
        self.assertNotIn("FAKE_SECRET", json.dumps(row))
        for code in ("503 FAKE_SECRET", True, 99, 600, None):
            error.code = code
            self.assertNotIn("local_http_status", probe.failure("failed-version", error))

    def test_exception_categories_cannot_inject_report_text(self):
        for reason in ("FAKE_SECRET", None, [], {"secret": "FAKE_SECRET"}):
            row = probe.failure("failed-version", probe.ObservationError(reason, "FAKE_SECRET"))
            self.assertEqual(row["reason"], "unclassified")
            self.assertNotIn("FAKE_SECRET", json.dumps(row))
            self.assertNotIn("local_http_status", row)

    def test_actual_transport_errors_reach_collect_without_extra_requests(self):
        cases = (
            (TimeoutError("FAKE_SECRET"), "timeout"),
            (probe.urllib.error.HTTPError("http://127.0.0.1:8191/v1",
             500, "FAKE_SECRET", {}, None), "local-http"),
        )
        for error, reason in cases:
            client = unittest.mock.Mock()
            client.open.side_effect = error
            with patch.object(probe.urllib.request, "build_opener", return_value=client):
                report = probe.collect(probe.request_page)
            self.assertEqual(client.open.call_count, 2)
            self.assertTrue(all(r["reason"] == reason for r in report["observations"]))
            self.assertNotIn("FAKE_SECRET", json.dumps(report))

    def test_success_after_failure_keeps_both_results(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if len(calls) == 1:
                raise TimeoutError("FAKE_SECRET")
            return self.raw()
        rows = probe.collect(fetch)["observations"]
        self.assertEqual([r["state"] for r in rows], ["UNKNOWN", "OBSERVED"])
        self.assertEqual(rows[0]["reason"], "timeout")
        self.assertNotIn("reason", rows[1])

    def test_resolver_error_with_solution_is_not_success(self):
        raw = json.loads(self.raw())
        raw.update(status="error", message="FAKE_SECRET")
        report = probe.collect(lambda _: json.dumps(raw).encode())
        self.assertTrue(all(r["reason"] == "resolver-error" and r["state"] == "UNKNOWN"
                            for r in report["observations"]))
        self.assertNotIn("FAKE_SECRET", json.dumps(report))

    def test_main_writes_failure_details_and_exits_two(self):
        old = Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            try:
                os.chdir(d)
                report = probe.collect(lambda _: b"FAKE_SECRET")
                env = {"GITHUB_REPOSITORY": "govinda-rajulu/patch-factory",
                       "GITHUB_SHA": "a"*40, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}
                output = io.StringIO()
                with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["probe"]), \
                        patch.object(probe, "collect", return_value=report), contextlib.redirect_stdout(output):
                    self.assertEqual(probe.main(), 2)
                saved = json.loads(Path("page-probe/report.json").read_bytes())
                self.assertEqual(saved["observations"][0]["reason"], "invalid-json")
                self.assertNotIn("FAKE_SECRET", output.getvalue())
            finally:
                os.chdir(old)
