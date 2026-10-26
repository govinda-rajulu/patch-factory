import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/etc/watch_state.py"


FAKE_GH = r'''#!/usr/bin/env python3
import base64, json, os, sys
from pathlib import Path

state_path = Path(os.environ["FAKE_STATE"])
state = json.loads(state_path.read_text())
args = sys.argv[1:]
if args[:1] != ["api"]:
    print("unexpected command", file=sys.stderr)
    raise SystemExit(2)
put = "-X" in args and args[args.index("-X") + 1] == "PUT"
endpoint = next((x for x in args if x.startswith("repos/")), "")
if endpoint.endswith("git/ref/heads/watch-state"):
    if not state.get("branch", True):
        print("HTTP 404", file=sys.stderr); raise SystemExit(1)
    print(json.dumps({"ref": "refs/heads/watch-state"})); raise SystemExit(0)
name = endpoint.split("/contents/", 1)[1].split("?", 1)[0]
files = state.setdefault("files", {})
if put:
    body = json.load(sys.stdin)
    state.setdefault("puts", []).append(body)
    if state.get("conflict_missing_once"):
        state["conflict_missing_once"] = False
        state_path.write_text(json.dumps(state))
        print("HTTP 409", file=sys.stderr); raise SystemExit(1)
    if state.get("conflict_once"):
        state["conflict_once"] = False
        state["files"][name + ".sha"] = "new-sha"
        state_path.write_text(json.dumps(state))
        print("HTTP 409", file=sys.stderr); raise SystemExit(1)
    old = files.get(name + ".sha")
    if old and body.get("sha") != old:
        print("HTTP 409", file=sys.stderr); raise SystemExit(1)
    files[name] = base64.b64decode(body["content"]).decode("utf-8")
    files[name + ".sha"] = "written-sha"
    state_path.write_text(json.dumps(state))
    print(json.dumps({"content": {"path": name}})); raise SystemExit(0)
if state.get("error"):
    print("HTTP " + str(state["error"]), file=sys.stderr); raise SystemExit(1)
if name not in files:
    print("HTTP 404", file=sys.stderr); raise SystemExit(1)
if any(x.startswith("Accept: application/vnd.github.raw") for x in args):
    sys.stdout.buffer.write(files[name].encode("utf-8"))
else:
    print(json.dumps({"name": name, "sha": files.get(name + ".sha", "old-sha")}))
raise SystemExit(0)
'''


class WatchStateContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fake = self.root / "gh"
        self.fake.write_text(FAKE_GH)
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IEXEC)
        self.state_file = self.root / "state.json"
        self.env = dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ.get("PATH", ""),
                        REPO="owner/repo", FAKE_STATE=str(self.state_file))

    def write_state(self, files=None, **extra):
        rows = {"branch": True, "files": files or {}}
        rows.update(extra)
        self.state_file.write_text(json.dumps(rows))

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True)

    def test_put_updates_one_file_and_keeps_the_other(self):
        self.write_state(files={"state.json": "old", "state.json.sha": "sha-state",
                                "needs-you-decisions.json": "ledger", "needs-you-decisions.json.sha": "sha-ledger"})
        source = self.root / "new-state"
        source.write_text("new")
        result = self.invoke("put", "state.json", str(source), "selection state")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.state_file.read_text())
        self.assertEqual(data["files"]["state.json"], "new")
        self.assertEqual(data["files"]["needs-you-decisions.json"], "ledger")
        self.assertEqual(data["puts"][0]["sha"], "sha-state")

    def test_put_retries_one_sha_conflict(self):
        self.write_state(files={"state.json": "old", "state.json.sha": "sha-state"}, conflict_once=True)
        source = self.root / "new-state"
        source.write_text("new")
        result = self.invoke("put", "state.json", str(source), "selection state")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.state_file.read_text())
        self.assertEqual(len(data["puts"]), 2)
        self.assertEqual(data["puts"][1]["sha"], "new-sha")

    def test_first_write_that_loses_to_another_file_is_created_again(self):
        # W16n review: two first writes to different files; the loser's path is still missing.
        self.write_state(files={"state.json": "s", "state.json.sha": "sha-state"}, conflict_missing_once=True)
        source = self.root / "ledger"
        source.write_text("[]")
        result = self.invoke("put", "needs-you-decisions.json", str(source), "needs you decisions")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.state_file.read_text())
        self.assertEqual(len(data["puts"]), 2)
        self.assertNotIn("sha", data["puts"][1])
        self.assertEqual(data["files"]["needs-you-decisions.json"], "[]")
        self.assertEqual(data["files"]["state.json"], "s")

    def test_get_writes_raw_bytes(self):
        self.write_state(files={"state.json": "{\"seen\":true}"})
        destination = self.root / "out"
        result = self.invoke("get", "state.json", str(destination))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(destination.read_bytes(), b'{"seen":true}')
        self.assertIn("OK watch-state get state.json 13 bytes", result.stdout)

    def test_get_distinguishes_404_from_other_error(self):
        destination = self.root / "out"
        self.write_state(files={}, error=404)
        missing = self.invoke("get", "state.json", str(destination))
        self.assertEqual(missing.returncode, 3)
        self.assertFalse(destination.exists())
        self.write_state(files={}, error=500)
        failed = self.invoke("get", "state.json", str(destination))
        self.assertEqual(failed.returncode, 1)

    def test_workflows_use_non_destructive_single_file_updates(self):
        for name in ("selection-watch.yml", "needs-you.yml"):
            text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            self.assertIn("watch_state.py", text)
            self.assertNotIn("git init", text)
            self.assertNotIn("push -q -f", text)

    def test_put_refuses_when_branch_is_missing(self):
        self.write_state(files={}, branch=False)
        source = self.root / "source"
        source.write_text("x")
        result = self.invoke("put", "state.json", str(source), "bad branch")
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing to create an orphan branch", result.stdout)

    def test_allowlist_refusal(self):
        self.write_state()
        source = self.root / "source"
        source.write_text("x")
        result = self.invoke("put", "other.json", str(source), "bad")
        self.assertEqual(result.returncode, 1)
        self.assertIn("allowlist", result.stdout)

    def test_size_bound(self):
        self.write_state()
        source = self.root / "large"
        source.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        result = self.invoke("put", "state.json", str(source), "too large")
        self.assertEqual(result.returncode, 1)
        self.assertIn("2 MiB", result.stdout)


if __name__ == "__main__":
    unittest.main()
