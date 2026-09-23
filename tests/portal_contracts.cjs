/* Pure page contracts through Node's standard library; no network or Android runtime. */
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'docs/portal.js'),'utf8'),html=fs.readFileSync(path.join(root,'docs/index.html'),'utf8');
const marker='// Expose pure contracts only for tests';assert.equal(source.split(marker).length,2);
const context={window:{},document:{getElementById:()=>null},URL,Map,Set,Date,JSON,console,setTimeout,clearTimeout,AbortController};
vm.runInNewContext(source.slice(0,source.indexOf(marker))+'window.contracts={parseTag,validateImport,validateMicroG,validateObtainium,microgConfig,microgRelease,validateTargets,releaseRows,safeLink,selectApps,appGroup,plain,noteText,changeSummary,jobRole,jobSummary};})();',context);
const c=context.window.contracts,targets=JSON.parse(fs.readFileSync(path.join(root,'src/targets.json'))),pack=JSON.parse(fs.readFileSync(path.join(root,'docs/obtainium.json')));
let count=0;function check(name,fn){fn();count++;console.log('PASS '+name)}
check('MicroG architecture selections stay single-file and refuse variant fallbacks',()=>{
 const pack=JSON.parse(fs.readFileSync(path.join(root,'docs/obtainium-microg.json'))),rel={tag_name:'7.1.0',published_at:'2026-09-06T09:08:10Z',prerelease:false,draft:false,html_url:'https://github.com/MorpheApp/MicroG-RE/releases/tag/7.1.0',assets:['microg-7.1.0.apk','microg-7.1.0-arm64-v8a.apk','microg-7.1.0-noicon.apk','microg-7.1.0-noicon-arm64-v8a.apk'].map((name,i)=>({name,state:'uploaded',size:2000000+i,browser_download_url:'https://github.com/MorpheApp/MicroG-RE/releases/download/7.1.0/'+name}))};
 for(const [arch,name] of [['universal','microg-7.1.0.apk'],['arm64-v8a','microg-7.1.0-arm64-v8a.apk']]){
  const app=c.microgConfig(pack,'stable',arch),settings=JSON.parse(app.additionalSettings);
  assert.equal(settings.autoApkFilterByArch,false);assert.ok(settings.apkFilterRegEx.includes(arch==='universal'?'[.]apk$':'-'+arch+'[.]apk$'));
  assert.equal(c.microgRelease([rel],'stable',arch).asset.name,name);
 }
 const auto=c.microgConfig(pack,'stable','auto');assert.equal(JSON.parse(auto.additionalSettings).autoApkFilterByArch,true);
 assert.throws(()=>c.microgRelease([rel],'stable','armeabi-v7a'));assert.throws(()=>c.microgConfig(pack,'stable','x86_64'));
});
check('optional Obtainium self companion matches the official standard entry',()=>{
 const pack=JSON.parse(fs.readFileSync(path.join(root,'docs/obtainium-self.json'))),app=c.validateObtainium(pack)[0],settings=JSON.parse(app.additionalSettings);
 assert.equal(app.id,'dev.imranr.obtainium');assert.equal(settings.apkFilterRegEx,'fdroid');assert.equal(settings.invertAPKFilter,true);assert.equal(settings.autoApkFilterByArch,true);assert.equal(settings.trackOnly,false);
 const d=structuredClone(pack);d.apps[0].id='dev.imranr.obtainium.fdroid';assert.throws(()=>c.validateObtainium(d));
});
check('one public catalog and full import have exact enabled coverage',()=>{assert.equal(c.validateTargets(targets).length,14);assert.equal(c.validateImport(pack,targets).length,14);assert.ok(html.includes('<option value="all">All apps</option>'));assert.ok(html.includes('<option value="custom">Select only</option>'));assert.ok(!html.includes('family pack'));assert.ok(!source.includes("['govind','parents'"));assert.ok(source.includes("RAW+'docs/obtainium.json'"))});
check('import encoded URI round trip retains full and selected app settings',()=>{const apps=c.validateImport(pack,targets),uri='obtainium://apps/'+encodeURIComponent(JSON.stringify(apps));assert.deepEqual(JSON.parse(decodeURIComponent(uri.slice(17))),pack.apps);assert.ok(uri.length<100000);const before=JSON.stringify(apps);const chosen=c.selectApps(apps,[apps[2].id,apps[0].id]);assert.deepEqual(JSON.parse(JSON.stringify(chosen)),[pack.apps[0],pack.apps[2]]);assert.equal(JSON.stringify(apps),before);for(const ids of [[],['unknown'],[apps[0].id,apps[0].id],null])assert.throws(()=>c.selectApps(apps,ids));assert.equal(c.selectApps(apps,apps.map(a=>a.id)).length,14)});
check('malformed imports refuse global settings, duplicates, foreign URLs and credentials',()=>{for(const mutate of [d=>d.settings={},d=>d.apps.pop(),d=>d.apps.push(d.apps[0]),d=>d.apps[0].url='https://evil.invalid',d=>d.apps[0].additionalSettings='{"token":"SECRET"}']){const d=structuredClone(pack);mutate(d);assert.throws(()=>c.validateImport(d,targets))}});
check('version and arbitrary precision build ID remain separate',()=>{const d=c.parseTag('youtube-morphe-v21.36.45-b2026091300000000034768808230000001');assert.equal(d.version,'21.36.45');assert.equal(d.run,'34768808230');assert.equal(d.attempt,'1');assert.equal(c.parseTag('app-v1.0-b2026091399999999999999999999000001').run,'99999999999999999999')});
check('legacy date tags accepted; malformed tags rejected',()=>{assert.equal(c.parseTag('app-v1.0-b20260913').run,null);for(const t of ['app-v1.0-b20260230','app-v1.0-b2026091300000000000000000000000000','app-v1<script>','app-v1.0-b20260913junk',null])assert.equal(c.parseTag(t),null)});
check('unsafe and cross-repository links refused',()=>{for(const url of ['javascript:alert(1)','http://github.com/'+ 'govinda-rajulu/patch-factory/releases','https://github.com/other/repo/releases','https://github.com.evil.invalid/govinda-rajulu/patch-factory/releases','https://user:pass@github.com/govinda-rajulu/patch-factory/releases'])assert.equal(c.safeLink(url),null)});
check('release grouping stays per target and ambiguous assets withheld',()=>{const tag='youtube-morphe-v21.36.45-b20260913',r={id:1,tag_name:tag,draft:false,prerelease:false,published_at:'2026-09-13T00:00:00Z',assets:[{name:'youtube-v21.36.45-arm64-v8a.apk',state:'uploaded',size:2000000,browser_download_url:'https://github.com/govinda-rajulu/patch-factory/releases/download/'+tag+'/youtube-v21.36.45-arm64-v8a.apk'}]};assert.equal(c.releaseRows([r],targets).map.get('youtube-morphe').length,1);assert.equal(c.releaseRows([r],targets).map.get('instagram').length,0);r.assets.push(r.assets[0]);assert.equal(c.releaseRows([r],targets).rejected,1)});
check('no credential input, persistent-token use or API write path',()=>{for(const s of ['localStorage','sessionStorage','innerHTML','insertAdjacentHTML','/dispatches','Authorization','method:'])assert.ok(!source.includes(s),s);assert.ok(!html.includes('type="password"'));assert.ok(html.includes('portal.js'));assert.ok(source.includes('credentials:\'omit\''))});
check('disabled or duplicate targets refused for full imports',()=>{let t=structuredClone(targets);t[0].enabled=false;assert.throws(()=>c.validateImport(pack,t));t=structuredClone(targets);t.push(t[0]);assert.throws(()=>c.validateTargets(t));assert.equal(c.appGroup('youtube')[0],'media');assert.equal(c.appGroup('instagram')[0],'social');assert.equal(c.appGroup('keymapper')[0],'tools');assert.equal(c.appGroup('future-app')[0],'other');for(const marker of ['Search apps','Filter app category','Evidence, notes & older versions','No matching apps.'])assert.ok(source.includes(marker),marker)});
check('labels allow hyphens but refuse controls and empty strings',()=>{
 assert.equal(c.plain('MicroG-RE'),true);
 for(const value of ['',null,'bad\nname','bad\tname','bad\u0000name','bad\u001fname','bad\u007fname'])assert.equal(c.plain(value),false);
});
check('ordinary import binds package and all reviewed tracking settings',()=>{
 for(const mutate of [d=>d.apps[0].id='other.valid.package',d=>d.apps[0].preferredApkIndex=2,d=>{const s=JSON.parse(d.apps[0].additionalSettings);s.trackOnly=true;d.apps[0].additionalSettings=JSON.stringify(s)},d=>{const s=JSON.parse(d.apps[0].additionalSettings);s.versionExtractionRegEx='.*';d.apps[0].additionalSettings=JSON.stringify(s)}]){
  const d=structuredClone(pack);mutate(d);assert.throws(()=>c.validateImport(d,targets));
 }
});
check('optional MicroG stays separate and preserves upstream package and exact filters',()=>{
 const d=JSON.parse(fs.readFileSync(path.join(root,'docs/obtainium-microg.json')));
 const [app]=c.validateMicroG(d),s=JSON.parse(app.additionalSettings);
 assert.equal(app.id,'app.revanced.android.gms');
 assert.equal(pack.apps.length,14);assert.ok(!pack.apps.some(x=>x.id===app.id));
 assert.equal(new RegExp(s.apkFilterRegEx).test('microg-6.1.4.apk'),true);
 for(const name of ['microg-6.1.4-hw.apk','microg-6.1.4-arm64.apk','other.apk','microg-6.1.4.apk.sig','microg-6.1.4-no-icon.apk'])assert.equal(new RegExp(s.apkFilterRegEx).test(name),false);
 assert.equal(new RegExp(s.versionExtractionRegEx).exec('v6.1.4')[1],'6.1.4');
 for(const mutate of [x=>x.settings={},x=>x.apps.push(x.apps[0]),x=>x.apps[0].id='com.google.android.gms',x=>x.apps[0].url='https://github.com/other/microg',x=>x.apps[0].additionalSettings='{}',x=>{let y=JSON.parse(x.apps[0].additionalSettings);y.fallbackToOlderReleases=true;x.apps[0].additionalSettings=JSON.stringify(y)}]){
  const bad=structuredClone(d);mutate(bad);assert.throws(()=>c.validateMicroG(bad));
 }
 assert.ok(!html.includes('<option value="microg">'));
 assert.ok(html.includes('id="includeMicrog"'));
 assert.ok(html.includes('obtainium://refresh'));
});
check('APK URL must belong to its exact release tag and asset name',()=>{
 const tag='youtube-morphe-v21.36.45-b20260913',name='youtube-v21.36.45-arm64-v8a.apk';
 const r={id:1,tag_name:tag,published_at:'2026-09-13T00:00:00Z',assets:[{name,state:'uploaded',size:2000000,browser_download_url:'https://github.com/govinda-rajulu/patch-factory/releases/download/'+tag+'/'+name}]};
 assert.equal(c.releaseRows([r],targets).rejected,0);
 for(const url of [r.assets[0].browser_download_url.replace('b20260913','b20260912'),r.assets[0].browser_download_url+'?redirect=other',r.assets[0].browser_download_url.replace(name,'other.apk')]){
  const bad=structuredClone(r);bad.assets[0].browser_download_url=url;assert.equal(c.releaseRows([bad],targets).rejected,1);
 }
});
check('MicroG channel retains full dev version and excludes every alternate asset',()=>{
 const data=JSON.parse(fs.readFileSync(path.join(root,'docs/obtainium-microg.json')));
 const before=JSON.stringify(data),app=c.microgConfig(data,'prerelease'),s=JSON.parse(app.additionalSettings);
 assert.equal(s.includePrereleases,true);assert.equal(s.fallbackToOlderReleases,false);
 assert.equal(new RegExp(s.versionExtractionRegEx).exec('7.2.1-dev.2')[1],'7.2.1-dev.2');
 for(const name of ['microg-6.1.4.apk','microg-7.2.1-dev.2.apk'])assert.ok(new RegExp(s.apkFilterRegEx).test(name));
 for(const name of ['microg-7.2.1-dev.2-arm64-v8a.apk','microg-7.2.1-dev.2-armeabi-v7a.apk'])assert.ok(new RegExp(s.apkFilterRegEx).test(name),name);
 for(const name of ['microg-7.2.1-dev.2-noicon.apk','microg-7.2.1-dev.2-noicon-arm64-v8a.apk','microg-7.2.1-dev.2-noicon-armeabi-v7a.apk','microg-7.2.1-dev.2.apk.sig','microg-7.2.1-beta.apk'])assert.ok(!new RegExp(s.apkFilterRegEx).test(name),name);
 assert.equal(JSON.stringify(data),before);assert.throws(()=>c.microgConfig(data,'whatever'));
 const stable=JSON.parse(c.microgConfig(data,'stable').additionalSettings);
 assert.equal(stable.includePrereleases,false);assert.ok(!new RegExp(stable.apkFilterRegEx).test('microg-7.2.1-dev.2.apk'));
});
check('upstream downloads bind exact version, tag, universal asset and channel',()=>{
 const web='https://github.com/MorpheApp/MicroG-RE';
 function row(v,pre,day){const name='microg-'+v+'.apk';return {tag_name:v,prerelease:pre,draft:false,published_at:day,html_url:web+'/releases/tag/'+v,assets:[{name,state:'uploaded',size:112296635,browser_download_url:web+'/releases/download/'+v+'/'+name}]};}
 const stable=row('6.1.4',false,'2026-04-28T00:00:00Z'),dev=row('7.2.1-dev.2',true,'2026-09-17T22:24:06Z');
 assert.equal(c.microgRelease([dev,stable],'stable').version,'6.1.4');
 assert.equal(c.microgRelease([stable,dev],'prerelease').version,'7.2.1-dev.2');
 for(const mutate of [r=>r.assets.push(r.assets[0]),r=>r.assets[0].name='microg-7.2.1-dev.2-noicon.apk',r=>r.assets[0].browser_download_url+='?bad',r=>r.html_url=web+'/releases/tag/6.1.4',r=>r.assets[0].size=0]){
  const r=structuredClone(dev);mutate(r);assert.throws(()=>c.microgRelease([r,stable],'prerelease'));
 }
 assert.throws(()=>c.microgRelease([],'stable'));
});
check('unified selection permits upstream without changing fourteen build targets or IDs',()=>{
 const d=JSON.parse(fs.readFileSync(path.join(root,'docs/obtainium-microg.json')));
 const mixed=[...pack.apps,c.microgConfig(d,'prerelease')];
 assert.equal(new Set(mixed.map(a=>a.id)).size,15);
 assert.equal(c.selectApps(mixed,['app.revanced.android.gms']).length,1);
 const tc=targets.find(t=>t.id==='truecaller-combo');assert.equal(tc.label,'Truecaller');assert.equal(tc.tag_prefix,'tc-combo');
 for(const marker of ['Filter source type','Filter publication date','Sort apps'])assert.ok(source.includes(marker));
 assert.ok(html.includes('manrope-v4.504.woff2'));assert.ok(!html.includes('Truecaller (combo)'));
});
check('release summaries keep same-version rebuild and unknown history distinct',()=>{
 const top={tag:{version:'1.0'},rel:{body:'Legacy notes'}};
 assert.match(c.changeSummary(top,{tag:{version:'1.0'}})[0],/Same app version/);
 assert.match(c.changeSummary(top,{tag:{version:'0.9'}})[0],/0.9 → 1.0/);
 assert.match(c.changeSummary(top,null)[0],/No earlier comparable/);
 top.rel.body='## What changed\n- App version unchanged.\n- Applied patch names added: A.\n\n## This download\nnot a change\n<!-- PF_RELEASE_V1 AAAA -->';
 assert.equal(c.changeSummary(top,null).length,2);
 assert.equal(c.changeSummary(top,null)[1],'Applied patch names added: A.');
 assert.ok(!c.noteText(top.rel.body).includes('AAAA'));
 assert.equal(c.noteText('Useful notes\n\n[pf-release-v1]: # "QUFBQQ=="'),'Useful notes');
});
check('reader flows retain disclosure, reset and explicit unknown evidence',()=>{
 for(const id of ['importPanel','collapseImport','resetChoices'])assert.ok(html.includes('id="'+id+'"'));
 for(const marker of ['Show job results and failed steps','Read latest saved report comments','Job/run identity changed','does not build or install apps'])assert.ok(source.includes(marker)); assert.ok(!source.includes('Read release notes here'));
 assert.ok(source.includes('/attempts/'));
 assert.ok(source.includes("j.run_attempt===run.run_attempt"));
 assert.ok(source.includes("j.head_sha===run.head_sha"));
 assert.ok(!source.includes("link('Release details',top.rel.html_url)"));
 assert.ok(html.includes('About downloads, updates & status'));
});
check('job roles distinguish dependencies from app builds',()=>{
 assert.equal(c.jobRole('Resolve shadow dependencies (youtube)'),'Dependencies only');
 assert.equal(c.jobRole('build (reddit) / Patch reddit'),'App build');
 assert.equal(c.jobRole('Patch youtube'),'App build');
 assert.equal(c.jobRole('Plan'),'Build selection');
 for(const name of [null,'Patch','Patch youtube malicious','Resolve shadow dependencies ()'])assert.equal(c.jobRole(name),'Other / unknown');
});
check('mixed jobs do not turn cancelled or incomplete jobs into successes',()=>{
 const job=(name,status,conclusion)=>({name,status,conclusion});
 const d=c.jobSummary([job('Patch youtube','completed','success'),job('Patch reddit','completed','failure'),job('Patch edge','completed','cancelled'),job('Patch instagram','in_progress',null),job('Resolve shadow dependencies (youtube)','completed','success'),job('Plan','completed','success')]);
 assert.equal(d.succeeded,1);assert.equal(d.failed,1);assert.equal(d.other,2);assert.equal(d.dependencies,1);
 assert.match(d.text,/Complete job inventory: 6/);
 assert.equal(c.jobSummary([]).succeeded,0);assert.throws(()=>c.jobSummary(null));
});
check('MicroG direct control and toolbar share explicit page-only state',()=>{
 assert.ok(source.includes("channelSelect.id='microgCardChannel'"));
 assert.ok(source.includes("channelSelect.value=microgChannel"));
 assert.ok(source.includes("async function changeMicrogChannel(value)"));
 assert.ok(source.includes("microgChannel=value;$('microgChannel').value=value"));
 assert.ok(source.includes('Open Obtainium import settings'));
 assert.ok(!source.includes("'Change MicroG channel'"));
 assert.ok(source.includes('tracked apps are unchanged'));
 assert.ok(source.includes('can show the same version when stable is newest'));
});
console.log('PORTAL_CONTRACTS_PASS='+count);
