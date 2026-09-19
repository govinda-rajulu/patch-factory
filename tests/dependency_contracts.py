import contextlib
import copy
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import dependency_observation as dep
import resolved_inputs as resolved
import shadow_inputs as shadow
import qualified_baselines as qualified
from resolved_contracts import ResolvedContracts
from shadow_contracts import ShadowContracts
import test_identity as fixtures


class DependencyContracts(unittest.TestCase):
    def setUp(self):
        self.f = ResolvedContracts()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.r, self.env = self.f.r, self.f.env

    def current(self, ident="keymapper"):
        self.f.prepare(ident)
        return dep.snapshot(self.r, ident, self.env)

    def reseal(self, doc):
        if doc.get("domain") == dep.DOMAIN:
            doc["subset_sha256"] = shadow.sha(doc["material"])
        return shadow.seal({k:v for k,v in doc.items() if k != "sha256"})

    def baseline(self, snapshot, **changes):
        return dict(target=snapshot["target"], repository=snapshot["run"]["GITHUB_REPOSITORY"],
                    source_commit=snapshot["run"]["GITHUB_SHA"], run_id=snapshot["run"]["GITHUB_RUN_ID"],
                    attempt=snapshot["run"]["GITHUB_RUN_ATTEMPT"],
                    tag="key-mapper-v4.2.1-b2026091900000000000000012345000002",
                    prepared_dependencies=snapshot, **changes)

    def observed(self, current=None, baseline=None, reason="VERIFIED_DURABLE_ACTIONS_RECORD"):
        if current is None:
            current = self.current()
        baseline = baseline if baseline is not None else self.baseline(current)
        with patch.object(shadow, "latest_baseline", return_value=(baseline, reason)):
            return dep.observe(self.r, current["target"], self.env, object())

    def artifact(self, doc):
        ident = doc["target"]
        folder = ("resolved-observation-" + ident + "-" + self.env["GITHUB_RUN_ID"] +
                  "-" + self.env["GITHUB_RUN_ATTEMPT"])
        path = self.r / "dependency-observations" / folder / (ident + "-comparison.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc))
        return path

    def test_prepare_compare_and_subset_never_authorizes_skip(self):
        current = self.current()
        doc = self.observed(current)
        self.assertEqual(doc["decision"]["state"], "MATCHED_SUBSET")
        self.assertEqual(doc["authority"], dep.AUTHORITY)
        self.assertEqual(doc["limits"], dep.LIMITS)
        self.assertNotIn("UNCHANGED", json.dumps(doc))
        self.assertNotIn("KEYSTORE_PASS", json.dumps(doc))
        self.assertEqual(dep.observation(doc, "keymapper", resolved.identity(self.r,self.env))["decision"],
                         doc["decision"])

    def test_same_label_version_different_bytes_detected(self):
        current = self.current()
        for field in ("patcher", "bundles"):
            old = copy.deepcopy(current)
            row = old["material"][field] if field == "patcher" else old["material"][field][0]
            row["sha256"] = "f"*64
            old = self.reseal(old)
            result = dep.compare(current, old)
            self.assertEqual(result["state"], "CHANGED_SUBSET")
            self.assertEqual(result["changed_components"], [field])
        old = copy.deepcopy(current);old["material"]["version"] = "4.2.0"
        self.assertEqual(dep.compare(current, self.reseal(old))["changed_components"], ["version"])

    def test_run_attempt_source_and_lock_envelope_do_not_change_subset_key(self):
        current = self.current()
        older = copy.deepcopy(current)
        older["run"].update(GITHUB_RUN_ID="22",GITHUB_RUN_ATTEMPT="3",GITHUB_SHA="a"*40)
        older["lock_sha256"] = "b"*64
        older["dependency_sha256"] = "c"*64
        older = self.reseal(older)
        self.assertEqual(dep.compare(current,older)["state"],"MATCHED_SUBSET")
        older["run"]["GITHUB_REPOSITORY"] = "another/repo"
        with self.assertRaises(ValueError):
            dep.compare(current,self.reseal(older))

    def test_patcher_filename_only_not_semantic_bytes(self):
        first = self.current()
        lock = self.f.lock();old=lock["material"]["patcher"]["path"]
        new="morphe-desktop-renamed-all.jar"
        (self.r/"resolved-inputs"/old).rename(self.r/"resolved-inputs"/new)
        lock["material"]["patcher"]["path"]=new
        self.f.rewrite(lock,reseal=True)
        second=dep.snapshot(self.r,"keymapper",self.env)
        self.assertNotEqual(first["lock_sha256"],second["lock_sha256"])
        self.assertEqual(dep.compare(first,second)["state"],"MATCHED_SUBSET")

    def test_note_json_format_and_revert_do_not_invalidate_current_subset(self):
        first=self.current()
        p=self.r/"src/targets.json";old=p.read_bytes()
        rows=json.loads(old);next(t for t in rows if t["id"]=="keymapper")["note"]="New explanation"
        p.write_text(json.dumps(rows,separators=(",",":")))
        self.assertEqual(dep.snapshot(self.r,"keymapper",self.env),first)
        p.write_bytes(old)
        self.assertEqual(dep.snapshot(self.r,"keymapper",self.env),first)

    def test_semantic_change_refuses_old_lock_until_reprepared(self):
        first=self.current()
        p=self.r/"src/targets.json";rows=json.loads(p.read_text())
        next(t for t in rows if t["id"]=="keymapper")["min_sdk_ceiling"]=28
        p.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):dep.snapshot(self.r,"keymapper",self.env)
        shutil.rmtree(self.r/"resolved-inputs")
        self.f.prepare()
        new=dep.snapshot(self.r,"keymapper",self.env)
        result=dep.compare(new,first)
        self.assertEqual(result["state"],"CHANGED_SUBSET")
        self.assertIn("local_effective_sha256",result["changed_components"])

    def test_failed_lock_never_reads_baseline_and_reports_unknown(self):
        self.current()
        (self.r/"resolved-inputs/09-lain.mpp").write_bytes(b"changed")
        with patch.object(shadow,"latest_baseline",side_effect=AssertionError("must not read")):
            doc=dep.observe(self.r,"keymapper",self.env,object())
        self.assertEqual(doc["decision"]["state"],"UNKNOWN")
        self.assertIsNone(doc["current"])

    def test_new_alternative_candidate_changes_declaration_not_unchanged_winner_bytes(self):
        first=self.current()
        p=self.r/"src/targets.json";rows=json.loads(p.read_text())
        t=next(t for t in rows if t["id"]=="keymapper")
        extra=copy.deepcopy(t["candidates"][0]);extra["name"]="alternative"
        t["candidates"].append(extra);p.write_text(json.dumps(rows))
        shutil.rmtree(self.r/"resolved-inputs")
        self.f.prepare()
        second=dep.snapshot(self.r,"keymapper",self.env)
        self.assertNotEqual(first["dependency_sha256"],second["dependency_sha256"])
        self.assertEqual(dep.compare(first,second)["state"],"MATCHED_SUBSET")

    def test_consumed_lock_mismatch_cannot_be_attached_to_publication(self):
        current=self.current()
        lock=self.f.lock()["material"]
        captured={"target":"keymapper","winner":lock["winner"],
                  "tools":[lock["patcher"]],"bundles":lock["bundles"]}
        captured["resolution"]=resolved.verify_consumed(self.r,"keymapper",captured,self.env)
        self.assertEqual(dep.snapshot(self.r,"keymapper",self.env,captured),current)
        captured["bundles"]=copy.deepcopy(captured["bundles"])
        captured["bundles"][0]["sha256"]="f"*64
        with self.assertRaises(ValueError):dep.snapshot(self.r,"keymapper",self.env,captured)

    def test_unpublished_receipt_never_becomes_comparison_baseline(self):
        sf,api,receipt,proof=self.live_chain_fixture()
        api.releases[0]["draft"]=True
        doc=dep.observe(sf.r,"keymapper",sf.env,api)
        self.assertEqual(doc["decision"]["state"],"UNKNOWN")
        self.assertEqual(doc["decision"]["reason"],"NO_PUBLISHED_BASELINE")

    def test_resealed_wrong_receipt_subset_identity_refused_by_both_readers(self):
        sf,api,receipt,proof=self.live_chain_fixture()
        bad=copy.deepcopy(receipt)
        subset=bad["prepared_dependencies"];subset["run"]["GITHUB_RUN_ATTEMPT"]="3"
        bad["prepared_dependencies"]=self.reseal(subset)
        bad=self.reseal(bad)
        with self.assertRaises(ValueError):
            shadow.verify_receipt(api,api.releases[0],bad,"keymapper")
        qualified_asset=next(a for a in api.rows if a["name"]==qualified.name("keymapper"))
        altered=copy.deepcopy(proof);altered["receipt"]=bad
        api.documents[qualified_asset["name"]]=self.reseal(altered)
        with self.assertRaises(ValueError):
            qualified.verify(api,api.releases[0],qualified_asset,"keymapper")

    def test_receipt_publication_missing_resolution_does_not_grow_new_baseline(self):
        sf=ShadowContracts();sf.setUp();self.addCleanup(sf.doCleanups)
        api=sf.verified();before=len(api.rows)
        sf.env["PF_RESOLVED_REQUESTED"]="true"
        with self.assertRaises(ValueError):sf.publish(api)
        self.assertEqual(len(api.rows),before)

    def test_all_comparison_states_are_accounted_without_effective_build_matrix(self):
        doc=self.observed();doc["decision"].update(state="CHANGED_SUBSET",changed_components=["patcher"])
        doc=self.reseal(doc);self.artifact(doc)
        report=dep.aggregate(self.r,self.env)
        self.assertEqual(report["counts"]["CHANGED_SUBSET"],1)
        self.assertEqual(report["counts"]["UNKNOWN"],13)
        self.assertNotIn("matrix",report)

    def test_duplicate_json_unknown_and_stale_local_semantics_unknown(self):
        doc=self.observed();p=self.artifact(doc)
        text=p.read_text();p.write_text(text[:-1]+',"schema":1}')
        self.assertEqual(dep.aggregate(self.r,self.env)["validated_observations"],0)
        p.write_text(json.dumps(doc))
        path=self.r/"src/targets.json";rows=json.loads(path.read_text())
        next(t for t in rows if t["id"]=="keymapper")["min_sdk_ceiling"]=28
        path.write_text(json.dumps(rows))
        self.assertEqual(dep.aggregate(self.r,self.env)["validated_observations"],0)

    def test_absent_lock_reports_unknown_and_does_not_fetch(self):
        with patch.object(shadow,"latest_baseline",side_effect=AssertionError("must not read")), \
             patch.object(resolved.github_patcher,"fetch",side_effect=AssertionError("must not fetch")):
            doc=dep.observe(self.r,"keymapper",self.env,object())
        self.assertEqual(doc["decision"]["reason"],"PREPARED_DEPENDENCIES_UNAVAILABLE_OR_INVALID")
        self.assertTrue((self.r/"resolved-observation/keymapper-comparison.json").exists())

    def test_legacy_receipt_has_explicit_migration_unknown(self):
        current=self.current();baseline=self.baseline(current);baseline.pop("prepared_dependencies")
        doc=self.observed(current,baseline)
        self.assertEqual(doc["decision"]["state"],"UNKNOWN")
        self.assertEqual(doc["decision"]["reason"],"LATEST_PUBLICATION_HAS_NO_PREPARED_SUBSET")

    def test_no_baseline_and_reader_failures_never_become_match(self):
        self.current()
        with patch.object(shadow,"latest_baseline",return_value=(None,"LATEST_RELEASE_HAS_NO_RECEIPT")):
            doc=dep.observe(self.r,"keymapper",self.env,object())
        self.assertEqual(doc["decision"]["reason"],"LATEST_RELEASE_HAS_NO_RECEIPT")
        with patch.object(shadow,"latest_baseline",side_effect=OSError("private detail")):
            doc=dep.observe(self.r,"keymapper",self.env,object())
        self.assertEqual(doc["decision"]["reason"],"BASELINE_UNAVAILABLE_OR_INVALID")
        self.assertNotIn("private detail",json.dumps(doc))

    def test_resealed_scope_digest_bool_size_and_order_corruption_refuse(self):
        current=self.current("truecaller-combo")
        mutations=[
            lambda d:d.update(run=[]),
            lambda d:d.update(authority="skip builds"),
            lambda d:d.update(limits=[]),
            lambda d:d["material"]["patcher"].update(bytes=True),
            lambda d:d["material"]["bundles"].reverse(),
            lambda d:d["material"]["bundles"].append(copy.deepcopy(d["material"]["bundles"][0])),
            lambda d:d["material"]["bundles"][0].update(role="winner"),
            lambda d:d["material"]["patcher"].update(sha256="bad"),
            lambda d:d.update(extra="untrusted"),
        ]
        for change in mutations:
            bad=copy.deepcopy(current);change(bad)
            with self.subTest(change=change),self.assertRaises(ValueError):
                dep.validate_snapshot(self.reseal(bad))
        bad=copy.deepcopy(current);bad["sha256"]="0"*64
        with self.assertRaises(ValueError):dep.validate_snapshot(bad)

    def test_receipt_snapshot_rejects_other_run_source_repo_and_target(self):
        current=self.current()
        for key,value in (("target","youtube"),("run_id","77"),("attempt","3"),
                          ("source_commit","a"*40),("repository","other/repo")):
            receipt=self.baseline(current);receipt[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                dep.receipt_snapshot(receipt)
        receipt=self.baseline(current);receipt.pop("prepared_dependencies")
        self.assertIsNone(dep.receipt_snapshot(receipt))

    def test_all_fourteen_have_observations_even_when_legacy_matrix_empty(self):
        out=self.r/"output";out.write_text('matrix={"target":[]}\n')
        shadow.plan(self.r,dict(self.env,GITHUB_OUTPUT=str(out)))
        expected=dep.expected_targets(self.r);self.assertEqual(len(expected),14)
        for ident in expected:
            self.f.prepare(ident)
            with patch.object(shadow,"latest_baseline",return_value=(None,"NO_PUBLISHED_BASELINE")):
                doc=dep.observe(self.r,ident,self.env,object())
            self.artifact(doc)
            shutil.rmtree(self.r/"resolved-inputs")
        report=dep.aggregate(self.r,self.env)
        self.assertEqual(report["coverage"],"complete")
        self.assertEqual(report["validated_observations"],14)
        self.assertEqual(report["counts"],{"MATCHED_SUBSET":0,"CHANGED_SUBSET":0,"UNKNOWN":14})
        self.assertTrue(out.read_text().startswith('matrix={"target":[]}\n'))

    def test_missing_all_observations_is_fourteen_unknown_not_healthy_zero(self):
        report=dep.aggregate(self.r,self.env)
        self.assertEqual(report["coverage"],"incomplete")
        self.assertEqual(report["validated_observations"],0)
        self.assertEqual(report["counts"]["UNKNOWN"],14)
        self.assertEqual(len(report["targets"]),14)

    def test_one_match_thirteen_missing_summary_keeps_coverage_separate(self):
        doc=self.observed();self.artifact(doc)
        p=self.r/"step-summary";p.write_text("Previous summary\n")
        report=dep.aggregate(self.r,dict(self.env,GITHUB_STEP_SUMMARY=str(p)))
        self.assertEqual(report["coverage"],"incomplete")
        self.assertEqual(report["counts"]["MATCHED_SUBSET"],1)
        self.assertEqual(report["counts"]["UNKNOWN"],13)
        self.assertTrue(p.read_text().startswith("Previous summary"))
        self.assertIn("UNKNOWN is not unchanged",p.read_text())

    def test_wrong_attempt_source_target_or_hash_observation_is_unknown(self):
        doc=self.observed();path=self.artifact(doc)
        for change in (lambda d:d["run"].update(GITHUB_RUN_ATTEMPT="3"),
                       lambda d:d["run"].update(GITHUB_SHA="f"*40),
                       lambda d:d.update(target="youtube"),
                       lambda d:d["decision"].update(state="UNCHANGED")):
            bad=copy.deepcopy(doc);change(bad);path.write_text(json.dumps(self.reseal(bad)))
            report=dep.aggregate(self.r,self.env)
            self.assertEqual(report["validated_observations"],0)
            self.assertEqual(report["counts"]["UNKNOWN"],14)
        bad=copy.deepcopy(doc);bad["sha256"]="0"*64;path.write_text(json.dumps(bad))
        self.assertEqual(dep.aggregate(self.r,self.env)["validated_observations"],0)

    def test_unexpected_artifact_or_symlink_invalidates_inventory(self):
        self.artifact(self.observed())
        p=self.r/"dependency-observations/unexpected";p.mkdir()
        report=dep.aggregate(self.r,self.env)
        self.assertEqual(report["counts"]["MATCHED_SUBSET"],0)
        self.assertIn("UNEXPECTED_OR_UNSAFE_ARTIFACT",report["inventory_issues"])
        p.rmdir();p.symlink_to(self.r,target_is_directory=True)
        self.assertEqual(dep.aggregate(self.r,self.env)["counts"]["UNKNOWN"],14)

    def test_extra_file_in_expected_artifact_cannot_hide_duplicate_evidence(self):
        p=self.artifact(self.observed());(p.parent/"duplicate-comparison.json").write_bytes(p.read_bytes())
        report=dep.aggregate(self.r,self.env)
        self.assertEqual(report["validated_observations"],0)

    def test_disabled_poll_false_and_duplicate_target_inventory(self):
        p=self.r/"src/targets.json";rows=json.loads(p.read_text())
        rows[0]["enabled"]=False;rows[1]["poll"]=False;p.write_text(json.dumps(rows))
        self.assertEqual(len(dep.expected_targets(self.r)),12)
        rows.append(rows[2]);p.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):dep.aggregate(self.r,self.env)
        self.assertFalse((self.r/"dependency-report/report.json").exists())

    def test_actual_cli_missing_lock_and_aggregate_are_nonpublishing(self):
        env=dict(self.env,PYTHONDONTWRITEBYTECODE="1")
        for args in (["observe","keymapper"],["aggregate"]):
            result=subprocess.run([sys.executable,"src/build/dependency_observation.py",*args],
                                  cwd=self.r,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn("DO_NOT_INHERIT",result.stdout+result.stderr)
        self.assertEqual(json.loads((self.r/"dependency-report/report.json").read_text())["counts"]["UNKNOWN"],14)

    def test_workflow_preserves_matrix_and_read_only_report_scope(self):
        text=(self.r/".github/workflows/ci.yml").read_text()
        report=text.split("\n  dependency_report:\n",1)[1].split("\n  build:\n",1)[0]
        self.assertIn("contents: read\n      actions: read",report)
        self.assertNotIn("secrets",report)
        self.assertNotIn("resolved-inputs-",report)
        self.assertIn("merge-multiple: false",report)
        self.assertIn("digest-mismatch: error",report)
        self.assertIn("resolved-observation-*-${{ github.run_id }}-${{ github.run_attempt }}",report)
        build=text.split("\n  build:\n",1)[1]
        self.assertIn("needs: [plan, resolve]",build)
        self.assertIn("needs.plan.outputs.count != '0'",build)
        self.assertIn("matrix: ${{ fromJson(needs.plan.outputs.matrix) }}",build)
        self.assertNotIn("dependency_report",build)
        self.assertIn("continue-on-error: true",report)

    def live_chain_fixture(self):
        """Actual capture -> identity -> receipt -> qualification, with fake APK tools/API."""
        sf=ShadowContracts();sf.setUp();self.addCleanup(sf.doCleanups)
        api=sf.verified()
        (sf.r/"morphe-desktop-fixture.jar").rename(sf.r/"morphe-desktop-fixture-all.jar")
        env=dict(sf.env,GITHUB_SHA=api.commit,PF_RESOLVED_REQUESTED="true",PF_RESOLVED_READY="true")
        def patcher(directory,clean):
            name="morphe-desktop-fixture-all.jar";(directory/name).write_bytes(b"fixture")
            return dict(resolved.regular(directory,name),name=name)
        def resolver(args,**kwargs):
            p=Path(kwargs["env"]["PF_RESOLVE_DIR"])/"upstream/bundle-1.0.mpp";p.parent.mkdir(parents=True);p.write_bytes(b"fixture")
            return subprocess.CompletedProcess(args,0,"WINNER=lain\nVERSION=4.2.1\nMPP="+str(p)+"\nMPP_SHA256="+hashlib.sha256(b"fixture").hexdigest()+"\nBUNDLE_TAG=v1.0\n","")
        resolved.prepare(sf.r,"keymapper",env,patcher,resolver)
        with contextlib.redirect_stdout(io.StringIO()):
            fixtures.identity.capture_inputs(sf.r,"keymapper","lain",env)
        sf.f.env.update(env);sf.env=env;sf.captured=json.loads((sf.r/".build-inputs.json").read_text())
        sf.f.verify_fixture()
        receipt=sf.publish(api)
        def upload(path,tag):
            api.upload(path,tag);api.rows[-1]["id"]=1001
            api.rows[-1]["uploader"]={"login":"github-actions[bot]","type":"Bot"}
        proof=qualified.qualify(api,api.releases[0],"keymapper",".github/workflows/ci.yml",sf.r,upload)
        return sf,api,receipt,proof

    def test_actual_capture_publication_qualification_observation_chain(self):
        sf,api,receipt,proof=self.live_chain_fixture()
        self.assertIn("prepared_dependencies",receipt)
        self.assertEqual(receipt["prepared_dependencies"]["run"]["GITHUB_SHA"],api.commit)
        self.assertEqual(proof["receipt"]["prepared_dependencies"],receipt["prepared_dependencies"])
        api.fail="/actions/runs/"
        api.calls.clear()
        doc=dep.observe(sf.r,"keymapper",sf.env,api)
        self.assertEqual(doc["decision"]["state"],"MATCHED_SUBSET")
        self.assertEqual(doc["baseline_trust"],"VERIFIED_DURABLE_ACTIONS_RECORD")
        self.assertFalse(any("/actions/runs/" in p for p in api.calls))
        self.assertEqual(len(api.rows),3)

    def test_newer_legacy_release_blocks_older_prepared_subset(self):
        sf,api,receipt,proof=self.live_chain_fixture()
        api.releases.append(dict(api.releases[0],id=124,tag_name="key-mapper-v4.2.1-b20260919",published_at="2026-09-19T08:00:00Z"))
        old=api.get
        def get(path,limit=None):
            return [] if "/releases/124/assets?" in path else old(path,limit)
        api.get=get
        doc=dep.observe(sf.r,"keymapper",sf.env,api)
        self.assertEqual(doc["decision"]["state"],"UNKNOWN")
        self.assertEqual(doc["decision"]["reason"],"LATEST_RELEASE_HAS_NO_RECEIPT")

    def test_changed_published_apk_or_receipt_breaks_comparison(self):
        sf,api,receipt,proof=self.live_chain_fixture()
        api.rows[0]["digest"]="sha256:"+"f"*64
        doc=dep.observe(sf.r,"keymapper",sf.env,api)
        self.assertEqual(doc["decision"]["state"],"UNKNOWN")
        self.assertEqual(doc["decision"]["reason"],"BASELINE_UNAVAILABLE_OR_INVALID")

    def test_live_failed_pending_cancelled_source_never_qualifies_subset(self):
        sf,api,receipt,proof=self.live_chain_fixture()
        api.rows=[r for r in api.rows if not r["name"].startswith("pf-qualified-")]
        for status,conclusion in (("in_progress",None),("completed","failure"),("completed","cancelled")):
            api.run_status,api.run_conclusion=status,conclusion
            doc=dep.observe(sf.r,"keymapper",sf.env,api)
            self.assertEqual(doc["decision"]["state"],"UNKNOWN")
        self.assertEqual(len(api.rows),2)
