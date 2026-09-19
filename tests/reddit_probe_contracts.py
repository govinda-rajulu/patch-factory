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
