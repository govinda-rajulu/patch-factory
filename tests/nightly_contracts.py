import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nightly_report', ROOT/'src/etc/nightly_report.py')
n = importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
ENV = {'GITHUB_REPOSITORY':'govinda-rajulu/patch-factory','GITHUB_SHA':'a'*40,
       'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','WATCH_SETUP':'success'}
TARGETS = [{'id':'fixture','enabled':True,'candidates':[],'extra_bundles':[]}]

class Nightly(unittest.TestCase):
    def test_report_failure_remains_failed(self):
        for rc in (0,1):
            _,d=n.analyze('missing patch\nreport mode=full fail=1\n',rc,True,TARGETS,ENV)
            self.assertEqual(d['status'],'FAILED')

    def test_nonzero_exit_overrides_claimed_zero(self):
        _,d=n.analyze('report mode=full fail=0\n',2,True,TARGETS,ENV)
        self.assertEqual(d['status'],'FAILED')

    def test_missing_empty_duplicate_result_never_healthy(self):
        for text in ('','hello','report mode=full fail=0\n'*2):
            _,d=n.analyze(text,0,True,TARGETS,ENV)
            self.assertEqual(d['status'],'UNKNOWN')

    def test_setup_failure_not_run_as_success(self):
        _,d=n.analyze('not executed',None,False,TARGETS,ENV)
        self.assertEqual(d['status'],'UNKNOWN')
        self.assertFalse(d['setup_ok'])

    def test_unreadable_reader_is_unknown(self):
        for message in ('?? fixture unreadable','provider UNVERIFIED','skipping','release read returned nothing'):
            _,d=n.analyze(message+'\nreport mode=full fail=0\n',0,True,TARGETS,ENV)
            self.assertEqual(d['status'],'UNKNOWN')

    def test_zero_exit_labels_remaining_coverage_gaps(self):
        targets=[dict(TARGETS[0],extra_bundles=[{'host':'gitlab'}])]
        _,d=n.analyze('report mode=full fail=0\n',0,True,targets,ENV)
        self.assertEqual(d['status'],'PARTIAL')
        self.assertEqual(d['coverage'],'partial')
        self.assertTrue(any('GitLab' in x for x in d['coverage_gaps']))

    def test_invalid_run_identity_does_not_create_a_run_link(self):
        for change in ({'GITHUB_SHA':''},{'GITHUB_REPOSITORY':'wrong/repo'},{'GITHUB_RUN_ID':'bad'}):
            _,d=n.analyze('report mode=full fail=0\n',0,True,TARGETS,dict(ENV,**change))
            self.assertEqual(d['status'],'UNKNOWN');self.assertIsNone(d['run_url'])

    def test_redacts_credentials_and_url_queries(self):
        text='github_pat_'+'X'*30+' https://user:pass@example.invalid/a?key=private KNOWN_SECRET_123'
        safe=n.redact(text,{'GH_TOKEN':'KNOWN_SECRET_123'})
        for value in ('X'*30,'user:pass','key=private','KNOWN_SECRET_123'):
            self.assertNotIn(value,safe)
        self.assertIn('example.invalid/a',safe)

    def test_capture_preserves_first_and_last_lines_and_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'src').mkdir();(root/'src/targets.json').write_text(json.dumps(TARGETS))
            text='FIRST\n'+'detail\n'*150+'LAST\nreport mode=full fail=1\n'
            result=subprocess.CompletedProcess([],1,text.encode(),b'')
            with patch.object(n.subprocess,'run',return_value=result):
                d=n.collect(root,ENV)
            self.assertEqual((root/'watch-evidence/nightly-report.txt').read_text(),text)
            self.assertEqual(d['report_bytes'],len(text.encode()))
            self.assertEqual(n.enforce(root),1)

    def test_capture_setup_failure_never_launches_legacy_report(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(n.subprocess,'run') as proc:
                d=n.collect(Path(td),dict(ENV,WATCH_SETUP='failure'))
                proc.assert_not_called()
            self.assertEqual(d['status'],'UNKNOWN')

    def test_collector_timeout_is_failed_and_evidence_exists(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(n.subprocess,'run',side_effect=subprocess.TimeoutExpired('fixture',900)):
                d=n.collect(Path(td),ENV)
            self.assertEqual(d['status'],'FAILED')
            self.assertTrue((Path(td)/'watch-evidence/nightly-report.json').is_file())

    def test_enforcement_detects_tampered_report(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            n.collect(root,dict(ENV,WATCH_SETUP='failure'))
            (root/'watch-evidence/nightly-report.txt').write_text('different')
            with self.assertRaises(ValueError):n.enforce(root)

    def test_workflow_preserves_evidence_before_enforcing_failure(self):
        text=(ROOT/'.github/workflows/watch.yml').read_text()
        self.assertNotIn('|| true',text)
        self.assertIn('python3 src/build/github_patcher.py .',text)
        self.assertLess(text.index('nightly_report.py collect'),text.index('uses: actions/upload-artifact@v4'))
        self.assertLess(text.index('uses: actions/upload-artifact@v4'),text.index('nightly_report.py enforce'))
        self.assertIn('if-no-files-found: error',text)
        self.assertIn('retention-days: 30',text)
        self.assertNotIn('secrets: inherit',text)

    def test_numbered_workflow_names_are_unique(self):
        numbers = []
        for path in (ROOT/'.github/workflows').glob('*.yml'):
            match = n.re.match(r'^name: ([0-9]+)\. ', path.read_text())
            if match:
                numbers.append(int(match[1]))
        self.assertEqual(sorted(numbers), list(range(1,10)))
        self.assertTrue((ROOT/'.github/workflows/batch-patch.yml').read_text().startswith('name: 9. Batch Patch\n'))
        self.assertTrue((ROOT/'.github/workflows/agent-watch.yml').read_text().startswith('name: 6. Provider watch\n'))

    def issue(self,text,mode='create',prior=''):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'bin').mkdir();report=root/'report.txt';report.write_text(text)
            gh=root/'bin/gh'
            gh.write_text('#!/usr/bin/env python3\nimport json,os,sys\na=sys.argv[1:]\n'
                'with open(os.environ["CALLS"],"a") as f:f.write(json.dumps(a)+"\\n")\n'
                'if a[0:2]==["issue","list"]:\n'
                ' if os.environ["MODE"]=="inventory_fail":sys.exit(1)\n'
                ' print("27" if os.environ["MODE"]=="existing" else "")\n'
                'elif a[0:2]==["issue","view"]:print(os.environ["PRIOR"])\n'
                'elif os.environ["MODE"]=="write_fail":sys.exit(1)\n')
            gh.chmod(0o755)
            env=dict(os.environ,**ENV,PATH=str(root/'bin')+':'+os.environ['PATH'],WATCH_REPORT=str(report),
                     CALLS=str(root/'calls.jsonl'),MODE=mode,PRIOR=prior)
            r=subprocess.run(['bash',str(ROOT/'src/etc/watch_issue.sh')],env=env,capture_output=True,text=True)
            calls=[json.loads(line) for line in (root/'calls.jsonl').read_text().splitlines()] if (root/'calls.jsonl').exists() else []
            return r,calls

    def test_issue_keeps_first_missing_lines_beyond_old_tail(self):
        r,calls=self.issue('FIRST MISSING\n'+'x\n'*150+'report mode=full fail=1\n')
        self.assertEqual(r.returncode,0,r.stderr)
        body=next(x[x.index('--body')+1] for x in calls if x[:2]==['issue','create'])
        self.assertIn('FIRST MISSING',body)
        self.assertIn('30 days',body)

    def test_issue_full_hash_detects_untagged_changes(self):
        a,ac=self.issue('unselected old\nreport mode=full fail=0\n')
        b,bc=self.issue('unselected new\nreport mode=full fail=0\n')
        def fingerprint(c):return next(x[x.index('--body')+1].splitlines()[0] for x in c if x[:2]==['issue','create'])
        self.assertNotEqual(fingerprint(ac),fingerprint(bc))

    def test_issue_unchanged_full_hash_no_write(self):
        text='report mode=full fail=0\n'
        r,calls=self.issue(text,'existing','fingerprint: '+n.hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue(all(c[:2] in (['issue','list'],['issue','view']) for c in calls))

    def test_issue_empty_inventory_and_write_failures_not_success(self):
        for text,mode in (('','create'),('hello','inventory_fail'),('hello','write_fail')):
            r,_=self.issue(text,mode);self.assertNotEqual(r.returncode,0)

    def test_issue_oversize_links_artifact_without_silent_tail(self):
        r,calls=self.issue('X'*46000)
        self.assertEqual(r.returncode,0,r.stderr)
        body=next(x[x.index('--body')+1] for x in calls if x[:2]==['issue','create'])
        self.assertIn('exceeds the issue preview limit',body);self.assertLess(len(body),1000)
