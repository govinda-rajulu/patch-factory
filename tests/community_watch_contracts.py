import copy
import re
import json
from pathlib import Path
import unittest
import sys
import tempfile
import subprocess
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/etc"))
import community_model as m
import community_watch as w

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return dict(bundles=[dict(source="github", repo="owner/patches", name="Test",
        patches=[dict(name="One", description="original", default=True, compatiblePackagesKey=0)],
        patchCount=1, targetApps=["com.example.app"])],
        compatibilities=[[dict(packageName="com.example.app", targets=[dict(version="1")])]])


TARGETS = [dict(id="app", enabled=True, package="com.example.app",
               candidates=[dict(owner="owner", repo="patches")])]


def expected_patch_count(data):
    """Independent count: per repository, the multiset union of its bundles' patch records, with
    compatibility references resolved (two listings may point at different but equal rows)."""
    import collections
    compat = data["compatibilities"]
    table = {str(k): m.compatibility(v) for k, v in (enumerate(compat) if isinstance(compat, list) else compat.items())}
    def resolved(patch):
        record = dict(patch)
        refs = [record.pop(f) for f in ("compatiblePackagesKey", "compatibilityKey") if f in record]
        record["compatibility"] = table[str(refs[0])] if refs and refs[0] is not None else {}
        return m.canonical(record)
    groups = collections.defaultdict(list)
    for b in data["bundles"]:
        groups[b.get("source", "github") + ":" + b["repo"].lower()].append(b)
    total = 0
    for members in groups.values():
        union = collections.Counter()
        for b in members:
            union |= collections.Counter(resolved(p) for p in b["patches"])
        total += sum(union.values())
    return total


class Model(unittest.TestCase):
    def test_real_snapshot_with_a_doubled_repository(self):
        data = json.loads((ROOT / "src/community/bundles.json").read_text())
        twin = copy.deepcopy(data["bundles"][0])
        twin["name"] = "Twin listing"
        twin["patches"] = twin["patches"] + [dict(name="Only in the twin listing")]
        twin["patchCount"] = len(twin["patches"])
        data["bundles"].append(twin)
        before = m.inventory(json.loads((ROOT / "src/community/bundles.json").read_text()))
        parsed = m.inventory(data)
        # Delta against the stored snapshot, which may already list a repository twice (26 Oct:
        # epabafree/sabp-eppy-patches; Validate run 40338726723, wrong call 81).
        self.assertEqual(parsed["coverage"]["patches"], expected_patch_count(data))
        self.assertEqual(parsed["coverage"]["patches"] - before["coverage"]["patches"], 1)
        self.assertEqual(len(parsed["coverage"]["merged_providers"]) - len(before["coverage"]["merged_providers"]),
                         0 if any(x["provider"] == "github:" + data["bundles"][0]["repo"].lower()
                                  for x in before["coverage"]["merged_providers"]) else 1)

    def test_real_snapshot_complete_accounting(self):
        data = json.loads((ROOT / "src/community/bundles.json").read_text())
        parsed = m.inventory(data)
        self.assertEqual(parsed["coverage"]["bundles"], len(data["bundles"]))
        # W16n merges every bundle of one repository; a record an earlier bundle of the same
        # repository already gave is counted once (26 Oct: the live snapshot lists one repo twice,
        # 5960 raw records, 5957 after the merge; Validate run 40333090933).
        self.assertEqual(parsed["coverage"]["patches"], expected_patch_count(data))
        self.assertEqual(parsed["coverage"]["patches"],
                         sum(len(v) for p in parsed["providers"].values() for v in p["patches"].values()))
        if not parsed["coverage"]["merged_providers"]:
            self.assertEqual(parsed["coverage"]["patches"], sum(len(b["patches"]) for b in data["bundles"]))
        self.assertEqual(parsed["coverage"]["compatibility_rows"], len(data["compatibilities"]))
        self.assertGreater(parsed["coverage"]["patches"], 0)
        targets = json.loads((ROOT / "src/targets.json").read_text())
        report = m.compare(data, data, targets)
        self.assertEqual(report["event_count"], 0)
        self.assertEqual(report["old_semantic_sha256"], report["new_semantic_sha256"])

    def test_compatibility_alias_and_package_map(self):
        data = fixture()
        data["compatibilities"] = [{"com.example.app": ["1", "2"]}]
        patch = data["bundles"][0]["patches"][0]
        patch["compatibilityKey"] = patch.pop("compatiblePackagesKey")
        parsed = m.inventory(data)
        row = parsed["providers"]["github:owner/patches"]["patches"]["One"][0]
        self.assertEqual(row["compatibility"]["com.example.app"][0]["versions"], ["1", "2"])
        self.assertEqual(parsed["coverage"]["unknown_applicability_patches"], 0)

    def test_options_defaults_description_and_versions(self):
        for field, value in (("options", [{"key":"test", "default":False}]), ("default", False),
                             ("description", "changed")):
            a, b = fixture(), fixture()
            b["bundles"][0]["patches"][0][field] = value
            report = m.compare(a, b, TARGETS)
            self.assertEqual(report["event_count"], 1)
            self.assertIn(field, report["events"][0]["changed_fields"])
            self.assertEqual(report["relevant_events"], 1)
        a, b = fixture(), fixture()
        b["compatibilities"][0][0]["targets"] = [{"version":"2"}]
        report = m.compare(a, b, TARGETS)
        self.assertIn("compatibility", report["events"][0]["changed_fields"])

    def test_add_remove_and_rename_without_guessing(self):
        a, b = fixture(), fixture()
        b["bundles"][0]["patches"][0]["name"] = "Renamed"
        report = m.compare(a, b, TARGETS)
        self.assertEqual({e["kind"] for e in report["events"]}, {"PATCH_ADDED", "PATCH_REMOVED"})
        self.assertEqual(report["event_count"], 2)

    def test_provider_host_identity_not_collapsed(self):
        a, b = fixture(), fixture()
        b["bundles"][0]["source"] = "gitlab"
        report = m.compare(a, b, TARGETS)
        self.assertEqual({e["kind"] for e in report["events"]}, {"PROVIDER_ADDED", "PROVIDER_REMOVED"})

    def test_duplicate_name_variants_are_preserved(self):
        a, b = fixture(), fixture()
        p = copy.deepcopy(b["bundles"][0]["patches"][0])
        p["default"] = False
        b["bundles"][0]["patches"].append(p)
        b["bundles"][0]["patchCount"] = 2
        parsed = m.inventory(b)
        self.assertEqual(len(parsed["providers"]["github:owner/patches"]["patches"]["One"]), 2)
        report = m.compare(a, b, TARGETS)
        self.assertEqual(report["events"][0]["kind"], "PATCH_CHANGED")
        self.assertIn("default", report["events"][0]["changed_fields"])

    def test_reordering_and_display_counters_are_not_patch_changes(self):
        a, b = fixture(), fixture()
        b["bundles"][0].update(stars=100, hotRank=1, avatarUrl="new.png", firstSeen=999)
        b["compatibilities"][0][0]["name"] = "Cosmetic App Name"
        self.assertEqual(m.compare(a, b, TARGETS)["event_count"], 0)

    def test_compatibility_table_reindex_is_semantic_noop(self):
        a, b = fixture(), fixture()
        b["compatibilities"].insert(0, [{"packageName":"other.app", "targets":[]}])
        b["bundles"][0]["patches"][0]["compatiblePackagesKey"] = 1
        self.assertEqual(m.compare(a, b, TARGETS)["event_count"], 0)

    def test_unknown_scope_never_silently_irrelevant(self):
        a, b = fixture(), fixture()
        for data in (a, b):
            data["bundles"][0]["patches"][0].pop("compatiblePackagesKey")
        b["bundles"][0]["patches"][0]["default"] = False
        report = m.compare(a, b, TARGETS)
        self.assertEqual(report["unknown_scope_events"], 1)
        self.assertEqual(report["events"][0]["relevance"], "UNKNOWN_SCOPE")
        self.assertIn("UNKNOWN_SCOPE", m.render(report))

    def test_late_relevant_provider_not_hidden_by_first_25(self):
        a, b = fixture(), fixture()
        for n in range(40):
            row = copy.deepcopy(b["bundles"][0])
            row["repo"] = "aaa/provider" + str(n)
            row["patches"][0]["compatiblePackagesKey"] = 1
            row["targetApps"] = ["other.app"]
            b["bundles"].append(row)
        b["compatibilities"].append([{"packageName":"other.app", "targets":[]}])
        last = copy.deepcopy(b["bundles"][0])
        last["repo"] = "zzz/relevant"
        b["bundles"].append(last)
        report = m.compare(a, b, TARGETS)
        self.assertEqual(report["event_count"], 41)
        self.assertEqual(report["relevant_events"], 1)
        self.assertIn("github:zzz/relevant", m.render(report))

    def test_unwired_offers_visible_even_without_new_delta(self):
        a = fixture()
        targets = copy.deepcopy(TARGETS)
        targets[0]["candidates"][0]["owner"] = "different"
        report = m.compare(a, a, targets)
        self.assertEqual(report["event_count"], 0)
        self.assertEqual(len(report["unwired_offers"]), 1)

    def test_duplicate_json_and_nonfinite_refused(self):
        for value in (b'{"x":1,"x":2}', b'{"x":NaN}', b"<html>not JSON</html>", b""):
            with self.assertRaises(ValueError):
                m.read_json(value)

    def test_missing_duplicate_malformed_and_empty_refused(self):
        # W16n: a repository listed twice is merged and named, no longer refused (see DuplicateProvider).
        for case in ("empty", "missing", "count", "map", "targets", "both"):
            data = fixture()
            if case == "empty":
                data["bundles"] = []
            elif case == "missing":
                data["bundles"][0]["patches"][0]["compatiblePackagesKey"] = 99
            elif case == "count":
                data["bundles"][0]["patchCount"] = 10
            elif case == "map":
                data["compatibilities"][0] = {"not-a-package":["1"]}
            elif case == "targets":
                data["bundles"][0]["targetApps"] = ["invalid"]
            else:
                data["bundles"][0]["patches"][0]["compatibilityKey"] = 0
            with self.subTest(case=case), self.assertRaises(ValueError):
                m.inventory(data)

    def test_provider_metadata_changes_and_html_escaping(self):
        a, b = fixture(), fixture()
        b["bundles"][0]["name"] = "<img> @all"
        report = m.compare(a, b, TARGETS)
        self.assertEqual(report["events"][0]["kind"], "PROVIDER_METADATA_CHANGED")
        self.assertIn("name", report["events"][0]["changed_fields"])
        self.assertNotIn("@all", m.safe("@all"))
        self.assertNotIn("<img>", m.safe("<img>"))

    def test_multiple_build_variants_for_same_package_survive(self):
        data = fixture()
        second = copy.deepcopy(data["compatibilities"][0][0])
        second["targets"][0]["version"] = "2"
        data["compatibilities"][0].append(second)
        parsed = m.inventory(data)
        variants = parsed["providers"]["github:owner/patches"]["patches"]["One"][0]["compatibility"]["com.example.app"]
        self.assertEqual(len(variants), 2)
        self.assertEqual({v["targets"][0]["version"] for v in variants}, {"1", "2"})


class Delivery(unittest.TestCase):
    def setUp(self):
        # W16n: these tests push to a local origin. suite.sh and Validate export GITHUB_ACTIONS=true,
        # and push_remote now fails closed in Actions without a token, so pin "outside Actions".
        env = patch.dict("os.environ", {})
        env.start()
        self.addCleanup(env.stop)
        import os
        os.environ.pop("GITHUB_ACTIONS", None)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        (self.root / "src/community").mkdir(parents=True)
        self.old = fixture()
        self.new = fixture()
        self.new["bundles"][0]["patches"][0]["default"] = False
        (self.root / w.BASELINE).write_bytes(w.encoded(self.old))
        (self.root / "src/targets.json").write_bytes(w.encoded(TARGETS))
        self.out = Path(self.temp.name) / "evidence"
        self.ident = dict(repository=w.REPO, run_id="123", attempt="1", head="a"*40,
                          run_url="https://github.com/" + w.REPO + "/actions/runs/123/attempts/1")
        self.news = [dict(date="September 25, 2026", bundles={"Display label only": {
            "apps": {"com.example.app": {"patches":["A recent patch"]}}}})]
        self.issues, self.comments, self.calls = [], [], []
        self.fail_comment = False
        self.omit_readback = False

    def fetch(self, url):
        return w.encoded(self.new if url == w.INDEX_URL else self.news)

    def collect(self):
        return w.collect(self.root, self.out, self.ident, self.fetch)

    def api(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET":
            if "/comments?" in path:
                return [] if self.omit_readback else copy.deepcopy(self.comments)
            if "/issues?" in path:
                return copy.deepcopy(self.issues)
            if path.endswith("/issues/1"):
                return copy.deepcopy(self.issues[0])
        if method == "POST":
            if path.endswith("/comments"):
                if self.fail_comment:
                    raise ValueError("synthetic failure")
                row = dict(id=len(self.comments)+10, body=payload["body"],
                           user=dict(login="github-actions[bot]", type="Bot"))
                self.comments.append(row)
                return copy.deepcopy(row)
            row = dict(id=1, number=1, user=dict(login="github-actions[bot]", type="Bot"), **payload)
            self.issues.append(row)
            return copy.deepcopy(row)
        raise AssertionError((method, path))

    def test_complete_collection_and_history_before_report(self):
        baseline = (self.root / w.BASELINE).read_bytes()
        status = self.collect()
        self.assertEqual(status["state"], "READY")
        data, parts = w.load_report(self.root, self.out, self.ident)
        self.assertEqual(data["relevant_events"], 1)
        self.assertEqual(data["website_history"]["relevant_rows"][0]["provider_label"], "Display label only")
        self.assertIn("A recent patch", "".join(parts))
        ack = w.report(self.root, self.out, self.ident, self.api)
        self.assertEqual(ack["state"], "READBACK_VERIFIED")
        self.assertEqual((self.root / w.BASELINE).read_bytes(), baseline)

    def test_delivery_failure_never_acknowledges_or_changes_snapshot(self):
        self.collect()
        baseline = (self.root / w.BASELINE).read_bytes()
        self.fail_comment = True
        with self.assertRaises(ValueError):
            w.report(self.root, self.out, self.ident, self.api)
        self.assertFalse((self.out / "acknowledgement.json").exists())
        self.assertEqual((self.root / w.BASELINE).read_bytes(), baseline)
        with self.assertRaises(FileNotFoundError), patch.object(w, "git") as git:
            w.advance(self.root, self.out, self.ident, git)
            git.assert_not_called()

    def test_failed_partial_report_can_resume_without_duplicate_issue(self):
        self.collect()
        self.fail_comment = True
        with self.assertRaises(ValueError):
            w.report(self.root, self.out, self.ident, self.api)
        self.fail_comment = False
        self.ident["attempt"] = "2"
        self.ident["run_url"] = self.ident["run_url"].replace("/attempts/1", "/attempts/2")
        self.out = Path(self.temp.name) / "evidence-retry"
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        w.report(self.root, self.out, self.ident, self.api)
        self.assertEqual(len(self.issues), 1)
        self.assertEqual(len(self.comments), 1)

    def test_missing_readback_prevents_acknowledgement(self):
        self.collect()
        self.omit_readback = True
        with self.assertRaisesRegex(ValueError, "READBACK"):
            w.report(self.root, self.out, self.ident, self.api)
        self.assertFalse((self.out / "acknowledgement.json").exists())

    def test_tampered_report_input_or_baseline_refuses(self):
        self.collect()
        for path in (self.out / "index.json", self.out / "parts.json",
                     self.root / w.BASELINE, self.root / "src/targets.json"):
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.subTest(path=path), self.assertRaises(ValueError):
                w.load_report(self.root, self.out, self.ident)
            path.write_bytes(original)

    def test_news_package_must_match_package_grammar_and_is_escaped(self):
        bad = copy.deepcopy(self.news)
        bad[0]["bundles"]["Display label only"]["apps"]["not a package"] = {"patches": ["x"]}
        with self.assertRaisesRegex(ValueError, "INVALID_NEWS_APP"):
            w.history(bad, TARGETS)
        good = copy.deepcopy(self.news)
        good[0]["bundles"]["Display label only"]["apps"] = {"com.example.app": {"patches": ["x"]}}
        report = m.compare(fixture(), fixture(), TARGETS)
        report["provider_ranks"] = []
        report["website_history"] = w.history(good, TARGETS)
        report["baseline_sha256"] = report["index_sha256"] = "a" * 64
        self.assertIn("com.example.app", w.report_text(report))

    def test_html_malformed_or_empty_feed_fails_without_report(self):
        for data in (b"<html>fallback</html>", b"{}", b'{"bundles":[],"compatibilities":[]}'):
            out = Path(self.temp.name) / ("bad-" + str(len(data)))
            status = w.collect(self.root, out, self.ident, lambda url: data)
            self.assertEqual(status["state"], "FAILED")
            self.assertFalse((out / "report.json").exists())
            # W16n: a failed compare still keeps the raw inputs for diagnosis.
            self.assertEqual((out / "index.json").read_bytes(), data)
            self.assertTrue((out / "baseline.json").exists())

    def test_exact_chunk_roundtrip_and_oversized_refusal(self):
        text = ("A full record, not a partial excerpt\n" * 5000)
        parts = w.chunks(text)
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(len(p.encode()) <= 48000 for p in parts))
        with self.assertRaises(ValueError):
            w.chunks("x" * 48001)

    def test_duplicate_issue_and_part_refused(self):
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        self.issues.append(dict(self.issues[0], id=2, number=2))
        with self.assertRaises(ValueError):
            w.report(self.root, self.out, self.ident, self.api)
        self.issues.pop()
        self.comments.append(dict(self.comments[0], id=20))
        with self.assertRaises(ValueError):
            w.report(self.root, self.out, self.ident, self.api)

    def git(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd or self.root, capture_output=True, check=True)
        return result.stdout.decode().strip()

    def git_setup(self):
        remote = Path(self.temp.name) / "remote.git"
        self.git("init", "--bare", str(remote))
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", "src")
        self.git("commit", "-m", "fixture baseline")
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "origin", "main")
        self.ident["head"] = self.git("rev-parse", "HEAD")
        return remote

    def test_actual_git_snapshot_advances_only_after_ack(self):
        remote = self.git_setup()
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        state = w.advance(self.root, self.out, self.ident, reader=self.api)
        self.assertEqual(state, "SNAPSHOT_ADVANCED_AFTER_REPORT")
        self.assertEqual(self.git("rev-parse", "HEAD^"), self.ident["head"])
        self.assertEqual(self.git("--git-dir=" + str(remote), "rev-parse", "main"), self.git("rev-parse", "HEAD"))
        self.assertEqual(self.git("diff", "--name-only", "HEAD^", "HEAD").splitlines(), [w.BASELINE, w.RECEIPT])
        self.assertEqual((self.root / w.BASELINE).read_bytes(), w.encoded(self.new))

    def test_stale_remote_and_wrong_ack_refuse_before_local_snapshot_write(self):
        remote = self.git_setup()
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        baseline = (self.root / w.BASELINE).read_bytes()
        ack_path = self.out / "acknowledgement.json"
        raw = ack_path.read_bytes()
        ack = json.loads(raw)
        ack["index_sha256"] = "f"*64
        ack_path.write_bytes(w.encoded(ack))
        with self.assertRaises(ValueError):
            w.advance(self.root, self.out, self.ident)
        self.assertEqual((self.root / w.BASELINE).read_bytes(), baseline)
        ack_path.write_bytes(raw)
        self.git("commit", "--allow-empty", "-m", "concurrent unrelated work")
        self.git("push", "origin", "main")
        self.git("checkout", "--detach", self.ident["head"])
        with self.assertRaisesRegex(ValueError, "REMOTE_MAIN_MOVED"):
            w.advance(self.root, self.out, self.ident)
        self.assertEqual((self.root / w.BASELINE).read_bytes(), baseline)

    def test_workflow_collect_artifact_report_snapshot_order_and_no_head_pipeline(self):
        text = (ROOT / ".github/workflows/community-watch.yml").read_text()
        self.assertLess(text.index("community_watch.py collect"), text.index("actions/upload-artifact"))
        self.assertLess(text.index("actions/upload-artifact"), text.index("community_watch.py report"))
        self.assertLess(text.index("community_watch.py report"), text.index("community_watch.py advance"))
        self.assertIn("cancel-in-progress: false", text)
        self.assertNotIn("head -", text)
        self.assertNotIn("|| true", text)
        # W15: any pinned sha; a hardcoded one failed every Dependabot bump (Validate #404, PR #185).
        self.assertEqual(len(re.findall(r"uses: actions/upload-artifact@[0-9a-f]{40} ", text)), 2)
        self.assertLess(text.index("community_watch.py advance"), text.index("community-watch-delivery-"))
        self.assertIn("if: ${{ always() }}", text)
        self.assertEqual(text.count("GH_TOKEN: ${{ github.token }}"), 2)

    def test_human_issue_collision_refuses_without_post(self):
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        self.issues[0]["user"] = dict(login="someone-else", type="User")
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "IDENTITY_DIFFERS"):
            w.report(self.root, self.out, self.ident, self.api)
        self.assertFalse(any(call[0] == "POST" for call in self.calls))

    def test_human_comment_collision_refuses_even_with_exact_text(self):
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        self.comments[0]["user"] = dict(login="someone-else", type="User")
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "PART_DIFFERS"):
            w.report(self.root, self.out, self.ident, self.api)
        self.assertFalse(any(call[0] == "POST" for call in self.calls))

    def test_changed_issue_title_refuses_instead_of_duplicate_post(self):
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        self.issues[0]["title"] = "Renamed by reviewer"
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "IDENTITY_DIFFERS"):
            w.report(self.root, self.out, self.ident, self.api)
        self.assertEqual(len(self.issues), 1)
        self.assertFalse(any(call[0] == "POST" for call in self.calls))

    def test_edited_remote_report_prevents_snapshot_write(self):
        self.git_setup()
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        baseline = (self.root / w.BASELINE).read_bytes()
        for row in (self.issues[0], self.comments[0]):
            old = row["body"]
            row["body"] = old + "\nEdited"
            with self.assertRaisesRegex(ValueError, "READBACK_FAILED"):
                w.advance(self.root, self.out, self.ident, reader=self.api)
            self.assertEqual((self.root / w.BASELINE).read_bytes(), baseline)
            self.assertEqual(self.git("rev-parse", "HEAD"), self.ident["head"])
            self.assertFalse((self.root / w.RECEIPT).exists())
            row["body"] = old

    def test_deleted_or_spoofed_part_prevents_snapshot_write(self):
        self.git_setup()
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        baseline = (self.root / w.BASELINE).read_bytes()
        original = copy.deepcopy(self.comments)
        cases = [[], [dict(original[0], user=dict(login="other", type="User"))],
                 original + [dict(original[0], id=999, body=original[0]["body"] + " fake")]]
        for comments in cases:
            self.comments = comments
            with self.assertRaisesRegex(ValueError, "READBACK_FAILED"):
                w.advance(self.root, self.out, self.ident, reader=self.api)
            self.assertEqual((self.root / w.BASELINE).read_bytes(), baseline)
            self.assertEqual(self.git("rev-parse", "HEAD"), self.ident["head"])

    def test_api_failure_before_advance_keeps_snapshot(self):
        self.git_setup()
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        baseline = (self.root / w.BASELINE).read_bytes()
        def failed(*args):
            raise ValueError("fixture API failure")
        with self.assertRaisesRegex(ValueError, "fixture API"):
            w.execute_phase("advance", self.root, self.out, self.ident, reader=failed)
        self.assertEqual((self.root / w.BASELINE).read_bytes(), baseline)
        status = json.loads((self.out / "advance-status.json").read_bytes())
        self.assertEqual(status["state"], "FAILED_EFFECTS_UNCONFIRMED")
        self.assertNotIn("result", status)

    def test_unchanged_snapshot_has_delivery_status_without_commit(self):
        self.new = copy.deepcopy(self.old)
        self.git_setup()
        self.collect()
        w.execute_phase("report", self.root, self.out, self.ident, reader=self.api)
        state = w.execute_phase("advance", self.root, self.out, self.ident, reader=self.api)
        self.assertEqual(state, "SNAPSHOT_UNCHANGED")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.ident["head"])
        self.assertFalse((self.root / w.RECEIPT).exists())
        for phase in ("report", "advance"):
            status = json.loads((self.out / (phase + "-status.json")).read_bytes())
            self.assertEqual(status["state"], "SUCCEEDED")
        self.assertTrue((self.out / "acknowledgement.json").is_file())

    def test_phase_failure_does_not_claim_no_remote_effects(self):
        self.collect()
        self.fail_comment = True
        with self.assertRaises(ValueError):
            w.execute_phase("report", self.root, self.out, self.ident, reader=self.api)
        self.assertEqual(len(self.issues), 1)
        status = json.loads((self.out / "report-status.json").read_bytes())
        self.assertEqual(status["state"], "FAILED_EFFECTS_UNCONFIRMED")
        self.assertEqual(status["error"], "ValueError")
        self.assertFalse((self.out / "acknowledgement.json").exists())

    def test_multipart_delivery_resumes_after_second_part_failure(self):
        app = self.news[0]["bundles"]["Display label only"]["apps"]["com.example.app"]
        app["patches"] = ["News patch " + str(n) + " " + "x"*90 for n in range(1200)]
        self.collect()
        data, parts = w.load_report(self.root, self.out, self.ident)
        self.assertGreaterEqual(len(parts), 3)
        def fail_second(method, path, payload=None):
            if method == "POST" and path.endswith("/comments") and len(self.comments) == 1:
                raise ValueError("second part failed")
            return self.api(method, path, payload)
        with self.assertRaisesRegex(ValueError, "second part failed"):
            w.execute_phase("report", self.root, self.out, self.ident, reader=fail_second)
        self.assertEqual(len(self.issues), 1)
        self.assertEqual(len(self.comments), 1)
        self.assertFalse((self.out / "acknowledgement.json").exists())
        w.execute_phase("report", self.root, self.out, self.ident, reader=self.api)
        self.assertEqual(len(self.issues), 1)
        self.assertEqual(len(self.comments), len(parts))
        for number, part in enumerate(parts, 1):
            self.assertEqual(self.comments[number-1]["body"], w.part_body(data["report_key"], number, len(parts), part))
        ack = json.loads((self.out / "acknowledgement.json").read_bytes())
        self.assertEqual(ack["parts"], len(parts))

    def test_readback_paginates_past_unrelated_comments(self):
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        data, parts = w.load_report(self.root, self.out, self.ident)
        comments = [dict(id=1000+n, body="Unrelated") for n in range(205)] + self.comments
        calls = []
        def paginated(method, path, payload=None):
            if "/comments?" in path:
                page = int(path.rsplit("page=", 1)[1])
                calls.append(page)
                return copy.deepcopy(comments[(page-1)*100:page*100])
            return self.api(method, path, payload)
        w.verify_delivery(data, parts, 1, paginated)
        self.assertEqual(calls, [1, 2, 3])
        comments[-1]["body"] += " modified"
        with self.assertRaisesRegex(ValueError, "PART_READBACK_FAILED"):
            w.verify_delivery(data, parts, 1, paginated)

    def test_acknowledgement_issue_binding_refuses_before_git(self):
        self.collect()
        w.report(self.root, self.out, self.ident, self.api)
        path = self.out / "acknowledgement.json"
        ack = json.loads(path.read_bytes())
        ack["issue_url"] = "https://github.com/other/repo/issues/1"
        path.write_bytes(w.encoded(ack))
        with patch.object(w, "git") as runner:
            with self.assertRaisesRegex(ValueError, "ISSUE_MISMATCH"):
                w.advance(self.root, self.out, self.ident, runner=runner, reader=self.api)
            runner.assert_not_called()

    def test_unrelated_same_name_variant_does_not_affect_configured_app(self):
        a, b = fixture(), fixture()
        b["compatibilities"].append([{"packageName":"other.app","targets":[{"version":"1"}]}])
        other = copy.deepcopy(b["bundles"][0]["patches"][0])
        other["compatiblePackagesKey"] = 1
        b["bundles"][0]["patches"].append(other)
        b["bundles"][0]["patchCount"] = 2
        report = m.compare(a,b,TARGETS)
        self.assertEqual(report["relevant_events"], 0)
        self.assertEqual(report["events"][0]["packages"], ["other.app"])



class DuplicateProvider(unittest.TestCase):
    """W16n, live 26 Oct 2026 run 40294788256: one repository listed twice stopped the watch."""

    def test_identical_twice_merges_to_the_same_provider(self):
        once, twice = fixture(), fixture()
        twice["bundles"].append(copy.deepcopy(twice["bundles"][0]))
        a, b = m.inventory(once), m.inventory(twice)
        self.assertEqual(a["providers"], b["providers"])
        self.assertEqual(b["coverage"]["patches"], 1)
        self.assertEqual(b["coverage"]["merged_providers"], [dict(provider="github:owner/patches", bundles=2)])
        self.assertEqual(m.compare(once, twice, TARGETS)["event_count"], 0)

    def test_two_bundles_one_repo_keep_every_patch_and_both_names(self):
        data = fixture()
        other = copy.deepcopy(data["bundles"][0])
        other.update(name="Test Extra", repo="Owner/Patches", targetApps=["com.example.other"],
                     patches=[dict(name="Two", description="x", default=False)], patchCount=1)
        data["bundles"].append(other)
        parsed = m.inventory(data)
        provider = parsed["providers"]["github:owner/patches"]
        self.assertEqual(sorted(provider["patches"]), ["One", "Two"])
        self.assertEqual(provider["metadata"]["name"], sorted(["Test", "Test Extra"], key=m.canonical))
        self.assertEqual(provider["metadata"]["targetApps"], ["com.example.app", "com.example.other"])
        self.assertEqual(parsed["coverage"]["providers"], 1)
        self.assertEqual(parsed["coverage"]["bundles"], 2)

    def test_merge_is_order_independent(self):
        data = fixture()
        other = copy.deepcopy(data["bundles"][0])
        other.update(name="B", patches=[dict(name="One", description="changed", default=True, compatiblePackagesKey=0)])
        data["bundles"].append(other)
        flipped = copy.deepcopy(data)
        flipped["bundles"].reverse()
        self.assertEqual(m.digest(m.inventory(data)["providers"]), m.digest(m.inventory(flipped)["providers"]))
        self.assertEqual(len(m.inventory(data)["providers"]["github:owner/patches"]["patches"]["One"]), 2)

    def test_merge_is_named_in_the_report(self):
        old, new = fixture(), fixture()
        new["bundles"].append(copy.deepcopy(new["bundles"][0]))
        text = m.render(m.compare(old, new, TARGETS))
        self.assertIn("Merged (listed more than once in the index, kept as one provider): github:owner/patches x2.", text)
        self.assertNotIn("Merged", m.render(m.compare(old, old, TARGETS)))

    def test_bad_bundle_in_a_merged_repo_still_refuses(self):
        data = fixture()
        bad = copy.deepcopy(data["bundles"][0])
        bad["patchCount"] = 7
        data["bundles"].append(bad)
        with self.assertRaises(ValueError):
            m.inventory(data)

if __name__ == "__main__":
    unittest.main(verbosity=2)


class Supersede(unittest.TestCase):
    """W15e (owner, 22 Oct 2026): one open community report; older ones close as superseded."""
    def test_older_open_reports_close_and_others_stay(self):
        bot = {"login": "github-actions[bot]", "type": "Bot"}
        rows = [{"id": 1, "number": 206, "title": w.TITLE, "user": bot}, {"id": 2, "number": 201, "title": w.TITLE, "user": bot},
                {"id": 3, "number": 197, "title": w.TITLE, "user": {"login": "someone", "type": "User"}},
                {"id": 4, "number": 154, "title": "Council desk", "user": bot}]
        calls = []
        def reader(method, path, payload=None):
            calls.append((method, path, payload))
            if method == "GET":
                return rows if path.endswith("page=1") else []
            return {}
        closed = w.supersede("repos/" + w.REPO + "/issues", 206, reader)
        self.assertEqual(closed, 1)
        self.assertIn(("PATCH", "repos/" + w.REPO + "/issues/201", {"state": "closed", "state_reason": "completed"}), calls)
        self.assertFalse(any(p.endswith("/206") or p.endswith("/197") or p.endswith("/154") for m, p, _ in calls if m == "PATCH"))

    def test_a_stop_names_its_own_code_and_issue_pages_run_oldest_first(self):
        # W16 (24 Oct 2026): "stopped: ValueError" alone hid the reason of run 40009076501.
        root = Path(__file__).resolve().parents[1]
        r = subprocess.run([sys.executable, str(root / "src/etc/community_watch.py"), "bogus"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("Community Watch stopped: ValueError INVALID_COMMAND.", r.stderr)
        self.assertIn('"?state=all&sort=created&direction=asc"', (root / "src/etc/community_watch.py").read_text())

    def test_supersede_failure_is_counted_and_warned(self):
        failures = []
        def reader(method, path, payload=None):
            raise ValueError("synthetic")
        with self.assertLogs() if False else __import__('contextlib').redirect_stdout(__import__('io').StringIO()) as out:
            self.assertEqual(w.supersede("repos/" + w.REPO + "/issues", 206, reader, failures), 0)
        self.assertEqual(failures, [w.SUPERSEDE_FAILURE_CODE])
        self.assertIn("SUPERSEDE_FAILURE", out.getvalue())

    def test_api_guard_allows_only_the_close_patch(self):
        with self.assertRaises(ValueError):
            w.api("PATCH", "repos/" + w.REPO + "/issues/5", {"title": "x"})
        with self.assertRaises(ValueError):
            w.api("DELETE", "repos/" + w.REPO + "/issues/5")
