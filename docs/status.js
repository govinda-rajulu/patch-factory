/* Patch Factory status page (packet W2, 8 Oct 2026). Reads one public JSON file written by the
   "Status page data" workflow. Read-only: no credentials, no storage, no HTML strings. */
(function () {
'use strict';
const REPO='govinda-rajulu/patch-factory';
const DATA='https://raw.githubusercontent.com/'+REPO+'/status/status.json';
const BAD=new Set(['failure','timed_out','startup_failure','action_required','cancelled']);
const $=id=>document.getElementById(id);
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined&&text!==null)n.textContent=String(text);if(cls)n.className=cls;return n;}
function safe(url){try{const u=new URL(url);return (u.protocol==='https:'&&u.hostname==='github.com'&&!u.port&&!u.username&&!u.password&&u.pathname.startsWith('/'+REPO+'/'))?u.href:null;}catch{return null;}}
function link(text,url){const s=safe(url);if(!s)return el('span','');const a=el('a',text,'button');a.href=s;a.target='_blank';a.rel='noopener noreferrer';return a;}
function ago(v){const t=Date.parse(v);if(!Number.isFinite(t))return 'time unknown';const m=Math.round((Date.now()-t)/60000);if(m<1)return 'just now';if(m<60)return m+' min ago';const h=Math.round(m/60);if(h<48)return h+' h ago';return Math.round(h/24)+' days ago';}
function day(v){const t=Date.parse(v);return Number.isFinite(t)?new Date(t).toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'}):'date unknown';}
function kind(code){return BAD.has(code)?'bad':code==='success'?'ok':code==='skipped'?'skip':'wait';}
function pill(words,code){return el('span',words||'Unknown','pill '+(kind(code)==='ok'?'':kind(code)));}
function appCard(a){
 const lb=a.last_build,card=el('article',undefined,'card'+(lb&&BAD.has(lb.result)?' bad':''));
 card.append(el('h3',a.label));
 const r=a.release;
 if(r){card.append(el('p',r.version+' · released '+day(r.published_at),'meta'));if(r.apk&&r.apk.url)card.append(link('Download APK',r.apk.url));if(r.url)card.append(link('Release notes',r.url));}
 else card.append(el('p',a.release_known?'No release yet.':'Release unknown (could not read the list).','meta'));
 const b=el('p');b.append(el('span','Last build: '));
 if(lb){b.append(pill(lb.words,lb.result),el('span',' '+ago(lb.when)+' ('+lb.workflow+')','meta'));}
 else b.append(el('span','none in the recent runs','meta'));
 card.append(b);
 if(lb&&BAD.has(lb.result)){
  if(lb.step_plain)card.append(el('p','Stopped at: '+lb.step_plain+'.','meta'));
  for(const w of (lb.why||[]))card.append(el('div',w,'why'));
  if(!(lb.why||[]).length)card.append(el('div','No reason line was printed; open the run.','why'));
  if(lb.url)card.append(link('Open the run',lb.url));
 }
 const lc=a.last_check;
 if(lc&&(!lb||lc.when!==lb.when))card.append(el('p','Last check: '+lc.words+' '+ago(lc.when)+'.','meta'));
 const and=r&&r.min_android?('Android '+r.min_android.version+' or newer'):a.android_cap?('Android '+a.android_cap.version+' or newer (build cap)'):'Android version unknown';
 card.append(el('p','Works on: '+a.cpu+' · '+and+(a.needs_microg?' · needs MicroG RE':''),'needs'));
 return card;
}
function workflowRow(w){
 const row=el('div',undefined,'row'),name=el('div');name.append(el('h3',w.name));if(w.url)name.append(link('Runs',w.url));
 const what=el('div');what.append(el('p',w.purpose||'No description recorded.','meta'));
 if(w.last&&w.last.jobs)for(const j of w.last.jobs){
  what.append(el('p',j.name+(j.step_plain?': stopped at '+j.step_plain:'')+'.'));
  for(const x of (j.why||[]))what.append(el('div',x,'why'));
 }
 const last=el('div');
 if(w.last){last.append(pill(w.last.words,w.last.result),el('span',' '+ago(w.last.when),'meta'));if(w.last.url)last.append(el('br'),link('Open the last run',w.last.url));}
 else last.append(el('span','No finished run recently.','meta'));
 const dots=el('div',undefined,'dots');
 for(const r of (w.recent||[])){const d=el('span',undefined,'dot '+kind(r.result));d.title=r.words+', '+ago(r.when)+(r.event?' ('+r.event+')':'');d.setAttribute('aria-label',d.title);dots.append(d);}
 last.append(dots);row.append(name,what,last);return row;
}
function render(d){
 $('updated').textContent='Updated '+ago(d.generated_at)+' ('+new Date(Date.parse(d.generated_at)).toLocaleString()+').';
 const h=$('headline');h.textContent=d.headline.text;h.className='headline'+((d.problems||[]).length?' unknown':(d.headline.apps.length||d.headline.workflows.length)?' bad':'');
 const apps=(d.apps||[]).slice().sort((a,b)=>{const x=a.last_build&&BAD.has(a.last_build.result)?0:1,y=b.last_build&&BAD.has(b.last_build.result)?0:1;return x-y||a.label.localeCompare(b.label);});
 $('apps').replaceChildren(...apps.map(appCard));
 const wfs=(d.workflows||[]).slice().sort((a,b)=>{const x=a.last&&BAD.has(a.last.result)?0:1,y=b.last&&BAD.has(b.last.result)?0:1;return x-y||a.name.localeCompare(b.name);});
 $('workflows').replaceChildren(...wfs.map(workflowRow));
 const iss=$('issues');iss.replaceChildren();
 if(!(d.issues||[]).length)iss.append(el('p','No open "Failing:" issues.'));
 for(const i of (d.issues||[])){const p=el('p');p.append(link(i.title,i.url));iss.append(p);}
 const pr=$('problems');pr.replaceChildren();
 if((d.problems||[]).length){pr.append(el('h2','Could not read'));const ul=el('ul');for(const p of d.problems)ul.append(el('li',p));pr.append(ul);}
}
async function load(){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),20000);
 try{
  const r=await fetch(DATA,{credentials:'omit',cache:'no-store',signal:ctrl.signal});
  if(r.status===404){$('headline').textContent='No status published yet. It appears after the first "Status page data" run.';$('headline').className='headline unknown';return;}
  if(!r.ok)throw new Error('HTTP '+r.status);
  const text=await r.text();if(text.length>2000000)throw new Error('status file too large');
  const d=JSON.parse(text);if(!d||d.schema!==1)throw new Error('unknown status format');
  render(d);
 }catch(e){$('headline').textContent='Status unavailable right now ('+e.message+'). Unknown, not fine.';$('headline').className='headline unknown';}
 finally{clearTimeout(timer);}
}
load();
})();
