/* Patch Factory public portal. Read-only HTTPS data; no credential storage, no workflow dispatch. */
(function () {
'use strict';
const REPO='govinda-rajulu/patch-factory';
const WEB='https://github.com/'+REPO;
const API='https://api.github.com/repos/'+REPO+'/';
const RAW='https://raw.githubusercontent.com/'+REPO+'/main/';
const $=id=>document.getElementById(id);
let tab='apps',generation=0,importGeneration=0,pollTimer=null;
let targets=null,importBlob=null,customApps=[];
let appQuery='',appCategory='all';
const GROUPS=[
 ['media','Watch & listen',['youtube','primevideo','hotstar','mxplayer']],
 ['social','Social & communities',['instagram','facebook','reddit','telegram']],
 ['tools','Everyday essentials',['adguard','photos','truecaller-combo','esfile','edge','keymapper']]
];
function appGroup(id){
 return GROUPS.find(g=>g[2].includes(id))||['other','More apps',[]];
}
const cache=new Map();
function need(ok,message){if(!ok)throw new Error(message);}
function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(className)n.className=className;return n;}
function plain(v,max=500){return typeof v==='string'&&v.length<=max&&!/[-\u001f\u007f]/.test(v);}
function date(v){return typeof v==='string'&&Number.isFinite(Date.parse(v))?new Date(v):null;}
function when(v){const d=date(v);return d?d.toLocaleString(): 'Date unknown';}
function safeLink(url,kind='repo'){
 try{const u=new URL(url);if(u.protocol!=='https:'||u.hostname!=='github.com'||u.port||u.username||u.password)return null;
 const prefix='/'+REPO+'/';if(!u.pathname.startsWith(prefix))return null;
 if(kind==='download'&&!u.pathname.startsWith(prefix+'releases/download/'))return null;
 if(kind==='run'&&!new RegExp('^/'+REPO+'/actions/runs/[0-9]+(?:/job/[0-9]+)?$').test(u.pathname))return null;
 return u.href;}catch{return null;}
}
function link(text,url,kind='repo'){const safe=safeLink(url,kind);if(!safe)return el('span',text+' (link unavailable)','meta');const a=el('a',text,'button');a.href=safe;a.target='_blank';a.rel='noopener noreferrer';return a;}
async function read(url,ttl=30000){
 const u=new URL(url);need(u.origin==='https://api.github.com'&&u.pathname.startsWith('/repos/'+REPO+'/')||u.origin==='https://raw.githubusercontent.com'&&u.pathname.startsWith('/'+REPO+'/main/'),'Unsupported data source');
 const existing=cache.get(url);if(existing&&Date.now()-existing.at<ttl)return existing.data;
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),25000);
 try{const r=await fetch(url,{headers:{Accept:'application/vnd.github+json'},credentials:'omit',cache:'no-store',signal:ctrl.signal});
 if(r.status===403||r.status===429)throw new Error('GitHub denied or rate-limited this read. Try later; no token is needed here.');need(r.ok,'Data request failed (HTTP '+r.status+')');
 const text=await r.text();need(text.length<=8000000,'Response exceeds safe display limit');const data=JSON.parse(text);cache.set(url,{at:Date.now(),data});return data;
 }finally{clearTimeout(timer);}
}
async function pages(path,key=null,max=20){
 let rows=[],seen=new Set();
 for(let p=1;p<=max;p++){
  const data=await read(API+path+(path.includes('?')?'&':'?')+'per_page=100&page='+p);
  const batch=key?data[key]:data;need(Array.isArray(batch),'Invalid inventory response');
  for(const row of batch){need(row&&Number.isSafeInteger(row.id)&&!seen.has(row.id),'Duplicate or invalid inventory row');seen.add(row.id);rows.push(row);}
  if(batch.length<100){if(key&&Number.isSafeInteger(data.total_count))need(rows.length===data.total_count,'Inventory changed or is incomplete; refresh to retry');return rows;}
 }
 throw new Error('Inventory exceeded the page limit. Coverage is unknown, not empty.');
}
function parseTag(tag){
 if(typeof tag!=='string')return null;
 const m=/^([a-z0-9-]+)-v([0-9]+(?:\.[0-9]+)*)-b([0-9]{8}(?:[0-9]{26})?)$/.exec(tag);if(!m)return null;
 const b=m[3],day=b.slice(0,4)+'-'+b.slice(4,6)+'-'+b.slice(6,8),d=new Date(day+'T00:00:00Z');
 if(!Number.isFinite(d.getTime())||d.toISOString().slice(0,10)!==day)return null;
 const run=b.length===34?b.slice(8,28).replace(/^0+/,''):null,attempt=b.length===34?b.slice(28).replace(/^0+/,''):null;
 if(b.length===34&&(!run||!attempt))return null;
 return {prefix:m[1],version:m[2],day,run,attempt,build:b};
}
function validateTargets(data){
 need(Array.isArray(data)&&data.length>0&&data.length<=100,'Invalid app catalog');const ids=new Set(),prefixes=new Set();
 for(const t of data){need(t&&/^[a-z0-9-]+$/.test(t.id||'')&&typeof t.enabled==='boolean'&&!ids.has(t.id),'Invalid or duplicate target');ids.add(t.id);const prefix=t.tag_prefix||t.id;need(/^[a-z0-9-]+$/.test(prefix)&&!prefixes.has(prefix),'Invalid or duplicate release prefix');prefixes.add(prefix);need(plain(t.label||t.id),'Invalid app label');}
 return data;
}
async function getTargets(){if(!targets)targets=validateTargets(await read(RAW+'src/targets.json'));return targets;}
function validateImport(data,ts){
 need(data&&Object.keys(data).length===1&&Array.isArray(data.apps),'Import must contain apps only, no global settings');
 const enabled=ts.filter(t=>t.enabled),ids=new Set(),names=new Set(),matched=new Set();
 need(data.apps.length>0&&data.apps.length<=enabled.length,'Invalid import count');
 for(const app of data.apps){need(app&&plain(app.id,200)&&/^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$/.test(app.id)&&!ids.has(app.id),'Invalid/duplicate app package');ids.add(app.id);
 need(app.url===WEB&&plain(app.name,200)&&!names.has(app.name),'Invalid import source/name');names.add(app.name);
 const target=enabled.find(t=>(t.label||t.id)===app.name);need(target&&!matched.has(target.id),'Import app not in enabled catalog');matched.add(target.id);
 need(typeof app.additionalSettings==='string'&&app.additionalSettings.length<10000,'Invalid app filters');const settings=JSON.parse(app.additionalSettings);
 need(settings&&Object.keys(settings).every(k=>['includePrereleases','fallbackToOlderReleases','filterReleaseTitlesByRegEx','apkFilterRegEx','versionExtractionRegEx','matchGroupToUse','trackOnly','appName'].includes(k)),'Unreviewed tracking settings; use reviewed JSON import instead');
 need(settings.filterReleaseTitlesByRegEx==='^'+(target.tag_prefix||target.id)+'-v[0-9.]+-b[0-9]+$','Unexpected release filter');
 need(settings.apkFilterRegEx==='arm64-v8a[.]apk$'&&settings.fallbackToOlderReleases===true&&settings.includePrereleases===false,'Unexpected APK/release policy');
 need(!Object.keys(settings).some(k=>/token|password|secret|credential/i.test(k)),'Credentials not permitted in import');
 need(Object.keys(app).every(k=>['id','url','author','name','categories','preferredApkIndex','additionalSettings'].includes(k)),'Unsupported import field');
 }
 need(data.apps.length===enabled.length,'Full import does not cover every enabled target');
 return data.apps;
}
function selectApps(apps,ids){
 need(Array.isArray(apps)&&Array.isArray(ids)&&ids.length>0,'Select at least one app');
 need(new Set(ids).size===ids.length&&ids.every(id=>apps.some(app=>app.id===id)),'Unknown or duplicate selected app');
 const chosen=new Set(ids);
 return apps.filter(app=>chosen.has(app.id));
}
function clearImportLinks(){
 $('openImport').hidden=true;$('openImport').removeAttribute('href');
 $('downloadImport').hidden=true;$('downloadImport').removeAttribute('href');
 if(importBlob){URL.revokeObjectURL(importBlob);importBlob=null;}
}
function resetImport(){
 ++importGeneration;clearImportLinks();customApps=[];
 $('customApps').replaceChildren();$('customApps').hidden=true;
 $('importMessage').textContent='';
}
function setImportLinks(apps,pack){
 clearImportLinks();
 const uri='obtainium://apps/'+encodeURIComponent(JSON.stringify(apps));need(uri.length<100000,'Configuration link too large for this page');
 $('openImport').href=uri;$('openImport').textContent='Import / update '+apps.length+' apps in Obtainium';$('openImport').hidden=false;
 importBlob=URL.createObjectURL(new Blob([JSON.stringify({apps},null,2)+'\n'],{type:'application/json'}));
 $('downloadImport').href=importBlob;$('downloadImport').download=pack==='selected'?'obtainium-selected.json':'obtainium.json';$('downloadImport').hidden=false;
 $('importMessage').textContent='Ready: '+apps.length+' configs. Tap Open, then confirm in Obtainium. Unselected apps already tracked in Obtainium are not removed. If the link cannot open, use the JSON fallback.';
}
function updateCustom(){
 clearImportLinks();
 const ids=Array.from($('customApps').querySelectorAll('input:checked'),n=>n.value);
 if(!ids.length){$('importMessage').textContent='Select at least one app. Nothing will be imported or removed.';return;}
 try{setImportLinks(selectApps(customApps,ids),'selected');}
 catch(e){$('importMessage').textContent='Import unavailable: '+e.message;}
}
function showCustom(apps){
 customApps=apps;
 const field=$('customApps');field.hidden=false;field.append(el('legend','Choose which apps to track'));
 const controls=el('div',undefined,'actions');
 for(const [label,checked] of [['Select all',true],['Clear selection',false]]){
  const b=el('button',label);b.type='button';b.addEventListener('click',()=>{for(const input of field.querySelectorAll('input'))input.checked=checked;updateCustom();});controls.append(b);
 }
 field.append(controls);
 for(const app of apps){
  const label=el('label');label.style.cssText='display:flex;align-items:center;gap:12px;min-height:44px;padding:6px';
  const input=el('input');input.type='checkbox';input.value=app.id;input.style.cssText='width:20px;height:20px;flex:none';input.addEventListener('change',updateCustom);
  label.append(input,el('span',app.name));field.append(label);
 }
 updateCustom();
}
async function prepareImport(){
 resetImport();const token=importGeneration,pack=$('pack').value;$('prepareImport').disabled=true;
 try{need(['all','custom'].includes(pack),'Unknown app list');
 cache.delete(RAW+'docs/obtainium.json');targets=null;const [ts,data]=await Promise.all([getTargets(),read(RAW+'docs/obtainium.json',0)]);if(token!==importGeneration)return;
 const apps=validateImport(data,ts);
 if(pack==='custom')showCustom(apps);else setImportLinks(apps,pack);
 }catch(e){if(token===importGeneration)$('importMessage').textContent='Import unavailable: '+e.message;}finally{$('prepareImport').disabled=false;}
}
function releaseRows(rows,ts){
 const map=new Map(ts.map(t=>[t.tag_prefix||t.id,[]]));let rejected=0;
 for(const rel of rows){if(rel.draft||rel.prerelease)continue;const tag=parseTag(rel.tag_name);if(!tag||!map.has(tag.prefix))continue;
 const apks=Array.isArray(rel.assets)?rel.assets.filter(a=>a&&typeof a.name==='string'&&a.name.endsWith('.apk')):[];
 if(apks.length!==1){rejected++;continue;}const a=apks[0];
 if(!a.name.endsWith('-v'+tag.version+'-arm64-v8a.apk')||!safeLink(a.browser_download_url,'download')||!Number.isSafeInteger(a.size)||a.size<=1000000||a.state!=='uploaded'||!date(rel.published_at)){rejected++;continue;}
 map.get(tag.prefix).push({tag,rel,asset:a});
 }
 for(const rows of map.values())rows.sort((a,b)=>b.tag.build.localeCompare(a.tag.build)||Date.parse(b.rel.published_at)-Date.parse(a.rel.published_at));
 return {map,rejected};
}
function buildMeta(row){const t=row.tag;return 'Build '+t.day+(t.run?' · run '+t.run+' · attempt '+t.attempt:' · legacy tag');}
async function appsPanel(root){
 const [ts,rels]=await Promise.all([getTargets(),pages('releases')]);const {map,rejected}=releaseRows(rels,ts);
 root.append(el('p','Published releases only. Test APKs are in Builds, not automatic Obtainium updates.','notice'));
 if(rejected)root.append(el('p',rejected+' ambiguous or incomplete APK releases withheld; inspect All releases.','notice'));
 for(const t of ts){const article=el('article');article.dataset.target=t.id;const heading=el('div',undefined,'app-title');heading.append(el('h3',t.label||t.id));article.append(heading);
 if(!t.enabled){heading.append(el('span','Disabled','badge'));article.append(el('p','Not eligible for new builds. Existing release history is available on GitHub.','meta'));root.append(article);continue;}
 const rows=map.get(t.tag_prefix||t.id)||[];
 if(!rows.length){article.append(el('p','No matching published APK in the complete release inventory.','meta'));root.append(article);continue;}
 const top=rows[0],age=Date.now()-Date.parse(top.asset.updated_at||top.rel.published_at);
 if(Number.isFinite(age)&&age>=0&&age<3*86400000)heading.append(el('span','Recent upload','badge'));
 article.append(el('p',top.tag.version),el('p',buildMeta(top),'meta'),el('p',Math.round(top.asset.size/1048576)+' MB · published '+when(top.rel.published_at),'meta'));
 const actions=el('div',undefined,'actions');actions.append(link('Download released APK',top.asset.browser_download_url,'download'),link('Release details',top.rel.html_url));article.append(actions);
 if(top.asset.digest&&/^sha256:[a-f0-9]{64}$/.test(top.asset.digest)){const d=el('details');d.append(el('summary','APK SHA256'),el('pre',top.asset.digest.slice(7)));article.append(d);}
 if(rows.length>1){const d=el('details');d.append(el('summary',(rows.length-1)+' older releases'));for(const r of rows.slice(1)) {const p=el('p');p.append(link(r.tag.version+' · '+buildMeta(r),r.rel.html_url));d.append(p);}article.append(d);}
 root.append(article);
 }
 return 'Published inventory checked: '+rels.length+' releases. Recent upload is not version freshness.';
}
async function buildsPanel(root){
 root.append(el('p','Recent workflow runs, not a per-app guess. Open a run for target jobs and test APK artifacts (GitHub sign-in may be required).','notice'));
 const data=await read(API+'actions/runs?per_page=30');need(Array.isArray(data.workflow_runs),'Invalid workflow results');
 const runs=data.workflow_runs.filter(r=>['.github/workflows/ci.yml','.github/workflows/batch-patch.yml','.github/workflows/manual-patch.yml'].includes(r.path));
 for(const r of runs){const a=el('article');a.append(el('h3',r.display_title||r.name),el('p',(r.status==='completed'?(r.conclusion||'Unknown result'):r.status)+' · '+when(r.created_at),'meta'),el('p','Branch '+r.head_branch+' · commit '+String(r.head_sha).slice(0,8),'meta'),link('Open exact run / artifacts',r.html_url,'run'));root.append(a);}
 if(!runs.length)root.append(el('p','No app-build runs in this 30-run window. This does not mean no builds exist.'));
 return 'Showing app-build runs from the latest 30 workflows; open GitHub for older runs.';
}
const WATCH=[['agent-watch.yml','Provider Watch','provider watch:'],['community-watch.yml','Community Watch','community: index changed for apps you build'],['watch.yml','Nightly Watch','watch: repo and provider status']];
async function watchPanel(root){
 const issues=await pages('issues?state=all');
 let failedReads=0;
 for(const [workflow,label,title] of WATCH){const a=el('article');a.append(el('h3',label));root.append(a);
 try{const data=await read(API+'actions/workflows/'+workflow+'/runs?per_page=1');need(Array.isArray(data.workflow_runs),'Invalid watcher run response');const run=data.workflow_runs[0];
 if(run)a.append(el('p','Workflow: '+(run.conclusion||run.status)+' · '+when(run.created_at),'meta'),link('Exact watcher run / full artifacts',run.html_url,'run'));
 else a.append(el('p','No visible watcher runs.','meta'));
 const reports=issues.filter(x=>!x.pull_request&&typeof x.title==='string'&&(workflow==='agent-watch.yml'?x.title.startsWith(title):x.title===title)).sort((a,b)=>Date.parse(b.updated_at)-Date.parse(a.updated_at));
 const report=reports[0];if(report){a.append(link('Saved findings / comments',report.html_url),el('p','Issue updated '+when(report.updated_at)+'; may summarize an older run.','meta'));
 const d=el('details');d.append(el('summary','Latest stored issue body (literal text)'),el('pre',typeof report.body==='string'?report.body:'No stored report text'));a.append(d);
 const failures=typeof report.body==='string'&&/report mode=full fail=1\b/.test(report.body);if(failures)a.append(el('p','Stored report declares fail=1. A green workflow is not a healthy report.','notice'));
 }else a.append(el('p','No saved issue found. Inspect run logs; absent findings are not an all-clear.','meta'));
 a.append(el('p','Coverage: legacy / partial. This page does not infer a verified delta from issue text or consume expiring JSON as durable baseline state.','meta'));
 }catch(e){failedReads++;a.append(el('p',e.message,'notice'));}
 }
 return failedReads?'Watcher inventory incomplete: '+failedReads+' workflow read(s) failed. No all-clear.':'Watcher runs and saved issues loaded. Findings coverage remains explicitly partial.';
}
async function render(){
 const own=++generation;clearTimeout(pollTimer);$('status').textContent='Checking '+tab+'...';$('refresh').disabled=true;
 const root=document.createDocumentFragment();
 try{const message=await ({apps:appsPanel,builds:buildsPanel,watch:watchPanel}[tab])(root);if(own!==generation)return;organizePanel(root,tab);$('panel').replaceChildren(root);$('status').textContent=message;filterApps();}
 catch(e){if(own!==generation)return;$('panel').replaceChildren(el('p',e.message,'notice'));$('status').textContent='Data unavailable. No success or empty coverage inferred.';}
 finally{if(own===generation){$('refresh').disabled=false;if(!document.hidden)pollTimer=setTimeout(()=>{if(!document.hidden)render();},120000);}}
}
function organizePanel(root,activeTab){
 $('appTools').hidden=activeTab!=='apps';
 const articles=Array.from(root.querySelectorAll('article'));
 if(activeTab!=='apps'){
  for(const article of articles){
   article.classList.add('result-card');
   const disclosure=el('details'),heading=article.querySelector('h3'),summary=el('summary');
   if(heading)summary.append(heading);
   const status=article.querySelector('p.meta');
   if(status)summary.append(status);
   disclosure.append(summary);
   const content=el('div',undefined,'result-content');
   while(article.firstChild)content.append(article.firstChild);
   disclosure.append(content);article.append(disclosure);
  }
  return;
 }
 const groups=new Map();
 for(const article of articles){
  const id=article.dataset.target;
  if(!id)continue;
  article.classList.add('app-card');
  article.dataset.category=appGroup(id)[0];
  article.dataset.search=(article.querySelector('h3')?.textContent+' '+id).toLowerCase();
  const heading=article.querySelector('.app-title');
  if(heading){
   const monogram=el('span',article.querySelector('h3')?.textContent.trim().slice(0,1)||'A','app-monogram');
   monogram.setAttribute('aria-hidden','true');heading.prepend(monogram);
  }
  const version=Array.from(article.children).find(n=>n.tagName==='P'&&!n.classList.contains('meta'));
  if(version)version.classList.add('app-version');
  // Keep the main download action visible; detailed provenance/history goes under one disclosure.
  const extra=Array.from(article.children).filter(n=>n.matches('p.meta,details'));
  if(extra.length){
   const details=el('details',undefined,'app-details');details.append(el('summary','Build details & older versions'));
   for(const node of extra)details.append(node);
   article.append(details);
  }
  const group=appGroup(id);
  if(!groups.has(group[0])){
   const box=el('details',undefined,'app-group');box.open=true;box.dataset.group=group[0];
   const summary=el('summary');summary.append(el('span',group[1]),el('span','','group-count'));
   const grid=el('div',undefined,'app-grid');box.append(summary,grid);groups.set(group[0],box);
  }
  groups.get(group[0]).querySelector('.app-grid').append(article);
 }
 for(const [id] of [...GROUPS,['other']])if(groups.has(id))root.append(groups.get(id));
 const empty=el('p','No matching apps. Try a different name or category.','notice');empty.id='noApps';empty.hidden=true;root.append(empty);
}
function filterApps(){
 if(tab!=='apps')return;
 let shown=0;
 for(const card of $('panel').querySelectorAll('.app-card')){
  card.hidden=!(card.dataset.search.includes(appQuery)&&(appCategory==='all'||card.dataset.category===appCategory));
  if(!card.hidden)shown++;
 }
 for(const group of $('panel').querySelectorAll('.app-group')){
  const count=Array.from(group.querySelectorAll('.app-card')).filter(c=>!c.hidden).length;
  group.hidden=count===0;group.querySelector('.group-count').textContent=count+' app'+(count===1?'':'s');
  if(appQuery||appCategory!=='all')group.open=true;
 }
 if($('noApps'))$('noApps').hidden=shown!==0;
 $('appCount').textContent=shown+' app'+(shown===1?'':'s');
}
// Expose pure contracts only for tests; no credentials, write endpoints or remote-script execution.
window.PFPortal={parseTag,validateImport,validateTargets,releaseRows,safeLink,selectApps,appGroup};
const tools=el('div',undefined,'catalog-tools');tools.id='appTools';
const search=el('input');search.id='appSearch';search.type='search';search.placeholder='Find an app';search.setAttribute('aria-label','Search apps');
search.addEventListener('input',()=>{appQuery=search.value.trim().toLowerCase();filterApps();});
const categories=el('select');categories.id='appCategory';categories.setAttribute('aria-label','Filter app category');
for(const [value,label] of [['all','All categories'],...GROUPS.map(g=>[g[0],g[1]]),['other','More apps']]){
 const option=el('option',label);option.value=value;categories.append(option);
}
categories.addEventListener('change',()=>{appCategory=categories.value;filterApps();});
const count=el('span','','meta');count.id='appCount';count.setAttribute('aria-live','polite');
tools.append(search,categories,count);$('panel').before(tools);
// The static page lists the same two public choices; no personal presets.
const customField=el('fieldset');customField.id='customApps';customField.hidden=true;customField.style.cssText='margin:16px 0;border:1px solid var(--rule);border-radius:8px;min-width:0';
$('importMessage').before(customField);
$('prepareImport').addEventListener('click',prepareImport);$('pack').addEventListener('change',resetImport);
$('refresh').addEventListener('click',()=>{cache.clear();targets=null;render();});
for(const b of document.querySelectorAll('[data-tab]'))b.addEventListener('click',()=>{tab=b.dataset.tab;for(const x of document.querySelectorAll('[data-tab]'))x.setAttribute('aria-selected',String(x===b));render();});
document.addEventListener('visibilitychange',()=>{clearTimeout(pollTimer);if(!document.hidden)render();});
render();
})();
