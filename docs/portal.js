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
let microgChannel='stable',microgArch='universal';
const GROUPS=[
 ['media','Watch & listen',['youtube','primevideo','hotstar','mxplayer']],
 ['social','Social & communities',['instagram','facebook','reddit','telegram']],
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
 const u=new URL(url);need(!u.username&&!u.password&&!u.port&&(
 u.origin==='https://api.github.com'&&u.pathname.startsWith('/repos/'+REPO+'/')||
 u.origin==='https://raw.githubusercontent.com'&&u.pathname.startsWith('/'+REPO+'/main/')||
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
 const packageId=({youtube:'app.morphe.android.youtube',photos:'app.morphe.android.apps.photos'})[target.id]||target.package;
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
 const s=JSON.parse(app.additionalSettings),expected={includePrereleases:false,fallbackToOlderReleases:false,filterReleaseTitlesByRegEx:'^v?[0-9]+([.][0-9]+)*$',apkFilterRegEx:'^microg-[0-9]+([.][0-9]+)*(?:-arm64-v8a|-armeabi-v7a)?[.]apk$',versionExtractionRegEx:'^v?([0-9]+(?:[.][0-9]+)*)$',matchGroupToUse:'1',autoApkFilterByArch:false,trackOnly:false,appName:'Morphe MicroG RE'};
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
function microgConfig(data,channel,arch='auto'){
 need(['stable','prerelease'].includes(channel),'Unknown MicroG channel');
 need(['auto','universal','arm64-v8a','armeabi-v7a'].includes(arch),'Unknown MicroG architecture');
 const app=JSON.parse(JSON.stringify(validateMicroG(data)[0]));
 if(channel==='prerelease'){
  const s=JSON.parse(app.additionalSettings);
  s.includePrereleases=true;
  s.filterReleaseTitlesByRegEx='^v?[0-9]+([.][0-9]+)*(-dev[.][0-9]+)?$';
  s.apkFilterRegEx='^microg-[0-9]+([.][0-9]+)*(-dev[.][0-9]+)?(?:-arm64-v8a|-armeabi-v7a)?[.]apk$';
  s.versionExtractionRegEx='^v?([0-9]+(?:[.][0-9]+)*(?:-dev[.][0-9]+)?)$';
  app.additionalSettings=JSON.stringify(s);
 }
 if(arch!=='auto'){
  const s=JSON.parse(app.additionalSettings),version=channel==='stable'?'[0-9]+([.][0-9]+)*':'[0-9]+([.][0-9]+)*(-dev[.][0-9]+)?';
  s.apkFilterRegEx='^microg-'+version+(arch==='universal'?'[.]apk$':'-'+arch+'[.]apk$');
  s.autoApkFilterByArch=false;app.additionalSettings=JSON.stringify(s);
 }else{
  const s=JSON.parse(app.additionalSettings);s.autoApkFilterByArch=true;app.additionalSettings=JSON.stringify(s);
 }
 return app;
}
function microgRelease(rows,channel,arch='auto'){
 need(['stable','prerelease'].includes(channel),'Unknown upstream channel');
 need(['auto','universal','arm64-v8a','armeabi-v7a'].includes(arch),'Unknown architecture');
 need(Array.isArray(rows)&&rows.length<=100,'Invalid upstream release inventory');
 const candidates=rows.filter(r=>r&&!r.draft&&(channel==='prerelease'||r.prerelease===false));
 candidates.sort((a,b)=>(Date.parse(b.published_at)||0)-(Date.parse(a.published_at)||0));
 need(candidates.length>0,'No eligible upstream release in this 100-release window');
 const r=candidates[0],tag=r.tag_name;
 const pattern=channel==='stable'?/^v?[0-9]+(?:[.][0-9]+)*$/:/^v?[0-9]+(?:[.][0-9]+)*(?:-dev[.][0-9]+)?$/;
 need(typeof tag==='string'&&pattern.test(tag)&&date(r.published_at),'Unsupported upstream release identity; inspect upstream instead');
 const version=tag.replace(/^v/,''),name='microg-'+version+(arch==='auto'||arch==='universal'?'':'-'+arch)+'.apk';
 need(r.html_url===MICROG_WEB+'/releases/tag/'+encodeURIComponent(tag),'Upstream release URL mismatch');
 const assets=Array.isArray(r.assets)?r.assets.filter(a=>a&&a.name===name):[];
 need(assets.length===1,(arch==='auto'||arch==='universal'?'Standard universal upstream APK':'Requested '+arch+' upstream APK')+' missing or ambiguous; no variant fallback');
 const a=assets[0];
 need(a.state==='uploaded'&&Number.isSafeInteger(a.size)&&a.size>1000000&&a.browser_download_url===MICROG_WEB+'/releases/download/'+encodeURIComponent(tag)+'/'+encodeURIComponent(name),'Upstream APK identity mismatch');
 return {rel:r,asset:a,version};
}
async function microgCard(root){
 const article=el('article');article.dataset.target='microg';article.dataset.type='upstream';
 const heading=el('div',undefined,'app-title');heading.append(el('h3','Morphe MicroG RE'),el('span','Upstream','badge'));article.append(heading);
 article.append(el('p','Direct from MorpheApp. Not patched or re-signed here.','meta'));
 const channelLabel=el('label','Download channel: '),channelSelect=el('select');
 channelSelect.id='microgCardChannel';channelSelect.setAttribute('aria-label','MicroG download channel');
 for(const [value,text] of [['stable','Stable only'],['prerelease','Stable + dev prereleases']]){
  const option=el('option',text);option.value=value;channelSelect.append(option);
 }
 channelSelect.value=microgChannel;channelLabel.append(channelSelect);article.append(channelLabel);
 channelSelect.addEventListener('change',async()=>{
  await changeMicrogChannel(channelSelect.value);
  $('microgCardChannel')?.focus({preventScroll:true});
 });
 const channelStatus=el('p','Selected: '+(microgChannel==='stable'?'Stable only':'Stable + dev prereleases')+'. Applies to this page; tracked apps are unchanged.','channel-status');
 channelStatus.setAttribute('role','status');article.append(channelStatus);
 try{
  const row=microgRelease(await read(MICROG_API+'?per_page=100'),microgChannel,microgArch);
  article.dataset.published=row.rel.published_at;
  article.append(el('p',row.version),el('p',(row.rel.prerelease?'Prerelease':'Stable')+' · '+Math.round(row.asset.size/1048576)+' MB · '+when(row.rel.published_at),'meta'));
  const actions=el('div',undefined,'actions');
  for(const [text,url] of [['Download upstream APK',row.asset.browser_download_url],['Release details',row.rel.html_url]]){
   const a=el('a',text,'button');a.href=url;a.target='_blank';a.rel='noopener noreferrer';actions.append(a);
  }
  article.append(actions);
  releaseNotes(article,row.rel.body,['Upstream release notes from MorpheApp. This companion is not built by Patch Factory.']);
 }catch(e){article.append(el('p','Upstream unavailable: '+e.message,'notice'));}
 const details=el('details');details.append(el('summary','Channel & installation notes'),
 el('p',"The card and Obtainium toolbar share one channel and architecture choice. Stable + dev prereleases can show the same version when stable is newest. Universal is the default; Auto uses Obtainium's filename-based CPU filter, and exact ARM64/ARMv7 choices never fall back to another CPU file."),
 el('p','Keep existing MicroG data. Installed signer compatibility is not checked here; never uninstall or bypass Android checks to force an update.'));
 article.append(details);root.append(article);
 const channelButton=el('button','Open Obtainium import settings');channelButton.type='button';
 channelButton.addEventListener('click',()=>{$('importPanel').open=true;$('microgChannel').focus();$('importPanel').scrollIntoView({block:'center'});});
 article.append(channelButton);
}
async function changeMicrogChannel(value){
 need(['stable','prerelease'].includes(value),'Unknown MicroG channel');
 microgChannel=value;$('microgChannel').value=value;
 resetImport();$('prepareImport').disabled=false;
 $('importMessage').textContent='MicroG channel changed for this page. Prepare a new import and confirm in Obtainium to update tracking; installed apps are unchanged.';
 if(tab==='apps')await render();
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
 if(apps.some(app=>app.id==='app.revanced.android.gms'))$('importMessage').textContent+=' Includes MicroG directly from upstream ('+(microgChannel==='stable'?'stable only':'stable + dev prereleases')+'). Existing tracked settings may change; installed signer compatibility is unverified.';
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
 const microg=wantMicrog?microgConfig(companion,microgChannel,microgArch):null;const self=wantSelf?validateObtainium(selfPack)[0]:null;
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
function markdown(body){
 const box=el('div',undefined,'release-copy'),text=noteText(body),limited=text.slice(0,24000);
 if(!text){box.append(el('p','No release notes were recorded. Changes are unknown, not “nothing changed”.','meta'));return box;}
 let list=null,table=null,code=null;
 for(const line of limited.split('\n').slice(0,400)){
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
 if(text.length>24000||limited.split('\n').length>400)box.append(el('p','Long notes shortened here; the exact release has the full text.','notice'));
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
 const details=el('details',undefined,'release-notes');details.append(el('summary','Read release notes here'),markdown(body));
 article.append(overview,details);
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
async function buildsPanel(root){
 root.append(el('p','Builds make APKs. Read target results and failed steps here; a successful workflow alone does not prove a published download. Test artifacts may require GitHub sign-in.','notice'));
 const runs=[],failures=[];
 await Promise.all(['ci.yml','batch-patch.yml','manual-patch.yml'].map(async workflow=>{
  try{
   const data=await read(API+'actions/workflows/'+workflow+'/runs?per_page=10');need(Array.isArray(data.workflow_runs),'Invalid workflow results');
   for(const r of data.workflow_runs){need(r&&Number.isSafeInteger(r.id)&&r.path==='.github/workflows/'+workflow&&safeLink(r.html_url,'run'),'Invalid app-build run');}
   runs.push(...data.workflow_runs);
  }catch(e){failures.push(workflow+': '+e.message);}
 }));
 runs.sort((a,b)=>(Date.parse(b.created_at)||0)-(Date.parse(a.created_at)||0));
 for(const failure of failures)root.append(el('p',failure,'notice'));
 for(const r of runs){const a=el('article');a.append(el('h3',r.display_title||r.name),el('p',(r.status==='completed'?(r.conclusion||'Unknown result'):r.status)+' · '+when(r.created_at),'meta'),
 el('p','Branch '+r.head_branch+' · commit '+String(r.head_sha).slice(0,8),'meta'));
 addJobs(a,r);
 a.append(link('Exact run / downloadable test artifacts',r.html_url,'run'));root.append(a);}
 if(!runs.length)root.append(el('p',failures.length?'Build inventory unavailable or incomplete, not proof of no builds.':'No visible runs in these workflow windows. Open GitHub for older builds.'));
 return failures.length?'Build inventory incomplete: '+failures.length+' workflow read(s) failed. Available runs remain visible.':'Up to 10 runs per app-build workflow. Unrelated validations cannot crowd this window out.';
}
const WATCH=[['agent-watch.yml','Provider Watch','provider watch:'],['community-watch.yml','Community Watch','community: index changed for apps you build'],['watch.yml','Nightly Watch','watch: repo and provider status']];
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
function addJobs(parent,run){
 lazySection(parent,'Show job results and failed steps',async root=>{
  need(Number.isSafeInteger(run.id)&&Number.isSafeInteger(run.run_attempt)&&run.run_attempt>0,'Invalid run identity');
  const jobs=await pages('actions/runs/'+run.id+'/attempts/'+run.run_attempt+'/jobs','jobs',10);
  need(jobs.every(j=>Number.isSafeInteger(j.id)&&j.id>0&&j.run_id===run.id&&j.run_attempt===run.run_attempt&&j.head_sha===run.head_sha&&j.html_url===WEB+'/actions/runs/'+run.id+'/job/'+j.id),'Job/run identity changed; refresh the page');
  if(!jobs.length){root.append(el('p','No jobs visible yet. This is not a passed build.'));return;}
  const summary=jobSummary(jobs);
  root.append(el('p',summary.text,'job-summary'));
  if(run.conclusion==='failure'&&summary.succeeded>0)root.append(el('p','Mixed result: the red workflow does not mean every app failed. Successful releases may exist; baseline qualification currently requires the whole source run to succeed.','notice'));
  const wrap=el('div',undefined,'table-scroll'),table=el('table'),header=el('tr');
  for(const title of ['Job / target','Role','Result','Failed or incomplete steps'])header.append(el('th',title));
  table.append(header);
  for(const job of jobs){
   const row=el('tr'),steps=Array.isArray(job.steps)?job.steps:[];
   const title=el('td');title.append(link(job.name||'Unnamed job',job.html_url,'run'));
   row.append(title,el('td',jobRole(job.name)),el('td',job.conclusion||job.status||'Unknown'));
   const bad=steps.filter(s=>s.status!=='completed'||!['success','skipped'].includes(s.conclusion));
   row.append(el('td',bad.length?bad.map(s=>s.name+': '+(s.conclusion||s.status||'Unknown')).join('; '):steps.length?'No failed steps reported; skipped steps may exist.':'Step detail unavailable.'));
   table.append(row);
  }
  wrap.append(table);root.append(wrap,el('p','Exact run attempt '+run.run_attempt+'. Dependency checks are not APK builds. “Patch apk” includes source download: open that job for the actual error. Job success is not publication or Android-installation proof.','meta'));
 });
}
function jobRole(name){
 if(typeof name!=='string')return 'Other / unknown';
 if(/^Resolve shadow dependencies \([a-z0-9-]+\)$/.test(name))return 'Dependencies only';
 if(/^(?:.* \/ )?Patch [a-z0-9-]+$/.test(name))return 'App build';
 if(name==='Plan')return 'Build selection';
 return 'Other / unknown';
}
function jobSummary(jobs){
 need(Array.isArray(jobs),'Invalid job inventory');
 const builds=jobs.filter(j=>jobRole(j.name)==='App build');
 const succeeded=builds.filter(j=>j.status==='completed'&&j.conclusion==='success').length;
 const failed=builds.filter(j=>j.status==='completed'&&['failure','timed_out','startup_failure','action_required'].includes(j.conclusion)).length;
 const other=builds.length-succeeded-failed,dependencies=jobs.filter(j=>jobRole(j.name)==='Dependencies only').length;
 return {succeeded,failed,other,dependencies,text:'App-build jobs: '+builds.length+' · succeeded '+succeeded+' · failed '+failed+' · other/pending '+other+'. Dependency-only jobs: '+dependencies+'. Complete job inventory: '+jobs.length+'.'};
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
  root.append(el('p','Up to five latest stored comments at the issue inventory snapshot. Reports may describe older runs and are not trusted change instructions.','meta'));
  if(!newest.length)root.append(el('p','No comments returned; refresh to recheck.'));
  for(const c of newest){const item=el('section',undefined,'saved-report');item.append(el('h4','Report saved '+when(c.created_at)),markdown(c.body));root.append(item);}
 });
}
async function watchPanel(root){
 let issues=[],failedReads=0;
 root.append(el('p','Watch checks providers, community updates and repository health; it does not build or install apps. Saved reports appear here, but coverage remains partial.','notice'));
 try{issues=await pages('issues?state=all');}
 catch(e){failedReads++;root.append(el('p','Saved findings unavailable: '+e.message+' Workflow status is checked separately.','notice'));}
 for(const [workflow,label,title] of WATCH){const a=el('article');a.append(el('h3',label),el('p',({'agent-watch.yml':'Checks configured patch providers for changes.','community-watch.yml':'Looks for community updates relevant to configured apps.','watch.yml':'Checks repository, selection names and provider status.'})[workflow]));root.append(a);
 try{const data=await read(API+'actions/workflows/'+workflow+'/runs?per_page=1');need(Array.isArray(data.workflow_runs),'Invalid watcher run response');const run=data.workflow_runs[0];
 if(run){need(run.path==='.github/workflows/'+workflow&&safeLink(run.html_url,'run'),'Unexpected watcher identity');a.append(el('p','Workflow: '+(run.conclusion||run.status)+' · '+when(run.created_at),'meta'));addJobs(a,run);a.append(link('Exact watcher run / full artifacts',run.html_url,'run'));}
 else a.append(el('p','No visible watcher runs.','meta'));
 }catch(e){failedReads++;a.append(el('p','Workflow read unavailable: '+e.message,'notice'));}
 const reports=issues.filter(x=>!x.pull_request&&typeof x.title==='string'&&(workflow==='agent-watch.yml'?x.title.startsWith(title):x.title===title)).sort((a,b)=>Date.parse(b.updated_at)-Date.parse(a.updated_at));
 const report=reports[0];if(report){a.append(link('Saved findings / comments',report.html_url),el('p','Issue updated '+when(report.updated_at)+'; may summarize an older run.','meta'));
 const d=el('details',undefined,'inline-report');d.append(el('summary','Read saved report here'),markdown(report.body));a.append(d);addComments(a,report);
 const failures=typeof report.body==='string'&&/report mode=full fail=1\b/.test(report.body);if(failures)a.append(el('p','Stored report declares fail=1. A green workflow is not a healthy report.','notice'));
 }else a.append(el('p','No saved issue found. Inspect run logs; absent findings are not an all-clear.','meta'));
 a.append(el('p','Coverage: legacy / partial. This page does not infer a verified delta from issue text or consume expiring JSON as durable baseline state.','meta'));
 }
 return failedReads?'Watcher inventory incomplete: '+failedReads+' workflow read(s) failed. No all-clear.':'Watcher runs and saved issues loaded. Findings coverage remains explicitly partial.';
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
  if($('panel').querySelector('.inline-report[open],.release-notes[open]'))schedulePoll();
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
   monogram.setAttribute('aria-hidden','true');heading.prepend(monogram);
  }
  const version=Array.from(article.children).find(n=>n.tagName==='P'&&!n.classList.contains('meta')&&!n.classList.contains('channel-status'));
  if(version)version.classList.add('app-version');
  // Keep the main download action visible; detailed provenance/history goes under one disclosure.
  const extra=Array.from(article.children).filter(n=>n.matches('p.meta:not(.release-facts),details:not(.release-notes)'));
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
window.PFPortal={parseTag,validateImport,validateMicroG,validateObtainium,microgConfig,microgRelease,validateTargets,releaseRows,safeLink,selectApps,appGroup,plain,noteText,changeSummary};
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
$('microgArch').addEventListener('change',()=>{need(['auto','universal','arm64-v8a','armeabi-v7a'].includes($('microgArch').value),'Unknown architecture');microgArch=$('microgArch').value;resetImport();$('prepareImport').disabled=false;if(tab==='apps')render();});
$('includeMicrog').addEventListener('change',()=>{resetImport();$('prepareImport').disabled=false;});
$('collapseImport').addEventListener('click',()=>{$('importPanel').open=false;$('importPanel').querySelector('summary').focus();});
$('resetChoices').addEventListener('click',()=>{
 resetImport();$('pack').value='all';$('includeMicrog').checked=false;$('includeObtainium').checked=false;$('includeMicrog').parentElement.hidden=false;
 $('microgChannel').value='stable';microgChannel='stable';$('microgArch').value='universal';microgArch='universal';$('prepareImport').disabled=false;
 $('importMessage').textContent='Page choices reset. No tracked or installed apps were changed.';
 if(tab==='apps')render();
});
$('refresh').addEventListener('click',()=>{cache.clear();targets=null;render();});
for(const b of document.querySelectorAll('[data-tab]'))b.addEventListener('click',()=>{tab=b.dataset.tab;for(const x of document.querySelectorAll('[data-tab]'))x.setAttribute('aria-selected',String(x===b));render();});
document.addEventListener('visibilitychange',()=>{clearTimeout(pollTimer);if(!document.hidden)render();});
render();
})();
