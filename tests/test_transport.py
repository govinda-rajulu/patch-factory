import io,json,os,pathlib,subprocess,sys,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/build'))
import github_bundle as bundle

class Transport(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('patches',b'x'*11000)
  self.payload=b.getvalue()
  self.release={'tag_name':'v1','published_at':'2026-09-10T00:00:00Z','prerelease':False,'assets':[{'id':1,'name':'patches-1.mpp','size':len(self.payload),'browser_download_url':'https://github.com/owner/repo/releases/download/v1/patches-1.mpp'}]}
 def tearDown(self):self.tmp.cleanup()
 def result(self,rc=0,text=''):return subprocess.CompletedProcess([],rc,stdout=text,stderr='')
 def test_api_token_stays_out_of_argv(self):
  with patch.object(bundle.subprocess,'run',return_value=self.result(text='[]')) as mock:
   bundle.api_page('owner','repo',1,{'GITHUB_TOKEN':'dummy-token'})
   argv=mock.call_args.args[0];self.assertNotIn('dummy-token',' '.join(argv));self.assertIn('Authorization: Bearer dummy-token',mock.call_args.kwargs['input']);self.assertNotIn('--location',argv)
 def test_api_403_is_not_empty_provider(self):
  with patch.object(bundle.subprocess,'run',return_value=self.result(22)):
   with self.assertRaisesRegex(ValueError,'not a version-compatibility'):bundle.api_page('owner','repo',1,{})
 def test_api_object_rejected(self):
  with patch.object(bundle.subprocess,'run',return_value=self.result(text='{"message":"rate limited"}')):
   with self.assertRaises(ValueError):bundle.api_page('owner','repo',1,{})
 def test_prerelease_preserves_newest_any_build_semantics(self):
  with patch.object(bundle,'api_page',return_value=[self.release,dict(self.release,prerelease=True,tag_name='dev')]):
   self.assertEqual(bundle.choose_release('owner','repo','prerelease',{})['tag_name'],'v1')
 def test_latest_paginates_past_devs(self):
  with patch.object(bundle,'api_page',side_effect=[[dict(self.release,prerelease=True)]*100,[self.release]]) as m:
   self.assertEqual(bundle.choose_release('owner','repo','latest',{})['tag_name'],'v1');self.assertEqual(m.call_count,2)
 def download(self,args,**kwargs):
  pathlib.Path(args[args.index('--output')+1]).write_bytes(self.payload);return self.result()
 def test_fetch_checks_shape_and_size(self):
  with patch.object(bundle,'choose_release',return_value=self.release),patch.object(bundle.subprocess,'run',side_effect=self.download) as m:
   r=bundle.fetch('owner','repo','prerelease',self.root,{'GITHUB_TOKEN':'dummy'})
   self.assertEqual(pathlib.Path(r['path']).read_bytes(),self.payload);self.assertNotIn('Authorization',' '.join(m.call_args.args[0]))
 def test_fetch_rejects_size_mismatch(self):
  r=json.loads(json.dumps(self.release));r['assets'][0]['size']+=1
  with patch.object(bundle,'choose_release',return_value=r),patch.object(bundle.subprocess,'run',side_effect=self.download):
   with self.assertRaises(ValueError):bundle.fetch('owner','repo','prerelease',self.root,{})
  self.assertFalse(list(self.root.glob('*.mpp')))
 def test_fetch_rejects_ambiguous_assets(self):
  r=json.loads(json.dumps(self.release));r['assets']*=2
  with patch.object(bundle,'choose_release',return_value=r):
   with self.assertRaises(ValueError):bundle.fetch('owner','repo','prerelease',self.root,{})
 def test_fetch_rejects_external_asset_url(self):
  r=json.loads(json.dumps(self.release));r['assets'][0]['browser_download_url']='https://example.invalid/file.mpp'
  with patch.object(bundle,'choose_release',return_value=r):
   with self.assertRaises(ValueError):bundle.fetch('owner','repo','latest',self.root,{})
 def test_fetch_rejects_wrong_digest(self):
  r=json.loads(json.dumps(self.release));r['assets'][0]['digest']='sha256:'+'0'*64
  with patch.object(bundle,'choose_release',return_value=r),patch.object(bundle.subprocess,'run',side_effect=self.download):
   with self.assertRaises(ValueError):bundle.fetch('owner','repo','latest',self.root,{})
 def test_resolver_process_failure_rejects_ceiling_fallback(self):
  (self.root/'src').mkdir();(self.root/'morphe-desktop-fixture.jar').write_text('fixture')
  (self.root/'src/targets.json').write_text(json.dumps([{'id':'facebook','package':'com.facebook.katana','max_app_version':'490','candidates':[{'name':'p','owner':'owner','repo':'repo','channel':'prerelease'}]}]))
  bin=self.root/'bin';bin.mkdir()
  for name,code in [('python3',"echo '{\"published_at\":\"2026-09-10T00:00:00Z\",\"path\":\"fixture.mpp\",\"sha256\":\"fixture\",\"tag\":\"v1\"}'"),('java','echo "fixture parser failure"; exit 2')]:
   p=bin/name;p.write_text('#!/bin/bash\n'+code+'\n');p.chmod(0o755)
  x=subprocess.run(['bash',str(ROOT/'src/build/resolve.sh'),'facebook'],cwd=self.root,env={**os.environ,'PATH':str(bin)+':'+os.environ['PATH']},capture_output=True,text=True)
  self.assertEqual(x.returncode,2);self.assertNotIn('WINNER=',x.stdout);self.assertIn('refusing version fallback',x.stdout)
 def test_resolution_and_build_have_single_winner_fetch(self):
  resolve=(ROOT/'src/build/resolve.sh').read_text();build=(ROOT/'src/build/build.sh').read_text()
  self.assertIn('--patches="$MPP"',resolve);self.assertNotIn('--patches="https://github.com/',resolve)
  self.assertNotIn('dl_gh "$REPO" "$OWNER" "$CHAN"',build);self.assertIn('cp "$MPP" ./',build);self.assertIn('MPP_HASH',build)

if __name__=='__main__':unittest.main()
