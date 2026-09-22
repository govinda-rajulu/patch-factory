#!/usr/bin/env python3
"""Two fixed Reddit HTML observations. No APKs, signing, tokens or raw HTML output."""
import json
import os
import re
from pathlib import Path
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import transfer_diagnostic as diagnostic

VERSION = "2026.38.0"
BASE = "https://apkpure.com/x/com.reddit.frontpage/download"
REQUESTS = (("failed-version", BASE + "/" + VERSION), ("current-download-page", BASE))
MAX = diagnostic.MAX_RESPONSE


class ObservationError(ValueError):
    """Only allow-listed categories and numeric status may enter the report."""
    def __init__(self, reason, http_status=None):
        super().__init__("page observation unavailable")
        self.reason = reason
        self.http_status = http_status


FAILURES = {
    "local-http": "transport",
    "local-response": "transport",
    "timeout": "transport",
    "connection": "transport",
    "transport-error": "transport",
    "oversized-response": "response",
    "invalid-input": "response",
    "invalid-json": "decode",
    "invalid-envelope": "resolver",
    "resolver-error": "resolver",
    "missing-solution": "resolver",
    "missing-html": "html",
    "invalid-html": "html",
    "invalid-final-url": "html",
    "unclassified": "observation",
}


def failure(label, error):
    reason = "unclassified"
    status = None
    if isinstance(error, ObservationError):
        reason = error.reason if isinstance(error.reason, str) and error.reason in FAILURES else "unclassified"
        status = error.http_status
    elif isinstance(error, urllib.error.HTTPError):
        reason, status = "local-http", error.code
    elif isinstance(error, TimeoutError):
        reason = "timeout"
    elif isinstance(error, ConnectionError):
        reason = "connection"
    elif isinstance(error, urllib.error.URLError):
        reason = ("timeout" if isinstance(error.reason, TimeoutError) else
                  "connection" if isinstance(error.reason, ConnectionError) else "transport-error")
    elif isinstance(error, OSError):
        reason = "transport-error"
    row = {"label": label, "state": "UNKNOWN", "stage": FAILURES[reason],
           "reason": reason, "raw_details": "WITHHELD"}
    if type(status) is int and 100 <= status <= 599:
        row["local_http_status"] = status
    return row


def request_page(url):
    if url not in {u for _, u in REQUESTS}:
        raise ValueError("outside fixed probe scope")
    payload = json.dumps({"cmd": "request.get", "url": url, "maxTimeout": 15000}).encode()
    request = urllib.request.Request("http://127.0.0.1:8191/v1", data=payload,
                                     headers={"Content-Type": "application/json"})
    # Never honor external proxies or follow a redirected local service endpoint.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with client.open(request, timeout=35) as response:
        if response.status != 200 or response.geturl() != "http://127.0.0.1:8191/v1":
            raise ObservationError("local-response", response.status)
        raw = response.read(MAX + 1)
    if len(raw) > MAX:
        raise ObservationError("oversized-response")
    return raw


def observe(label, url, raw):
    # Do not publish raw resolver output or exception messages.
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):
        raise ObservationError("invalid-json") from None
    if not isinstance(data, dict):
        raise ObservationError("invalid-envelope")
    if data.get("status") == "error":
        raise ObservationError("resolver-error")
    if data.get("status") != "ok":
        raise ObservationError("invalid-envelope")
    if not isinstance(data.get("solution"), dict):
        raise ObservationError("missing-solution")
    sol = data["solution"]
    body = sol.get("response")
    if not isinstance(body, str):
        raise ObservationError("missing-html")
    final_url = sol.get("url")
    if not isinstance(final_url, str) or not final_url:
        raise ObservationError("invalid-final-url")
    try:
        parsed = urlsplit(final_url)
        hostname = parsed.hostname
    except (ValueError, TypeError):
        raise ObservationError("invalid-final-url") from None
    try:
        shape = diagnostic.page(body.encode("utf-8"))
    except (ValueError, RecursionError):
        raise ObservationError("invalid-html") from None
    if shape["parser"] != "ok":
        raise ObservationError("invalid-html")
    return {"label": label, "state": "OBSERVED", "diagnostic": diagnostic.resolver(raw, url),
            "same_apkpure_host": parsed.scheme == "https" and hostname in ("apkpure.com", "www.apkpure.com") and not parsed.username and not parsed.password,
            "expected_package_in_path": "/com.reddit.frontpage/" in parsed.path,
            "requested_version_in_html": VERSION in body,
            "limits": "Current page observation only; not the historical response, APK availability, parser repair or recovery proof."}


def collect(fetch=request_page):
    rows = []
    for label, url in REQUESTS:
        try:
            raw = fetch(url)
            if not isinstance(raw, bytes):
                raise ObservationError("invalid-input")
            if len(raw) > MAX:
                raise ObservationError("oversized-response")
            rows.append(observe(label, url, raw))
        except (ValueError, TypeError, KeyError, OSError, RecursionError) as error:
            rows.append(failure(label, error))
    return {"schema": 1, "scope": "reddit; two fixed APKPure pages; no APK transfer",
            "target_version": VERSION, "observations": rows,
            "authority": "diagnostic-only; no build, selection, fallback or publication authority"}


def main():
    if len(sys.argv) != 1:
        raise ValueError("no arguments supported")
    # This is a dedicated workflow, not a normal build with secrets inherited.
    if any(os.environ.get(k) for k in ("GH_TOKEN", "GITHUB_TOKEN", "KEYSTORE_PASS", "KEYSTORE_ALIAS", "KEYSTORE_B64")):
        raise ValueError("credential-bearing environment refused")
    identity = {k: os.environ.get(k, "") for k in
                ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")}
    if (identity["GITHUB_REPOSITORY"] != "govinda-rajulu/patch-factory" or
            not re.fullmatch(r"[0-9a-f]{40}", identity["GITHUB_SHA"]) or
            not all(re.fullmatch(r"[1-9][0-9]*", identity[k]) for k in
                    ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))):
        raise ValueError("missing or invalid workflow identity")
    report = collect()
    report["workflow_identity"] = identity
    dest = Path("page-probe")
    if dest.is_symlink():
        raise ValueError("invalid output")
    dest.mkdir(exist_ok=True)
    body = json.dumps(report, indent=2) + "\n"
    with (dest / "report.json").open("x", encoding="utf-8") as stream:
        stream.write(body)
    print(body)
    return 0 if all(r["state"] == "OBSERVED" for r in report["observations"]) else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError):
        print("PAGE_PROBE_REFUSED: no raw response, URL, token or exception details printed", file=sys.stderr)
        sys.exit(2)
