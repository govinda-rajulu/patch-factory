import io,json,os,pathlib,subprocess,sys,tempfile,unittest,zipfile,hashlib,copy
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/build'))
import github_bundle as bundle
import github_patcher as patcher
import extra_bundle as extra
sys.path.insert(0,str(ROOT/'src/etc'))
import release_retention as retention
import build_identity

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


class ExtraTransport(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name);self.out=self.root/'01-paresh.mpp'
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:z.writestr('fixture',b'x'*11000)
  self.payload=data.getvalue()
  # Actual metadata supplied by owner on 10 Sep; bundle bytes here are synthetic.
  self.link={'id':12729975,'name':'patches-1.20.0.mpp','url':'https://gitlab.com/-/project/82031658/uploads/bf2f3bcc525c867b790a800cfe77a115/patches-1.20.0.mpp','direct_asset_url':'https://gitlab.com/Paresh-Maheshwari/paresh-patches/-/releases/v1.20.0/downloads/patches-1.20.0.mpp','link_type':'other'}
  self.release={'tag_name':'v1.20.0','released_at':'2026-09-01T16:37:52.954Z','assets':{'links':[self.link]}}
  self.gh={'tag_name':'v1','published_at':'2026-09-01T00:00:00Z','assets':[{'id':1,'name':'patches-1.mpp','size':len(self.payload),'digest':'sha256:'+hashlib.sha256(self.payload).hexdigest(),'browser_download_url':'https://github.com/owner/repo/releases/download/v1/patches-1.mpp'}]}
 def transfer(self,args,**kwargs):
  pathlib.Path(args[args.index('--output')+1]).write_bytes(self.payload);return subprocess.CompletedProcess(args,0,stdout='',stderr='')
 def fetch(self,host='gitlab',fn=None):
  with patch.object(extra,'gitlab_page',return_value=[self.release]),patch.object(extra,'choose_release',return_value=self.gh),patch.object(extra.subprocess,'run',side_effect=fn or self.transfer):
   return extra.fetch(host,'82031658' if host=='gitlab' else 'owner/repo','prerelease',self.out,{'GITHUB_TOKEN':'dummy-secret'})
 def test_observed_gitlab_link_shape(self):
  r=self.fetch();self.assertEqual(r['asset_id'],12729975);self.assertEqual(r['tag'],'v1.20.0');self.assertEqual(self.out.read_bytes(),self.payload)
 def test_gitlab_hash_is_not_claimed_upstream_verified(self):
  r=self.fetch();self.assertFalse(r['upstream_digest_verified']);self.assertFalse(r['upstream_size_verified']);self.assertTrue(r['zip_verified']);self.assertEqual(r['sha256'],hashlib.sha256(self.payload).hexdigest())
 def test_github_digest_and_size_verified(self):
  r=self.fetch('github');self.assertTrue(r['upstream_digest_verified']);self.assertTrue(r['upstream_size_verified'])
 def test_github_missing_digest_explicit(self):
  self.gh['assets'][0].pop('digest');self.assertFalse(self.fetch('github')['upstream_digest_verified'])
 def test_github_wrong_digest_refused(self):
  self.gh['assets'][0]['digest']='sha256:'+'0'*64
  with self.assertRaisesRegex(ValueError,'digest differs'):self.fetch('github')
 def test_github_wrong_size_refused(self):
  self.gh['assets'][0]['size']+=1
  with self.assertRaisesRegex(ValueError,'size differs'):self.fetch('github')
 def test_github_other_repo_url_refused(self):
  self.gh['assets'][0]['browser_download_url']='https://github.com/other/repo/releases/download/v1/patches-1.mpp'
  with self.assertRaisesRegex(ValueError,'another repository'):self.fetch('github')
 def test_gitlab_cross_project_link_refused(self):
  self.link['url']=self.link['url'].replace('/82031658/','/999/')
  with self.assertRaisesRegex(ValueError,'project-scoped'):self.fetch()
 def test_gitlab_external_host_refused(self):
  self.link['url']=self.link['url'].replace('gitlab.com','example.invalid')
  with self.assertRaisesRegex(ValueError,'origin'):self.fetch()
 def test_gitlab_http_refused(self):
  self.link['url']=self.link['url'].replace('https:','http:')
  with self.assertRaises(ValueError):self.fetch()
 def test_url_credentials_refused(self):
  self.link['url']=self.link['url'].replace('gitlab.com','user@gitlab.com')
  with self.assertRaises(ValueError):self.fetch()
 def test_ambiguous_links_refused(self):
  self.release['assets']['links']*=2
  with self.assertRaisesRegex(ValueError,'exactly one'):self.fetch()
 def test_sources_are_not_bundle_links(self):
  self.release['assets']={'sources':[{'format':'zip','url':'https://gitlab.com/archive.zip'}],'links':[]}
  with self.assertRaisesRegex(ValueError,'exactly one'):self.fetch()
 def test_unknown_host_refused(self):
  with self.assertRaisesRegex(ValueError,'unsupported'):extra.select('other','1','latest',{})
 def test_invalid_channel_refused(self):
  with self.assertRaises(ValueError):extra.select('gitlab','82031658','guess',{})
 def test_invalid_project_refused(self):
  with self.assertRaises(ValueError):extra.select('gitlab','../x','latest',{})
 def test_tag_output_injection_refused(self):
  self.release['tag_name']='v1\nSIZE=1'
  with self.assertRaises(ValueError):self.fetch()
 def test_invalid_date_refused(self):
  self.release['released_at']='bad-date'
  with self.assertRaises(ValueError):self.fetch()
 def test_gitlab_latest_skips_dev_with_pagination(self):
  dev=dict(self.release,tag_name='v9-dev')
  with patch.object(extra,'gitlab_page',side_effect=[[dev]*100,[self.release]]) as m:
   self.assertEqual(extra.select('gitlab','82031658','latest',{})['tag'],'v1.20.0');self.assertEqual(m.call_count,2)
 def test_gitlab_prerelease_keeps_newest_including_stable(self):
  with patch.object(extra,'gitlab_page',return_value=[self.release]):
   self.assertEqual(extra.select('gitlab','82031658','prerelease',{})['tag'],'v1.20.0')
 def test_empty_release_inventory_refused(self):
  with patch.object(extra,'gitlab_page',return_value=[]):
   with self.assertRaises(ValueError):extra.select('gitlab','82031658','latest',{})
 def test_gitlab_api_nonarray_refused(self):
  with patch.object(extra.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='{"message":"error"}')):
   with self.assertRaisesRegex(ValueError,'non-array'):extra.gitlab_page('82031658',1)
 def test_gitlab_api_http_failure_refused(self):
  with patch.object(extra.subprocess,'run',return_value=subprocess.CompletedProcess([],22,stdout='')):
   with self.assertRaisesRegex(ValueError,'API failed'):extra.gitlab_page('82031658',1)
 def test_gitlab_api_carries_no_token(self):
  with patch.object(extra.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='[]')) as m:
   extra.gitlab_page('82031658',1)
  self.assertNotIn('--location',m.call_args.args[0]);self.assertNotIn('Authorization',str(m.call_args));self.assertIn('--fail',m.call_args.args[0])
 def test_transfer_uses_https_and_no_credentials(self):
  with patch.object(extra,'gitlab_page',return_value=[self.release]),patch.object(extra.subprocess,'run',side_effect=self.transfer) as m:
   extra.fetch('gitlab','82031658','prerelease',self.out,{'GITHUB_TOKEN':'dummy-secret'})
  self.assertIn('--max-filesize',m.call_args.args[0]);self.assertIn('--proto-redir',m.call_args.args[0]);self.assertNotIn('dummy-secret',str(m.call_args))
 def test_html_error_body_refused(self):
  self.payload=b'<html>'+b'x'*11000
  with self.assertRaises(ValueError):self.fetch()
  self.assertFalse(self.out.exists());self.assertFalse(list(self.root.glob('*.cand')))
 def test_transfer_failure_preserves_previous_destination(self):
  self.out.write_bytes(b'previous')
  def bad(args,**kwargs):
   self.assertEqual(self.out.read_bytes(),b'previous');return subprocess.CompletedProcess(args,22,stdout='',stderr='')
  with self.assertRaisesRegex(ValueError,'destination not replaced'):self.fetch(fn=bad)
  self.assertEqual(self.out.read_bytes(),b'previous')
 def test_retry_after_bad_archive(self):
  paths=[]
  def retry(args,**kwargs):
   p=pathlib.Path(args[args.index('--output')+1]);paths.append(str(p));p.write_bytes(b'bad' if len(paths)==1 else self.payload);return subprocess.CompletedProcess(args,0,stdout='',stderr='')
  self.fetch(fn=retry);self.assertEqual(len(set(paths)),2)
 def test_symlink_destination_refused(self):
  other=self.root/'other';other.write_bytes(b'keep');self.out.symlink_to(other)
  with self.assertRaises(ValueError):self.fetch()
  self.assertEqual(other.read_bytes(),b'keep')
 def test_crc_failure_refused(self):
  self.payload=self.payload.replace(b'x'*32,b'y'*32,1)
  with self.assertRaises(ValueError):self.fetch()
 def test_traversal_zip_refused(self):
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:z.writestr('../outside',b'x'*11000)
  self.payload=data.getvalue()
  with self.assertRaisesRegex(ValueError,'unsafe'):self.fetch()
 def test_duplicate_zip_refused(self):
  import warnings
  data=io.BytesIO()
  with warnings.catch_warnings():
   warnings.simplefilter('ignore')
   with zipfile.ZipFile(data,'w') as z:z.writestr('same',b'x'*11000);z.writestr('same',b'x')
  self.payload=data.getvalue()
  with self.assertRaisesRegex(ValueError,'duplicate'):self.fetch()
 def test_expansion_limit_refused(self):
  with patch.object(extra,'MAX_EXPANDED',10):
   with self.assertRaisesRegex(ValueError,'expansion'):self.fetch()
 def test_existing_shell_contract_preserved(self):
  s=(ROOT/'src/build/fetch_bundle.sh').read_text();self.assertIn('exec python3',s);self.assertNotIn('curl -sSL',s)
  build=(ROOT/'src/build/build.sh').read_text();self.assertIn('printf',build);self.assertIn('fetch_bundle.sh "$EH" "$EID" "$ECH"',build)

class Retention(unittest.TestCase):
 def setUp(self):
  self.repo='owner/repo';self.targets=[{'id':'app','tag_prefix':'app'},{'id':'other','tag_prefix':'other'}]
 def row(self,n,prefix='app',day=None,**values):
  date=day or ('202609'+str(n).zfill(2));tag=prefix+'-v1.0-b'+date
  row={'id':n,'tag_name':tag,'html_url':'https://github.com/'+self.repo+'/releases/tag/'+tag,
       'published_at':'2026-09-10T00:00:00Z','draft':False,'prerelease':False,
       'body':retention.CI_MARKER,'assets':[{'name':prefix+'-v1.0-arm64-v8a.apk','size':2000000}]}
  row.update(values);return row
 def plan(self,rows,prefix=None):return retention.preview(rows,self.targets,self.repo,prefix)
 def test_two_newest_protected(self):
  p=self.plan([self.row(n) for n in range(1,5)])
  self.assertEqual([r['release_id'] for r in p['candidates']],[1,2])
  self.assertFalse(p['deletion_authorized']);self.assertEqual(p['candidate_asset_count'],2)
 def test_per_prefix_not_global(self):
  p=self.plan([self.row(n) for n in range(1,4)]+[self.row(n+10,prefix='other',day='2026090'+str(n)) for n in range(1,4)])
  self.assertEqual({r['release_id'] for r in p['candidates']},{1,11})
 def test_input_order_does_not_change_fingerprint(self):
  rows=[self.row(n) for n in range(1,5)]
  self.assertEqual(self.plan(rows)['fingerprint'],self.plan(rows[::-1])['fingerprint'])
 def test_empty_inventory_is_empty_preview_not_delete_all(self):
  p=self.plan([]);self.assertEqual(p['candidate_count'],0);self.assertEqual(p['protected'],[])
 def test_one_release_kept(self):
  self.assertEqual(self.plan([self.row(1)])['candidate_count'],0)
 def test_frozen_tag_protected(self):
  r=self.row(1,tag_name='truecaller-v26.10.6')
  self.assertIn('frozen',self.plan([r])['protected'][0]['reason'])
 def test_manual_suffixless_tag_protected(self):
  p=self.plan([self.row(1,tag_name='app-v1.0')]);self.assertEqual(p['candidate_count'],0)
 def test_unknown_prefix_protected(self):
  p=self.plan([self.row(1,prefix='unknown')]);self.assertEqual(p['candidate_count'],0)
 def test_old_manual_dated_entry_protected(self):
  p=self.plan([self.row(1,body='Manually uploaded'),self.row(2),self.row(3)])
  self.assertEqual(p['candidate_count'],0)
 def test_keep_marker_protected(self):
  for marker in ['frozen','manual','keep forever','do not delete','retention: keep']:
   p=self.plan([self.row(1,body=retention.CI_MARKER+' '+marker),self.row(2),self.row(3)])
   self.assertEqual(p['candidate_count'],0)
 def test_draft_and_prerelease_protected(self):
  for field in ['draft','prerelease']:
   p=self.plan([self.row(1,**{field:True}),self.row(2),self.row(3)])
   self.assertEqual(p['candidate_count'],0)
 def test_unexpected_assets_protected(self):
  p=self.plan([self.row(1,assets=[]),self.row(2),self.row(3)])
  self.assertEqual(p['candidate_count'],0)
 def test_wrong_apk_version_protected(self):
  p=self.plan([self.row(1,assets=[{'name':'app-v2.0-arm64-v8a.apk','size':2000000}]),self.row(2),self.row(3)])
  self.assertEqual(p['candidate_count'],0)
 def test_prefix_filter_preserves_other_apps(self):
  p=self.plan([self.row(n) for n in range(1,4)],prefix='other');self.assertEqual(p['candidate_count'],0)
 def test_invalid_calendar_date_protected(self):
  p=self.plan([self.row(1,day='20260231')]);self.assertEqual(p['candidate_count'],0)
 def test_missing_timestamp_refuses_partial_plan(self):
  with self.assertRaises(ValueError):self.plan([self.row(1,published_at=None)])
 def test_duplicate_inventory_refused(self):
  with self.assertRaisesRegex(ValueError,'duplicate'):self.plan([self.row(1),self.row(1)])
 def test_unknown_filter_refused(self):
  with self.assertRaises(ValueError):self.plan([],prefix='unknown')
 def test_bad_url_refused(self):
  with self.assertRaises(ValueError):self.plan([self.row(1,html_url='https://evil.invalid/')])
 def test_pagination_reads_beyond_first_hundred(self):
  first=[self.row(n,day='20260901') for n in range(1,101)]
  with patch.object(retention.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,stdout=json.dumps(first)),subprocess.CompletedProcess([],0,stdout=json.dumps([self.row(101,day='20260902')]))]) as m:
   rows=retention.inventory(self.repo);self.assertEqual(len(rows),101);self.assertEqual(m.call_count,2)
 def test_second_page_failure_no_partial_success(self):
  with patch.object(retention.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,stdout=json.dumps([self.row(n,day='20260901') for n in range(1,101)])),subprocess.CompletedProcess([],22,stdout='')]):
   with self.assertRaisesRegex(ValueError,'no partial'):retention.inventory(self.repo)
 def test_api_error_object_refused(self):
  with patch.object(retention.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='{\"message\":\"error\"}')):
   with self.assertRaises(ValueError):retention.inventory(self.repo)
 def test_no_delete_command_in_planner_or_release_action(self):
  action=(ROOT/'.github/actions/release/action.yml').read_text()
  self.assertNotIn('gh release delete',action);self.assertNotIn('--cleanup-tag',action)
  self.assertIn('Preview retention (no deletion)',action);self.assertIn('release_retention.py',action)
  source=(ROOT/'src/etc/release_retention.py').read_text()
  self.assertNotIn("'DELETE'",source);self.assertNotIn('gh release delete',source)
 def test_summary_is_preview_not_authorization(self):
  s=retention.summary(self.plan([self.row(n) for n in range(1,4)]))
  self.assertIn('Nothing deleted',s);self.assertIn('Approval is required separately',s)

class BuildIdentityTests(unittest.TestCase):
 def setUp(self):
  import datetime
  self.now=datetime.datetime(2026,9,10,23,59,tzinfo=datetime.timezone.utc)
  self.env={'GITHUB_RUN_ID':'34481169955','GITHUB_RUN_ATTEMPT':'1'}
 def suffix(self,**env):return build_identity.create(dict(self.env,**env),self.now)
 def test_fixed_width_numeric(self):
  s=self.suffix();self.assertEqual(len(s),36);self.assertTrue(s[2:].isdigit());self.assertTrue(s.startswith('-b20260910'))
 def test_exact_layout(self):
  self.assertEqual(self.suffix(),'-b20260910'+'34481169955'.zfill(20)+'000001')
 def test_different_run_same_day(self):
  self.assertNotEqual(self.suffix(),self.suffix(GITHUB_RUN_ID='34481169956'))
 def test_rerun_attempt_is_distinct(self):
  self.assertNotEqual(self.suffix(),self.suffix(GITHUB_RUN_ATTEMPT='2'))
 def test_same_run_attempt_deterministic(self):
  self.assertEqual(self.suffix(),self.suffix())
 def test_parse_new(self):
  p=build_identity.parse(self.suffix());self.assertEqual(p,{'date':'20260910','legacy':False,'run_id':34481169955,'attempt':1})
 def test_parse_legacy(self):
  self.assertTrue(build_identity.parse('-b20260910')['legacy'])
 def test_missing_run_refused(self):
  with self.assertRaises(ValueError):build_identity.create({'GITHUB_RUN_ATTEMPT':'1'},self.now)
 def test_missing_attempt_refused(self):
  with self.assertRaises(ValueError):build_identity.create({'GITHUB_RUN_ID':'1'},self.now)
 def test_zero_negative_and_injected_values_refused(self):
  for v in ['0','-1','1\nx','1.5','01','1;false','']:
   with self.assertRaises(ValueError):self.suffix(GITHUB_RUN_ID=v)
 def test_attempt_limits(self):
  self.assertEqual(build_identity.parse(self.suffix(GITHUB_RUN_ATTEMPT='999999'))['attempt'],999999)
  with self.assertRaises(ValueError):self.suffix(GITHUB_RUN_ATTEMPT='1000000')
 def test_run_limits(self):
  self.assertEqual(build_identity.parse(self.suffix(GITHUB_RUN_ID='9'*20))['run_id'],int('9'*20))
  with self.assertRaises(ValueError):self.suffix(GITHUB_RUN_ID='9'*21)
 def test_date_invalid(self):
  with self.assertRaises(ValueError):build_identity.parse('-b20260231')
 def test_nonstandard_length(self):
  for suffix in ['-b202609101','-b20260910-r1','-b'+'0'*34]:
   with self.assertRaises(ValueError):build_identity.parse(suffix)
 def test_zero_identity_refused(self):
  with self.assertRaises(ValueError):build_identity.parse('-b20260910'+'0'*26)
 def test_verify_correct_run(self):
  self.assertFalse(build_identity.verify_run(self.suffix(),self.env)['legacy'])
 def test_verify_wrong_run(self):
  with self.assertRaises(ValueError):build_identity.verify_run(self.suffix(),dict(self.env,GITHUB_RUN_ID='2'))
 def test_verify_wrong_attempt(self):
  with self.assertRaises(ValueError):build_identity.verify_run(self.suffix(),dict(self.env,GITHUB_RUN_ATTEMPT='2'))
 def test_cannot_publish_legacy_identity(self):
  with self.assertRaises(ValueError):build_identity.verify_run('-b20260910',self.env)
 def test_timezone_is_utc(self):
  import datetime
  local=datetime.datetime(2026,9,11,1,tzinfo=datetime.timezone(datetime.timedelta(hours=5,minutes=30)))
  self.assertTrue(build_identity.create(self.env,local).startswith('-b20260910'))
 def test_naive_time_refused(self):
  with self.assertRaises(ValueError):build_identity.create(self.env,self.now.replace(tzinfo=None))
 def test_existing_obtainium_filters_match_both_formats(self):
  import re
  for filename in ['obtainium-govind.json','obtainium-parents.json']:
   for app in json.loads((ROOT/'docs'/filename).read_text())['apps']:
    settings=json.loads(app['additionalSettings'])
    prefix=next(t['tag_prefix'] for t in json.loads((ROOT/'src/targets.json').read_text()) if t['label']==app['name'])
    for suffix in ['-b20260910',self.suffix()]:
     tag=prefix+'-v1.2.3'+suffix
     self.assertIsNotNone(re.fullmatch(settings['filterReleaseTitlesByRegEx'],tag))
     self.assertEqual(re.search(settings['versionExtractionRegEx'],tag).group(int(settings['matchGroupToUse'])),'1.2.3')
 def test_tag_uniqueness_does_not_fix_obtainium_version_equality(self):
  import re
  regex=r'-v([0-9.]+)-b[0-9]+$'
  tags=['app-v1.0'+self.suffix(GITHUB_RUN_ATTEMPT=str(n)) for n in [1,2]]
  self.assertNotEqual(*tags);self.assertEqual(*[re.search(regex,t)[1] for t in tags])
 def test_retention_mixed_old_new(self):
  fixture=Retention();fixture.setUp()
  rows=[fixture.row(1),fixture.row(2),fixture.row(3)]
  for r,a in zip(rows,[None,'1','2']):
   if a:
    r['tag_name']='app-v1.0'+self.suffix(GITHUB_RUN_ATTEMPT=a)
    r['html_url']='https://github.com/owner/repo/releases/tag/'+r['tag_name']
  p=fixture.plan(rows);self.assertEqual([x['release_id'] for x in p['candidates']],[1])
 def test_retention_orders_reruns_numerically(self):
  fixture=Retention();fixture.setUp();rows=[]
  for n in [9,10,11]:
   tag='app-v1.0'+self.suffix(GITHUB_RUN_ATTEMPT=str(n))
   rows.append(fixture.row(n,tag_name=tag,html_url='https://github.com/owner/repo/releases/tag/'+tag))
  self.assertEqual([x['release_id'] for x in fixture.plan(rows)['candidates']],[9])
 def test_retention_bad_long_id_protected(self):
  fixture=Retention();fixture.setUp()
  tag='app-v1.0-b20260910'+'0'*26
  self.assertEqual(fixture.plan([fixture.row(1,tag_name=tag)])['candidate_count'],0)
 def test_release_action_refuses_updates_and_upload_failures(self):
  s=(ROOT/'.github/actions/release/action.yml').read_text()
  self.assertIn('allowUpdates: false',s);self.assertIn('replacesArtifacts: false',s)
  self.assertIn('artifactErrorsFailBuild: true',s);self.assertIn('commit: ${{ github.sha }}',s)
 def test_build_generates_identity_not_date_only(self):
  s=(ROOT/'src/build/build.sh').read_text();self.assertIn('python3 src/build/build_identity.py',s)
  self.assertNotIn('echo "-b$(date -u +%Y%m%d)"',s)

if __name__=='__main__':unittest.main()
