import contextlib
import copy
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_identity as fixtures
import shadow_inputs as shadow
import build_identity

ROOT = fixtures.ROOT

class FakeAPI:
    repo = "fixture/repo"
    def __init__(self, release=None, commit=None, apk=None):
        self.releases = [] if release is None else [release]
        self.commit = commit
        self.rows = [] if apk is None else [apk]
        self.documents = {}
        self.calls = []
        self.fail = None
        self.run_status = "completed"
        self.run_conclusion = "success"
        self.publish_step = "success"
    def get(self, path, limit=None):
        self.calls.append(path)
        if self.fail and self.fail in path:
            raise OSError("fixture API unavailable")
        if "/actions/runs/" in path and "/jobs?" in path:
            return {"total_count":1,"jobs":[{"id":88,"run_id":12345,"run_attempt":2,
                    "head_sha":self.commit,"name":"build (keymapper) / Patch keymapper",
                    "status":"completed","conclusion":"success","steps":[
                        {"name":name,"status":"completed","conclusion":self.publish_step if name=="Releasing APK files" else "success"}
                        for name in ["Verify finished APK identity","Verify release handoff (no publishing)","Releasing APK files"]]}]}
        if "/actions/runs/" in path:
            return {"id":12345,"run_attempt":2,"head_sha":self.commit,"head_branch":"main",
                    "repository":{"full_name":self.repo},"status":self.run_status,"conclusion":self.run_conclusion}
        if "/git/ref/tags/" in path:
            return {"object": {"type": "commit", "sha": self.commit}}
        if "/releases/tags/" in path:
            if not self.releases: raise OSError("not published")
            return self.releases[0]
        if "/assets?" in path:
            page = int(path.rsplit("page=",1)[1])
            return copy.deepcopy(self.rows[(page-1)*100:page*100])
        if "/releases?" in path:
            page = int(path.rsplit("page=",1)[1])
            return copy.deepcopy(self.releases[(page-1)*100:page*100])
        raise AssertionError(path)
    def asset(self, asset):
        return copy.deepcopy(self.documents[asset["name"]])
    def upload(self, path, tag):
        blob=Path(path).read_bytes()
        name=Path(path).name
        self.rows.append({"id":999,"name":name,"size":len(blob),"state":"uploaded",
                          "digest":"sha256:"+hashlib.sha256(blob).hexdigest()})
        self.documents[name]=json.loads(blob)

class ShadowContracts(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Identity()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.r = self.f.r
        self.env = dict(self.f.env, GITHUB_REPOSITORY="fixture/repo", GITHUB_RUN_ID="12345",
                        GITHUB_RUN_ATTEMPT="2", GITHUB_REF="refs/heads/main")
        self.env.pop("COE", None)
        self.f.env.pop("COE", None)
        self.env.pop("PF_SHADOW_PLAN_KEY", None)

    def declare(self, ident="keymapper"):
        return shadow.declaration(self.r, ident)

    def target_change(self, ident, key, value):
        p=self.r/"src/targets.json";ts=json.loads(p.read_text())
        next(t for t in ts if t["id"]==ident)[key]=value
        p.write_text(json.dumps(ts))

    def capture(self):
        self.captured=self.f.capture_fixture()
        return self.captured

    def verified(self):
        self.capture()
        report=self.f.verify_fixture()
        suffix=build_identity.create(self.env,datetime.datetime(2026,9,18,tzinfo=datetime.timezone.utc))
        for key,value in {".tagprefix":"key-mapper",".tagsuffix":suffix,
                          ".provider":"lain",".patchver":"1.0"}.items():
            self.f.put("release/"+key,value+"\n")
        tag="key-mapper-v4.2.1"+suffix
        release={"id":123,"tag_name":tag,"draft":False,"prerelease":False,"published_at":"2026-09-18T08:00:00Z"}
        output=report["output"]
        apk={"id":321,"name":Path(output["path"]).name,"state":"uploaded","size":output["bytes"],
             "digest":"sha256:"+output["sha256"]}
        return FakeAPI(release,self.captured["source_commit"],apk)

    def publish(self, api):
        with patch.dict(os.environ,self.env,clear=True):
            return shadow.publish_receipt(self.r,"keymapper",self.env,api,api.upload)

    def test_all_fourteen_declarations_valid(self):
        ts=json.loads((self.r/"src/targets.json").read_text())
        keys=[shadow.declaration(self.r,t["id"])["sha256"] for t in ts if t["enabled"]]
        self.assertEqual(len(keys),14)
        self.assertEqual(len(set(keys)),14)

    def test_note_formatting_unrelated_doc_do_not_change_declaration(self):
        before=self.declare()
        self.target_change("keymapper","note","changed notes")
        self.f.put("README.md","not relevant")
        self.assertEqual(self.declare(),before)
        p=self.r/"src/targets.json"
        p.write_text(json.dumps(json.loads(p.read_text()),separators=(",",":")))
        self.assertEqual(self.declare(),before)

    def test_channel_pin_ceiling_changes_and_revert(self):
        p=self.r/"src/targets.json";old=p.read_bytes();before=self.declare()
        for k,v in [("pin","lain"),("max_app_version","4.2.0"),("min_sdk_ceiling",28),("source","apkmirror")]:
            p.write_bytes(old);self.target_change("keymapper",k,v)
            if k=="source":
                # Absent mapping is a refusal, never evidence of equivalence.
                try:after=self.declare()
                except (ValueError,KeyError):continue
            else:after=self.declare()
            self.assertNotEqual(before["sha256"],after["sha256"])
        p.write_bytes(old);self.assertEqual(self.declare(),before)

    def test_selected_resource_and_modes_affect_declaration(self):
        before=self.declare("reddit")
        p=self.r/"src/options/hosts.txt";old=p.read_bytes();mode=p.stat().st_mode
        p.write_bytes(old+b"\nexample.invalid\n")
        self.assertNotEqual(self.declare("reddit")["sha256"],before["sha256"])
        p.write_bytes(old);self.assertEqual(self.declare("reddit"),before)
        p.chmod(mode^0o100)
        self.assertNotEqual(self.declare("reddit")["sha256"],before["sha256"])

    def test_plan_keys_do_not_emit_build_matrix_or_false_unchanged(self):
        out=self.r/"out";out.write_text("matrix=preserved\n")
        env=dict(self.env,GITHUB_OUTPUT=str(out))
        keys=shadow.plan(self.r,env)
        self.assertEqual(len(keys),14)
        text=out.read_text()
        self.assertTrue(text.startswith("matrix=preserved\nkeys="))
        report=json.loads((self.r/"shadow-evidence/plan.json").read_text())
        self.assertTrue(all(t["state"]=="RESOLVE" for t in report["targets"]))
        self.assertNotIn("UNCHANGED",json.dumps(report))

    def test_plan_disabled_skipped_and_duplicates_refused(self):
        self.target_change("keymapper","enabled",False)
        out=self.r/"out";out.touch()
        keys=shadow.plan(self.r,dict(self.env,GITHUB_OUTPUT=str(out)))
        self.assertNotIn("keymapper",keys)
        p=self.r/"src/targets.json";ts=json.loads(p.read_text());ts.append(ts[0]);p.write_text(json.dumps(ts))
        old=out.read_bytes()
        with self.assertRaises(ValueError):shadow.plan(self.r,dict(self.env,GITHUB_OUTPUT=str(out)))
        self.assertEqual(out.read_bytes(),old)

    def test_consumed_key_bound_to_planned_declaration(self):
        planned=self.declare()["sha256"];c=self.capture()
        doc=shadow.realized(self.r,c,dict(self.env,PF_SHADOW_PLAN_KEY=planned))
        self.assertEqual(doc["binding"],"MATCH")
        shadow.verify_consumed(self.r,c,doc,dict(self.env,PF_SHADOW_PLAN_KEY=planned))
        self.assertNotIn("fixture password",json.dumps(doc))

    def test_empty_explicit_request_ledger_is_valid_for_default_selections(self):
        c=self.capture()
        c["requested_ledger"]["bytes"]=0
        c["requested_ledger"]["sha256"]=hashlib.sha256(b"").hexdigest()
        self.assertEqual(shadow.realized(self.r,c,self.env)["material"]["requested"]["bytes"],0)

    def test_plan_drift_is_blocked_not_unchanged(self):
        c=self.capture();doc=shadow.realized(self.r,c,dict(self.env,PF_SHADOW_PLAN_KEY="a"*64))
        self.assertEqual(shadow.compare(doc,None,"missing")["state"],"BLOCKED")

    def test_missing_plan_is_explicit_not_match(self):
        doc=shadow.realized(self.r,self.capture(),self.env)
        self.assertEqual(doc["binding"],"NO_PLAN")
        self.assertEqual(shadow.compare(doc,None,"NO_PUBLISHED_BASELINE")["state"],"UNKNOWN")

    def test_required_daily_plan_missing_is_unknown_and_cannot_publish_receipt(self):
        api=self.verified();self.env["PF_SHADOW_PLAN_REQUIRED"]="true"
        result=shadow.observe(self.r,"keymapper",self.env,api)
        self.assertEqual(result["decision"]["reason"],"REQUIRED_PLAN_UNAVAILABLE")
        self.assertEqual(result["consumed"]["binding"],"MISSING_REQUIRED_PLAN")
        with self.assertRaisesRegex(ValueError,"cannot advance"):self.publish(api)
        self.assertEqual(len(api.rows),1)

    def test_changed_consumed_bytes_same_name_changes_key(self):
        c=self.capture();first=shadow.realized(self.r,c,self.env)
        for kind in ["tools","bundles"]:
            changed=copy.deepcopy(c);changed[kind][0]["sha256"]="f"*64
            self.assertNotEqual(shadow.realized(self.r,changed,self.env)["effective_sha256"],first["effective_sha256"])
        changed=copy.deepcopy(c);changed["patcher_input_apk"]["sha256"]="e"*64
        self.assertNotEqual(shadow.realized(self.r,changed,self.env)["effective_sha256"],first["effective_sha256"])

    def test_missing_duplicate_wrong_bundle_identity_refused(self):
        c=self.capture()
        for change in [lambda d:d["bundles"].clear(),lambda d:d["bundles"].append(d["bundles"][0]),
                       lambda d:d["bundles"][0].update(path="foreign.mpp")]:
            v=copy.deepcopy(c);change(v)
            with self.assertRaises(ValueError):shadow.realized(self.r,v,self.env)

    def test_observe_refuses_changed_actual_bytes(self):
        self.capture();self.f.put("morphe-desktop-fixture.jar","mutated")
        with self.assertRaisesRegex(ValueError,"input changed"):
            shadow.observe(self.r,"keymapper",self.env,FakeAPI())
        self.assertFalse((self.r/"shadow-evidence/keymapper.json").exists())

    def test_baseline_absent_and_api_failure_stay_unknown(self):
        self.capture()
        for api in [FakeAPI(),FakeAPI()]:
            if api is not None:api.fail="/releases?"
            doc=shadow.observe(self.r,"keymapper",self.env,api)
            self.assertEqual(doc["decision"]["state"],"UNKNOWN")
        doc=shadow.observe(self.r,"keymapper",self.env,FakeAPI())
        self.assertEqual(doc["decision"]["reason"],"NO_PUBLISHED_BASELINE")

    def test_plan_drift_not_hidden_by_baseline_failure(self):
        self.capture();api=FakeAPI();api.fail="/releases?"
        result=shadow.observe(self.r,"keymapper",dict(self.env,PF_SHADOW_PLAN_KEY="a"*64),api)
        self.assertEqual(result["decision"]["state"],"BLOCKED")

    def test_full_capture_verify_publish_readback_and_compare(self):
        api=self.verified()
        self.env["PF_SHADOW_PLAN_KEY"]=self.declare()["sha256"]
        result=shadow.observe(self.r,"keymapper",self.env,api)
        self.assertEqual(result["decision"]["state"],"UNKNOWN")
        receipt=self.publish(api)
        self.assertEqual(receipt["publication"],"confirmed")
        baseline,reason=shadow.latest_baseline(api,"keymapper","key-mapper")
        self.assertEqual(reason,"VERIFIED")
        self.assertEqual(shadow.compare(result["consumed"],baseline,reason)["state"],"UNCHANGED")
        c=copy.deepcopy(self.captured);c["tools"][0]["sha256"]="f"*64
        changed=shadow.realized(self.r,c,self.env)
        self.assertEqual(shadow.compare(changed,baseline,reason)["state"],"BUILD")
        # Receipt contains no local filenames, raw argv, full environment or keys.
        text=json.dumps(receipt)
        for secret in ["fixture password","src/ks.keystore","KEYSTORE_PASS"]:
            self.assertNotIn(secret,text)

    def test_receipt_is_idempotent_not_overwrite(self):
        api=self.verified();first=self.publish(api);n=len(api.rows)
        self.assertEqual(self.publish(api),first);self.assertEqual(len(api.rows),n)
        api.documents[shadow.receipt_name("keymapper")]["effective_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"never overwrite"):self.publish(api)

    def test_no_receipt_for_nonmain_or_missing_publication(self):
        api=self.verified();self.env["GITHUB_REF"]="refs/heads/test"
        with self.assertRaises(ValueError):self.publish(api)
        self.env["GITHUB_REF"]="refs/heads/main";api.releases=[]
        with self.assertRaises(OSError):self.publish(api)
        self.assertEqual(len(api.rows),1)

    def test_no_receipt_for_wrong_attempt_wrong_commit_draft_or_wrong_apk(self):
        for kind in ["attempt","commit","draft","digest","size"]:
            # One fixture reset per scenario, preserve exact report origin.
            with self.subTest(kind=kind):
                api=self.verified() if not hasattr(self,"captured") else self._api_for_existing()
                saved=dict(self.env)
                if kind=="attempt":self.env["GITHUB_RUN_ATTEMPT"]="3"
                elif kind=="commit":api.commit="a"*40
                elif kind=="draft":api.releases[0]["draft"]=True
                elif kind=="digest":api.rows[0]["digest"]="sha256:"+"a"*64
                else:api.rows[0]["size"]+=1
                with self.assertRaises((ValueError,KeyError)):self.publish(api)
                self.assertEqual(len(api.rows),1);self.env=saved

    def _api_for_existing(self):
        report=json.loads((self.r/"build-evidence/keymapper.json").read_text())
        tag="key-mapper-v4.2.1"+(self.r/"release/.tagsuffix").read_text().strip()
        return FakeAPI({"id":123,"tag_name":tag,"draft":False,"prerelease":False,"published_at":"2026-09-18T08:00:00Z"},
                       self.captured["source_commit"],{"id":321,"name":Path(report["output"]["path"]).name,
                       "state":"uploaded","size":report["output"]["bytes"],"digest":"sha256:"+report["output"]["sha256"]})

    def test_failed_upload_and_missing_readback_never_claim_durable(self):
        api=self.verified()
        with patch.dict(os.environ,self.env,clear=True):
            with self.assertRaises(ValueError):
                shadow.publish_receipt(self.r,"keymapper",self.env,api,lambda p,t:None)
        self.assertEqual(len(api.rows),1)

    def test_newest_release_missing_receipt_does_not_reuse_old(self):
        api=self.verified();self.publish(api)
        api.releases.append({"id":9999,"tag_name":"key-mapper-v4.2.2-b20260919",
                             "draft":False,"prerelease":False,"published_at":"2026-09-19T08:00:00Z"})
        real=api.get
        def get(path,limit=None):
            if "/releases/9999/assets?" in path:return []
            return real(path,limit)
        api.get=get
        baseline,reason=shadow.latest_baseline(api,"keymapper","key-mapper")
        self.assertIsNone(baseline);self.assertEqual(reason,"LATEST_RELEASE_HAS_NO_RECEIPT")

    def test_tampered_receipt_and_wrong_target_refused(self):
        api=self.verified();self.publish(api)
        name=shadow.receipt_name("keymapper");original=copy.deepcopy(api.documents[name])
        api.documents[name]["effective_sha256"]="a"*64
        with self.assertRaises(ValueError):shadow.latest_baseline(api,"keymapper","key-mapper")
        body={k:v for k,v in original.items() if k!="sha256"};body["target"]="reddit"
        api.documents[name]=shadow.seal(body)
        with self.assertRaises(ValueError):shadow.latest_baseline(api,"keymapper","key-mapper")

    def test_failed_partial_skipped_or_pending_run_never_becomes_baseline(self):
        api=self.verified();self.publish(api)
        for conclusion in ["failure","cancelled","skipped","timed_out"]:
            api.run_conclusion=conclusion
            with self.assertRaises(ValueError):shadow.latest_baseline(api,"keymapper","key-mapper")
        api.run_conclusion="success";api.run_status="in_progress"
        with self.assertRaises(ValueError):shadow.latest_baseline(api,"keymapper","key-mapper")
        api.run_status="completed";api.publish_step="skipped"
        with self.assertRaises(ValueError):shadow.latest_baseline(api,"keymapper","key-mapper")

    def test_duplicate_release_and_page_coverage_fail_closed(self):
        api=self.verified();api.releases*=2
        with self.assertRaises(ValueError):shadow.latest_baseline(api,"keymapper","key-mapper")

    def test_no_plan_matrix_or_publish_policy_takeover_in_wiring(self):
        ci=(ROOT/".github/workflows/ci.yml").read_text()
        manual=(ROOT/".github/workflows/manual-patch.yml").read_text()
        release=(ROOT/".github/actions/release/action.yml").read_text()
        self.assertIn("matrix: ${{ steps.plan.outputs.matrix }}",ci)
        self.assertIn("shadow_keys: ${{ steps.shadow.outputs.keys }}",ci)
        self.assertIn("continue-on-error: true",ci)
        self.assertIn("name: Preserve shadow Plan evidence\n        if: always()\n        continue-on-error: true",ci)
        self.assertIn("name: Preserve shadow consumed-input comparison\n        if: always()\n        continue-on-error: true",manual)
        self.assertIn("PF_SHADOW_PLAN_KEY: ${{ inputs.shadow_plan_key || '' }}",manual)
        self.assertIn("inputs.publish && github.ref == 'refs/heads/main'",manual)
        self.assertLess(release.index("- name: Release\n"),release.index("Record confirmed-publication input receipt"))
        self.assertIn("if: steps.shadow_receipt.outcome == 'failure'",release)
        self.assertNotIn("timeout-minutes:",release)
        self.assertIn('timeout 180s python3 src/build/shadow_inputs.py receipt "$TARGET"',release)
        self.assertIn("allowUpdates: false",release)
        self.assertNotIn("--clobber",(ROOT/"src/build/shadow_inputs.py").read_text())

    def test_semantic_alternative_change_does_not_change_selected_recipe(self):
        p=self.r/"src/targets.json";ts=json.loads(p.read_text());t=next(t for t in ts if t["id"]=="adguard")
        winner=t["candidates"][0]["name"]
        before=shadow.semantics(self.r,"adguard",winner);declared=shadow.declaration(self.r,"adguard")
        t["candidates"][1]["channel"]="latest" if t["candidates"][1]["channel"]!="latest" else "prerelease"
        p.write_text(json.dumps(ts))
        self.assertNotEqual(shadow.declaration(self.r,"adguard"),declared)
        self.assertEqual(shadow.semantics(self.r,"adguard",winner),before)

    def test_no_receipt_from_consumed_input_drift(self):
        api=self.verified();self.f.put("09-lain.mpp","changed")
        with self.assertRaisesRegex(ValueError,"input changed"):self.publish(api)
        self.assertEqual(len(api.rows),1)

    def test_write_refuses_symlink_and_schema_corruption(self):
        (self.r/"shadow-evidence").mkdir()
        victim=self.r/"untouched";victim.write_text("safe")
        (self.r/"shadow-evidence/x.json").symlink_to(victim)
        with self.assertRaises(ValueError):shadow.write(self.r,"shadow-evidence/x.json",{})
        self.assertEqual(victim.read_text(),"safe")
        with self.assertRaises(ValueError):shadow.unseal({"domain":"wrong","schema":1},shadow.DOMAIN)

    def test_actual_http_reader_scopes_auth_and_bounds_response(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return b'{"ok":true}'
        class Opener:
            def __init__(self):self.requests=[]
            def open(self,req,timeout):
                self.requests.append(req)
                return Response()
        opener=Opener();api=shadow.API("fixture/repo",{"GH_TOKEN":"not-printed"})
        with patch.object(shadow.urllib.request,"build_opener",return_value=opener):
            self.assertEqual(api.get("/repos/fixture/repo/releases"),{"ok":True})
            self.assertEqual(opener.requests[0].get_header("Authorization"),"Bearer not-printed")
            with self.assertRaises(ValueError):api.get("/repos/elsewhere/repo/releases")
            with self.assertRaises(ValueError):api.get("/repos/fixture/repo/releases",limit=2)
        # JSON duplicate keys are not accepted.
        with patch.object(Response,"read",return_value=b'{"x":1,"x":2}'), \
             patch.object(shadow.urllib.request,"build_opener",return_value=opener):
            with self.assertRaises(ValueError):api.get("/repos/fixture/repo/releases")

    def test_asset_reader_uses_no_credentials_and_validates_bytes(self):
        blob=b'{"hello":"world"}'
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return blob
        class Opener:
            def open(self,req,timeout):
                self.request=req
                return Response()
        opener=Opener();api=shadow.API("fixture/repo",{"GH_TOKEN":"not-for-download"})
        asset={"browser_download_url":"https://github.com/fixture/repo/releases/download/t/receipt.json",
               "size":len(blob),"digest":"sha256:"+hashlib.sha256(blob).hexdigest()}
        with patch.object(shadow.urllib.request,"build_opener",return_value=opener):
            self.assertEqual(api.asset(asset),{"hello":"world"})
            self.assertIsNone(opener.request.get_header("Authorization"))
            for mutation in [{"size":len(blob)+1},{"digest":"sha256:"+"a"*64},
                             {"browser_download_url":"https://evil.invalid/receipt.json"}]:
                with self.assertRaises(ValueError):api.asset(dict(asset,**mutation))

    def test_schema_or_option_failure_cannot_emit_shadow_plan_keys(self):
        out=self.r/"out";out.write_text("keep=yes\n")
        self.target_change("keymapper","poll","false")
        with self.assertRaises(ValueError):shadow.plan(self.r,dict(self.env,GITHUB_OUTPUT=str(out)))
        self.assertEqual(out.read_text(),"keep=yes\n")

    def test_failed_actual_cli_preserves_unknown_evidence_not_false_success(self):
        result=subprocess.run(
            [sys.executable,str(ROOT/"src/build/shadow_inputs.py"),"observe","keymapper"],
            cwd=self.r,env=self.env,capture_output=True,text=True,timeout=20)
        self.assertNotEqual(result.returncode,0)
        record=json.loads((self.r/"shadow-evidence/keymapper-observe-unknown.json").read_text())
        self.assertEqual(record["state"],"UNKNOWN")
        self.assertNotIn("fixture password",json.dumps(record))
