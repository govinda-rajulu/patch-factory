import copy
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_identity as fixtures
from test_identity import ROOT, identity, input_recipe, release_contract

class InputRecipeTests(unittest.TestCase):
    """Actual source layouts, semantic controls and no-write failure tests."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pf-recipe-')
        self.addCleanup(self.tmp.cleanup)
        self.r = pathlib.Path(self.tmp.name)
        for directory in ('src', 'docs', '.github'):
            shutil.copytree(ROOT / directory, self.r / directory)

    def recipe(self, ident='reddit', winner='adobo'):
        return input_recipe.create(self.r, ident, winner)

    def edit_json(self, relative, change):
        p = self.r / relative
        d = json.loads(p.read_text());change(d);p.write_text(json.dumps(d))

    def change_target(self, ident, key, value):
        self.edit_json('src/targets.json', lambda ts: next(t for t in ts if t['id']==ident).update({key:value}))

    def test_every_current_candidate_closure(self):
        ts=json.loads((self.r/'src/targets.json').read_text())
        counts=[]
        for t in ts:
            if not t.get('enabled'): continue
            for c in t['candidates']:
                with self.subTest(target=t['id'],winner=c['name']):
                    d=self.recipe(t['id'],c['name'])
                    input_recipe.verify(self.r,t['id'],c['name'],d)
                    self.assertGreater(len(d['components']),len(input_recipe.SHARED))
                    counts.append(t['id'])
        self.assertEqual(len(set(counts)),14)
        self.assertEqual(len(counts),15)

    def test_real_hosts_option_is_discovered(self):
        self.assertEqual(self.recipe()['resource_paths'],['src/options/hosts.txt'])

    def test_configured_extra_is_not_claimed_consumed(self):
        d=self.recipe('truecaller-combo','bufferk')
        row=next(x for x in d['bundle_roles'] if x['name']=='binarymend')
        self.assertEqual(row['options_state'],'configured-not-passed-by-current-argv')

    def test_primary_and_extra_changes_are_both_detected(self):
        for path, ident, winner in (
            ('src/options/adobo.json','reddit','adobo'),
            ('src/options/binarymend.json','truecaller-combo','bufferk'),
            ('src/patches/reddit-adobo/include-patches','reddit','adobo'),
            ('src/patches/reddit-adobo/exclude-patches','reddit','adobo'),
            ('src/patches/truecaller-paresh/include-patches','truecaller-combo','bufferk')):
            with self.subTest(path=path):
                p=self.r/path;old=p.read_bytes();a=self.recipe(ident,winner)
                try:
                    if path.endswith('.json'):p.write_text('[{"fixture":true}]')
                    else:p.write_bytes(old+b'\nFixture unique addition\n')
                    self.assertNotEqual(a['sha256'],self.recipe(ident,winner)['sha256'])
                finally:p.write_bytes(old)

    def test_target_settings_not_just_selection_paths(self):
        fields={'pin':'adobo','max_app_version':'1.0','min_sdk_ceiling':30,
                'exclusive':False,'any_version':True,'poll':False,'new_behavior':True}
        p=self.r/'src/targets.json';old=p.read_bytes()
        for key,value in fields.items():
            with self.subTest(key=key):
                a=self.recipe();self.change_target('reddit',key,value)
                self.assertNotEqual(a['sha256'],self.recipe()['sha256'])
                p.write_bytes(old)

    def test_candidate_and_extra_channel_changes(self):
        p=self.r/'src/targets.json';old=p.read_bytes()
        for role in ('candidates','extra_bundles'):
            with self.subTest(role=role):
                a=self.recipe('truecaller-combo','bufferk')
                def change(ts):
                    t=next(t for t in ts if t['id']=='truecaller-combo')
                    t[role][0]['channel']='latest'
                self.edit_json('src/targets.json',change)
                self.assertNotEqual(a['sha256'],self.recipe('truecaller-combo','bufferk')['sha256'])
                p.write_bytes(old)

    def test_shared_recipe_changes_each_consumer(self):
        path=self.r/'src/build/utils.sh';old=path.read_bytes()
        a=self.recipe();b=self.recipe('keymapper','lain')
        path.write_bytes(old+b'\n# changed recipe\n')
        self.assertNotEqual(a['sha256'],self.recipe()['sha256'])
        self.assertNotEqual(b['sha256'],self.recipe('keymapper','lain')['sha256'])

    def test_hosts_changes_only_its_consumer(self):
        p=self.r/'src/options/hosts.txt'
        a=self.recipe();b=self.recipe('keymapper','lain')
        p.write_bytes(p.read_bytes()+b'\n0.0.0.0 fixture.invalid\n')
        self.assertNotEqual(a['sha256'],self.recipe()['sha256'])
        self.assertEqual(b,self.recipe('keymapper','lain'))

    def test_notes_and_unrelated_target_do_not_change_recipe(self):
        a=self.recipe()
        self.change_target('reddit','note','new note only')
        self.change_target('keymapper','min_sdk_ceiling',30)
        self.assertEqual(a,self.recipe())

    def test_json_formatting_and_object_order_are_noop(self):
        a=self.recipe()
        for name in ('src/options/adobo.json','src/targets.json',
                     'src/build/helper/apps.json','docs/obtainium-govind.json'):
            p=self.r/name
            value=json.loads(p.read_text())
            p.write_text(json.dumps(value,indent=4,sort_keys=True))
        self.assertEqual(a,self.recipe())

    def test_revert_and_clock_change_are_noop(self):
        p=self.r/'src/options/hosts.txt';old=p.read_bytes();a=self.recipe()
        p.write_bytes(old+b'changed');p.write_bytes(old);os.utime(p,(1,1))
        self.assertEqual(a,self.recipe())

    def test_same_size_and_timestamp_still_detected(self):
        p=self.r/'src/options/hosts.txt';old=p.read_bytes();a=self.recipe();stamp=p.stat().st_mtime
        self.assertGreater(len(old),0)
        p.write_bytes(bytes([old[0]^1])+old[1:]);os.utime(p,(stamp,stamp))
        self.assertNotEqual(a['sha256'],self.recipe()['sha256'])

    def test_executable_mode_detected(self):
        p=self.r/'src/build/build.sh';a=self.recipe()
        p.chmod((p.stat().st_mode&0o777)^0o100)
        self.assertNotEqual(a['sha256'],self.recipe()['sha256'])

    def test_current_required_files_missing_refused(self):
        for name in ('src/options/hosts.txt','src/options/adobo.json',
                     '.github/actions/release/action.yml','src/build/TOOLING.sha256'):
            with self.subTest(path=name):
                p=self.r/name;old=p.read_bytes();mode=p.stat().st_mode;p.unlink()
                try:
                    with self.assertRaises((ValueError,OSError)):self.recipe()
                finally:p.write_bytes(old);p.chmod(mode)

    def test_missing_configured_extra_options_refused(self):
        (self.r/'src/options/binarymend.json').unlink()
        with self.assertRaises(ValueError):self.recipe('truecaller-combo','bufferk')

    def test_symlink_file_and_parent_refused(self):
        p=self.r/'src/options/hosts.txt';p.rename(self.r/'hosts-copy');p.symlink_to(self.r/'hosts-copy')
        with self.assertRaisesRegex(ValueError,'symlink'):self.recipe()
        p.unlink();(self.r/'hosts-copy').rename(p)
        op=self.r/'src/options';op.rename(self.r/'options-copy');op.symlink_to(self.r/'options-copy',target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):self.recipe()

    def test_duplicate_json_keys_and_nonfinite_refused(self):
        p=self.r/'src/options/adobo.json'
        for text in ('[{"a":1,"a":2}]','[NaN]','[Infinity]'):
            with self.subTest(text=text):
                p.write_text(text)
                with self.assertRaises(ValueError):self.recipe()

    def test_unsafe_resource_values_refused(self):
        p=self.r/'src/options/adobo.json'
        for loc in ('../outside','/tmp/outside','https://example.invalid/hosts','src/../private',''):
            with self.subTest(location=loc):
                p.write_text(json.dumps([{'patches':{'p':{'options':{'hosts':loc}}}}]))
                with self.assertRaises((ValueError,OSError)):self.recipe()

    def test_empty_unknown_disabled_and_duplicate_target_refused(self):
        p=self.r/'src/targets.json';old=p.read_bytes()
        for mode in ('empty','disabled','duplicate'):
            p.write_bytes(old)
            if mode=='empty':p.write_text('[]')
            elif mode=='disabled':self.change_target('reddit','enabled',False)
            else:
                self.edit_json('src/targets.json',lambda ts:ts.append(copy.deepcopy(ts[0])))
            with self.assertRaises(ValueError):self.recipe()
        p.write_bytes(old)
        with self.assertRaises(ValueError):self.recipe('unknown','adobo')
        with self.assertRaises(ValueError):self.recipe('reddit','unknown')

    def test_corrupt_missing_and_wrong_manifest_refused(self):
        a=self.recipe()
        for value in (None,{},dict(a,sha256='0'*64),dict(a,target='keymapper'),dict(a,winner='lain')):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):input_recipe.verify(self.r,'reddit','adobo',value)

    def test_a_self_consistent_but_incomplete_manifest_is_refused(self):
        a=self.recipe()
        a['components']=[x for x in a['components'] if x['path']!='src/options/hosts.txt']
        a['sha256']=input_recipe.digest({k:v for k,v in a.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'changed'):input_recipe.verify(self.r,'reddit','adobo',a)

    def test_cli_outputs_real_manifest_and_failure_is_nonzero(self):
        r=subprocess.run([sys.executable,str(ROOT/'src/build/input_recipe.py'),'reddit','adobo'],
                         cwd=self.r,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout),self.recipe())
        r=subprocess.run([sys.executable,str(ROOT/'src/build/input_recipe.py'),'unknown','adobo'],
                         cwd=self.r,capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(r.stdout,'')

    def test_generation_is_read_only(self):
        before={str(p.relative_to(self.r)):(p.read_bytes(),p.stat().st_mode) for p in self.r.rglob('*') if p.is_file()}
        self.recipe()
        after={str(p.relative_to(self.r)):(p.read_bytes(),p.stat().st_mode) for p in self.r.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_runtime_switch_boolean_captured_not_private_values(self):
        a=input_recipe.create(self.r,'reddit','adobo',{})
        b=input_recipe.create(self.r,'reddit','adobo',{'COE':'true','KEYSTORE_PASS':'NEVER_RECORD_THIS'})
        self.assertNotEqual(a['sha256'],b['sha256'])
        self.assertTrue(b['continue_on_error'])
        self.assertNotIn('NEVER_RECORD_THIS',json.dumps(b))
        self.assertEqual(b,input_recipe.create(self.r,'reddit','adobo',{'COE':'different-nonempty'}))

    def test_extra_order_is_preserved(self):
        a=self.recipe('truecaller-combo','bufferk')
        def change(ts):
            next(t for t in ts if t['id']=='truecaller-combo')['extra_bundles'].reverse()
        self.edit_json('src/targets.json',change)
        self.assertNotEqual(a['sha256'],self.recipe('truecaller-combo','bufferk')['sha256'])

    def test_manifest_is_not_provider_or_published_identity(self):
        doc=input_recipe.__doc__
        self.assertIn('NOT change polling',doc)
        self.assertIn('not a complete dynamic',doc)
        a=self.recipe()
        # No fabricated build/run/provider bytes in a local-only recipe.
        self.assertNotIn('published',a)
        self.assertNotIn('downloaded_bundle_sha256',a)

    def test_old_test_probe_never_used_as_implementation(self):
        # The implementation uses no Git dates, mtime or provider asset timestamps.
        source=(ROOT/'src/build/input_recipe.py').read_text()
        self.assertNotIn('git log',source)
        self.assertNotIn('updated_at',source)
        self.assertNotIn('st_mtime',source)


class InputRecipeFlow(unittest.TestCase):
    """Capture -> final APK evidence -> real release helper. Android tools mocked only."""
    def setUp(self):
        self.fixture=fixtures.Identity()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.r=self.fixture.r

    def setup_verified(self):
        captured=self.fixture.capture_fixture()
        report=self.fixture.verify_fixture()
        for name,value in {'.tagprefix':'key-mapper','.tagsuffix':'-b20260910',
                           '.provider':'lain','.patchver':'1.0'}.items():
            self.fixture.put('release/'+name,value+'\n')
        return captured,report

    def test_capture_final_and_release_accept_unchanged(self):
        captured,report=self.setup_verified()
        self.assertEqual(captured['local_input_recipe'],report['inputs']['local_input_recipe'])
        self.assertEqual(release_contract.verify(self.r,'keymapper')['prefix'],'key-mapper')

    def test_mode_change_before_final_refused(self):
        self.fixture.capture_fixture()
        p=self.r/'src/build/build.sh';p.chmod((p.stat().st_mode&0o777)^0o100)
        with self.assertRaisesRegex(ValueError,'input recipe'):
            self.fixture.verify_fixture()

    def test_untracked_option_change_before_final_refused(self):
        self.fixture.capture_fixture()
        self.fixture.put('src/options/lain.json','[{"fixture":true}]')
        with self.assertRaisesRegex(ValueError,'input recipe'):self.fixture.verify_fixture()

    def test_recipe_change_after_final_before_release_refused(self):
        self.setup_verified()
        self.fixture.put('src/options/lain.json','[{"fixture":true}]')
        with self.assertRaisesRegex(ValueError,'input recipe'):
            release_contract.verify(self.r,'keymapper')

    def test_runtime_switch_changed_before_final_refused(self):
        self.fixture.env['COE']=''
        self.fixture.capture_fixture()
        self.fixture.env['COE']='1'
        with self.assertRaisesRegex(ValueError,'input recipe'):self.fixture.verify_fixture()

    def test_runtime_switch_changed_before_release_refused(self):
        self.fixture.env['COE']=''
        self.setup_verified()
        with patch.dict(os.environ,{'COE':'1'}):
            with self.assertRaisesRegex(ValueError,'input recipe'):
                release_contract.verify(self.r,'keymapper')

    def test_workflow_change_after_final_before_release_refused(self):
        self.setup_verified()
        p=self.r/'.github/workflows/manual-patch.yml';p.write_bytes(p.read_bytes()+b'\n# changed\n')
        with self.assertRaisesRegex(ValueError,'input recipe'):
            release_contract.verify(self.r,'keymapper')

    def test_missing_manifest_before_final_refused(self):
        self.fixture.capture_fixture()
        p=self.r/'.build-inputs.json';d=json.loads(p.read_text());del d['local_input_recipe'];p.write_text(json.dumps(d))
        with self.assertRaises((KeyError,ValueError)):self.fixture.verify_fixture()

    def test_old_report_without_manifest_cannot_publish(self):
        self.setup_verified()
        p=self.r/'build-evidence/keymapper.json';d=json.loads(p.read_text());del d['inputs']['local_input_recipe'];p.write_text(json.dumps(d))
        with self.assertRaises((KeyError,ValueError)):release_contract.verify(self.r,'keymapper')

    def test_release_cli_fails_before_writing_github_outputs(self):
        self.setup_verified()
        self.fixture.put('src/options/lain.json','[{"fixture":true}]')
        dest=self.r/'output.txt';dest.write_text('existing=value\n')
        r=subprocess.run([sys.executable,str(ROOT/'src/build/release_contract.py'),'keymapper','--github-output'],
                         cwd=self.r,env={**os.environ,'GITHUB_OUTPUT':str(dest)},capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(dest.read_text(),'existing=value\n')

    def test_mutation_removing_final_gate_is_caught(self):
        self.fixture.capture_fixture()
        self.fixture.put('src/options/lain.json','[{"fixture":true}]')
        # Positive mutation control: disabling ONLY the new gate lets the deliberately
        # untracked fixture input through. The real negative test above must kill it.
        with patch.object(input_recipe,'verify',return_value=None):
            report=self.fixture.verify_fixture()
        self.assertEqual(report['status'],'verified')

    def test_mutation_removing_release_gate_is_caught(self):
        self.setup_verified();self.fixture.put('src/options/lain.json','[{"fixture":true}]')
        with patch.object(input_recipe,'verify',return_value=None):
            self.assertEqual(release_contract.verify(self.r,'keymapper')['prefix'],'key-mapper')
