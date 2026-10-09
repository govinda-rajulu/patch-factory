/* Patch Factory public portal. Read-only HTTPS data; no credential storage, no workflow dispatch. */
(function () {
'use strict';
const REPO='govinda-rajulu/patch-factory';
const WEB='https://github.com/'+REPO;
const API='https://api.github.com/repos/'+REPO+'/';
const RAW='https://raw.githubusercontent.com/'+REPO+'/main/';
const MICROG_WEB='https://github.com/MorpheApp/MicroG-RE';
const MICROG_API='https://api.github.com/repos/MorpheApp/MicroG-RE/releases';
const OBTAINIUM_WEB='https://github.com/ImranR98/Obtainium';
const $=id=>document.getElementById(id);
let tab='apps',generation=0,importGeneration=0,pollTimer=null;
let targets=null,importBlob=null,customApps=[];
let appQuery='',appCategory='all',appType='all',appAge='all',appSort='name';
let microgChannel='stable',microgArch='universal',microgIcon='icon';
// Local brand tiles only (docs/assets/logos, provenance in docs/review/ICON-PROVENANCE.md); others keep the monogram.
const LOGOS=new Set(['adguard','amazonmusic','edge','facebook','hotstar','instagram','keymapper','linkedin','mxplayer','photos','primevideo','reddit','telegram','truecaller-combo','youtube','ytmusic']);
const GROUPS=[
 ['media','Watch & listen',['youtube','ytmusic','primevideo','hotstar','mxplayer','amazonmusic']],
 ['social','Social & communities',['instagram','facebook','reddit','telegram','linkedin']],
 ['tools','Everyday essentials',['adguard','photos','truecaller-combo','esfile','edge','keymapper']]
];
function appGroup(id){
 if(id==='microg')return ['tools','Everyday essentials',[]];
 return GROUPS.find(g=>g[2].includes(id))||['other','More apps',[]];
}
const cache=new Map();
function need(ok,message){if(!ok)throw new Error(message);}
function el(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(className)n.className=className;return n;}
function plain(v,max=500){return typeof v==='string'&&v.length>0&&v.length<=max&&!/[\u0000-\u001f\u007f]/.test(v);}
function date(v){return typeof v==='string'&&Number.isFinite(Date.parse(v))?new Date(v):null;}
function ago(v){const t=Date.parse(v);if(!Number.isFinite(t))return 'time unknown';const m=Math.round((Date.now()-t)/60000);if(m<1)return 'just now';if(m<60)return m+' min ago';const h=Math.round(m/60);if(h<48)return h+' h ago';return Math.round(h/24)+' days ago';}
function when(v){const d=date(v);return d?d.toLocaleString(): 'Date unknown';}
function safeLink(url,kind='repo'){
 try{const u=new URL(url);if(u.protocol!=='https:'||u.hostname!=='github.com'||u.port||u.username||u.password)return null;
 if(kind==='upstream')return u.href===MICROG_WEB+'/releases'?u.href:null;
 const prefix='/'+REPO+'/';if(!u.pathname.startsWith(prefix))return null;
 if(kind==='download'&&!u.pathname.startsWith(prefix+'releases/download/'))return null;
 if(kind==='run'&&!new RegExp('^/'+REPO+'/actions/runs/[0-9]+(?:/job/[0-9]+)?$').test(u.pathname))return null;
 return u.href;}catch{return null;}
}
function link(text,url,kind='repo'){const safe=safeLink(url,kind);if(!safe)return el('span',text+' (link unavailable)','meta');const a=el('a',text,'button');a.href=safe;a.target='_blank';a.rel='noopener noreferrer';return a;}
async function read(url,ttl=30000){
 const u=new URL(url);need(!u.username&&!u.password&&!u.port&&(
 u.origin==='https://api.github.com'&&u.pathname.startsWith('/repos/'+REPO+'/')||
 u.origin==='https://raw.githubusercontent.com'&&u.pathname.startsWith('/'+REPO+'/main/')||
 u.origin==='https://raw.githubusercontent.com'&&u.pathname==='/'+REPO+'/status/status.json'||
 u.origin==='https://api.github.com'&&u.pathname==='/repos/MorpheApp/MicroG-RE/releases'),'Unsupported data source');
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
 const packageId=target.installed_package||target.package;
 need(app.id===packageId,'Import package does not match this target');
 need(typeof app.additionalSettings==='string'&&app.additionalSettings.length<10000,'Invalid app filters');const settings=JSON.parse(app.additionalSettings);
 need(settings&&Object.keys(settings).every(k=>['includePrereleases','fallbackToOlderReleases','filterReleaseTitlesByRegEx','apkFilterRegEx','versionExtractionRegEx','matchGroupToUse','trackOnly','appName'].includes(k)),'Unreviewed tracking settings; use reviewed JSON import instead');
 need(settings.filterReleaseTitlesByRegEx==='^'+(target.tag_prefix||target.id)+'-v[0-9.]+-b[0-9]+$','Unexpected release filter');
 need(settings.apkFilterRegEx==='arm64-v8a[.]apk$'&&settings.fallbackToOlderReleases===true&&settings.includePrereleases===false,'Unexpected APK/release policy');
 need(settings.versionExtractionRegEx==='-v([0-9.]+)-b[0-9]+$'&&settings.matchGroupToUse==='1'&&settings.trackOnly===false&&settings.appName===app.name,'Unexpected version/import policy');
 need(Object.keys(settings).length===8&&app.preferredApkIndex===0&&app.author==='govinda-rajulu'&&JSON.stringify(app.categories)==='["patch-factory"]','Unexpected import identity/settings');
 need(!Object.keys(settings).some(k=>/token|password|secret|credential/i.test(k)),'Credentials not permitted in import');
 need(Object.keys(app).every(k=>['id','url','author','name','categories','preferredApkIndex','additionalSettings'].includes(k)),'Unsupported import field');
 }
 need(data.apps.length===enabled.length,'Full import does not cover every enabled target');
 return data.apps;
}
function validateMicroG(data){
 need(data&&Object.keys(data).length===1&&Array.isArray(data.apps)&&data.apps.length===1,'Expected one optional MicroG companion');
 const app=data.apps[0];
 need(app&&Object.keys(app).length===7&&Object.keys(app).every(k=>['id','url','author','name','categories','preferredApkIndex','additionalSettings'].includes(k)),'Unsupported companion fields');
 need(app.id==='app.revanced.android.gms'&&app.url==='https://github.com/MorpheApp/MicroG-RE'&&app.author==='MorpheApp'&&app.name==='Morphe MicroG RE'&&app.preferredApkIndex===0&&JSON.stringify(app.categories)==='["morphe-companion"]','Unexpected companion identity');
 need(typeof app.additionalSettings==='string'&&app.additionalSettings.length<10000,'Invalid companion settings');
 const s=JSON.parse(app.additionalSettings),expected={includePrereleases:false,fallbackToOlderReleases:false,filterReleaseTitlesByRegEx:'^v?[0-9]+([.][0-9]+)*$',apkFilterRegEx:'^microg-[0-9]+([.][0-9]+)*[.]apk$',versionExtractionRegEx:'^v?([0-9]+(?:[.][0-9]+)*)$',matchGroupToUse:'1',autoApkFilterByArch:false,trackOnly:false,appName:'Morphe MicroG RE'};
 need(s&&Object.keys(s).length===Object.keys(expected).length&&Object.entries(expected).every(([k,v])=>s[k]===v),'Unreviewed companion filters/settings');
 return data.apps;
}
function validateObtainium(data){
 need(data&&Object.keys(data).length===1&&Array.isArray(data.apps)&&data.apps.length===1,'Expected one optional Obtainium companion');
 const app=data.apps[0];
 need(app&&Object.keys(app).length===7&&Object.keys(app).every(k=>['id','url','author','name','categories','preferredApkIndex','additionalSettings'].includes(k)),'Unsupported companion fields');
 need(app.id==='dev.imranr.obtainium'&&app.url===OBTAINIUM_WEB&&app.author==='ImranR98'&&app.name==='Obtainium'&&app.preferredApkIndex===0&&JSON.stringify(app.categories)==='["obtainium-companion"]','Unexpected Obtainium identity');
 need(typeof app.additionalSettings==='string'&&app.additionalSettings.length<10000,'Invalid companion settings');
 const s=JSON.parse(app.additionalSettings),expected={includePrereleases:false,fallbackToOlderReleases:true,verifyLatestTag:true,trackOnly:false,versionDetection:true,apkFilterRegEx:'fdroid',invertAPKFilter:true,autoApkFilterByArch:true,appName:'Obtainium'};
 need(s&&Object.keys(s).length===Object.keys(expected).length&&Object.entries(expected).every(([k,v])=>s[k]===v),'Unreviewed Obtainium filters/settings');
 return data.apps;
}
function selectApps(apps,ids){
 need(Array.isArray(apps)&&Array.isArray(ids)&&ids.length>0,'Select at least one app');
 need(new Set(ids).size===ids.length&&ids.every(id=>apps.some(app=>app.id===id)),'Unknown or duplicate selected app');
 const chosen=new Set(ids);
 return apps.filter(app=>chosen.has(app.id));
}
// MicroG RE ships six files per release (W4, owner ask 8 Oct 2026): with or without a launcher
// icon, for ARM64, ARMv7 or every CPU. Names: microg-V.apk, microg-V-noicon.apk,
// microg-V-icon-ARCH.apk, microg-V-noicon-ARCH.apk (before 7.2: microg-V-ARCH.apk).
const MICROG_ICONS=[['noicon','No icon','hidden from the launcher; open it from Android Settings → Apps'],['icon','With icon','shows in the app drawer']];
const MICROG_ARCHES=[['arm64-v8a','ARM64','most phones'],['armeabi-v7a','ARMv7','older 32-bit phones'],['universal','Universal','any phone, biggest file']];
function microgName(version,icon,arch){
 need(['icon','noicon'].includes(icon),'Unknown MicroG icon choice');
 need(['universal','arm64-v8a','armeabi-v7a'].includes(arch),'Unknown MicroG architecture');
 return 'microg-'+version+(arch==='universal'?(icon==='noicon'?'-noicon':''):'-'+icon+'-'+arch)+'.apk';
}
function microgConfig(data,channel,arch='auto',icon='icon'){
 need(['stable','prerelease'].includes(channel),'Unknown MicroG channel');
 need(['auto','universal','arm64-v8a','armeabi-v7a'].includes(arch),'Unknown MicroG architecture');
 need(['icon','noicon'].includes(icon),'Unknown MicroG icon choice');
 const app=JSON.parse(JSON.stringify(validateMicroG(data)[0])),s=JSON.parse(app.additionalSettings);
 const version=channel==='stable'?'[0-9]+([.][0-9]+)*':'[0-9]+([.][0-9]+)*(-dev[.][0-9]+)?';
 if(channel==='prerelease'){
  s.includePrereleases=true;
  s.filterReleaseTitlesByRegEx='^v?[0-9]+([.][0-9]+)*(-dev[.][0-9]+)?$';
  s.versionExtractionRegEx='^v?([0-9]+(?:[.][0-9]+)*(?:-dev[.][0-9]+)?)$';
 }
 const cpu=arch==='auto'?'(?:arm64-v8a|armeabi-v7a)':arch;
 s.apkFilterRegEx='^microg-'+version+(arch==='universal'?(icon==='noicon'?'-noicon':''):(icon==='noicon'?'-noicon-':'(?:-icon)?-')+cpu)+'[.]apk$';
 s.autoApkFilterByArch=arch==='auto';
 app.additionalSettings=JSON.stringify(s);
 return app;
}
function microgLatest(rows,channel){
 need(['stable','prerelease'].includes(channel),'Unknown upstream channel');
 need(Array.isArray(rows)&&rows.length<=100,'Invalid upstream release inventory');
 const candidates=rows.filter(r=>r&&!r.draft&&(channel==='prerelease'?r.prerelease===true:r.prerelease===false));
 candidates.sort((a,b)=>(Date.parse(b.published_at)||0)-(Date.parse(a.published_at)||0));
 need(candidates.length>0,'No '+(channel==='stable'?'stable':'pre-release')+' MicroG RE release in the newest 100');
 const r=candidates[0],tag=r.tag_name;
 const pattern=channel==='stable'?/^v?[0-9]+(?:[.][0-9]+)*$/:/^v?[0-9]+(?:[.][0-9]+)*-dev[.][0-9]+$/;
 need(typeof tag==='string'&&pattern.test(tag)&&date(r.published_at),'Unsupported upstream release identity; inspect upstream instead');
 need(r.html_url===MICROG_WEB+'/releases/tag/'+encodeURIComponent(tag),'Upstream release URL mismatch');
 return {rel:r,version:tag.replace(/^v/,'')};
}
function microgRelease(rows,channel,arch='universal',icon='icon'){
 const {rel,version}=microgLatest(rows,channel),name=microgName(version,icon,arch==='auto'?'universal':arch);
 const assets=Array.isArray(rel.assets)?rel.assets.filter(a=>a&&a.name===name):[];
 need(assets.length===1,name+' missing or ambiguous upstream; no variant fallback');
 const a=assets[0];
 need(a.state==='uploaded'&&Number.isSafeInteger(a.size)&&a.size>1000000&&a.browser_download_url===MICROG_WEB+'/releases/download/'+encodeURIComponent(rel.tag_name)+'/'+encodeURIComponent(name),'Upstream APK identity mismatch');
 return {rel,asset:a,version};
}
function mb(bytes){return Math.round(bytes/1048576)+' MB';}
function microgChannelBlock(rows,channel){
 const box=el('section',undefined,'microg-channel');
 let latest;try{latest=microgLatest(rows,channel);}catch(e){box.append(el('h4',channel==='stable'?'Stable':'Pre-release'),el('p',e.message,'meta'));return box;}
 const head=el('h4',(channel==='stable'?'Stable ':'Pre-release ')+latest.version);head.append(el('span',' · '+ago(latest.rel.published_at),'meta'));box.append(head);
 const grid=el('div',undefined,'variant-grid'),sums=[];
 grid.append(el('span',''));for(const [,label,hint] of MICROG_ICONS){const h=el('span',label,'variant-head');h.title=hint;grid.append(h);}
 for(const [arch,label,hint] of MICROG_ARCHES){
  const rowHead=el('span',undefined,'variant-row');rowHead.append(el('strong',label),el('small',hint));grid.append(rowHead);
  for(const [icon] of MICROG_ICONS){
   try{const {asset}=microgRelease(rows,channel,arch,icon);const a=el('a','Download · '+mb(asset.size),'button');a.href=asset.browser_download_url;a.target='_blank';a.rel='noopener noreferrer';a.title=asset.name;grid.append(a);
    if(/^sha256:[a-f0-9]{64}$/.test(asset.digest||''))sums.push(asset.name+'  '+asset.digest.slice(7));}
   catch(e){grid.append(el('span','Not in this release','meta'));}
  }
 }
 box.append(grid);
 const d=el('details');d.append(el('summary','SHA-256 checksums'),el('pre',sums.join('\n')||'Not published for this release.'));box.append(d);
 return box;
}
async function microgCard(root){
 const article=el('article');article.dataset.target='microg';article.dataset.type='upstream';
 const heading=el('div',undefined,'app-title');heading.append(el('h3','MicroG RE'),el('span','Upstream','badge'));article.append(heading);
 article.append(el('p','Needed by YouTube, YouTube Music and Google Photos. Straight from MorpheApp, not rebuilt here.','meta release-facts'));
 article.append(el('p','No icon or With icon: same app, the icon only changes whether it shows in your app drawer. ARM64 fits most phones.','meta release-facts'));
 try{
  const rows=await read(MICROG_API+'?per_page=100');
  const stable=microgChannelBlock(rows,'stable');article.append(stable);
  try{article.dataset.published=microgLatest(rows,'stable').rel.published_at;}catch(e){}
  let newer=false;try{newer=Date.parse(microgLatest(rows,'prerelease').rel.published_at)>Date.parse(microgLatest(rows,'stable').rel.published_at);}catch(e){}
  if(newer)article.append(microgChannelBlock(rows,'prerelease'));
  const notes=microgLatest(rows,newer?'prerelease':'stable');
  releaseNotes(article,notes.rel.body,['Release notes from MorpheApp.']);
  const more=el('p',undefined,'meta');more.append(link('All MicroG RE releases',MICROG_WEB+'/releases','upstream'));article.append(more);
 }catch(e){article.append(el('p','MicroG RE releases unavailable: '+e.message,'notice'));}
 const details=el('details');details.append(el('summary','Installing and updating'),
 el('p','Install MicroG RE before the Google apps. Updating keeps its data. Do not uninstall it to switch between icon and no-icon: both are the same app, install the other file over it.'),
 el('p','Pre-releases are tested less. The page shows one only when it is newer than the stable release; Stable + dev prereleases can show the same version when stable is newest.'));
 article.append(details);root.append(article);
 const channelButton=el('button','Open Obtainium import settings');channelButton.type='button';
 channelButton.addEventListener('click',()=>{$('importPanel').open=true;$('microgIcon').focus();$('importPanel').scrollIntoView({block:'center'});});
 article.append(channelButton);
}
async function changeMicrogChannel(value){
 need(['stable','prerelease'].includes(value),'Unknown MicroG channel');
 microgChannel=value;$('microgChannel').value=value;
 resetImport();$('prepareImport').disabled=false;
 $('importMessage').textContent='MicroG choice changed. Prepare the import again; tracked apps are unchanged until you confirm in Obtainium.';
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
 $('downloadImport').href=importBlob;$('downloadImport').download=pack==='selected'?'obtainium-selected.json':apps.length===1&&apps[0].id==='app.revanced.android.gms'?'obtainium-microg.json':apps.length===1&&apps[0].id==='dev.imranr.obtainium'?'obtainium-self.json':'obtainium.json';$('downloadImport').hidden=false;
 $('importMessage').textContent='Ready: '+apps.length+' configs. Tap Open, then confirm in Obtainium. Unselected apps already tracked in Obtainium are not removed. If the link cannot open, use the JSON fallback.';
 if(apps.some(app=>app.id==='app.revanced.android.gms'))$('importMessage').textContent+=' Includes MicroG RE ('+(microgIcon==='noicon'?'no icon':'with icon')+', '+({auto:'CPU picked by Obtainium',universal:'universal','arm64-v8a':'ARM64','armeabi-v7a':'ARMv7'})[microgArch]+', '+(microgChannel==='stable'?'stable only':'pre-releases allowed')+'). Existing tracked settings may change; installed signer compatibility is unverified.';
 if(apps.some(app=>app.id==='dev.imranr.obtainium'))$('importMessage').textContent+=' Includes standard Obtainium tracking. F-Droid installs are not replaced or migrated.';
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
 const wantMicrog=pack==='custom'||$('includeMicrog').checked;
 cache.delete(RAW+'docs/obtainium.json');targets=null;const wantSelf=$('includeObtainium').checked;const [ts,data,companion,selfPack]=await Promise.all([getTargets(),read(RAW+'docs/obtainium.json',0),wantMicrog?read(RAW+'docs/obtainium-microg.json',0):Promise.resolve(null),wantSelf?read(RAW+'docs/obtainium-self.json',0):Promise.resolve(null)]);if(token!==importGeneration)return;
 const apps=validateImport(data,ts);
 const microg=wantMicrog?microgConfig(companion,microgChannel,microgArch,microgIcon):null;const self=wantSelf?validateObtainium(selfPack)[0]:null;
 const extras=[microg,self].filter(Boolean);if(pack==='custom')showCustom([...apps,...extras]);else setImportLinks([...apps,...extras],pack);
 }catch(e){if(token===importGeneration)$('importMessage').textContent='Import unavailable: '+e.message;}finally{if(token===importGeneration)$('prepareImport').disabled=false;}
}
function releaseRows(rows,ts){
 const map=new Map(ts.map(t=>[t.tag_prefix||t.id,[]]));let rejected=0;
 for(const rel of rows){if(rel.draft||rel.prerelease)continue;const tag=parseTag(rel.tag_name);if(!tag||!map.has(tag.prefix))continue;
 const apks=Array.isArray(rel.assets)?rel.assets.filter(a=>a&&typeof a.name==='string'&&a.name.endsWith('.apk')):[];
 if(apks.length!==1){rejected++;continue;}const a=apks[0];
 if(!a.name.endsWith('-v'+tag.version+'-arm64-v8a.apk')||!safeLink(a.browser_download_url,'download')||!Number.isSafeInteger(a.size)||a.size<=1000000||a.state!=='uploaded'||!date(rel.published_at)){rejected++;continue;}
 if(a.browser_download_url!==WEB+'/releases/download/'+encodeURIComponent(rel.tag_name)+'/'+encodeURIComponent(a.name)){rejected++;continue;}
 map.get(tag.prefix).push({tag,rel,asset:a});
 }
 for(const rows of map.values())rows.sort((a,b)=>b.tag.build.localeCompare(a.tag.build)||Date.parse(b.rel.published_at)-Date.parse(a.rel.published_at));
 return {map,rejected};
}
function buildMeta(row){const t=row.tag;return 'Build '+t.day+(t.run?' · run '+t.run+' · attempt '+t.attempt:' · legacy tag');}
function noteText(body){
 if(typeof body!=='string')return '';
 return body.replace(/<!--[\s\S]*?-->/g,'').replace(/^\[pf-release-v1\]: # "[A-Za-z0-9+/=]+"[ \t]*$/gm,'').trim();
}
function readable(text){
 return text.replace(/\\([\\`*_[\]|])/g,'$1').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
}
function inline(parent,text){
 // Small literal-safe Markdown subset. Never interpret HTML or load images/scripts.
 const pattern=/\[([^\]\n]+)\]\((https:\/\/[^\s)]+)\)|`([^`\n]+)`|\*\*([^*\n]+)\*\*/g;
 let start=0;
 for(const match of text.matchAll(pattern)){
  parent.append(document.createTextNode(readable(text.slice(start,match.index))));
  if(match[1]){
   let url=safeLink(match[2]);
   try{const u=new URL(match[2]);if(!u.username&&!u.password&&!u.port&&u.origin==='https://github.com'&&u.pathname.startsWith('/MorpheApp/MicroG-RE/'))url=u.href;}catch{}
   if(url){const a=el('a',readable(match[1]));a.href=url;a.target='_blank';a.rel='noopener noreferrer';parent.append(a);}
   else parent.append(document.createTextNode(readable(match[1])));
  }else parent.append(el(match[3]?'code':'strong',readable(match[3]||match[4])));
  start=match.index+match[0].length;
 }
 parent.append(document.createTextNode(readable(text.slice(start))));
}
function reportIdentity(workflow,issue){
 const title=typeof issue.title==='string'?issue.title:'',body=typeof issue.body==='string'?issue.body:'';
 if(workflow==='agent-watch.yml'){
  const m=/^provider watch: (?:OK|CHANGED|PARTIAL|FAILED) run ([1-9][0-9]*)\/([1-9][0-9]*)$/.exec(title);
  const url=/https:\/\/github\.com\/govinda-rajulu\/patch-factory\/actions\/runs\/([1-9][0-9]*)\/attempts\/([1-9][0-9]*)/.exec(body);
  if(m&&url&&m[1]===url[1]&&m[2]===url[2])return {run_id:m[1],attempt:m[2]};
  return null;
 }
 if(workflow==='community-watch.yml'){
  const key=/<!-- pf-community:([0-9a-f]{64}) -->/.exec(body);
  if(title==='community: index changed for apps you build'&&key)return {report_key:key[1]};
  return null;
 }
 return null;
}
function reportBinding(workflow,run,issue,state){
 const identity=reportIdentity(workflow,issue);
 if(!identity)return {state:'unidentified',identity:null};
 if(identity.report_key){
  if(!state||state.report_key!==identity.report_key)return {state:'stale-receipt',identity};
  if(String(issue.number)!==String(state.issue))return {state:'issue-mismatch',identity};
  if(run&&String(run.id)===String(state.run_id)&&String(run.run_attempt)===String(state.attempt))return {state:'joined',identity};
  return {state:'different-run',identity};
 }
 if(!run)return {state:'no-run',identity};
 if(String(run.id)===identity.run_id&&String(run.run_attempt)===identity.attempt)return {state:'joined',identity};
 return {state:'different-run',identity};
}
function checkCompleteness(body,rows){
 const key=/<!-- pf-community:([0-9a-f]{64}) -->/.exec(typeof body==='string'?body:'');
 const expected=/Expected report: ([1-9][0-9]*) numbered comment/.exec(typeof body==='string'?body:'');
 if(!key||!expected)return {known:false};
 const parts=[];
 for(let i=1;i<=Number(expected[1]);i++){
  const tag='<!-- pf-community:'+key[1]+':'+i+' -->';
  const found=rows.filter(c=>c&&typeof c.body==='string'&&c.body.includes(tag));
  const c=found.length===1?found[0]:null;
  const ok=!!(c&&c.user&&c.user.login==='github-actions[bot]'&&c.user.type==='Bot'&&c.created_at===c.updated_at);
  parts.push({part:i,ok});
 }
 const missing=parts.filter(p=>!p.ok).map(p=>p.part);
 return {known:true,expected:Number(expected[1]),complete:missing.length===0,missing};
}
function markdown(body,budget){
 const maxChars=budget&&budget.chars||24000,maxLines=budget&&budget.lines||400;
 const box=el('div',undefined,'release-copy'),text=noteText(body),limited=text.slice(0,maxChars);
 if(!text){box.append(el('p','No release notes were recorded. Changes are unknown, not “nothing changed”.','meta'));return box;}
 let list=null,table=null,code=null;
 for(const line of limited.split('\n').slice(0,maxLines)){
  if(line.startsWith('```')){if(code){code=null;}else{code=el('pre','');box.append(code);}continue;}
  if(code){code.textContent+=line+'\n';continue;}
  if(/^\s*\|/.test(line)){
   if(/^[\s|:\-]+$/.test(line))continue;
   if(!table){const wrap=el('div',undefined,'table-scroll');table=el('table');wrap.append(table);box.append(wrap);}
   const row=el('tr');for(const cell of line.trim().replace(/^\||\|$/g,'').split(/(?<!\\)\|/)){const td=el(table.children.length?'td':'th');inline(td,cell.trim());row.append(td);}table.append(row);list=null;continue;
  }
  table=null;
  if(/^\s*[-*]\s+/.test(line)){if(!list){list=el('ul');box.append(list);}const item=el('li');inline(item,line.replace(/^\s*[-*]\s+/,''));list.append(item);continue;}
  list=null;if(!line.trim())continue;
  const heading=/^#{1,6}\s+/.test(line),node=el(heading?'h4':'p');inline(node,line.replace(/^#{1,6}\s+/,''));box.append(node);
 }
 if(text.length>maxChars||limited.split('\n').length>maxLines)box.append(el('p','Showing '+Math.min(text.length,maxChars).toLocaleString()+' of '+text.length.toLocaleString()+' characters and up to '+maxLines+' lines. The full report is in the GitHub issue; this view is shortened.','notice'));
 return box;
}
function changeSummary(top,previous){
 const body=noteText(top.rel.body),section=/^## What changed[ \t]*\n([\s\S]*?)(?=^## |$(?![\s\S]))/m.exec(body);
 if(section){const rows=section[1].split('\n').filter(x=>x.startsWith('- ')).slice(0,3);if(rows.length)return rows.map(x=>readable(x.slice(2)));}
 if(previous)return [previous.tag.version===top.tag.version?'Same app version, another build.':'App version '+previous.tag.version+' → '+top.tag.version+'.','Patch-by-patch changes were not recorded in comparable release metadata.'];
 return ['No earlier comparable release in this inventory. Read the publisher’s notes below.'];
}
function releaseNotes(article,body,summary){
 const overview=el('div',undefined,'change-preview');overview.append(el('h4','What changed'));
 for(const line of summary.slice(0,2))overview.append(el('p',line.length>160?line.slice(0,157)+'…':line));
 article.append(overview);
}
async function appsPanel(root){
 const [ts,releaseResult]=await Promise.all([getTargets(),pages('releases').then(rows=>({rows})).catch(error=>({error}))]);
 const {map,rejected}=releaseRows(releaseResult.rows||[],ts);
 if(releaseResult.error)root.append(el('p','Patched releases unavailable: '+releaseResult.error.message+' Catalog and upstream companion remain usable.','notice'));
 if(rejected)root.append(el('p',rejected+' ambiguous or incomplete APK releases withheld; inspect All releases.','notice'));
 for(const t of ts){const article=el('article');article.dataset.target=t.id;article.dataset.type='patched';const heading=el('div',undefined,'app-title');heading.append(el('h3',t.label||t.id));article.append(heading);
 if(!t.enabled){heading.append(el('span','Disabled','badge'));article.append(el('p','Not eligible for new builds. Existing release history is available on GitHub.','meta'));root.append(article);continue;}
 const rows=map.get(t.tag_prefix||t.id)||[];
 if(!rows.length){article.append(el('p',releaseResult.error?'Release availability unknown.':'No matching published APK in the complete release inventory.','meta'));root.append(article);continue;}
 const top=rows[0],age=Date.now()-Date.parse(top.asset.updated_at||top.rel.published_at);
 article.dataset.published=top.rel.published_at;
 if(Number.isFinite(age)&&age>=0&&age<3*86400000)heading.append(el('span','Recent upload','badge'));
 article.append(el('p',top.tag.version),el('p',buildMeta(top),'meta'),el('p',Math.round(top.asset.size/1048576)+' MB · published '+when(top.rel.published_at),'meta release-facts'));
 const actions=el('div',undefined,'actions');actions.append(link('Download released APK',top.asset.browser_download_url,'download'));article.append(actions);
 releaseNotes(article,top.rel.body,changeSummary(top,rows[1]));
 const original=el('p',undefined,'meta');original.append(link('Original release / evidence',top.rel.html_url));article.append(original);
 if(top.asset.digest&&/^sha256:[a-f0-9]{64}$/.test(top.asset.digest)){const d=el('details');d.append(el('summary','APK SHA256'),el('pre',top.asset.digest.slice(7)));article.append(d);}
 if(rows.length>1){const d=el('details');d.append(el('summary',(rows.length-1)+' older releases'));for(const r of rows.slice(1)) {const p=el('p');p.append(link(r.tag.version+' · '+buildMeta(r),r.rel.html_url));d.append(p);}article.append(d);}
 root.append(article);
 }
 await microgCard(root);
 return releaseResult.error?'Partial data: patched release availability unknown.':'Patched inventory checked: '+releaseResult.rows.length+' releases. Upstream channel checked separately.';
}
function lazySection(parent,label,loader){
 const section=el('details',undefined,'inline-report'),summary=el('summary',label),content=el('div');
 section.append(summary,content);parent.append(section);
 let loaded=false,busy=false;
 async function load(){
  if(busy)return;busy=true;content.replaceChildren(el('p','Loading report…','meta'));
  try{const root=document.createDocumentFragment();await loader(root);content.replaceChildren(root);loaded=true;}
  catch(e){const retry=el('button','Retry report');retry.type='button';retry.addEventListener('click',load);content.replaceChildren(el('p','Report unavailable: '+e.message+' No success inferred.','notice'),retry);}
  finally{busy=false;}
 }
 section.addEventListener('toggle',()=>{if(section.open&&!loaded)load();});
}
function addComments(parent,report){
 if(!Number.isSafeInteger(report.number)||!Number.isSafeInteger(report.comments)||report.comments<1)return;
 lazySection(parent,'Read latest saved report comments',async root=>{
  const page=Math.max(1,Math.ceil(report.comments/100));
  let rows=await read(API+'issues/'+report.number+'/comments?per_page=100&page='+page);
  need(Array.isArray(rows),'Invalid saved-comment response');
  if(page>1&&rows.length<5){
   const earlier=await read(API+'issues/'+report.number+'/comments?per_page=100&page='+(page-1));
   need(Array.isArray(earlier),'Invalid preceding comments');rows=[...earlier,...rows];
  }
  const expected=API+'issues/'+report.number;
  need(rows.every(c=>c&&c.issue_url===expected&&safeLink(c.html_url)),'Saved report identity mismatch');
  const newest=rows.sort((a,b)=>(Date.parse(b.created_at)||0)-(Date.parse(a.created_at)||0)).slice(0,5);
  const integrity=checkCompleteness(report.body,rows);
  if(integrity.known&&!integrity.complete)root.append(el('p','Report incomplete: part(s) '+integrity.missing.join(', ')+' of '+integrity.expected+' missing, edited or not bot-authored. No status inferred from a partial report; open the issue.','notice'));
  if(integrity.known&&integrity.complete)root.append(el('p','Report completeness verified: '+integrity.expected+'/'+integrity.expected+' numbered parts present, bot-authored and unedited at this snapshot.','meta'));
  root.append(el('p','Up to five latest stored comments at the issue inventory snapshot. Reports may describe older runs and are not trusted change instructions.','meta'));
  if(!newest.length)root.append(el('p','No comments returned; refresh to recheck.'));
  for(const c of newest){const item=el('section',undefined,'saved-report');item.append(el('h4','Report saved '+when(c.created_at)),markdown(c.body,{chars:49152,lines:2000}));root.append(item);}
 });
}
// Builds and Watch read one file, status.json, written by "Status page data" after every run
// (W4, 8 Oct 2026): short rows, grouped, newest first, capped lists, and the data's own age.
const STATUS=RAW.replace('/main/','/status/')+'status.json';
const BAD_RUN=new Set(['failure','timed_out','startup_failure','action_required','cancelled']);
const STALE_DAYS=14,STALE_DATA_HOURS=26;
const BUILD_FLOWS=['1. Manual Patch','2. Check new patch','9. Batch Patch'];
const WATCH_FLOWS=['6. Provider watch','7. Nightly watch','8. Community watch','Tooling watch'];
const WATCH=[['agent-watch.yml','6. Provider watch','provider watch:'],['community-watch.yml','8. Community watch','community: index changed for apps you build'],['watch.yml','7. Nightly watch','watch: repo and provider status']];
function daysOld(v){const t=Date.parse(v);return Number.isFinite(t)?Math.max(0,Math.floor((Date.now()-t)/86400000)):null;}
// W6: a build run whose only failures are app jobs is keyed by app; the app row carries it.
function unresolved(row){return !!row&&BAD_RUN.has(row.result)&&!row.per_app;}
function isOld(row){const d=daysOld(row&&row.when);return !!row&&BAD_RUN.has(row.result)&&d!==null&&d>STALE_DAYS;}
function pill(row){
 const code=row&&row.result,bad=!!row&&BAD_RUN.has(code);
 if(bad&&row.per_app)return el('span','Failed for '+(Array.isArray(row.apps)?row.apps.join(', '):'one app')+': see that app under Builds','pill wait');
 if(bad&&row.changed_since)return el('span','Changed since it failed: run once to confirm','pill wait');
 return el('span',row?(bad&&isOld(row)?'Failed '+daysOld(row.when)+' days ago, not fixed yet':row.words||'Unknown'):'No run yet','pill '+(bad?'bad':code==='success'?'ok':'wait'));
}
function runLink(text,url){return safeLink(url)?link(text,url):el('span','','meta');}
async function readStatus(){
 const d=await read(STATUS,30000);
 need(d&&d.schema===1&&Array.isArray(d.apps)&&Array.isArray(d.workflows)&&date(d.generated_at),'Status data is missing or in an unknown format');
 return d;
}
function freshness(root,d){
 const hours=(Date.now()-Date.parse(d.generated_at))/3600000;
 const p=el('p',hours>STALE_DATA_HOURS?'Status data is '+ago(d.generated_at).replace(' ago','')+' old: "Status page data" may have stopped. Open Actions to check.':'Status data from '+ago(d.generated_at)+'.',hours>STALE_DATA_HOURS?'notice':'meta fresh');
 root.append(p);
 if(Array.isArray(d.problems)&&d.problems.length)root.append(el('p','Partly unknown: '+d.problems.length+' GitHub read(s) failed when the data was written. Unknown is not fine.','notice'));
}
function headline(d){
 // A failure stays here until a later run of the same app or workflow works; age never hides it.
 const apps=d.apps.filter(a=>unresolved(a.last_build)).map(a=>a.label);
 const flows=d.workflows.filter(w=>unresolved(w.last)).map(w=>w.name);
 if(!apps.length&&!flows.length)return el('p','Nothing is failing: the latest run of every app and automation worked.','headline ok');
 return el('p','Needs a look: '+[...apps,...flows].join(', ')+'.','headline bad');
}
function whyLines(row){
 const out=[];if(!unresolved(row))return out;
 if(row.changed_since)out.push('The workflow was changed after this failure. Run it once; a success clears this row.');
 if(row.step_plain)out.push('Stopped at: '+row.step_plain+'.');
 for(const w of (row.why||[]).slice(0,2))out.push(w);
 for(const j of (row.jobs||[]).slice(0,2)){if(j.step_plain)out.push(j.name+': stopped at '+j.step_plain+'.');for(const w of (j.why||[]).slice(0,1))out.push(w);}
 return out;
}
function statusRow(title,sub,row,url){
 const r=el('div',undefined,'status-row');
 const name=el('div',undefined,'status-name');name.append(el('strong',title));if(sub)name.append(el('small',sub));
 const state=el('div',undefined,'status-state');state.append(pill(row));if(row)state.append(el('small',ago(row.when)));
 r.append(name,state,runLink('Open',url||(row&&row.url)));
 for(const w of whyLines(row))r.append(el('div',w,'why'));
 return r;
}
function capped(parent,rows,make,first=5,label='more',pinned=()=>false){
 // Unresolved rows are never hidden behind "show more".
 first=Math.max(first,rows.filter(pinned).length);
 rows.slice(0,first).forEach(x=>parent.append(make(x)));
 if(rows.length>first){const d=el('details',undefined,'more');d.append(el('summary','Show '+(rows.length-first)+' '+label));rows.slice(first).forEach(x=>d.append(make(x)));parent.append(d);}
}
async function buildsPanel(root){
 const d=await readStatus();freshness(root,d);root.append(headline(d));
 const groups=new Map();
 for(const a of d.apps){const g=appGroup(a.id);if(!groups.has(g[0]))groups.set(g[0],{label:g[1],rows:[]});groups.get(g[0]).rows.push(a);}
 for(const [id] of [...GROUPS,['other']]){
  const g=groups.get(id);if(!g)continue;
  const box=el('section',undefined,'status-group');box.append(el('h3',g.label));
  g.rows.sort((a,b)=>(unresolved(b.last_build)-unresolved(a.last_build))||(a.label||'').localeCompare(b.label||''));
  for(const a of g.rows){const rel=a.release?a.release.version+' · released '+ago(a.release.published_at):a.release_known?'no release yet':'release unknown';box.append(statusRow(a.label,rel,a.last_build));}
  root.append(box);
 }
 const runs=[];for(const w of d.workflows)if(BUILD_FLOWS.includes(w.name))for(const r of (w.recent||[]))runs.push(Object.assign({flow:w.name},r));
 runs.sort((a,b)=>(Date.parse(b.when)||0)-(Date.parse(a.when)||0));
 const box=el('section',undefined,'status-group');box.append(el('h3','Recent build runs'));
 if(!runs.length)box.append(el('p','No build runs in the data.','meta'));
 capped(box,runs.slice(0,15),r=>statusRow(r.flow,r.event==='schedule'?'scheduled':r.event==='workflow_dispatch'?'started by hand':r.event,r),5,'older runs');
 root.append(box);
 return 'Builds: '+d.apps.length+' apps, '+Math.min(runs.length,15)+' recent runs.';
}
function savedReport(parent,file,title){
 lazySection(parent,'Read the saved report',async root=>{
  const [issues,data]=await Promise.all([read(API+'issues?state=all&per_page=100'),read(API+'actions/workflows/'+file+'/runs?per_page=1')]);
  need(Array.isArray(issues)&&Array.isArray(data.workflow_runs),'Invalid report inventory');
  const run=data.workflow_runs[0]||null;
  const report=issues.filter(x=>!x.pull_request&&typeof x.title==='string'&&(file==='agent-watch.yml'?x.title.startsWith(title):x.title===title)).sort((a,b)=>Date.parse(b.updated_at)-Date.parse(a.updated_at))[0];
  if(!report){root.append(el('p','No saved report yet.','meta'));return;}
  const binding=reportBinding(file,run,report,null);
  root.append(el('p',binding.state==='joined'?'This report belongs to the latest run.':'This report may describe an older run.','meta'));
  root.append(markdown(report.body,{chars:49152,lines:2000}));
  if(typeof report.body==='string'&&/report mode=full fail=1\b/.test(report.body))root.append(el('p','The report says fail=1: something in it failed.','notice'));
  const p=el('p');p.append(link('Open the report issue',report.html_url));root.append(p);addComments(root,report);
 });
}
async function watchPanel(root){
 const d=await readStatus();freshness(root,d);root.append(headline(d));
 const sections=[['Watchers','Look for new patches, tools and community changes. They never build.',w=>WATCH_FLOWS.includes(w.name)],
  ['Checks and housekeeping','Repository checks, this page, failure issues and helpers.',w=>!WATCH_FLOWS.includes(w.name)&&!BUILD_FLOWS.includes(w.name)]];
 for(const [label,sub,pick] of sections){
  const box=el('section',undefined,'status-group');box.append(el('h3',label),el('p',sub,'meta'));
  const rows=d.workflows.filter(pick).sort((a,b)=>{const x=unresolved(a.last),y=unresolved(b.last);return (y-x)||(a.name||'').localeCompare(b.name||'');});
  capped(box,rows,w=>{const r=statusRow(w.name,w.purpose,w.last,w.url);const hit=WATCH.find(x=>x[1]===w.name);if(hit)savedReport(r,hit[0],hit[2]);return r;},label==='Watchers'?8:6,'more automations',w=>unresolved(w.last));
  root.append(box);
 }
 if(Array.isArray(d.issues)&&d.issues.length){const box=el('section',undefined,'status-group');box.append(el('h3','Open failure issues'));for(const i of d.issues.slice(0,8)){const p=el('p');p.append(runLink(i.title,i.url));box.append(p);}root.append(box);}
 return 'Watch: '+d.workflows.length+' automations.';
}
async function render(){
 const own=++generation;clearTimeout(pollTimer);$('status').textContent='Checking '+tab+'...';$('refresh').disabled=true;
 $('appTools').hidden=tab!=='apps';
 $('importPanel').hidden=tab!=='apps';
 const root=document.createDocumentFragment();
 try{const message=await ({apps:appsPanel,builds:buildsPanel,watch:watchPanel}[tab])(root);if(own!==generation)return;organizePanel(root,tab);$('panel').replaceChildren(root);$('status').textContent=message;filterApps();}
 catch(e){if(own!==generation)return;$('panel').replaceChildren(el('p',e.message,'notice'));$('status').textContent='Data unavailable. No success or empty coverage inferred.';}
 finally{if(own===generation){$('refresh').disabled=false;schedulePoll();}}
}
function schedulePoll(){
 clearTimeout(pollTimer);
 if(!document.hidden)pollTimer=setTimeout(()=>{
  if(document.hidden)return;
  if($('panel').querySelector('.inline-report[open]'))schedulePoll();
  else render();
 },120000);
}
function organizePanel(root,activeTab){
 $('appTools').hidden=activeTab!=='apps';
 const articles=Array.from(root.querySelectorAll('article'));
 if(activeTab!=='apps'){
  for(const article of articles)article.classList.add('result-card');
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
   monogram.setAttribute('aria-hidden','true');
   if(LOGOS.has(id)||id==='microg'){const logo=el('img',undefined,'app-logo');logo.src=id==='microg'?'assets/microg.png':'assets/logos/'+id+'.png';logo.alt='';logo.width=40;logo.height=40;logo.decoding='async';logo.addEventListener('error',()=>{logo.remove();monogram.classList.remove('has-logo');});monogram.textContent='';monogram.classList.add('has-logo');monogram.append(logo);}
   heading.prepend(monogram);
  }
  const version=Array.from(article.children).find(n=>n.tagName==='P'&&!n.classList.contains('meta')&&!n.classList.contains('channel-status'));
  if(version)version.classList.add('app-version');
  // Keep the main download action visible; detailed provenance/history goes under one disclosure.
  const extra=Array.from(article.children).filter(n=>n.matches('p.meta:not(.release-facts),details'));
  if(extra.length){
   const details=el('details',undefined,'app-details');details.append(el('summary','Evidence, notes & older versions'));
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
  const age=Date.now()-Date.parse(card.dataset.published||'');
  card.hidden=!(card.dataset.search.includes(appQuery)&&(appCategory==='all'||card.dataset.category===appCategory)&&
   (appType==='all'||card.dataset.type===appType)&&(appAge==='all'||Number.isFinite(age)&&age>=0&&age<=Number(appAge)*86400000));
  if(!card.hidden)shown++;
 }
 for(const group of $('panel').querySelectorAll('.app-group')){
  const count=Array.from(group.querySelectorAll('.app-card')).filter(c=>!c.hidden).length;
  group.hidden=count===0;group.querySelector('.group-count').textContent=count+' app'+(count===1?'':'s');
  const grid=group.querySelector('.app-grid'),cards=Array.from(grid.children);
  cards.sort((a,b)=>appSort==='date'?((Date.parse(b.dataset.published)||0)-(Date.parse(a.dataset.published)||0)):
   (a.querySelector('h3')?.textContent||'').localeCompare(b.querySelector('h3')?.textContent||''));
  for(const card of cards)grid.append(card);
  if(appQuery||appCategory!=='all')group.open=true;
 }
 if($('noApps'))$('noApps').hidden=shown!==0;
 $('appCount').textContent=shown+' app'+(shown===1?'':'s');
}
// Expose pure contracts only for tests; no credentials, write endpoints or remote-script execution.
window.PFPortal={parseTag,validateImport,validateMicroG,validateObtainium,microgConfig,microgRelease,microgLatest,microgName,validateTargets,releaseRows,safeLink,selectApps,appGroup,plain,noteText,changeSummary,reportIdentity,reportBinding,checkCompleteness};
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
for(const [id,label,options,update] of [
 ['appType','Filter source type',[['all','All sources'],['patched','Patched apps'],['upstream','Upstream']],v=>appType=v],
 ['appAge','Filter publication date',[['all','Any date'],['7','Last 7 days'],['30','Last 30 days'],['90','Last 90 days']],v=>appAge=v],
 ['appSort','Sort apps',[['name','Name A to Z'],['date','Recently published']],v=>appSort=v]]){
 const select=el('select');select.id=id;select.setAttribute('aria-label',label);
 for(const [value,text] of options){const o=el('option',text);o.value=value;select.append(o);}
 select.addEventListener('change',()=>{update(select.value);filterApps();});count.before(select);
}
// The static page lists the same two public choices; no personal presets.
const customField=el('fieldset');customField.id='customApps';customField.hidden=true;customField.style.cssText='margin:16px 0;border:1px solid var(--rule);border-radius:8px;min-width:0';
$('importMessage').before(customField);
$('prepareImport').addEventListener('click',prepareImport);$('pack').addEventListener('change',()=>{
 resetImport();$('prepareImport').disabled=false;$('includeMicrog').parentElement.hidden=$('pack').value==='custom';
});
$('microgChannel').addEventListener('change',()=>changeMicrogChannel($('microgChannel').value));
$('microgArch').addEventListener('change',()=>{need(['auto','universal','arm64-v8a','armeabi-v7a'].includes($('microgArch').value),'Unknown architecture');microgArch=$('microgArch').value;resetImport();$('prepareImport').disabled=false;});
$('microgIcon').addEventListener('change',()=>{need(['icon','noicon'].includes($('microgIcon').value),'Unknown icon choice');microgIcon=$('microgIcon').value;resetImport();$('prepareImport').disabled=false;});
$('includeMicrog').addEventListener('change',()=>{resetImport();$('prepareImport').disabled=false;});
$('collapseImport').addEventListener('click',()=>{$('importPanel').open=false;$('importPanel').querySelector('summary').focus();});
$('resetChoices').addEventListener('click',()=>{
 resetImport();$('pack').value='all';$('includeMicrog').checked=true;$('includeObtainium').checked=false;$('includeMicrog').parentElement.hidden=false;
 $('microgChannel').value='stable';microgChannel='stable';$('microgArch').value='universal';microgArch='universal';$('microgIcon').value='icon';microgIcon='icon';$('prepareImport').disabled=false;
 $('importMessage').textContent='Page choices reset. No tracked or installed apps were changed.';
 if(tab==='apps')render();
});
$('refresh').addEventListener('click',()=>{cache.clear();targets=null;render();});
function selectTab(name){tab=name;for(const x of document.querySelectorAll('[data-tab]'))x.setAttribute('aria-selected',String(x.dataset.tab===name));}
for(const b of document.querySelectorAll('[data-tab]'))b.addEventListener('click',()=>{selectTab(b.dataset.tab);history.replaceState(null,'',tab==='apps'?location.pathname:'#'+tab);render();});
if(['builds','watch'].includes(location.hash.slice(1)))selectTab(location.hash.slice(1));
document.addEventListener('visibilitychange',()=>{clearTimeout(pollTimer);if(!document.hidden)render();});
render();
})();
