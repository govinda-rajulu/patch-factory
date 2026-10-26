"""Contracts for the manual-only, read-only MCP community scout."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/mcp-scout.yml"

spec = importlib.util.spec_from_file_location("mcp_scout_check", ROOT / "src/etc/mcp_scout_check.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class McpScoutWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WF.read_text(encoding="utf-8")

    def test_manual_only_trigger(self):
        trigger = self.text.split("on:", 1)[1].split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotRegex(trigger, r"(?m)^\s+(schedule|push|pull_request|workflow_run):")

    def test_read_only_permissions_and_no_issue_write(self):
        head = self.text.split("jobs:", 1)[0]
        self.assertRegex(head, r"(?ms)^permissions:\s*\n\s+contents:\s+read\s*$")
        job = self.text.split("  scout:\n", 1)[1]
        self.assertIn("permissions:\n      contents: read", job)
        self.assertNotIn("issues: write", head + job)
        self.assertNotIn("pull-requests: write", head + job)
        self.assertIn("timeout-minutes: 15", job)

    def test_actions_are_full_sha_pinned(self):
        import re
        refs = re.findall(r"uses:\s*([^@\s]+)@([^\s#]+)", self.text)
        self.assertGreaterEqual(len(refs), 3)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", sha) for _, sha in refs), refs)
        self.assertIn("google-github-actions/run-gemini-cli", dict(refs))

    def test_server_is_read_only_and_minimal(self):
        self.assertIn("ghcr.io/github/github-mcp-server:v2.0.3", self.text)
        self.assertIn('"--read-only"', self.text)
        self.assertIn('"--toolsets=repos"', self.text)
        self.assertIn('"core":[]', self.text)
        self.assertIn('"exclude":["run_shell_command","write_file","replace"]', self.text)

    def test_lockdown_and_missing_key_paths_are_present(self):
        self.assertIn("GEMINI_API_KEY is not configured", self.text)
        self.assertIn("git status --porcelain", self.text)
        self.assertIn("exit 1", self.text)
        self.assertIn("if: always()", self.text)


class McpScoutSchema(unittest.TestCase):
    def test_bad_lines_are_dropped_and_valid_lines_are_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "targets.json").write_text(json.dumps([{"id": "youtube"}, {"id": "ytmusic"}]))
            (d / "input.txt").write_text(
                '{"app":"youtube","repo":"owner/good_repo","reason":"patches the app"}\n'
                '{"app":"unknown","repo":"owner/nope","reason":"not a target"}\n'
                '{"app":"youtube","repo":"https://github.com/owner/nope","reason":"url rejected"}\n'
                'not json\n'
                '{"app":"ytmusic","repo":"owner/ok","reason":"  another repo  "}\n'
            )
            out = d / "out.jsonl"
            self.assertEqual(checker.check(d / "input.txt", d / "targets.json", out), 0)
            rows = [json.loads(line) for line in out.read_text().splitlines()]
            self.assertEqual(rows, [
                {"app": "youtube", "repo": "owner/good_repo", "reason": "patches the app"},
                {"app": "ytmusic", "repo": "owner/ok", "reason": "another repo"},
            ])



class McpScoutW16n(unittest.TestCase):
    """W16n: run 40298683531 got HTTP 503 ten times on the CLI default model."""

    @classmethod
    def setUpClass(cls):
        cls.text = WF.read_text(encoding="utf-8")

    def test_models_are_named_and_turns_capped(self):
        self.assertIn("gemini_model: 'gemini-3.5-flash'", self.text)
        self.assertIn("gemini_model: 'gemini-3.1-flash-lite'", self.text)
        self.assertEqual(self.text.count('"model":{"maxSessionTurns":25}'), 2)

    def test_retry_only_after_a_failed_first_attempt_and_named_verdict(self):
        self.assertEqual(self.text.count("continue-on-error: true"), 2)
        self.assertEqual(self.text.count("if: steps.gemini.outcome == 'failure'"), 2)
        self.assertIn("steps.gemini.outputs.summary || steps.gemini_lite.outputs.summary", self.text)
        verdict = self.text.split("- name: Name the scout result", 1)[1]
        self.assertIn("MODEL_UNAVAILABLE", verdict)
        self.assertIn("exit 1", verdict)
        self.assertNotIn("${{", verdict.split("run: |", 1)[1])

    def test_prompt_does_not_read_the_large_index(self):
        for prompt in self.text.split("prompt: >-")[1:]:
            body = prompt.split("- name:", 1)[0]
            self.assertIn("Do not open src/community/bundles.json", body)
            self.assertNotIn("files src/targets.json and", body)

    def test_checker_drops_wired_and_repeated_repos(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "targets.json").write_text(json.dumps([
                {"id": "reddit", "candidates": [{"owner": "MorpheApp", "repo": "morphe-patches"}],
                 "extra_bundles": [{"owner": "Adobo", "repo": "Extra"}]},
                {"id": "youtube"}]))
            (d / "input.txt").write_text(
                '{"app":"reddit","repo":"morpheapp/Morphe-Patches","reason":"already wired"}\n'
                '{"app":"reddit","repo":"adobo/extra","reason":"already an extra bundle"}\n'
                '{"app":"reddit","repo":"new/one","reason":"first"}\n'
                '{"app":"reddit","repo":"New/One","reason":"repeat"}\n'
                '{"app":"youtube","repo":"new/one","reason":"other app is fine"}\n')
            out, summary = d / "out.jsonl", d / "summary.md"
            checker.check(d / "input.txt", d / "targets.json", out, summary)
            rows = [json.loads(line) for line in out.read_text().splitlines()]
            self.assertEqual([(r["app"], r["repo"]) for r in rows], [("reddit", "new/one"), ("youtube", "new/one")])
            self.assertIn("2 accepted, 2 already wired, 1 repeated, 0 dropped (of 5 non-empty lines)", summary.read_text())

if __name__ == "__main__":
    unittest.main()
