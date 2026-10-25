import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from target_counts import ENABLED, TOTAL, ROWS, CANDIDATES, GITHUB_ROWS  # W4: counts follow src/targets.json

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("provider_watch", ROOT / "src/etc/provider_watch.py")
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)
ENV = dict(GITHUB_REPOSITORY="govinda-rajulu/patch-factory", GITHUB_RUN_ID="123",
           GITHUB_RUN_ATTEMPT="1", GITHUB_SHA="a" * 40)
IDENTITY = watch.run_identity(ENV)


class ProviderWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.base = self.root / "docs/review/providers"
        self.base.mkdir(parents=True)
        self.out = self.root / "provider-watch-evidence"
        self.targets = json.loads((ROOT / "src/targets.json").read_text())
        self.write_config(self.targets)
        self.rows = watch.inventory(self.targets)
        for row in self.rows:
            (self.base / row["baseline"]).write_text("Alpha\nOld\n")
        self.before = {p.name: p.read_bytes() for p in self.base.iterdir()}

    def write_config(self, targets):
        (self.root / "src/targets.json").write_text(json.dumps(targets))

    def observe(self, row):
        return dict(names=["Alpha", "New"])

    def collect(self, observe=None):
        return watch.collect(self.root, self.out, observe or self.observe, IDENTITY)

    def unchanged_baselines(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.base.iterdir()}, self.before)

    def test_inventory_includes_candidates_and_gitlab_extras(self):
        self.assertEqual(len(self.rows), ROWS)
        self.assertEqual(sum(r["host"] == "github" for r in self.rows), GITHUB_ROWS)
        self.assertEqual([(r["target"], r["role"]) for r in self.rows if r["host"] == "gitlab"],
                         [("truecaller-combo", "extra"), ("mxplayer", "extra")])  # W16h: the combo is back

    def test_good_deltas_and_coverage(self):
        result = self.collect()
        self.assertEqual(result["status"], "CHANGED")
        self.assertEqual(result["coverage"], dict(expected=ROWS, attempted=ROWS, succeeded=ROWS, failed=0, pending=0))
        for row in result["sources"]:
            self.assertEqual(row["delta"], dict(state="LEGACY_NAMES", added=["New"], removed=["Old"]))
        self.unchanged_baselines()

    def test_failure_never_becomes_all_removed_and_other_sources_continue(self):
        def observe(row):
            if row["target"] == "youtube":
                raise ValueError("credential-must-not-be-published")
            return self.observe(row)
        result = self.collect(observe)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["coverage"]["succeeded"], ROWS - 1)
        row = result["sources"][0]
        self.assertEqual(row["status"], "FAILED")
        self.assertIsNone(row["delta"])
        self.assertNotIn("observation", row)
        for p in self.out.iterdir():
            self.assertNotIn(b"credential-must-not-be-published", p.read_bytes())
        self.unchanged_baselines()

    def test_empty_bad_and_duplicate_output_refused(self):
        for data, code in ((b"Name: A\n", 2), (b"", 0), (b"network failed", 0),
                           (b"Name: \n", 0),
                           (b"Name: A\x00\n", 0), (b"x" * (watch.LIMIT + 1), 0),
                           (b"Name: \xff\n", 0)):
            with self.subTest(data=data[:20], code=code), self.assertRaises((ValueError, UnicodeError)):
                watch.names_from_output(data, code)
        self.assertEqual(watch.names_from_output(b"Header\nName: B\nDescription: test\nName: A\n", 0), ["A", "B"])
        # W16: Morphe lists "Spoof signature" twice for Reddit (universal and for the app): one name.
        self.assertEqual(watch.names_from_output(b"Name: A\nName: B\nName: A\n", 0), ["A", "B"])

    def test_empty_observation_is_failure_not_removal(self):
        result = self.collect(lambda row: dict(names=[]))
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(all(r["delta"] is None for r in result["sources"]))
        self.unchanged_baselines()

    def test_missing_baseline_not_added_or_unchanged(self):
        (self.base / self.rows[0]["baseline"]).unlink()
        result = self.collect()
        self.assertEqual(result["sources"][0]["delta"], dict(state="MISSING", added=None, removed=None))
        self.assertIn("NOT an all-added or unchanged", watch.markdown(result))

    def test_malformed_config_refuses_without_observing(self):
        cases = [[], {}, self.targets + [self.targets[0]]]
        for mutate in ("enabled", "host", "channel", "name"):
            target = copy.deepcopy(self.targets[:1])
            if mutate == "enabled":
                target[0]["enabled"] = "yes"
            else:
                target[0]["candidates"][0][mutate] = "../invalid"
            cases.append(target)
        for data in cases:
            self.write_config(data)
            with patch.object(self, "observe") as obs:
                report = self.collect(obs)
                self.assertEqual(report["status"], "FAILED")
                obs.assert_not_called()
        self.unchanged_baselines()

    def test_pending_coverage_cannot_be_healthy(self):
        report = self.collect()
        report["sources"][-1] = dict(self.rows[-1], status="PENDING")
        self.assertEqual(watch.rollup(report)["status"], "PARTIAL")

    def test_report_reader_rejects_missing_duplicate_unknown_and_forged_deltas(self):
        report = self.collect()
        for case in ("missing", "duplicate", "status", "delta", "coverage", "identity"):
            bad = copy.deepcopy(report)
            if case == "missing":
                bad["sources"].pop()
            elif case == "duplicate":
                bad["sources"][1] = copy.deepcopy(bad["sources"][0])
            elif case == "status":
                bad["sources"][0]["status"] = "HEALTHY"
            elif case == "delta":
                bad["sources"][0]["delta"]["removed"] = ["Alpha", "Old"]
            elif case == "coverage":
                bad["coverage"]["succeeded"] = 0
            else:
                bad["head"] = "b" * 40
            with self.subTest(case=case), self.assertRaises(ValueError):
                watch.validate_report(bad, self.root, IDENTITY)

    def test_uninterrupted_same_names_are_ok_but_global_error_never_is(self):
        report = self.collect(lambda row: dict(names=["Alpha", "Old"]))
        self.assertEqual(report["status"], "OK")
        report["error"] = "INTERRUPTED"
        self.assertEqual(watch.rollup(report)["status"], "FAILED")

    def test_partial_stdout_with_nonzero_exit_cannot_create_removal(self):
        def observe(row):
            return dict(names=watch.names_from_output(b"Name: Alpha\n", 7))
        report = self.collect(observe)
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(all(r["error"] == "LIST_COMMAND_FAILED" and r["delta"] is None
                            for r in report["sources"]))
        self.unchanged_baselines()

    def test_invalid_baseline_and_markdown_escape(self):
        (self.base / self.rows[0]["baseline"]).write_bytes(b"")
        result = self.collect()
        self.assertEqual(result["sources"][0]["status"], "FAILED")
        self.assertIsNone(result["sources"][0]["delta"])
        self.assertNotIn("@all", watch.display("<x> @all `bad` |"))
        self.assertNotIn("<x>", watch.display("<x>"))

    def test_runtime_uses_existing_fetchers_and_exact_local_bytes(self):
        jar, bundle = self.root / "tool.jar", self.root / "bundle.mpp"
        jar.write_bytes(b"jar")
        bundle.write_bytes(b"bundle")
        def meta(path):
            import hashlib
            return dict(path=str(path), bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), tag="fixture", asset_id=1)
        observed_argv = []
        def java(argv, **kwargs):
            observed_argv.append(argv)
            self.assertNotIn("GH_TOKEN", kwargs["env"])
            self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
            kwargs["stdout"].write(b"Name: Alpha\nName: New\n")
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(watch.github_patcher, "fetch", return_value=meta(jar)) as tool, \
             patch.object(watch.github_bundle, "fetch", return_value=meta(bundle)) as primary, \
             patch.object(watch.extra_bundle, "fetch") as extra, \
             patch.object(watch.subprocess, "run", side_effect=java), \
             patch.dict(os.environ, GH_TOKEN="never-pass-to-java"):
            obs = watch.Observer(self.root, self.root / "work")
            result = obs(self.rows[0])
            self.assertEqual(result["names"], ["Alpha", "New"])
            obs(self.rows[0])
            self.assertEqual(tool.call_count, 1)
            self.assertEqual(primary.call_count, 1)
            extra.assert_not_called()
            self.assertIn("--patches=" + str(bundle), observed_argv[0])
            self.assertIn("-x", observed_argv[0])
            # W10 (#102): "-u" hides universal patches; the watch must list them.
            self.assertNotIn("-u", observed_argv[0])

    def test_gitlab_extra_routed_to_existing_extra_transport(self):
        jar = self.root / "tool.jar"
        jar.write_bytes(b"jar")
        import hashlib
        jm = dict(path=str(jar), bytes=3, sha256=hashlib.sha256(b"jar").hexdigest(), tag="fixture", asset_id=1)
        row = next(r for r in self.rows if r["host"] == "gitlab")
        def fetch(host, ident, channel, path, env):
            self.assertEqual((host, ident, channel), ("gitlab", "82031658", "prerelease"))
            path.parent.mkdir(parents=True)
            path.write_bytes(b"bundle")
            return dict(bytes=6, sha256=hashlib.sha256(b"bundle").hexdigest(), tag="fixture", asset_id=2)
        def java(argv, **kwargs):
            kwargs["stdout"].write(b"Name: One\n")
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(watch.github_patcher, "fetch", return_value=jm), \
             patch.object(watch.extra_bundle, "fetch", side_effect=fetch), \
             patch.object(watch.subprocess, "run", side_effect=java):
            self.assertEqual(watch.Observer(self.root, self.root / "work")(row)["names"], ["One"])

    def test_cli_enforces_partial_and_delivery_failure_keeps_baselines(self):
        self.collect()
        with patch.object(watch, "ROOT", self.root), patch.dict(os.environ, ENV), \
             patch.object(watch.sys, "argv", ["provider_watch.py", "enforce"]):
            self.assertEqual(watch.main(), 0)
        with patch.object(watch, "ROOT", self.root), patch.dict(os.environ, ENV), \
             patch.object(watch.sys, "argv", ["provider_watch.py", "issue"]), \
             patch.object(watch.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as gh:
            with self.assertRaisesRegex(ValueError, "ISSUE_DELIVERY_FAILED"):
                watch.main()
            self.assertEqual(gh.call_count, 1)
        self.unchanged_baselines()
        self.collect(lambda row: dict(names=[]))
        with patch.object(watch, "ROOT", self.root), patch.dict(os.environ, ENV), \
             patch.object(watch.sys, "argv", ["provider_watch.py", "enforce"]):
            self.assertEqual(watch.main(), 1)

    def test_audit_record_covers_fixed_findings_without_live_claims(self):
        text = (ROOT / "docs/review/history/AUDIT-2026-09-26.md").read_text()
        for marker in ("PF-BUILD-001", "PF-WIRE-002", "PF-EXPLORE-003", "PF-CI-004",
                       "PORTAL-001", "36173375425", "36173399118"):
            self.assertIn(marker, text)
        self.assertIn("observation-only", text)
        self.assertNotIn("all-clear", text.lower())
        self.assertIn("ICON-PROVENANCE.md", text)
        self.assertIn("#26", text)

    def test_icon_provenance_keeps_unlicensed_marks_generic(self):
        text = (ROOT / "docs/review/ICON-PROVENANCE.md").read_text()
        for marker in ("Owner approval", "Blocked", "docs/assets/NOTICE.txt", "monogram"):
            self.assertIn(marker, text)
        self.assertIn("that estimate is not evidence", text)
        setup = (ROOT / "docs/review/history/AGENT-SETUP-2026-09.md").read_text()  # moved in W9
        self.assertIn("20 provider entries", setup)
        self.assertNotIn("all fourteen providers", setup)

    def test_provider_delta_packet_flags_mxplayer_and_preserves_exclusion(self):
        text = (ROOT / "docs/review/PROVIDER-DELTAS-2026-09.md").read_text()
        self.assertIn("Hide Settings Page UseLess Buttons", text)
        self.assertIn("still in include-patches", text)
        self.assertIn("Remember live stream playback position", text)
        self.assertIn("Stays excluded", text)
        self.assertIn("UNREVIEWED", text)
        self.assertNotIn("apply them", text)

    def test_all_third_party_actions_are_sha_pinned(self):
        import re
        roots = list((ROOT / ".github/workflows").glob("*.yml"))
        roots += list((ROOT / ".github/actions").glob("*/action.yml"))
        for path in roots:
            for match in re.finditer(r"uses:\s*([^\s#]+)@([^\s#]+)", path.read_text()):
                if match.group(1).startswith("."):
                    continue
                self.assertRegex(match.group(2), r"^[0-9a-f]{40}$",
                                 "mutable action ref " + match.group(0) + " in " + str(path))

    def test_explore_executes_only_verified_patcher(self):
        source = (ROOT / ".github/workflows/explore.yml").read_text()
        self.assertIn("persist-credentials: false", source)
        self.assertIn("python3 src/build/github_patcher.py .", source)
        self.assertNotIn("curl -sSL", source)
        self.assertNotIn("gh api repos/MorpheApp/morphe-desktop", source)
        self.assertNotIn("morphe-desktop.jar list-patches", source)
        self.assertIn('java -jar "${{ steps.patcher.outputs.jar }}"', source)
        self.assertLess(source.index("github_patcher.py"), source.index("java -jar"))

    def test_validate_rejects_gitlab_primary_candidates(self):
        source = (ROOT / ".github/workflows/validate.yml").read_text()
        self.assertIn("primary candidates must be host=github", source)
        self.assertNotIn("gitlab candidate needs project_id", source)

    def test_workflow_keeps_report_artifact_before_enforcement_without_issue_delivery(self):
        source = (ROOT / ".github/workflows/agent-watch.yml").read_text()
        self.assertLess(source.index("provider_watch.py collect"), source.index("actions/upload-artifact"))
        self.assertLess(source.index("actions/upload-artifact"), source.index("provider_watch.py enforce"))
        self.assertIn("persist-credentials: false", source)
        self.assertNotIn("provider_watch.py issue", source)
        self.assertNotIn("issues: write", source)
        self.assertNotIn("|| true", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("git push", source)


class StandingIssue(unittest.TestCase):
    """W15e (owner, 22 Oct 2026): one standing issue edited in place; old per-run issues close."""
    IDENT = {"repository": "govinda-rajulu/patch-factory", "run_id": "9", "attempt": "1"}

    def fake(self, listing, calls):
        def run(argv, **kwargs):
            calls.append(argv[:3])
            if argv[1:3] == ["issue", "list"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps(listing), "")
            if argv[1:3] == ["issue", "view"]:
                return subprocess.CompletedProcess(argv, 0, "# Provider watch: OK\n", "")
            if argv[1:3] == ["issue", "create"]:
                return subprocess.CompletedProcess(argv, 0, "https://github.com/x/issues/300\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")
        return run

    def body(self):
        import tempfile as tf
        d = Path(tf.mkdtemp())
        (d / "r.md").write_text("# Provider watch: CHANGED\n\n| a | b |\n", encoding="utf-8")
        return d / "r.md"

    def test_edits_the_standing_issue_comments_the_change_and_closes_old_ones(self):
        calls = []
        rows = [{"number": 210, "title": "provider watch"}, {"number": 205, "title": "provider watch: CHANGED run 1/1"},
                {"number": 200, "title": "provider watch: CHANGED run 2/1"}, {"number": 27, "title": "watch: repo and provider status"}]
        watch.deliver(self.IDENT, self.body(), "CHANGED", run=self.fake(rows, calls))
        verbs = [c[2] for c in calls]
        self.assertEqual(verbs, ["list", "view", "edit", "comment", "close", "close"])
        self.assertNotIn("create", verbs)

    def test_creates_one_standing_issue_when_none_exists(self):
        calls = []
        watch.deliver(self.IDENT, self.body(), "CHANGED", run=self.fake([{"number": 205, "title": "provider watch: CHANGED run 1/1"}], calls))
        self.assertEqual([c[2] for c in calls], ["list", "create", "close"])

    def test_quiet_when_nothing_changed_and_no_standing_issue(self):
        calls = []
        watch.deliver(self.IDENT, self.body(), "OK", run=self.fake([], calls))
        self.assertEqual([c[2] for c in calls], ["list"])

    def test_body_puts_changes_first_and_folds_unchanged(self):
        rows = [dict(target="facebook", name="hushfacebook", host="github", status="OK",
                     delta=dict(state="OK", added=["Open comments at full height"], removed=[]), observation=dict(names=["x"])),
                dict(target="youtube", name="morphe", host="github", status="OK",
                     delta=dict(state="OK", added=[], removed=[]), observation=dict(names=["y"]))]
        text = watch.markdown(dict(status="CHANGED", run_url="u", expected=2, sources=rows,
                                   coverage=dict(succeeded=2, failed=0, pending=0)))
        self.assertIn("**Needs you:** 1 item(s)", text)
        self.assertIn("| facebook/hushfacebook | github | CHANGED | `Open comments at full height` | (none) |", text)
        self.assertIn("1 of 2 provider(s) unchanged.", text)
        self.assertLess(text.index("## Changed or not read"), text.index("<details><summary>Every provider (2)"))
