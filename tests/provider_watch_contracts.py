import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

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
        self.assertEqual(len(self.rows), 19)
        self.assertEqual(sum(r["host"] == "github" for r in self.rows), 17)
        self.assertEqual([(r["target"], r["role"]) for r in self.rows if r["host"] == "gitlab"],
                         [("truecaller-combo", "extra"), ("mxplayer", "extra")])

    def test_good_deltas_and_coverage(self):
        result = self.collect()
        self.assertEqual(result["status"], "CHANGED")
        self.assertEqual(result["coverage"], dict(expected=19, attempted=19, succeeded=19, failed=0, pending=0))
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
        self.assertEqual(result["coverage"]["succeeded"], 18)
        row = result["sources"][0]
        self.assertEqual(row["status"], "FAILED")
        self.assertIsNone(row["delta"])
        self.assertNotIn("observation", row)
        for p in self.out.iterdir():
            self.assertNotIn(b"credential-must-not-be-published", p.read_bytes())
        self.unchanged_baselines()

    def test_empty_bad_and_duplicate_output_refused(self):
        for data, code in ((b"Name: A\n", 2), (b"", 0), (b"network failed", 0),
                           (b"Name: \n", 0), (b"Name: A\nName: A\n", 0),
                           (b"Name: A\x00\n", 0), (b"x" * (watch.LIMIT + 1), 0),
                           (b"Name: \xff\n", 0)):
            with self.subTest(data=data[:20], code=code), self.assertRaises((ValueError, UnicodeError)):
                watch.names_from_output(data, code)
        self.assertEqual(watch.names_from_output(b"Header\nName: B\nDescription: test\nName: A\n", 0), ["A", "B"])

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
            self.assertIn("-u", observed_argv[0])

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

    def test_workflow_preserves_reports_before_enforcement(self):
        source = (ROOT / ".github/workflows/agent-watch.yml").read_text()
        self.assertLess(source.index("provider_watch.py collect"), source.index("provider_watch.py issue"))
        self.assertLess(source.index("actions/upload-artifact"), source.index("provider_watch.py enforce"))
        self.assertIn("persist-credentials: false", source)
        self.assertNotIn("|| true", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("git push", source)
