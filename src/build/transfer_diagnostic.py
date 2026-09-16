#!/usr/bin/env python3
"""Redacted download-stage diagnostics. No HTTP, files, cookies or URL output.

Observe resolver metadata and the downloader handoff without changing requests.
Signed URL query values never appear in output, including on malformed input.
The resolver's URL is evidence only, never automatically used as a download source.
"""
import json
import os
import sys
from urllib.parse import urlsplit

MAX_RESPONSE = 16 * 1024 * 1024

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
                "user_agent_present":isinstance(sol.get("userAgent"),str) and bool(sol["userAgent"])}
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
    else:
        result={"stage":"diagnostic","parser":"invalid-mode"}
    print("DOWNLOAD_DIAGNOSTIC "+json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
