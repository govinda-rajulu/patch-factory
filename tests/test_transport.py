import io,json,os,pathlib,subprocess,sys,tempfile,unittest,zipfile,hashlib,copy
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/build'))
import github_bundle as bundle
import github_patcher as patcher

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

class PatcherTransport(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name)
  self.payload=self.jar()
  self.asset={'id':542686729,'state':'uploaded','name':'morphe-desktop-1.15.0-all.jar',
              'size':len(self.payload),'digest':'sha256:'+hashlib.sha256(self.payload).hexdigest(),
              'browser_download_url':'https://github.com/MorpheApp/morphe-desktop/releases/download/v1.15.0/morphe-desktop-1.15.0-all.jar'}
  self.release={'draft':False,'prerelease':False,'tag_name':'v1.15.0','published_at':'2026-09-03T11:42:05Z','assets':[self.asset]}
 def jar(self,manifest=b'Manifest-Version: 1.0\r\nMain-Class: app.Main\r\n\r\n',main=True):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   if manifest is not None:z.writestr('META-INF/MANIFEST.MF',manifest)
   if main:z.writestr('app/Main.class',b'\xca\xfe\xba\xbe'+b'x'*1000001)
   else:z.writestr('data',b'x'*1000001)
  return out.getvalue()
 def download(self,args,**kwargs):
  pathlib.Path(args[args.index('--output')+1]).write_bytes(self.payload)
  return subprocess.CompletedProcess(args,0,stdout=b'',stderr=b'')
 def fetch(self,download=None):
  with patch.object(patcher,'api_json',return_value=self.release),patch.object(patcher.subprocess,'run',side_effect=download or self.download):
   return patcher.fetch(self.root,{'GITHUB_TOKEN':'test-secret'})
 def update_payload(self,payload):
  self.payload=payload;self.asset.update(size=len(payload),digest='sha256:'+hashlib.sha256(payload).hexdigest())
 def test_valid_download(self):
  r=self.fetch();self.assertFalse(r['cache_hit_verified']);self.assertTrue(r['github_digest_verified']);self.assertEqual(pathlib.Path(r['path']).read_bytes(),self.payload)
 def test_valid_cache_reused_only_after_fresh_metadata(self):
  (self.root/self.asset['name']).write_bytes(self.payload)
  with patch.object(patcher,'api_json',return_value=self.release) as a,patch.object(patcher.subprocess,'run') as c:
   self.assertTrue(patcher.fetch(self.root,{})['cache_hit_verified']);a.assert_called_once_with(patcher.LATEST,{},'MorpheApp/morphe-desktop');c.assert_not_called()
 def test_corrupt_cache_replaced(self):
  (self.root/self.asset['name']).write_bytes(b'corrupt')
  self.assertFalse(self.fetch()['cache_hit_verified'])
  self.assertEqual((self.root/self.asset['name']).read_bytes(),self.payload)
 def test_failed_download_leaves_existing_bytes_untouched(self):
  dest=self.root/self.asset['name'];dest.write_bytes(b'old-invalid')
  def bad(args,**kwargs):
   self.assertEqual(dest.read_bytes(),b'old-invalid')
   pathlib.Path(args[args.index('--output')+1]).write_bytes(b'partial')
   return subprocess.CompletedProcess(args,22)
  with self.assertRaisesRegex(ValueError,'no cache fallback'):self.fetch(bad)
  self.assertEqual(dest.read_bytes(),b'old-invalid');self.assertFalse(list(self.root.glob('*.cand')))
 def test_corrupt_transfer_retried_as_new_candidate(self):
  paths=[]
  def retry(args,**kwargs):
   paths.append(args[args.index('--output')+1])
   pathlib.Path(paths[-1]).write_bytes(b'junk' if len(paths)==1 else self.payload)
   return subprocess.CompletedProcess(args,0)
  self.fetch(retry);self.assertEqual(len(set(paths)),2);self.assertFalse(list(self.root.glob('*.cand')))
 def test_same_size_corruption_refused(self):
  original=self.payload
  def bad(args,**kwargs):
   pathlib.Path(args[args.index('--output')+1]).write_bytes(b'X'*len(original));return subprocess.CompletedProcess(args,0)
  with self.assertRaisesRegex(ValueError,'SHA-256'):self.fetch(bad)
  self.assertFalse((self.root/self.asset['name']).exists())
 def test_http_error_page_refused_even_with_matching_size_and_digest(self):
  self.update_payload(b'<html>'+b'x'*1000001)
  with self.assertRaises(ValueError):self.fetch()
 def test_missing_digest_fails_before_network(self):
  self.asset.pop('digest')
  with patch.object(patcher,'api_json',return_value=self.release),patch.object(patcher.subprocess,'run') as c:
   with self.assertRaisesRegex(ValueError,'lacks a usable'):patcher.fetch(self.root,{})
   c.assert_not_called()
 def test_wrong_digest(self):
  self.asset['digest']='sha256:'+'0'*64
  with self.assertRaisesRegex(ValueError,'SHA-256'):self.fetch()
 def test_missing_manifest(self):
  self.update_payload(self.jar(manifest=None))
  with self.assertRaisesRegex(ValueError,'manifest missing'):self.fetch()
 def test_missing_main_class(self):
  self.update_payload(self.jar(main=False))
  with self.assertRaisesRegex(ValueError,'bytecode missing'):self.fetch()
 def test_main_class_continuation(self):
  self.update_payload(self.jar(b'Manifest-Version: 1.0\r\nMain-Class: app.\r\n Main\r\n\r\n'))
  self.assertTrue(self.fetch()['jar_structure_verified'])
 def test_duplicate_main_class(self):
  self.update_payload(self.jar(b'Main-Class: app.Main\nMain-Class: app.Main\n\n'))
  with self.assertRaisesRegex(ValueError,'exactly one valid'):self.fetch()
 def test_no_main_class(self):
  self.update_payload(self.jar(b'Manifest-Version: 1.0\n\n'))
  with self.assertRaises(ValueError):self.fetch()
 def test_duplicate_entries(self):
  import warnings
  out=io.BytesIO(self.payload)
  with warnings.catch_warnings():
   warnings.simplefilter('ignore')
   with zipfile.ZipFile(out,'a') as z:z.writestr('app/Main.class',b'bad')
  self.update_payload(out.getvalue())
  with self.assertRaisesRegex(ValueError,'duplicate'):self.fetch()
 def test_bad_crc_despite_matching_download_digest(self):
  self.update_payload(self.payload.replace(b'x'*32,b'y'*32,1))
  with self.assertRaises(ValueError):self.fetch()
 def test_expansion_limit(self):
  with patch.object(patcher,'MAX_EXPANDED',100):
   with self.assertRaisesRegex(ValueError,'expansion'):self.fetch()
 def test_wrong_asset_url(self):
  for url in ('http://github.com/MorpheApp/morphe-desktop/releases/download/v1/'+self.asset['name'],
              'https://github.com.evil.invalid/file.jar','https://user@github.com/MorpheApp/morphe-desktop/releases/download/v1/'+self.asset['name']):
   self.asset['browser_download_url']=url
   with self.assertRaisesRegex(ValueError,'URL'):self.fetch()
 def test_ambiguous_all_jars(self):
  self.release['assets']=[self.asset,self.asset]
  with self.assertRaisesRegex(ValueError,'exactly one'):self.fetch()
 def test_nonrunnable_assets_not_selected(self):
  self.release['assets'].append(dict(self.asset,name='morphe-desktop-sources.jar'))
  self.assertEqual(self.fetch()['name'],self.asset['name'])
 def test_error_object_not_release(self):
  self.release={'message':'rate limit exceeded'}
  with self.assertRaisesRegex(ValueError,'invalid latest'):self.fetch()
 def test_prerelease_refused(self):
  self.release['prerelease']=True
  with self.assertRaises(ValueError):self.fetch()
 def test_draft_refused(self):
  self.release['draft']=True
  with self.assertRaises(ValueError):self.fetch()
 def test_symlink_destination_refused(self):
  outside=self.root/'outside';outside.write_bytes(b'keep')
  (self.root/self.asset['name']).symlink_to(outside)
  with self.assertRaisesRegex(ValueError,'symlinked'):self.fetch()
  self.assertEqual(outside.read_bytes(),b'keep')
 def test_api_failure_no_cache_fallback(self):
  (self.root/self.asset['name']).write_bytes(self.payload)
  with patch.object(patcher,'api_json',side_effect=ValueError('api failed')),patch.object(patcher.subprocess,'run') as c:
   with self.assertRaisesRegex(ValueError,'api failed'):patcher.fetch(self.root,{})
   c.assert_not_called()
 def test_asset_request_carries_no_token_and_uses_https(self):
  with patch.object(patcher,'api_json',return_value=self.release),patch.object(patcher.subprocess,'run',side_effect=self.download) as c:
   patcher.fetch(self.root,{'GITHUB_TOKEN':'test-secret'})
  args=c.call_args.args[0];self.assertNotIn('test-secret',' '.join(args));self.assertIn('--fail',args);self.assertIn('--proto-redir',args);self.assertNotIn('--config',args)
 def test_latest_version_is_not_hardcoded(self):
  self.asset['name']='morphe-desktop-9.99.0-all.jar';self.asset['browser_download_url']='https://github.com/MorpheApp/morphe-desktop/releases/download/v9.99.0/'+self.asset['name'];self.release['tag_name']='v9.99.0'
  self.assertEqual(self.fetch()['tag'],'v9.99.0')
 def test_build_uses_verified_downloader_before_resolution(self):
  s=(ROOT/'src/build/build.sh').read_text()
  self.assertNotIn('dl_gh "morphe-desktop"',s);self.assertIn('python3 src/build/github_patcher.py .',s)
  self.assertLess(s.index('github_patcher.py'),s.index('RES=$(bash ./src/build/resolve.sh'))

if __name__=='__main__':unittest.main()
