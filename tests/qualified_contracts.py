import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import qualified_baselines as qualified
import shadow_inputs as shadow
from shadow_contracts import ShadowContracts


class QualifiedContracts(unittest.TestCase):
    def setUp(self):
        self.f = ShadowContracts()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.r, self.env = self.f.r, self.f.env
        self.api = self.f.verified()
        self.receipt = self.f.publish(self.api)
        self.release = self.api.releases[0]
        self.real_get = self.api.get
        self.real_upload = self.api.upload
        self.uploads = 0
        self.source = {
            "id": 12345, "run_attempt": 2, "head_sha": self.api.commit,
            "head_branch": "main", "repository": {"full_name": self.api.repo},
            "head_repository": {"full_name": self.api.repo}, "status": "completed",
            "conclusion": "success", "event": "schedule", "path": ".github/workflows/ci.yml"
        }

    def uploader(self, path, tag):
        self.uploads += 1
        self.real_upload(path, tag)
        self.api.rows[-1]["id"] = 999 + self.uploads
        self.api.rows[-1]["uploader"] = {"login": "github-actions[bot]", "type": "Bot"}

    def qualify(self):
        return qualified.qualify(self.api, self.release, "keymapper",
                                 ".github/workflows/ci.yml", self.r, self.uploader)

    def asset(self):
        return next(a for a in self.api.rows if a["name"] == qualified.name("keymapper"))

    def event(self, source=None):
        p = self.r / "event.json"
        p.write_text(json.dumps({"action": "completed", "workflow_run": source or self.source}))
        return dict(self.env, GITHUB_EVENT_NAME="workflow_run", GITHUB_EVENT_PATH=str(p))

    def event_api(self, path, limit=None):
        if "/actions/runs/" in path and "/jobs?" not in path:
            self.api.calls.append(path)
            return copy.deepcopy(self.source)
        return self.real_get(path, limit)

    def test_live_qualification_then_deleted_run_still_verifies_from_retained_proof(self):
        doc = self.qualify()
        self.assertEqual(self.uploads, 1)
        self.assertEqual(doc["proof"]["coverage"], "complete")
        self.api.fail = "/actions/runs/"
        self.api.calls.clear()
        baseline, reason = shadow.latest_baseline(self.api, "keymapper", "key-mapper")
        self.assertEqual(baseline["effective_sha256"], self.receipt["effective_sha256"])
        self.assertEqual(reason, "VERIFIED_DURABLE_ACTIONS_RECORD")
        self.assertFalse(any("/actions/runs/" in p for p in self.api.calls))
        self.assertNotIn("fixture password", json.dumps(doc))

    def test_pending_failed_cancelled_or_partial_source_never_qualifies(self):
        for status, conclusion in (("in_progress", None), ("completed", "failure"),
                                   ("completed", "cancelled"), ("completed", "skipped")):
            self.api.run_status, self.api.run_conclusion = status, conclusion
            with self.subTest(status=status, conclusion=conclusion), self.assertRaises(ValueError):
                self.qualify()
        self.assertEqual(self.uploads, 0)
        self.assertFalse((self.r / "shadow-qualified").exists())

    def test_failed_publication_step_never_qualifies(self):
        self.api.publish_step = "failure"
        with self.assertRaises(ValueError):
            self.qualify()
        self.assertEqual(self.uploads, 0)

    def test_same_existing_record_is_idempotent_not_overwritten(self):
        first = self.qualify()
        self.assertEqual(self.qualify(), first)
        self.assertEqual(self.uploads, 1)

    def test_different_existing_qualification_refuses_without_overwrite(self):
        self.qualify()
        self.api.documents[self.asset()["name"]]["proof"]["jobs_checked"] = 999
        with self.assertRaises(ValueError):
            self.qualify()
        self.assertEqual(self.uploads, 1)

    def test_qualified_reader_requires_actions_bot_upload(self):
        self.qualify()
        for uploader in (None, {"login": "human", "type": "User"},
                         {"login": "github-actions[bot]", "type": "User"}):
            self.asset()["uploader"] = uploader or {}
            with self.subTest(uploader=uploader), self.assertRaises(ValueError):
                qualified.verify(self.api, self.release, self.asset(), "keymapper")

    def test_resealed_wrong_job_run_target_coverage_or_steps_refuse(self):
        original = self.qualify()
        name = self.asset()["name"]
        mutations = (
            lambda d: d["proof"]["run"].update(conclusion="failure"),
            lambda d: d["proof"]["run"].update(run_attempt=3),
            lambda d: d["proof"]["job"].update(name="Patch reddit"),
            lambda d: d["proof"]["job"].update(head_sha="f" * 40),
            lambda d: d["proof"].update(coverage="partial"),
            lambda d: d["proof"].update(jobs_checked=0),
            lambda d: d["proof"].update(steps=[]),
            lambda d: d.update(workflow_path=".github/workflows/untrusted.yml"),
            lambda d: d.update(repository="other/repo"),
            lambda d: d.update(trust="independent attestation"),
        )
        for mutation in mutations:
            doc = copy.deepcopy(original);mutation(doc)
            doc = shadow.seal({k: v for k, v in doc.items() if k != "sha256"})
            self.api.documents[name] = doc
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                qualified.verify(self.api, self.release, self.asset(), "keymapper")

    def test_changed_apk_tag_original_receipt_or_asset_identity_still_refuses(self):
        self.qualify()
        old_commit = self.api.commit
        self.api.commit = "e" * 40
        with self.assertRaises(ValueError):
            qualified.verify(self.api, self.release, self.asset(), "keymapper")
        self.api.commit = old_commit
        for row in self.api.rows:
            if row["name"] == qualified.name("keymapper"):
                continue
            old = row["digest"];row["digest"] = "sha256:" + "f" * 64
            with self.subTest(asset=row["name"]), self.assertRaises(ValueError):
                qualified.verify(self.api, self.release, self.asset(), "keymapper")
            row["digest"] = old

    def test_newer_legacy_release_never_falls_back_to_old_qualified_record(self):
        self.qualify()
        newer = dict(self.release, id=222, tag_name="key-mapper-v4.2.2-b2026091900000000000000012345000002",
                     published_at="2026-09-19T20:00:00Z")
        self.api.releases.append(newer)
        def get(path, limit=None):
            if "/releases/222/assets?" in path:
                return []
            return self.real_get(path, limit)
        self.api.get = get
        baseline, reason = shadow.latest_baseline(self.api, "keymapper", "key-mapper")
        self.assertIsNone(baseline)
        self.assertEqual(reason, "LATEST_RELEASE_HAS_NO_RECEIPT")

    def test_invalid_qualification_does_not_silently_fall_back_to_live_receipt(self):
        self.qualify();self.asset()["uploader"]["login"] = "untrusted"
        with self.assertRaises(ValueError):
            shadow.latest_baseline(self.api, "keymapper", "key-mapper")

    def test_upload_readback_failure_preserves_partial_outcome(self):
        def lost(path, tag):
            self.uploader(path, tag)
            self.api.documents[Path(path).name] = {}
        with self.assertRaises(ValueError):
            qualified.qualify(self.api, self.release, "keymapper", ".github/workflows/ci.yml",
                              self.r, lost)
        self.assertEqual(self.uploads, 1)
        self.assertTrue((self.r / "shadow-qualified" / qualified.name("keymapper")).exists())

    def test_finalize_checks_exact_event_against_api_and_qualifies_only_its_attempt(self):
        self.api.get = self.event_api
        rows = qualified.finalize(self.r, self.event(), self.api, self.uploader)
        self.assertEqual(rows, [{"target": "keymapper", "state": "QUALIFIED"}])
        self.assertEqual(self.uploads, 1)
        summary = json.loads((self.r / "shadow-qualified/result.json").read_text())
        self.assertEqual(summary["source_attempt"], 2)
        self.assertEqual(summary["authority"], "shadow-only")

    def test_fork_pr_wrong_branch_workflow_event_or_identity_refuse_before_upload(self):
        self.api.get = self.event_api
        changes = (
            {"head_branch": "repair/test"}, {"conclusion": "failure"},
            {"head_repository": {"full_name": "fork/repo"}},
            {"repository": {"full_name": "fork/repo"}}, {"event": "pull_request"},
            {"path": ".github/workflows/not-authorized.yml"}, {"run_attempt": 3},
            {"id": True}, {"head_sha": "a" * 40},
        )
        for change in changes:
            source = dict(self.source, **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                qualified.finalize(self.r, self.event(source), self.api, self.uploader)
        self.assertEqual(self.uploads, 0)

    def test_manual_smoke_without_publication_does_not_invent_a_baseline(self):
        self.api.get = self.event_api
        self.api.releases = []
        self.assertEqual(qualified.finalize(self.r, self.event(), self.api, self.uploader), [])
        self.assertEqual(self.uploads, 0)

    def test_missing_receipt_reports_unknown_without_apk_or_tag_changes(self):
        self.api.get = self.event_api
        self.api.rows = [a for a in self.api.rows if not a["name"].startswith("pf-publication")]
        old = copy.deepcopy(self.api.rows)
        with self.assertRaises(ValueError):
            qualified.finalize(self.r, self.event(), self.api, self.uploader)
        self.assertEqual(self.api.rows, old)
        report = json.loads((self.r / "shadow-qualified/result.json").read_text())
        self.assertEqual(report["targets"], [{"target": "keymapper", "state": "UNKNOWN"}])

    def test_trusted_workflow_does_not_checkout_source_head_or_download_run_artifacts(self):
        text = (self.r / ".github/workflows/qualify-baselines.yml").read_text()
        self.assertIn("workflow_run:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertIn("ref: main", text)
        self.assertNotIn("ref: ${{", text)
        self.assertNotIn("download-artifact", text)
        self.assertNotIn("secrets.", text)
        self.assertIn("actions: read", text)
        self.assertIn("contents: write", text)
        self.assertNotIn('"--clobber"', (self.r / "src/build/qualified_baselines.py").read_text())

    def test_later_page_publication_job_is_checked_not_first_page_only(self):
        target = self.real_get("/actions/runs/12345/attempts/2/jobs?per_page=100&page=1")["jobs"][0]
        jobs = [dict(target, id=1000 + i, name="Other job " + str(i), steps=[]) for i in range(100)]
        jobs.append(target)
        def get(path, limit=None):
            if "/jobs?" in path:
                page = int(path.rsplit("page=", 1)[1])
                return {"total_count": 101, "jobs": jobs[(page-1)*100:page*100]}
            return self.real_get(path, limit)
        self.api.get = get
        self.assertEqual(self.qualify()["proof"]["jobs_checked"], 101)
        self.assertEqual(self.uploads, 1)

    def test_duplicate_or_incomplete_job_inventory_refuses_before_upload(self):
        target = self.real_get("/actions/runs/12345/attempts/2/jobs?per_page=100&page=1")["jobs"][0]
        for rows, count in (([target, target], 2), ([target], 2), ([], 0)):
            def get(path, limit=None):
                if "/jobs?" in path:
                    return {"total_count": count, "jobs": rows}
                return self.real_get(path, limit)
            self.api.get = get
            with self.subTest(count=count, rows=len(rows)), self.assertRaises(ValueError):
                self.qualify()
        self.assertEqual(self.uploads, 0)

    def test_finalizer_release_pagination_and_duplicate_refusal(self):
        self.api.get = self.event_api
        unrelated = [dict(self.release, id=2000+i, tag_name="unrelated-"+str(i)) for i in range(100)]
        self.api.releases = unrelated + [self.release]
        self.assertEqual(qualified.finalize(self.r, self.event(), self.api, self.uploader),
                         [{"target": "keymapper", "state": "QUALIFIED"}])
        self.assertTrue(any("releases?per_page=100&page=2" in p for p in self.api.calls))
        self.api.releases.append(self.release)
        with self.assertRaises(ValueError):
            qualified.finalize(self.r, self.event(), self.api, self.uploader)
        self.assertEqual(self.uploads, 1)

    def test_actual_upload_argv_has_no_overwrite_dispatch_or_token(self):
        from types import SimpleNamespace
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(argv[:3], ["gh", "release", "upload"])
            self.assertEqual(argv[-2:], ["--repo", self.api.repo])
            self.assertEqual(len(argv), 7)
            self.uploader(argv[4], argv[3])
            return SimpleNamespace(returncode=0)
        with patch.object(qualified.subprocess, "run", side_effect=run):
            qualified.qualify(self.api, self.release, "keymapper", ".github/workflows/ci.yml", self.r)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.uploads, 1)


if __name__ == "__main__":
    unittest.main()
