#!/usr/bin/env python3
"""Redacted download-stage diagnostics. No HTTP, files, cookies or URL output.

Observe resolver metadata and the downloader handoff without changing requests.
Signed URL query values never appear in output, including on malformed input.
The resolver's URL is evidence only, never automatically used as a download source.
"""
import json
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

MAX_RESPONSE = 16 * 1024 * 1024
MAX_PAGE = 2 * 1024 * 1024


def page(raw):
    """Bounded shape only. No text, hrefs, titles, cookies or selector authority."""
    result = {"stage": "download-page", "authority": "diagnostic-only",
              "parser": "invalid-or-oversized"}
    if not isinstance(raw, bytes) or len(raw) > MAX_PAGE:
        return result
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        return result
    counts = {"anchors": 0, "apkpure_download_ids": 0,
              "apkmirror_download_ids": 0, "download_ids_with_href": 0,
              "download_ids_with_duplicate_href": 0}
    class Shape(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag != "a":
                return
            counts["anchors"] += 1
            ids = [v for k, v in attrs if k == "id"]
            hrefs = [v for k, v in attrs if k == "href"]
            if "download_link" in ids:
                counts["apkpure_download_ids"] += 1
            if "download-link" in ids:
                counts["apkmirror_download_ids"] += 1
            if "download_link" in ids or "download-link" in ids:
                counts["download_ids_with_href"] += int(any(hrefs))
                counts["download_ids_with_duplicate_href"] += int(len(hrefs) > 1)
    try:
        parser = Shape(convert_charrefs=True)
        parser.feed(text)
        parser.close()
    except (ValueError, AssertionError, RecursionError):
        return result
    lower = text.lower()
    result.update(parser="ok", bytes=len(raw), empty=not text.strip(), **counts,
                  challenge_marker_present=any(x in lower for x in
                      ("cf-chl-", "challenge-platform", "just a moment", "verify you are human")),
                  unavailable_marker_present=any(x in lower for x in
                      ("version not found", "page not found", "no longer available")),
                  marker_limit="heuristic presence only, not a diagnosis")
    return result

def location(value):
    if not isinstance(value,str) or not value or len(value)>32768:
        return {"present":False,"kind":"missing-or-invalid"}
    try:
        u=urlsplit(value)
        if u.scheme!="https" or u.username or u.password or u.port not in (None,443):
            return {"present":True,"kind":"unsupported"}
        host=(u.hostname or "").lower()
        if host in ("www.apkmirror.com","apkmirror.com"):
            kind="apkmirror-download-endpoint" if u.path.endswith("/download.php") else "apkmirror-page"
        elif host.endswith(".r2.cloudflarestorage.com") and host!="r2.cloudflarestorage.com":
            kind="r2-object"
        else:kind="other-https"
        return {"present":True,"kind":kind,"has_query":bool(u.query)}
    except (ValueError,TypeError):
        return {"present":True,"kind":"unparseable"}

def resolver(raw, request):
    try:
        if len(raw)>MAX_RESPONSE:raise ValueError()
        d=json.loads(raw)
        sol=d.get("solution",{})
        if not isinstance(sol,dict):raise ValueError()
        resolved=sol.get("url")
        status=sol.get("status")
        return {"stage":"resolver","parser":"ok",
                "resolver_ok":d.get("status")=="ok",
                "http_status":status if type(status) is int and 100<=status<=599 else None,
                "requested":location(request),"resolved":location(resolved),
                "same_url":resolved==request if isinstance(resolved,str) and bool(resolved) else None,
                "cookies_present":bool(sol.get("cookies")),
                "user_agent_present":isinstance(sol.get("userAgent"),str) and bool(sol["userAgent"]),
                "response_shape":page(sol["response"].encode("utf-8"))
                    if isinstance(sol.get("response"),str) else page(None)}
    except (ValueError,TypeError,AttributeError):
        return {"stage":"resolver","parser":"invalid-or-oversized"}

def handoff(env):
    return {"stage":"binary-handoff","destination":location(env.get("PF_DIAG_DEST")),
            "referer":location(env.get("PF_DIAG_REFERER")),
            "cookies_present":bool(env.get("PF_DIAG_COOKIES")),
            "user_agent_present":bool(env.get("PF_DIAG_UA"))}

def main():
    mode=sys.argv[1] if len(sys.argv)==2 else ""
    if mode=="resolver":
        result=resolver(sys.stdin.buffer.read(MAX_RESPONSE+1),os.environ.get("PF_DIAG_REQUEST"))
    elif mode=="handoff":result=handoff(os.environ)
    elif mode=="page":result=page(sys.stdin.buffer.read(MAX_PAGE+1))
    else:
        result={"stage":"diagnostic","parser":"invalid-mode"}
    print("DOWNLOAD_DIAGNOSTIC "+json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
