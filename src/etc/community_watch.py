#!/usr/bin/env python3
"""Community feed -> complete report -> verified acknowledgement -> snapshot.

No external provider code executes. Collect is read-only. Report and advance
are separate commands; neither runs during PR validation or local unit tests.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit

import community_model as model

ROOT = Path(__file__).resolve().parents[2]
REPO = "govinda-rajulu/patch-factory"
TITLE = "community: index changed for apps you build"
HOST = "morphe-patches.software"
INDEX_URL = "https://" + HOST + "/data/bundles.json"
NEWS_URL = "https://" + HOST + "/data/whats-new.json"
BASELINE = "src/community/bundles.json"
RECEIPT = "src/community/watch-state.json"
MAX_BYTES = 12 * 1024 * 1024
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(data):
    return (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def write(path, data):
    temp = path.with_name(path.name + ".cand")
    need(not path.is_symlink() and not temp.is_symlink(), "UNSAFE_EVIDENCE_PATH")
    temp.write_bytes(data)
    temp.replace(path)


def identity(env):
    need(env.get("GITHUB_REPOSITORY") == REPO, "WRONG_REPOSITORY")
    need(env.get("GITHUB_REF") == "refs/heads/main", "MAIN_ONLY")
    run, attempt, head = (env.get(k, "") for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"))
    need(re.fullmatch(r"[1-9][0-9]*", run) and re.fullmatch(r"[1-9][0-9]*", attempt)
         and re.fullmatch(r"[0-9a-f]{40}", head), "INVALID_RUN_IDENTITY")
    return dict(repository=REPO, run_id=run, attempt=attempt, head=head,
                run_url="https://github.com/" + REPO + "/actions/runs/" + run + "/attempts/" + attempt)


class SameOrigin(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        need(parsed.scheme == "https" and parsed.netloc == HOST, "CROSS_ORIGIN_REDIRECT")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch(url):
    need(url in (INDEX_URL, NEWS_URL), "UNEXPECTED_FEED")
    request = Request(url, headers={"User-Agent": UA, "Accept": "application/json",
                                   "Referer": "https://" + HOST + "/"})
    with build_opener(SameOrigin()).open(request, timeout=60) as response:
        need(response.status == 200, "FEED_HTTP_FAILURE")
        need(response.headers.get_content_type() == "application/json", "FEED_NOT_JSON")
        data = response.read(MAX_BYTES + 1)
        need(0 < len(data) <= MAX_BYTES, "FEED_SIZE")
    model.read_json(data)
    return data


def history(data, targets):
    need(isinstance(data, list) and 0 < len(data) <= 100, "INVALID_NEWS_WINDOW")
    packages, _ = model.scope(targets)
    rows, seen = [], set()
    for entry in data:
        need(isinstance(entry, dict), "INVALID_NEWS_ENTRY")
        date = model.string(entry.get("date"), "NEWS_DATE")
        bundles = entry.get("bundles")
        need(isinstance(bundles, dict), "INVALID_NEWS_PROVIDERS")
        for label, bundle in bundles.items():
            model.string(label, "NEWS_LABEL")
            need(isinstance(bundle, dict) and isinstance(bundle.get("apps"), dict), "INVALID_NEWS_APPS")
            for package, app in bundle["apps"].items():
                need(isinstance(package, str) and isinstance(app, dict), "INVALID_NEWS_APP")
                patches = app.get("patches")
                need(isinstance(patches, list) and all(isinstance(p, str) and p for p in patches), "INVALID_NEWS_PATCHES")
                if package in packages:
                    row = dict(date=date, provider_label=label, package=package, patches=patches,
                               new_app=app.get("isNew") is True, new_provider=bundle.get("isNew") is True)
                    key = model.canonical(row)
                    need(key not in seen, "DUPLICATE_NEWS_ROW")
                    seen.add(key)
                    rows.append(row)
    return dict(entries=len(data), first_date=data[0]["date"], last_date=data[-1]["date"],
                relevant_rows=rows,
                limit="Rolling website history, not a complete release ledger. Labels are NOT repository identities; entries are not claimed new since the baseline.")


def chunks(text, limit=48000):
    """Preserve all text while fitting issue/comment byte limits."""
    result, buffer = [], ""
    for line in text.splitlines(keepends=True):
        need(len(line.encode()) <= limit, "REPORT_LINE_TOO_LARGE")
        if buffer and len((buffer + line).encode()) > limit:
            result.append(buffer)
            buffer = ""
        buffer += line
    if buffer:
        result.append(buffer)
    need(0 < len(result) <= 20 and "".join(result) == text, "REPORT_TOO_LARGE")
    return result


def report_text(report):
    news = report["website_history"]
    text = model.render(report)
    text += "\n## Website What's New, current rolling window\n" + news["limit"] + "\n"
    for row in news["relevant_rows"]:
        text += "- " + model.safe(row["date"]) + " | " + model.safe(row["provider_label"]) + " | " + row["package"] + "\n"
        for name in row["patches"]:
            text += "  - " + model.safe(name) + "\n"
    text += "\n## Evidence and recovery limits\n"
    text += "Source: " + INDEX_URL + "\nHistory: " + NEWS_URL + "\n"
    text += "Baseline SHA256: " + report["baseline_sha256"] + "\nObserved SHA256: " + report["index_sha256"] + "\n"
    text += "Full before/after JSON is in the run artifact; Markdown classifies all observed events, not a patch approval list.\n"
    text += "Legacy baseline may include previously unreported changes (September 21 push-before-report incident). Rolling history and current offers help review, but do not reconstruct every lost event.\n"
    return text


def collect(root, out, ident, reader=fetch):
    need(not out.exists(), "EVIDENCE_DIRECTORY_ALREADY_EXISTS")
    out.mkdir(parents=True)
    status = dict(state="COLLECTING", **ident)
    try:
        baseline = (root / BASELINE).read_bytes()
        targets_raw = (root / "src/targets.json").read_bytes()
        targets = model.read_json(targets_raw)
        raw_index, raw_news = reader(INDEX_URL), reader(NEWS_URL)
        old, new = model.read_json(baseline), model.read_json(raw_index)
        report = model.compare(old, new, targets)
        report.update(ident, fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      baseline_sha256=sha(baseline), index_sha256=sha(raw_index),
                      targets_sha256=sha(targets_raw), news_sha256=sha(raw_news),
                      website_history=history(model.read_json(raw_news), targets))
        # Bound to exact inputs and current config, independent of retry/run attempt.
        key = model.digest(dict(renderer="community-report-v1", **{k: report[k] for k in
                           ("baseline_sha256", "index_sha256", "targets_sha256", "news_sha256")}))
        report["report_key"] = key
        text = report_text(report)
        pieces = chunks(text)
        write(out / "index.json", raw_index)
        write(out / "news.json", raw_news)
        write(out / "baseline.json", baseline)
        write(out / "targets.json", targets_raw)
        write(out / "report.json", encoded(report))
        write(out / "report.md", text.encode())
        write(out / "parts.json", encoded(pieces))
        status.update(state="READY", report_key=key, parts=len(pieces),
                      report_sha256=sha(encoded(report)), parts_sha256=sha(encoded(pieces)))
    except Exception as error:
        status.update(state="FAILED", error=type(error).__name__)
    write(out / "status.json", encoded(status))
    return status


def load_report(root, out, ident):
    status = model.read_json((out / "status.json").read_bytes())
    need(status.get("state") == "READY" and all(status.get(k) == v for k, v in ident.items()), "NOT_READY_OR_WRONG_RUN")
    raw = (out / "report.json").read_bytes()
    parts_raw = (out / "parts.json").read_bytes()
    need(sha(raw) == status["report_sha256"] and sha(parts_raw) == status["parts_sha256"], "REPORT_DRIFT")
    report, parts = model.read_json(raw), model.read_json(parts_raw)
    for file, key in (("index.json", "index_sha256"), ("news.json", "news_sha256"),
                      ("baseline.json", "baseline_sha256"), ("targets.json", "targets_sha256")):
        need(sha((out / file).read_bytes()) == report[key], "INPUT_DRIFT")
    need(sha((root / BASELINE).read_bytes()) == report["baseline_sha256"] and
         sha((root / "src/targets.json").read_bytes()) == report["targets_sha256"], "BASELINE_OR_CONFIG_MOVED")
    need(all(report.get(k) == v for k, v in ident.items()), "REPORT_RUN_DRIFT")
    need("".join(parts) == report_text(report) and
         (out / "report.md").read_bytes() == report_text(report).encode(), "REPORT_TEXT_DRIFT")
    return report, parts


def api(method, path, payload=None):
    need(method in ("GET", "POST") and path.startswith("repos/" + REPO + "/"), "API_SCOPE")
    args = ["gh", "api", "--method", method, path]
    if payload is not None:
        args += ["--input", "-"]
    result = subprocess.run(args, input=encoded(payload) if payload is not None else b"",
                            capture_output=True, timeout=120)
    need(result.returncode == 0 and len(result.stdout) <= MAX_BYTES, "GITHUB_API_FAILURE")
    return json.loads(result.stdout)


def pages(path, reader=api):
    rows, seen = [], set()
    for page in range(1, 21):
        data = reader("GET", path + ("&" if "?" in path else "?") + "per_page=100&page=" + str(page))
        need(isinstance(data, list), "INVALID_API_PAGE")
        for row in data:
            need(type(row.get("id")) is int and row["id"] not in seen, "DUPLICATE_API_ROW")
            seen.add(row["id"])
            rows.append(row)
        if len(data) < 100:
            return rows
    raise ValueError("API_PAGINATION_LIMIT")


def header(report, parts):
    marker = "<!-- pf-community:" + report["report_key"] + " -->"
    return marker + "\n# Community observation report\n\n" + \
        "Run artifacts: https://github.com/" + REPO + "/actions/workflows/community-watch.yml\n\n" + \
        "Expected report: " + str(len(parts)) + " numbered comment(s). Missing parts mean INCOMPLETE; every part must pass exact readback before snapshot advancement.\n" + \
        "Index providers: " + str(report["old_coverage"]["bundles"]) + " -> " + str(report["new_coverage"]["bundles"]) + \
        "; events: " + str(report["event_count"]) + "; configured-app events: " + str(report["relevant_events"]) + \
        "; unknown-scope events: " + str(report["unknown_scope_events"]) + ".\n" + \
        "Metadata changes are not necessarily behavior changes. Review before using any provider or patch.\n" + \
        "Full data and before/after records: run artifact. The page displays saved report comments; open the issue for ALL numbered parts.\n"


def part_body(key, number, total, text):
    return "<!-- pf-community:" + key + ":" + str(number) + " -->\n" + \
        "## Report part " + str(number) + "/" + str(total) + "\n\n" + text


def bot_record(record):
    return (isinstance(record, dict) and type(record.get("id")) is int and record["id"] > 0
            and record.get("user", {}).get("login") == "github-actions[bot]"
            and record.get("user", {}).get("type") == "Bot")


def verify_delivery(data, parts, number, reader):
    need(type(number) is int and number > 0, "INVALID_ISSUE_NUMBER")
    issue_path = "repos/" + REPO + "/issues/" + str(number)
    current = reader("GET", issue_path)
    need(bot_record(current) and "pull_request" not in current and current.get("number") == number
         and current.get("title") == TITLE and current.get("body") == header(data, parts),
         "ISSUE_READBACK_FAILED")
    comments = pages(issue_path + "/comments", reader)
    for i, text in enumerate(parts, 1):
        wanted = part_body(data["report_key"], i, len(parts), text)
        tag = "<!-- pf-community:" + data["report_key"] + ":" + str(i) + " -->"
        found = [c for c in comments if tag in (c.get("body") or "")]
        need(len(found) == 1 and bot_record(found[0]) and found[0].get("body") == wanted,
             "REPORT_PART_READBACK_FAILED")


def report(root, out, ident, reader=api):
    data, parts = load_report(root, out, ident)
    body = header(data, parts)
    marker = "<!-- pf-community:" + data["report_key"] + " -->"
    path = "repos/" + REPO + "/issues"
    rows = pages(path + "?state=all", reader)
    matches = [r for r in rows if "pull_request" not in r and marker in (r.get("body") or "")]
    need(len(matches) <= 1, "DUPLICATE_REPORT_ISSUES")
    if matches:
        issue = matches[0]
        # Identical inputs get identical parts across runs. A retry can finish
        # missing parts, then must verify every part before acknowledging.
        need(bot_record(issue) and issue.get("title") == TITLE and issue.get("body") == body,
             "EXISTING_REPORT_IDENTITY_DIFFERS")
    else:
        issue = reader("POST", path, dict(title=TITLE, body=body))
    number = issue.get("number")
    need(type(number) is int and number > 0 and bot_record(issue), "INVALID_ISSUE_NUMBER_OR_AUTHOR")
    issue_path = path + "/" + str(number)
    comments = pages(issue_path + "/comments", reader)
    for i, text in enumerate(parts, 1):
        wanted = part_body(data["report_key"], i, len(parts), text)
        tag = "<!-- pf-community:" + data["report_key"] + ":" + str(i) + " -->"
        found = [c for c in comments if tag in (c.get("body") or "")]
        need(len(found) <= 1, "DUPLICATE_REPORT_PART")
        if found:
            need(bot_record(found[0]) and found[0].get("body") == wanted, "EXISTING_REPORT_PART_DIFFERS")
        else:
            reader("POST", issue_path + "/comments", dict(body=wanted))
    # Actual API readback, not trusting a local successful-write flag.
    verify_delivery(data, parts, number, reader)
    receipt = dict(report_key=data["report_key"], report_sha256=sha((out / "report.json").read_bytes()),
                   index_sha256=data["index_sha256"], baseline_sha256=data["baseline_sha256"],
                   issue=number, issue_url="https://github.com/" + REPO + "/issues/" + str(number),
                   parts=len(parts), state="READBACK_VERIFIED", **ident)
    write(out / "acknowledgement.json", encoded(receipt))
    return receipt


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=120)
    need(result.returncode == 0, "GIT_OPERATION_FAILED")
    return result.stdout.decode().strip()


def advance(root, out, ident, runner=git, reader=api):
    data, parts = load_report(root, out, ident)
    ack = model.read_json((out / "acknowledgement.json").read_bytes())
    need(ack.get("state") == "READBACK_VERIFIED" and all(ack.get(k) == v for k, v in ident.items())
         and ack.get("report_key") == data["report_key"] and ack.get("index_sha256") == data["index_sha256"]
         and ack.get("baseline_sha256") == data["baseline_sha256"] and ack.get("parts") == len(parts)
         and ack.get("report_sha256") == sha((out / "report.json").read_bytes()), "ACKNOWLEDGEMENT_MISMATCH")
    need(type(ack.get("issue")) is int and ack["issue"] > 0 and ack.get("issue_url") ==
         "https://github.com/" + REPO + "/issues/" + str(ack["issue"]), "ACKNOWLEDGEMENT_ISSUE_MISMATCH")
    need(runner(root, "rev-parse", "HEAD") == ident["head"], "CHECKOUT_HEAD_MOVED")
    need(not runner(root, "diff", "--name-only") and not runner(root, "diff", "--cached", "--name-only"), "DIRTY_CHECKOUT")
    need(runner(root, "ls-remote", "origin", "refs/heads/main").split() == [ident["head"], "refs/heads/main"],
         "REMOTE_MAIN_MOVED")
    # A saved acknowledgement is not authority if its remote report was edited
    # or removed. Re-read all parts before touching either snapshot path.
    verify_delivery(data, parts, ack["issue"], reader)
    # An unchanged byte snapshot needs no write. Reporting is still preserved.
    if data["baseline_sha256"] == data["index_sha256"]:
        return "SNAPSHOT_UNCHANGED"
    need(not (root / BASELINE).is_symlink() and not (root / RECEIPT).is_symlink(), "UNSAFE_SNAPSHOT_PATH")
    write(root / BASELINE, (out / "index.json").read_bytes())
    write(root / RECEIPT, encoded(ack))
    runner(root, "add", "--", BASELINE, RECEIPT)
    need(runner(root, "diff", "--cached", "--name-only").splitlines() == sorted([BASELINE, RECEIPT]), "STAGED_SCOPE")
    runner(root, "diff", "--cached", "--check")
    # Check again immediately before the commit; no rebase/retry/force push.
    need(runner(root, "ls-remote", "origin", "refs/heads/main").split() == [ident["head"], "refs/heads/main"],
         "REMOTE_MAIN_MOVED")
    runner(root, "-c", "user.name=github-actions[bot]", "-c",
           "user.email=41898282+github-actions[bot]@users.noreply.github.com",
           "commit", "-m", "community: acknowledge reported index " + data["report_key"][:12])
    new_head = runner(root, "rev-parse", "HEAD")
    need(runner(root, "rev-parse", "HEAD^") == ident["head"], "SNAPSHOT_PARENT_DRIFT")
    runner(root, "push", "origin", "HEAD:refs/heads/main")
    need(runner(root, "ls-remote", "origin", "refs/heads/main").split() == [new_head, "refs/heads/main"],
         "SNAPSHOT_PUSH_READBACK_FAILED")
    return "SNAPSHOT_ADVANCED_AFTER_REPORT"


def execute_phase(phase, root, out, ident, reader=api, runner=git):
    need(phase in ("report", "advance"), "INVALID_DELIVERY_PHASE")
    state = dict(phase=phase, state="STARTED", **ident)
    path = out / (phase + "-status.json")
    write(path, encoded(state))
    try:
        result = report(root, out, ident, reader) if phase == "report" else advance(root, out, ident, runner, reader)
        state.update(state="SUCCEEDED", result=result)
        return result
    except Exception as error:
        # A failed write/readback may already have had remote effects.
        # Never promise rollback or invite a blind replay.
        state.update(state="FAILED_EFFECTS_UNCONFIRMED", error=type(error).__name__,
                     recovery="Inspect run, issue and remote main before retry; no rollback inferred.")
        raise
    finally:
        write(path, encoded(state))


def main():
    need(len(sys.argv) == 2 and sys.argv[1] in ("collect", "report", "advance"), "INVALID_COMMAND")
    ident = identity(os.environ)
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    out = temp / ("community-watch-" + ident["run_id"] + "-" + ident["attempt"])
    if sys.argv[1] == "collect":
        status = collect(ROOT, out, ident)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as stream:
                stream.write("# Community Watch: " + status["state"] + "\n")
                if status["state"] == "READY":
                    data = model.read_json((out / "report.json").read_bytes())
                    stream.write(header(data, model.read_json((out / "parts.json").read_bytes())))
        return 0 if status["state"] == "READY" else 1
    print(json.dumps(execute_phase(sys.argv[1], ROOT, out, ident)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("Community Watch stopped: " + type(error).__name__ + ". No success inferred.", file=sys.stderr)
        sys.exit(2)
